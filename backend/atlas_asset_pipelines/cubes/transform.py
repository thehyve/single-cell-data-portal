import concurrent
import logging
import time

import numba as nb
import numpy as np

import tiledb

from backend.corpora.common.utils.math_utils import MB
from backend.wmg.data.schemas.corpus_schema import INTEGRATED_ARRAY_NAME
from backend.wmg.data.tiledb import create_ctx

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def reduce_X(tdb_group, start_time, cube_indices, *accum):
    """
    # TODO
    """
    with concurrent.futures.ThreadPoolExecutor() as tp:
        cfg = {
            "py.init_buffer_bytes": 512 * MB,
            "py.exact_init_buffer_bytes": "true",
        }
        with tiledb.open(f"{tdb_group}/{INTEGRATED_ARRAY_NAME}", ctx=create_ctx(config_overrides=cfg)) as X:
            iterable = X.query(return_incomplete=True, order="U", attrs=["rankit"])
            future = None
            for i, result in enumerate(iterable.df[:]):
                logger.info(f"reduce integrated expression data, iter {i}, {time.time() - start_time}")
                if future is not None:
                    future.result()  # forces a wait
                future = tp.submit(
                    coo_cube_pass1_into,
                    result["rankit"].values,
                    result["obs_idx"].values,
                    result["var_idx"].values,
                    cube_indices,
                    *accum,
                )

        return accum


"""
TODO: this could be further optimize by parallel chunking.  Might help large
arrays if compute ends up being a bottleneck.
"""


@nb.njit(fastmath=True, error_model="numpy", parallel=False, nogil=True)
def coo_cube_pass1_into(data, row, col, row_groups, sum_into, nnz_into, min_into, max_into):
    """
    # TODO
    """
    for k in range(len(data)):
        val = data[k]
        if np.isfinite(val):
            cidx = col[k]
            grp_idx = row_groups[row[k]]
            sum_into[grp_idx, cidx] += val
            nnz_into[grp_idx, cidx] += 1
            if val < min_into[grp_idx, cidx]:
                min_into[grp_idx, cidx] = val
            if val > max_into[grp_idx, cidx]:
                max_into[grp_idx, cidx] = val
