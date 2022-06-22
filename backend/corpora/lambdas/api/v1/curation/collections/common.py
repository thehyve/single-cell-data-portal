from ...authorization import is_user_owner_or_allowed
from ......common.corpora_config import CorporaConfig
from ......common.corpora_orm import (
    CollectionVisibility,
    DbCollectionLink,
    DbCollection,
    DbDataset,
    DbDatasetProcessingStatus,
    DbDatasetArtifact,
)


def get_access_type(collection, token_info, uuid_provided=False):
    """
    Determine user's access to collection
    :param collection: the Collection being returned in the API response
    :param token_info: user access token
    :param uuid_provided: bool - whether the collection uuid was provided by the user, for access purposes
    @return: user's level of access (str)
    """
    owner = collection["owner"]
    if is_user_owner_or_allowed(token_info, owner):
        return "WRITE"
    elif not uuid_provided and collection["visibility"] == CollectionVisibility.PRIVATE:
        # User neither provided the uuid for access nor are they authorized by their access token
        return None
    elif token_info:
        # Access token was provided but user is not authorized
        return "READ"


def reshape_for_curation_api(collection, access_type=None):
    """
    Reshape Collection data for the Curation API response, in-place.
    :param collection: the Collection being returned in the API response
    :param access_type: str - user access type to collection. Value must be READ or WRITE
    """
    if access_type == "READ" or access_type == "WRITE":
        collection["access_type"] = access_type

    del collection["owner"]  # Don't actually want to return 'owner' in response
    collection["collection_url"] = f"{CorporaConfig().collections_base_url}/collections/{collection['id']}"

    if "datasets" in collection:
        for dataset in collection["datasets"]:
            if "artifacts" in dataset:
                dataset["dataset_assets"] = dataset.pop("artifacts")
            if "processing_status" in dataset:
                dataset["processing_status"] = dataset["processing_status"]["processing_status"]


class EntityColumns:

    collections_cols = [
        "id",
        "name",
        "visibility",
        "tombstone",
        "contact_name",
        "contact_email",
        "curator_name",
        "revised_at",
        "created_at",
        "published_at",
        "description",
        "publisher_metadata",
        "revision_of",
        "tombstone",
        "owner",  # Needed for determining view permissions
        "links",
        "datasets",
    ]

    link_cols = [
        "link_name",
        "link_url",
        "link_type",
    ]

    dataset_preview_cols = [
        "id",
        "curator_tag",
        "tissue",
        "assay",
        "disease",
        "organism",
        "tombstone",
        "processing_status",
    ]

    dataset_cols = [
        *dataset_preview_cols,
        "name",
        "revision",
        "revised_at",
        "is_primary_data",
        "x_normalization",
        "artifacts",
        "sex",
        "ethnicity",
        "development_stage",
        "explorer_url",
        "cell_type",
        "cell_count",
        "x_approximate_distribution",
        # "batch_condition",  # TODO: https://app.zenhub.com/workspaces/single-cell-5e2a191dad828d52cc78b028/issues/chanzuckerberg/single-cell-data-portal/1461  # noqa: E501
        "mean_genes_per_cell",
        "schema_version",
    ]

    dataset_asset_cols = [
        "filetype",
        "filename",
    ]

    dataset_processing_status_cols = [
        "processing_status",
    ]

    columns_for_collections = {
        DbCollectionLink: link_cols,
        DbCollection: collections_cols,
        DbDataset: dataset_preview_cols,
        DbDatasetProcessingStatus: dataset_processing_status_cols,
    }

    columns_for_collection_uuid = {
        DbCollectionLink: link_cols,
        DbCollection: collections_cols,
        DbDataset: dataset_cols,
        DbDatasetArtifact: dataset_asset_cols,
        DbDatasetProcessingStatus: dataset_processing_status_cols,
    }
