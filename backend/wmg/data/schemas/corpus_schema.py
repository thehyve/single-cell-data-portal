"""
Learning: TileDB push-down queries do not currently support conditions on variable length unicode strings.
It is a roadmap item.  Currently supported:
    * Unicode, fixed length
    * ASCII, variable length
Casting to ASCII for now as that covers 99.99% of our data (eg, ontology IDs).
"""

# Hints on how to map between H5AD and TDB schemas.
import logging
from collections import namedtuple
from typing import Union, List

import numpy as np
import pandas as pd
import tiledb

import pathlib

from backend.wmg.data.wmg_constants import INTEGRATED_ARRAY_NAME

uint32_domain = (np.iinfo(np.uint32).min, np.iinfo(np.uint32).max - 1)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# TODO: define and use constants for obs and var array names


class LabelType(
    namedtuple(
        "Label",
        ["key", "dtype", "domain", "decode_from_index", "encode_as_dim", "var", "custom_decoder"],
        defaults=[None, False, False, None, None],
    )
):
    __slots__ = ()

    def _get_col(self, df: pd.DataFrame) -> Union[pd.Index, pd.Series, None]:
        if self.decode_from_index:
            return df.index
        elif self.key in df:
            return df[self.key]
        else:
            return None

    def decode(self, df: pd.DataFrame, *args, **kwargs) -> np.ndarray:
        if self.custom_decoder:
            return self.custom_decoder(self, df, *args, **kwargs)

        # else, simple dataframe column extraction
        col = self._get_col(df)
        if col is None:
            return np.full((df.shape[0],), b"", dtype="O")
        elif self.dtype is str:
            return col.to_numpy(dtype=str)
        elif self.dtype in ["ascii", np.bytes_]:
            return np.char.encode(col.to_numpy(dtype=str), encoding="ascii")
        else:
            return col.to_numpy(dtype=self.dtype)


def gen_idx(_lbl, df, start_coord=0):
    return np.arange(start_coord, start_coord + df.shape[0])


# dimensions - order matters for dimension
obs_labels = [
    # obs_idx is the join index with the X array, and IS ALSO the "iloc" from original dataset.
    LabelType("obs_idx", np.uint32, domain=uint32_domain, custom_decoder=gen_idx),
    LabelType("dataset_id", "ascii", encode_as_dim=True),
    *[
        LabelType(key, "ascii", encode_as_dim=True)
        for key in [
            "cell_type_ontology_term_id",
            "tissue_ontology_term_id",
        ]
    ],
    *[
        LabelType(key, "ascii", var=True)
        for key in [
            "cell_type",
            "assay",
            "assay_ontology_term_id",
            "development_stage",
            "development_stage_ontology_term_id",
            "disease_ontology_term_id",
            "tissue",
            "ethnicity",
            "ethnicity_ontology_term_id",
            "sex",
            "sex_ontology_term_id",
            "organism",
            "organism_ontology_term_id",
        ]
    ],
    LabelType("dataset_local_cell_id", "ascii", var=True, decode_from_index=True),
]

# order matters for dimensions
var_labels = [
    # var_idx is the join index with the X array
    LabelType("var_idx", np.uint32, domain=uint32_domain, custom_decoder=gen_idx),
    # what if we just remove this and use the gen ontololgy id as an index
    LabelType("gene_ontology_term_id", "ascii", decode_from_index=True, encode_as_dim=True),
    LabelType("feature_reference", "ascii", var=True),
    LabelType("feature_name", "ascii", var=True),
]


