import numpy as np
import tiledb

# These are the queryable cube dimensions that will be modeled as
# TileDB `Dim`s and thus can be used for _efficiently_ querying
# (slicing) the TileDB array. Order matters here!
cube_indexed_dims_no_gene_ontology = [
    "cell_type_ontology_term_id",
    "tissue_ontology_term_id",
    "organism_ontology_term_id",
]
cube_indexed_dims = [
    "gene_ontology_term_id",
    *cube_indexed_dims_no_gene_ontology
]
# These are the queryable cube dimensions that will be modeled as
# TileDB `Attrs` (i.e. (non-indexed") and thus will require
# client-side filtering, which may result in less efficient querying.
cube_non_indexed_dims = [
    "dataset_id",
    "assay_ontology_term_id",
    "development_stage_ontology_term_id",
    "disease_ontology_term_id",
    "ethnicity_ontology_term_id",
    "sex_ontology_term_id",
]

# The full set of logical cube dimensions by which the cube can be queried.
cube_logical_dims = cube_indexed_dims + cube_non_indexed_dims

filters = [tiledb.ZstdFilter(level=+22)]

domain = tiledb.Domain(
    [
        tiledb.Dim(name=cube_indexed_dim, domain=None, tile=None, dtype="ascii", filters=filters)
        for cube_indexed_dim in cube_indexed_dims
    ]
)

# The cube attributes that comprise the core data stored within the cube.
cube_logical_attrs = [
    tiledb.Attr(name="n_cells", dtype=np.uint32, filters=filters),
    tiledb.Attr(name="nnz", dtype=np.uint64, filters=filters),  # TODO: Why uint64?
    tiledb.Attr(name="sum", dtype=np.float32, filters=filters),
]

# The TileDB `Attr`s of the cube TileDB Array. This includes the
# logical cube attributes, above, along with the non-indexed logical
# cube dimensions, which we models as TileDB `Attr`s.
cube_physical_attrs = [
    tiledb.Attr(name=nonindexed_dim, dtype="ascii", var=True, filters=filters)
    for nonindexed_dim in cube_non_indexed_dims
] + cube_logical_attrs

schema = tiledb.ArraySchema(
    domain=domain,
    sparse=True,
    allows_duplicates=True,
    attrs=cube_physical_attrs,
    cell_order="row-major",
    tile_order="row-major",
    capacity=10000,
)