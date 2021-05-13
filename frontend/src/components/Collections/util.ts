import memoize from "lodash/memoize";
import { Collection, VISIBILITY_TYPE } from "src/common/entities";
import {
  CollectionResponse,
  RevisionResponse,
  REVISION_STATUS,
} from "src/common/queries/collections";

export function generateRevisions(
  collections: CollectionResponse[],
  revisionsEnabled: boolean
): RevisionResponse[] {
  const revisionMap = generateRevisionMap(collections, revisionsEnabled);
  return Array.from(revisionMap.values());
}

export const generateRevisionMap = memoize(
  (collections: CollectionResponse[], revisionsEnabled: boolean) => {
    // generate list of collections with revision status (default to disabled)
    const newCollections = collections.map(
      (collection): RevisionResponse => {
        return { ...collection, revision: REVISION_STATUS.DISABLED };
      }
    );
    // If revisions are disabled just return the array with objects' revisions status set to disabled
    if (!revisionsEnabled) return newCollections;

    const revisionMap = new Map<Collection["id"], RevisionResponse>();

    newCollections.forEach((collection) => {
      const revisionObj = revisionMap.get(collection.id) || collection;
      if (revisionObj.revision !== REVISION_STATUS.STARTED) {
        revisionObj.revision =
          revisionObj.revision === REVISION_STATUS.DISABLED
            ? REVISION_STATUS.NOT_STARTED
            : REVISION_STATUS.STARTED;
        revisionObj.visibility =
          revisionObj.revision === REVISION_STATUS.STARTED
            ? VISIBILITY_TYPE.PUBLIC
            : revisionObj.visibility;
        revisionMap.set(collection.id, revisionObj);
      }
    });
    return revisionMap;
  },
  hashFn
);

function hashFn(collections: CollectionResponse[], revisionsEnabled: boolean) {
  return `${collections.map(
    (collection) => collection.id
  )} + ${revisionsEnabled}`;
}
