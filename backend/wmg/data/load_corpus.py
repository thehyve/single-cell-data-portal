import gc
import logging
import os
from typing import List, Union

import anndata
import numpy
import numpy as np
import pandas as pd
import tiledb
from anndata._core.views import ArrayView
from scipy import sparse
import scanpy
from scipy.sparse import coo_matrix, csr_matrix

from backend.wmg.data.rankit import rankit
from backend.wmg.data.schemas.corpus_schema import var_labels, obs_labels, INTEGRATED_ARRAY_NAME
from backend.wmg.data.utils import get_all_dataset_ids
from backend.wmg.data.validation import validate_corpus_load

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Minimum number of expressed genes for a cell to be included in the corpus.
# See the following document for further details:
# https://github.com/chanzuckerberg/cellxgene-documentation/blob/main/scExpression/scExpression-documentation.md#removal-of-low-coverage-cells
GENE_EXPRESSION_COUNT_MIN_THRESHOLD = 500

# Minimum value for raw expression counts that will be used to filter out computed RankIt values. Details:
# https://github.com/chanzuckerberg/cellxgene-documentation/blob/main/scExpression/scExpression-documentation.md#removal-of-noisy-ultra-low-expression-values
RANKIT_RAW_EXPR_COUNT_FILTERING_MIN_THRESHOLD = 3


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

    # Apply a low expression gene cell filtering.
    scanpy.pp.filter_cells(anndata_object, min_genes=GENE_EXPRESSION_COUNT_MIN_THRESHOLD)

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
    transform_dataset_raw_counts_to_rankit(anndata_object, corpus_path, global_var_index, first_obs_idx)
    # TODO: Remove this is we don't use output TileDB arrays
    # save_X(anndata_object, group_name, global_var_index, first_obs_idx)

    if validate:
        validate_corpus_load(anndata_object, corpus_path, dataset_id)


def update_global_var(corpus_path: str, src_var_df: pd.DataFrame) -> pd.DataFrame:
    """
    Update the global var (gene) array. Adds any gene_ids we have not seen before.
    Returns the global var array as dataframe
    """

    var_array_name = f"{corpus_path}/var"
    with tiledb.open(var_array_name, "r") as var:
        var_df = var.df[:]
        missing_var = set(src_var_df.index.to_numpy(dtype=str)) - set(
            var_df["gene_ontology_term_id"].to_numpy(dtype=str)
        )

    if len(missing_var) > 0:
        logger.info(f"Adding {len(missing_var)} gene records...")
        missing_var_df = src_var_df[src_var_df.index.isin(missing_var)]
        save_axes_labels(missing_var_df, var_array_name, var_labels)
    with tiledb.open(var_array_name, "r") as var:
        var_df = var.df[:]
        var_df.index = var_df.gene_ontology_term_id

    logger.info(f"Global var index length: {var_df.shape}")
    return var_df


def save_axes_labels(df: pd.DataFrame, array_name: str, label_info: List) -> int:
    """
    # TODO
    """
    logger.info(f"Saving {array_name}...\n")

    with tiledb.open(array_name) as array:
        next_join_index = array.meta.get("next_join_index", 0)

    with tiledb.open(array_name, mode="w") as array:
        data = {}
        coords = []
        for lbl in label_info:
            datum = lbl.decode(df, next_join_index)
            if lbl.encode_as_dim:
                coords.append(datum)
            else:
                data[lbl.key] = datum
        array[tuple(coords)] = data
        array.meta["next_join_index"] = next_join_index + len(coords[0])

    logger.info("saved.")
    return next_join_index


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


def transform_dataset_raw_counts_to_rankit(
    anndata_object: anndata.AnnData, corpus_path: str, global_var_index: numpy.ndarray, first_obs_idx: int
):
    """
    Apply rankit normalization to raw count expression values and save to the tiledb corpus object
    """
    array_name = f"{corpus_path}/{INTEGRATED_ARRAY_NAME}"
    expression_matrix = get_X_raw(anndata_object)
    logger.info(f"saving {array_name}...")
    stride = max(int(np.power(10, np.around(np.log10(1e9 / expression_matrix.shape[1])))), 10_000)
    with tiledb.open(array_name, mode="w") as array:
        for start in range(0, expression_matrix.shape[0], stride):
            end = min(start + stride, expression_matrix.shape[0])
            csr_sparse_raw_expression_matrix = sparse.csr_matrix(expression_matrix[start:end, :])

            raw_expression_coo_matrix = csr_sparse_raw_expression_matrix.tocoo(copy=False)
            rows = raw_expression_coo_matrix.row + start + first_obs_idx
            cols = global_var_index[raw_expression_coo_matrix.col]
            raw_expr_counts_data = raw_expression_coo_matrix.data

            # Compute RankIt
            rankit_integrated_csr_matrix = rankit(csr_sparse_raw_expression_matrix)

            zero_out_low_expression_count_values(rankit_integrated_csr_matrix, raw_expression_coo_matrix)

            rankit_integrated_coo_matrix = rankit_integrated_csr_matrix.tocoo(copy=False)
            assert np.array_equal(raw_expression_coo_matrix.row, rankit_integrated_coo_matrix.row)
            assert np.array_equal(raw_expression_coo_matrix.col, rankit_integrated_coo_matrix.col)

            rankit_data = rankit_integrated_coo_matrix.data

            array[rows, cols] = {"rankit": rankit_data}
            del (
                raw_expression_coo_matrix,
                rankit_integrated_coo_matrix,
                rows,
                cols,
                raw_expr_counts_data,
                rankit_data,
            )
            gc.collect()

    logger.debug(f"Saved {array_name}.")


def zero_out_low_expression_count_values(rankit: csr_matrix, raw_counts: coo_matrix):
    """
    Zero-out rankit values that were computed from expression values having raw count <= 3. This updates the `rankit`
    matrix in-place.
    """
    # TODO: Ideally, we would just *remove* these elements from rankit matrix, but that would
    #  require also adjusting the `obs` matrix and first_obs_idx, which are already updated. For now,
    #  we will also need to ignore zero values when computing nnz attribute of the expression summary cube.

    to_zero_mask = raw_counts.data <= RANKIT_RAW_EXPR_COUNT_FILTERING_MIN_THRESHOLD
    to_zero_rows = raw_counts.row[to_zero_mask]
    to_zero_cols = raw_counts.col[to_zero_mask]
    rankit[to_zero_rows, to_zero_cols] = 0.0

