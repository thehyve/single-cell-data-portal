from flask import g, jsonify, Response

from backend.corpora.lambdas.api.v1.collection import (
    get_collection_and_verify_body,
    get_publisher_metadata,
    normalize_and_get_doi,
)
from ..common import (
    add_collection_level_processing_status,
    reshape_for_curation_api_and_is_allowed,
    EntityColumns,
)
from backend.corpora.api_server.db import dbconnect
from backend.corpora.common.corpora_orm import (
    CollectionVisibility,
    DbCollectionLink,
    DbCollection,
)
from backend.corpora.common.entities import Collection
from backend.corpora.common.utils.http_exceptions import (
    MethodNotAllowedException,
    NotFoundHTTPException,
    InvalidParametersHTTPException,
    ForbiddenHTTPException,
)
from backend.corpora.lambdas.api.v1.authorization import owner_or_allowed
from backend.corpora.lambdas.api.v1.common import get_collection_else_forbidden


@dbconnect
def delete(collection_id: str, token_info: dict):
    db_session = g.db_session
    collection = get_collection_else_forbidden(db_session, collection_id, owner=owner_or_allowed(token_info))
    if collection.visibility == CollectionVisibility.PUBLIC:
        raise MethodNotAllowedException(detail="Cannot delete a public collection through API.")
    else:
        collection.delete()
    return "", 204


@dbconnect
def get(collection_id: str, token_info: dict):
    db_session = g.db_session
    collection = Collection.get_collection(db_session, collection_id, include_tombstones=False)
    if not collection:
        raise NotFoundHTTPException
    collection_response: dict = collection.to_dict_keep(EntityColumns.columns_for_collection_id)

    collection_response["processing_status"] = add_collection_level_processing_status(collection)
    reshape_for_curation_api_and_is_allowed(db_session, collection_response, token_info, id_provided=True)

    return jsonify(collection_response)


@dbconnect
def patch(collection_id: str, body: dict, token_info: dict) -> Response:
    db_session = g.db_session

    keep_links = True  # links have NOT been provided; keep existing links
    if "links" in body:
        if not body["links"]:
            raise InvalidParametersHTTPException(detail="If provided, the 'links' array may not be empty")
        keep_links = False  # links have been provided; replace all old links

    try:
        collection, errors = get_collection_and_verify_body(db_session, collection_id, body, token_info)
    except ForbiddenHTTPException as err:
        # If the Collection is public, the get_collection_and_verify_body method throws empty ForbiddenHTTPException
        if Collection.get_collection(
            db_session, collection_id, CollectionVisibility.PUBLIC, owner=owner_or_allowed(token_info)
        ):
            raise MethodNotAllowedException(
                detail="Directly editing a public Collection is not allowed; you must create a revision."
            )
        raise err

    if not keep_links:
        # Compute the diff between old and new DOI
        old_doi = collection.get_doi()
        new_doi = normalize_and_get_doi(body, errors)
        if new_doi and new_doi != old_doi:
            # If the DOI has changed, fetch and update the metadata
            publisher_metadata = get_publisher_metadata(new_doi, errors)
            body["publisher_metadata"] = publisher_metadata

    if errors:
        raise InvalidParametersHTTPException(detail=errors)

    collection.update(**body, keep_links=keep_links)
    collection_dict = collection.to_dict_keep(
        {
            DbCollection: ["name", "description", "contact_name", "contact_email", "links", "publisher_metadata"],
            DbCollectionLink: ["link_url", "link_name", "link_type"],
        }
    )

    return jsonify(collection_dict)
