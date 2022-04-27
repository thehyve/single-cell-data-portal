import logging
from typing import List

import numpy as np
import pandas as pd
import tiledb

from backend.wmg.data.schemas.corpus_schema import var_labels, obs_labels, OBS_ARRAY_NAME, VAR_ARRAY_NAME

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_h5ad(corpus_path: str, anndata_object: pd.DataFrame, dataset_id: str) -> (int, np.ndarray):
    var_df = update_corpus_var(corpus_path, anndata_object)

    # Calculate mapping between var/feature coordinates in H5AD (file local) and TDB (global)
    # todo use gene_ontology_id as var_idx
    global_var_index = np.zeros((anndata_object.shape[1],), dtype=np.uint32)
    var_feature_to_coord_map = {k: v for k, v in var_df[["gene_ontology_term_id", "var_idx"]].to_dict("split")["data"]}
    for idx in range(anndata_object.shape[1]):
        gene_ontology_term_id = anndata_object.var.index.values[idx]
        global_coord = var_feature_to_coord_map[gene_ontology_term_id]
        global_var_index[idx] = global_coord

    first_obs_idx = update_corpus_obs(corpus_path, anndata_object, dataset_id)
    return first_obs_idx, global_var_index


def update_corpus_axis(df: pd.DataFrame, array_name: str, label_info: List) -> int:
    """
    Safely add given dataframe to extend the specified array with the appropriate encoding
    typically used to update integrated_corpus obs/var frames for each new dataset

    """
    logger.info(f"Saving {array_name}...\n")

    with tiledb.open(array_name) as array:
        starting_join_index = array.meta.get("next_join_index", 0)

    with tiledb.open(array_name, mode="w") as array:
        data = {}
        coords = []
        for lbl in label_info:
            datum = lbl.decode(df, starting_join_index)
            if lbl.encode_as_dim:
                coords.append(datum)
            else:
                data[lbl.key] = datum
        array[tuple(coords)] = data
        array.meta["next_join_index"] = starting_join_index + len(coords[0])

    logger.info("saved.")
    return starting_join_index


def update_corpus_obs(corpus_path: str, anndata_object: pd.DataFrame, dataset_id: str) -> int:
    """
    Add the dataset_id to the obs dataframe and
    update the Corpus obs by adding the anndata_object
    Returns an int representing the starting index for this dataset's obs in the corpus df
    """
    obs_array_path = f"{corpus_path}/{OBS_ARRAY_NAME}"
    obs = anndata_object.obs
    obs["dataset_id"] = dataset_id
    return update_corpus_axis(obs, obs_array_path, obs_labels)


def update_corpus_var(corpus_path: str, anndata_object: pd.DataFrame) -> pd.DataFrame:
    """
    Update the global var (gene) array. Adds any gene_ids we have not seen before.
    Returns the global var array as dataframe
    """

    var_array_path = f"{corpus_path}/{VAR_ARRAY_NAME}"
    addit_var = anndata_object.var
    with tiledb.open(var_array_path, "r") as var:
        var_df = var.df[:]
        missing_var = set(addit_var.index.to_numpy(dtype=str)) - set(
            var_df["gene_ontology_term_id"].to_numpy(dtype=str)
        )

    if len(missing_var) > 0:
        logger.info(f"Adding {len(missing_var)} gene records...")
        missing_var_df = addit_var[addit_var.index.isin(missing_var)]
        update_corpus_axis(missing_var_df, var_array_path, var_labels)

    with tiledb.open(var_array_path, "r") as var:
        var_df = var.df[:]
        var_df.index = var_df.gene_ontology_term_id

    logger.info(f"Global var index length: {var_df.shape}")
    return var_df


def create