def create_tdb_corpus(corpus_location: str, corpus_name: str):
    """
    Create the empty tiledb object for the corpus
    ## TODO break out each array
    """
    uri = f"{corpus_location}/{corpus_name}"
    pathlib.Path(uri).mkdir(parents=True, exist_ok=True)
    tiledb.group_create(uri)

    X_capacity = 128000
    X_extent = [512, 2048]  # guess - needs tuning
    filters = tiledb.FilterList([tiledb.ZstdFilter(level=-22)])

    """ Optional array, normalized X from original dataset. """
    tiledb.Array.create(
        f"{uri}/X",
        tiledb.ArraySchema(
            domain=tiledb.Domain(
                [
                    tiledb.Dim(
                        name="obs_idx",
                        domain=uint32_domain,
                        tile=X_extent[0],
                        dtype=np.uint32,
                        filters=filters,
                    ),
                    tiledb.Dim(
                        name="var_idx",
                        domain=uint32_domain,
                        tile=X_extent[1],
                        dtype=np.uint32,
                        filters=filters,
                    ),
                ]
            ),
            sparse=True,
            allows_duplicates=True,
            attrs=[tiledb.Attr(name="data", dtype=np.float32, filters=filters)],
            cell_order="row-major",
            tile_order="col-major",
            capacity=X_capacity,
        ),
    )

    """ rankit expression values """
    tiledb.Array.create(
        f"{uri}/{INTEGRATED_ARRAY_NAME}",
        tiledb.ArraySchema(
            domain=tiledb.Domain(
                [
                    tiledb.Dim(
                        name="obs_idx",
                        domain=uint32_domain,
                        tile=X_extent[0],
                        dtype=np.uint32,
                        filters=filters,
                    ),
                    tiledb.Dim(
                        name="var_idx",
                        domain=uint32_domain,
                        tile=X_extent[1],
                        dtype=np.uint32,
                        filters=filters,
                    ),
                ]
            ),
            sparse=True,
            allows_duplicates=True,
            attrs=[
                tiledb.Attr(name="rankit", dtype=np.float32, filters=filters),
            ],
            cell_order="row-major",
            tile_order="col-major",
            capacity=X_capacity,
        ),
    )

    """
    obs/cell axes labels
    """
    tiledb.Array.create(
        f"{uri}/obs",
        tiledb.ArraySchema(
            domain=tiledb.Domain(create_axes_label_dims(obs_labels)),
            sparse=True,
            allows_duplicates=True,
            attrs=[
                tiledb.Attr(name=lbl.key, dtype=lbl.dtype, var=lbl.var, filters=filters)
                for lbl in obs_labels
                if lbl.encode_as_dim is False
            ],
            cell_order="row-major",
            tile_order="row-major",
            capacity=10000,
        ),
    )

    """
    var/feature/gene axes labels.
    """
    tiledb.Array.create(
        f"{uri}/var",
        tiledb.ArraySchema(
            domain=tiledb.Domain(create_axes_label_dims(var_labels)),
            sparse=True,
            allows_duplicates=True,
            attrs=[
                tiledb.Attr(name=lbl.key, dtype=lbl.dtype, var=lbl.var, filters=filters)
                for lbl in var_labels
                if lbl.encode_as_dim is False
            ],
            cell_order="row-major",
            tile_order="row-major",
            capacity=10000,
        ),
    )


def create_axes_label_dims(labels: List[LabelType]) -> List[tiledb.Dim]:
    dims = []
    extent = 1024  # guess - needs tuning
    filters = tiledb.FilterList([tiledb.ZstdFilter(level=22)])
    for lbl in labels:
        if not lbl.encode_as_dim:
            continue
        if lbl.encode_as_dim and lbl.dtype in [np.bytes_, "ascii"]:  # special case strings
            dim = tiledb.Dim(name=lbl.key, domain=None, tile=None, dtype=lbl.dtype, filters=filters, var=lbl.var)
        else:
            dim = tiledb.Dim(
                name=lbl.key, domain=lbl.domain, tile=extent, dtype=lbl.dtype, var=lbl.var, filters=filters
            )
        dims.append(dim)
    return dims


def create_local_to_global_gene_coord_index(
        var_df: pd.DataFrame, gene_ontology_term_ids: Union[List[str], np.ndarray]
) -> np.ndarray:
    """
    Create an array mapping feature ids local to global index
    """
    n_features = len(gene_ontology_term_ids)
    local_to_global_feature_coord = np.zeros((n_features,), dtype=np.uint32)
    var_feature_to_coord_map = {k: v for k, v in var_df[["gene_ontology_term_id", "var_idx"]].to_dict("split")["data"]}
    for idx in range(n_features):
        gene_ontology_term_id = gene_ontology_term_ids[idx]
        global_coord = var_feature_to_coord_map[gene_ontology_term_id]
        local_to_global_feature_coord[idx] = global_coord

    return local_to_global_feature_coord


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