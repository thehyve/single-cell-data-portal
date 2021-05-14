from flask import make_response, g

from .....common.corpora_orm import CollectionVisibility
from .....common.entities import Collection
from .....common.utils.exceptions import ForbiddenHTTPException, MethodNotAllowedException


def post(collection_uuid: str, user: str):
    db_session = g.db_session
    collection = Collection.get_collection(db_session, collection_uuid, CollectionVisibility.PRIVATE, owner=user)
    if not collection:
        raise ForbiddenHTTPException()
    if not publishable(collection):
        raise MethodNotAllowedException("Unable to publish a revision with delete or revised datasets at this time.")
    collection.publish()
    return make_response({"collection_uuid": collection.id, "visibility": collection.visibility}, 202)


def publishable(collection) -> bool:
    """Check if the dataset can be publish. Remove this once tombstones and refresh datasets are supported"""
    result = True
    for dataset in collection.datasets:
        if dataset.original_id:
            if dataset.tombstone or not dataset.published:
                result = False
                break
    return result
