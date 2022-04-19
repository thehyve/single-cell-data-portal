import logging
import pathlib
import sys
import time
import tiledb
from backend.atlas_asset_pipelines import concat_corpus
from backend.atlas_asset_pipelines.concat_corpus.load import load_h5ad_datasets
from backend.wmg.data.load_cube import update_s3_resources

from backend.wmg.data.schemas.corpus_schema import create_tdb
from backend.wmg.data.transform import get_cell_types_by_tissue, generate_cell_ordering
from backend.wmg.data.wmg_cube import create_cubes

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_data_and_create_cube(
    path_to_h5ad_datasets: str, corpus_name: str = "corpus_group", snapshot_path=None, extract_data=True
):
    """
    Function to copy H5AD datasets (from a preconfiugred s3 bucket) to the path given then,
    open, transform, normalize and concatenate them together as a tiledb object with a global gene index
    under the given concat_corpus name.
    A cube of expression summary statistics (known as the expression summary cube) across genes (but queryable by
    the given dimensions/data) is then generated and stored under big-cube.
    A per-tissue mapping of cell ontologies is generated and the files are copied to s3 under a shared timestamp,.
    On success the least recent set of files are removed from s3
    """
    if not snapshot_path:
        timestamp = int(time.time())
        snapshot_path = f"{pathlib.Path().resolve()}/{timestamp}"
    corpus_path = f"{snapshot_path}/{corpus_name}"


    if extract_data:
        s3_uris = concat_corpus.extract.get_dataset_s3_uris()
        concat_corpus.extract.copy_datasets_to_instance(s3_uris, path_to_h5ad_datasets)
        logger.info("Copied datasets to instance")

    if not tiledb.VFS().is_dir(corpus_path):
        create_tdb(snapshot_path, corpus_name)

    load_h5ad_datasets(path_to_h5ad_datasets, corpus_path, True)
    logger.info("Loaded datasets into concat_corpus")
    create_cubes(corpus_path)
    logger.info("Built expression summary cube")

    cell_type_by_tissue = get_cell_types_by_tissue(corpus_path)
    generate_cell_ordering(snapshot_path, cell_type_by_tissue)
    generate_primary_filter_dimensions(snapshot_path, corpus_name, timestamp)
    logger.info("Generated cell ordering json file")
    update_s3_resources(snapshot_path, timestamp)
    logger.info("Copied snapshot to s3")


if __name__ == "__main__":
    load_data_and_create_cube("datasets", ".")
    sys.exit()
