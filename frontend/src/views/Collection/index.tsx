import { H3, Intent } from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import Head from "next/head";
import { useRouter } from "next/router";
import React, { FC, useEffect, useState } from "react";
import { ROUTES } from "src/common/constants/routes";
import { ACCESS_TYPE, VISIBILITY_TYPE } from "src/common/entities";
import { get } from "src/common/featureFlags";
import { FEATURES } from "src/common/featureFlags/features";
import { useExplainNewTab } from "src/common/hooks/useExplainNewTab";
import { BOOLEAN } from "src/common/localStorage/set";
import {
  useCollection,
  useCollectionUploadLinks,
  useDeleteCollection,
} from "src/common/queries/collections";
import { removeParams } from "src/common/utils/removeParams";
import { isTombstonedCollection } from "src/common/utils/typeGuards";
import CollectionDescription from "src/components/Collection/components/CollectionDescription";
import CollectionMetadata from "src/components/Collection/components/CollectionMetadata";
import CollectionMigrationCallout from "src/components/Collection/components/CollectionMigrationCallout";
import CollectionRevisionStatusCallout from "src/components/Collection/components/CollectionRevisionStatusCallout";
import { UploadingFile } from "src/components/DropboxChooser";
import DatasetTab from "src/views/Collection/components/DatasetTab";
import ActionButtons from "./components/ActionButtons";
import DeleteCollectionButton from "./components/ActionButtons/components/DeleteButton";
import Toast from "./components/Toast";
import { CollectionDetail, CollectionHero, ViewCollection } from "./style";
import {
  buildCollectionMetadataLinks,
  getIsPublishable,
  revisionIsPublishable,
} from "./utils";

const Collection: FC = () => {
  const router = useRouter();
  const { params, tombstoned_dataset_id } = router.query;

  const [userWithdrawn, setUserWithdrawn] = useState(false);

  let id = "";

  if (Array.isArray(params)) {
    id = params[0];
  } else if (params) {
    id = params;
  }

  const { mutateAsync: uploadLink } = useCollectionUploadLinks(id);

  const [isUploadingLink, setIsUploadingLink] = useState(false);

  const collectionState = useCollection({
    id,
  });

  const [hasShownWithdrawToast, setHasShownWithdrawToast] = useState(false);

  const { data: collection, isError, isFetching } = collectionState;

  const { mutateAsync: deleteMutation, isLoading } = useDeleteCollection(
    id,
    collection && "visibility" in collection
      ? collection.visibility
      : VISIBILITY_TYPE.PRIVATE
  );

  const isCurator = get(FEATURES.CURATOR) === BOOLEAN.TRUE;

  useEffect(() => {
    if (
      hasShownWithdrawToast ||
      !tombstoned_dataset_id ||
      !collection ||
      isTombstonedCollection(collection)
    )
      return;

    Toast.show({
      icon: IconNames.ISSUE,
      intent: Intent.PRIMARY,
      message:
        "A dataset was withdrawn. You've been redirected to the parent collection.",
    });
    removeParams("tombstoned_dataset_id");
    setHasShownWithdrawToast(true);
  }, [tombstoned_dataset_id, collection, hasShownWithdrawToast]);

  useEffect(() => {
    if (!userWithdrawn && isTombstonedCollection(collection)) {
      const redirectUrl = ROUTES.HOMEPAGE;
      router.push(redirectUrl + "?tombstoned_collection_id=" + id);
    }
  }, [collection, id, router, userWithdrawn]);

  /* Pop toast if user has come from Explorer with work in progress */
  useExplainNewTab(
    "To maintain your in-progress work on the previous dataset, we opened this collection in a new tab."
  );

  if (!collection || isError || isTombstonedCollection(collection)) {
    return null;
  }

  const isPrivate = collection.visibility === VISIBILITY_TYPE.PRIVATE;

  const isRevision = isCurator && !!collection?.revision_of;

  const addNewFile = (newFile: UploadingFile) => {
    if (!newFile.link) return;

    const payload = JSON.stringify({ url: newFile.link });

    setIsUploadingLink(true);

    uploadLink(
      { collectionId: id, payload },
      {
        onSettled: () => setIsUploadingLink(false),
        onSuccess: () => {
          Toast.show({
            icon: IconNames.TICK,
            intent: Intent.PRIMARY,
            message:
              "Your file is being uploaded which will continue in the background, even if you close this window.",
          });
        },
      }
    );
  };

  let datasets = Array.from(collection.datasets.values());

  // Filter out tombstoned datasets if we're not looking at revision
  if (!isRevision) datasets = datasets.filter((dataset) => !dataset.tombstone);

  // (thuang): `isFetching` is used to prevent incorrectly enabling "Publish"
  // when React Query is fetching cached `collection` and its outdated
  // `datasets`
  const isPublishable =
    getIsPublishable(datasets) &&
    !isUploadingLink &&
    !isFetching &&
    revisionIsPublishable(collection, isCurator);

  const hasWriteAccess = collection.access_type === ACCESS_TYPE.WRITE;
  const shouldShowPrivateWriteAction = hasWriteAccess && isPrivate;
  const shouldShowPublicWriteAction = hasWriteAccess && !isPrivate;
  const shouldShowCollectionRevisionCallout =
    collection.revision_of && isPrivate;
  const collectionMetadataLinks = buildCollectionMetadataLinks(
    collection.links,
    collection.contact_name,
    collection.contact_email,
    collection.summaryCitation
  );

  const handleDeleteCollection = async () => {
    setUserWithdrawn(true);

    await deleteMutation({
      collectionID: id,
    });

    router.push(ROUTES.MY_COLLECTIONS);
  };

  return (
    <>
      <Head>
        <title>cellxgene | {collection.name}</title>
      </Head>
      <ViewCollection>
        {/* Collection revision status callout */}
        {shouldShowCollectionRevisionCallout && (
          <CollectionRevisionStatusCallout
            isRevisionDifferent={collection.revision_diff}
          />
        )}
        {/* Incomplete collection callout */}
        {!isRevision && (
          <CollectionMigrationCallout collectionId={collection.id} />
        )}
        {/* Collection title and actions */}
        <CollectionHero>
          <H3 data-test-id="collection-name">{collection.name}</H3>
          {shouldShowPrivateWriteAction && (
            <ActionButtons
              id={id}
              addNewFile={addNewFile}
              isPublishable={isPublishable}
              revisionOf={collection.revision_of}
              visibility={collection.visibility}
            />
          )}
          {shouldShowPublicWriteAction && (
            <DeleteCollectionButton
              collectionName={collection.name}
              handleConfirm={handleDeleteCollection}
              loading={isLoading}
            />
          )}
        </CollectionHero>
        {/* Collection description and metadata */}
        <CollectionDetail>
          <CollectionDescription description={collection.description} />
          {collectionMetadataLinks.length > 0 && (
            <CollectionMetadata
              collectionMetadataLinks={collectionMetadataLinks}
            />
          )}
        </CollectionDetail>
        {/* Collection grid */}
        {/* TODO Reusing DatasetTab as-is as functionality is too dense to refactor for this iteration of filter. Complete refactor (including update to React Table) can be done when filter is productionalized. */}
        <DatasetTab
          collectionID={id}
          datasets={datasets}
          isRevision={isRevision}
          visibility={collection.visibility}
        />
      </ViewCollection>
    </>
  );
};

export default Collection;
