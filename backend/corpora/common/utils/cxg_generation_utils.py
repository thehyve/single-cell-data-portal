import json

import numpy as np
import tiledb

from backend.corpora.common.utils.type_conversion_utils import (
    get_encoding_dtype_of_array,
    get_dtype_and_schema_of_array,
)


def convert_dictionary_to_cxg_group(cxg_container, metadata_dict, group_metadata_name="cxg_group_metadata", ctx=None):
    """
    Saves the contents of the dictionary to the CXG output directory specified.

    This function is primarily used to save metadata about a dataset to the CXG directory. At some point, tiledb will
    have support for metadata on groups at which point the utility of this function should be revisited. Until such
    feature exists, this function create an empty array and annotate that array.

    For more information, visit https://github.com/TileDB-Inc/TileDB-Py/issues/254.
    """

    array_name = f"{cxg_container}/{group_metadata_name}"

    # Because TileDB does not allow one to attach metadata directly to a CXG group, we need to have a workaround
    # where we create an empty array and attached the metadata onto to this empty array. Below we construct this empty
    # array.
    tiledb.from_numpy(array_name, np.zeros((1,)))

    with tiledb.open(array_name, mode="w", ctx=ctx) as metadata_array:
        for key, value in metadata_dict.items():
            metadata_array.meta[key] = value


def convert_dataframe_to_cxg_array(cxg_container, dataframe_name, dataframe, index_column_name, ctx):
    """
    Saves the contents of the dataframe to the CXG output directory specified.

    Current access patterns are oriented toward reading very large slices of the dataframe, one attribute at a time.
    Attribute data also tends to be (often) repetitive (bools, categories, strings). Given this, we use a large tile
    size (1000) and very aggressive compression levels.
    """

    def create_dataframe_array(array_name, dataframe):
        tiledb_filter = tiledb.FilterList(
            [
                # Attempt aggressive compression as many of these dataframes are very repetitive strings, bools and
                # other non-float data.
                tiledb.ZstdFilter(level=22),
            ]
        )
        attrs = [
            tiledb.Attr(name=column, dtype=get_encoding_dtype_of_array(dataframe[column]), filters=tiledb_filter)
            for column in dataframe
        ]
        domain = tiledb.Domain(
            tiledb.Dim(domain=(0, dataframe.shape[0] - 1), tile=min(dataframe.shape[0], 1000), dtype=np.uint32)
        )
        schema = tiledb.ArraySchema(
            domain=domain, sparse=False, attrs=attrs, cell_order="row-major", tile_order="row-major"
        )
        tiledb.DenseArray.create(array_name, schema)

    array_name = f"{cxg_container}/{dataframe_name}"

    create_dataframe_array(array_name, dataframe)

    with tiledb.open(array_name, mode="w", ctx=ctx) as array:
        value = {}
        schema_hints = {}
        for column_name, column_values in dataframe.items():
            dtype, hints = get_dtype_and_schema_of_array(column_values)
            value[column_name] = column_values.to_numpy(dtype=dtype)
            if hints:
                schema_hints.update({column_name: hints})

        schema_hints.update({"index": index_column_name})
        array[:] = value
        array.meta["cxg_schema"] = json.dumps(schema_hints)

    tiledb.consolidate(array_name, ctx=ctx)


def convert_ndarray_to_cxg_dense_array(ndarray_name, ndarray, ctx):
    """
    Saves contents of ndarray to the CXG output directory specified.

    Generally this function is used to convert dataset embeddings. Because embeddings are typically accessed with
    very large slices (or all of the embedding), they do not benefit from overly aggressive compression due to their
    format.  Given this, we use a large tile size (1000) but only default compression level.
    """

    def create_ndarray_array(ndarray_name, ndarray):
        filters = tiledb.FilterList([tiledb.ZstdFilter()])
        attrs = [tiledb.Attr(dtype=ndarray.dtype, filters=filters)]
        dimensions = [
            tiledb.Dim(
                domain=(0, ndarray.shape[dimension] - 1), tile=min(ndarray.shape[dimension], 1000), dtype=np.uint32
            )
            for dimension in range(ndarray.ndim)
        ]
        domain = tiledb.Domain(*dimensions)
        schema = tiledb.ArraySchema(
            domain=domain, sparse=False, attrs=attrs, capacity=1_000_000, cell_order="row-major", tile_order="row-major"
        )
        tiledb.DenseArray.create(ndarray_name, schema)

    create_ndarray_array(ndarray_name, ndarray)

    with tiledb.open(ndarray_name, mode="w", ctx=ctx) as array:
        array[:] = ndarray

    tiledb.consolidate(ndarray_name, ctx=ctx)


def convert_matrix_to_cxg_array(matrix_name, matrix, encode_as_sparse_array, ctx):
    """
    Converts a numpy array matrix into a TileDB SparseArray of DenseArray based on whether `encode_as_sparse_array`
    is true or not. Note that when the matrix is encoded as a SparseArray, it only writes the values that are
    nonzero. This means that if you count the number of elements in the SparseArray, it will not equal the total
    number of elements in the matrix, only the number of nonzero elements.
    """

    def create_matrix_array(matrix_name, number_of_rows, number_of_columns, encode_as_sparse_array, compression=22):
        attrs = [tiledb.Attr(dtype=np.float32, filters=tiledb.FilterList([tiledb.ZstdFilter(level=compression)]))]
        dim_filters = tiledb.FilterList([tiledb.ByteShuffleFilter(), tiledb.ZstdFilter(level=compression)])
        domain = tiledb.Domain(
            tiledb.Dim(
                name="obs",
                domain=(0, number_of_rows - 1),
                tile=min(number_of_rows, 256),
                dtype=np.uint32,
                filters=dim_filters,
            ),
            tiledb.Dim(
                name="var",
                domain=(0, number_of_columns - 1),
                tile=min(number_of_columns, 2048),
                dtype=np.uint32,
                filters=dim_filters,
            ),
        )
        schema = tiledb.ArraySchema(
            domain=domain,
            sparse=encode_as_sparse_array,
            allows_duplicates=True if encode_as_sparse_array else False,
            attrs=attrs,
            cell_order="row-major",
            tile_order="col-major",
            capacity=128000 if encode_as_sparse_array else 0,
        )
        tiledb.Array.create(matrix_name, schema)

    number_of_rows = matrix.shape[0]
    number_of_columns = matrix.shape[1]
    stride = min(int(np.power(10, np.around(np.log10(1e9 / number_of_columns)))), 10_000)

    create_matrix_array(matrix_name, number_of_rows, number_of_columns, encode_as_sparse_array)

    with tiledb.open(matrix_name, mode="w", ctx=ctx) as array:
        for start_row_index in range(0, number_of_rows, stride):
            end_row_index = min(start_row_index + stride, number_of_rows)
            matrix_subset = matrix[start_row_index:end_row_index, :]
            if not isinstance(matrix_subset, np.ndarray):
                matrix_subset = matrix_subset.toarray()
            if encode_as_sparse_array:
                indices = np.nonzero(matrix_subset)
                trow = indices[0] + start_row_index
                array[trow, indices[1]] = matrix_subset[indices[0], indices[1]]
            else:
                array[start_row_index:end_row_index, :] = matrix_subset
