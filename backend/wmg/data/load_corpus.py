import gc
import logging
import os
from typing import Union

import anndata
import numpy as np
import scanpy
import tiledb
from anndata._core.views import ArrayView
from scipy import sparse

from backend.wmg.data.schemas.corpus_schema import obs_labels, update_global_var, save_axes_labels
from backend.wmg.data.transform import transform_expression_raw_counts_to_rankit
from backend.wmg.data.utils import get_all_dataset_ids
from backend.wmg.data.validation import validate_corpus_load
from backend.wmg.data.wmg_constants import GENE_EXPRESSION_COUNT_MIN_THRESHOLD, included_assay_ontologies

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def is_dataset_already_loaded(corpus_path: str, dataset_id: str) -> bool:
    if dataset_id in get_all_dataset_ids(corpus_path):
        logger.info("oops, that dataset is already loaded!")
        return True
    return False


def get_dataset_id(h5ad_path: str) -> str:
    dataset_id = os.path.splitext(os.path.split(h5ad_path)[1])[0]
    if dataset_id == "local":
        dataset_id = os.path.split(os.path.split(h5ad_path)[0])[1]
    return dataset_id


def validate_dataset_properties(anndata_object: anndata.AnnData) -> bool:
    if not sparse.issparse(anndata_object.X):
        logger.warning("No dense handling yet, not loading")
        return False
    schema_version = anndata_object.uns.get("schema_version", None)
    if not schema_version:
        logger.warning("Unknown schema, not loading")
        return False
    if schema_version < "2.0.0" or schema_version >= "3.0.0":
        logger.warning("Invalid schema version, not loading")
        return False
    return True


def load_h5ad(h5ad_path: str, corpus_path: str, validate: bool):
    """
    Given the location of a h5ad dataset and a group name, check the dataset is not already loaded
    then read the dataset into the tiledb object (under group name), updating the var and feature indexes
    to avoid collisions within the larger tiledb object
    """
    logger.info(f"Loading {h5ad_path}...")
    dataset_id = get_dataset_id(h5ad_path)
    if is_dataset_already_loaded(corpus_path, dataset_id):
        return

    anndata_object = anndata.read_h5ad(h5ad_path)

    # TODO move to filter function in transform.py
    # Apply a low expression gene cell filtering.
    scanpy.pp.filter_cells(anndata_object, min_genes=GENE_EXPRESSION_COUNT_MIN_THRESHOLD)
    # remove cells that were not generated by excluded assays
    assay_ontologies = list(included_assay_ontologies.keys())
    anndata_object = anndata_object[anndata_object.obs['assay_ontology_term_id'].isin(assay_ontologies), :]

    logger.info(f"loaded: shape={anndata_object.shape}")
    if not validate_dataset_properties(anndata_object):
        return

    var_df = update_global_var(corpus_path, anndata_object.var)

    # Calculate mapping between var/feature coordinates in H5AD (file local) and TDB (global)
    global_var_index = np.zeros((anndata_object.shape[1],), dtype=np.uint32)
    var_feature_to_coord_map = {k: v for k, v in var_df[["gene_ontology_term_id", "var_idx"]].to_dict("split")["data"]}
    for idx in range(anndata_object.shape[1]):
        gene_ontology_term_id = anndata_object.var.index.values[idx]
        global_coord = var_feature_to_coord_map[gene_ontology_term_id]
        global_var_index[idx] = global_coord

    obs = anndata_object.obs
    obs["dataset_id"] = dataset_id
    first_obs_idx = save_axes_labels(obs, f"{corpus_path}/obs", obs_labels)
    transform_expression_raw_counts_to_rankit(anndata_object, corpus_path, global_var_index, first_obs_idx)

    if validate:
        validate_corpus_load(anndata_object, corpus_path, dataset_id)


def save_X(anndata_object: anndata.AnnData, group_name: str, global_var_index: np.ndarray, first_obs_idx: int):
    """
    Save (pre)normalized expression counts to the tiledb corpus object
    """
    array_name = f"{group_name}/X"
    expression_matrix = anndata_object.X
    logger.debug(f"saving {array_name}...\n")
    stride = max(int(np.power(10, np.around(np.log10(1e9 / expression_matrix.shape[1])))), 10_000)
    with tiledb.open(array_name, mode="w") as array:
        for start in range(0, expression_matrix.shape[0], stride):
            end = min(start + stride, expression_matrix.shape[0])
            sparse_expression_matrix = sparse.coo_matrix(expression_matrix[start:end, :])
            rows = sparse_expression_matrix.row + start + first_obs_idx
            cols = global_var_index[sparse_expression_matrix.col]
            data = sparse_expression_matrix.data

            array[rows, cols] = data
            del sparse_expression_matrix, rows, cols, data
            gc.collect()

    logger.debug(f"Saved {group_name}.")


def get_X_raw(anndata_object: anndata.AnnData) -> Union[np.ndarray, sparse.spmatrix, ArrayView]:
    """
    Current rules for our curated H5ADs:
    * if there is a .raw, it is the raw counts, and .X is transformed/normalized (by author) or is == to .raw.X
    * if there is no .raw, ad.X contains the raw counts
    """
    raw_expression_matrix = getattr(anndata_object.raw, "X", None)
    return raw_expression_matrix if raw_expression_matrix is not None else anndata_object.X
