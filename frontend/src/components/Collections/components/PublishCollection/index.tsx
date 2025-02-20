import { H6, Intent } from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import loadable from "@loadable/component";
import { useRouter } from "next/router";
import { FC, useState } from "react";
import { ROUTES } from "src/common/constants/routes";
import { Collection } from "src/common/entities";
import { usePublishCollection } from "src/common/queries/collections";
import { StyledPrimaryButton } from "src/components/common/Button/common/style";
import Toast from "src/views/Collection/components/Toast";
import Policy, { POLICY_BULLETS } from "./components/Policy";

const AsyncAlert = loadable(
  () =>
    /*webpackChunkName: 'src/components/Alert' */ import("src/components/Alert")
);

interface Props {
  id: Collection["id"];
  isPublishable: boolean;
  revisionOf: Collection["revision_of"];
}

const PublishCollection: FC<Props> = ({
  id = "",
  isPublishable,
  revisionOf,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const { mutateAsync: publish, isSuccess, isLoading } = usePublishCollection();
  const router = useRouter();

  if (isSuccess) {
    console.log(
      "IS SUCCESS, used to be private collection redirect, now just refreshes data?"
    );
    if (revisionOf) router.push(ROUTES.COLLECTION.replace(":id", revisionOf));
    else router.reload();
  }

  const toggleAlert = () => setIsOpen(!isOpen);

  const handleConfirm = async () => {
    const payload = JSON.stringify({
      data_submission_policy_version: POLICY_BULLETS.version,
    });
    await publish(
      { id, payload },
      {
        onSuccess: () => {
          //if revision show revision toast
          if (revisionOf) {
            console.log("Published a revision");
            Toast.show({
              icon: IconNames.TICK,
              intent: Intent.SUCCESS,
              message: "New version published",
            });
          }
        },
      }
    );

    toggleAlert();
  };

  const handleHover = () => {
    AsyncAlert.preload();
  };

  const handleClick = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      <StyledPrimaryButton
        onMouseEnter={handleHover}
        onClick={handleClick}
        intent={Intent.PRIMARY}
        text="Publish"
        disabled={!isPublishable}
        data-test-id="publish-collection-button"
      />
      {isOpen && (
        <AsyncAlert
          cancelButtonText={"Cancel"}
          confirmButtonText={
            revisionOf ? "Publish Revision" : "Publish Collection"
          }
          intent={Intent.PRIMARY}
          isOpen={isOpen}
          onCancel={toggleAlert}
          onConfirm={handleConfirm}
          loading={isLoading}
        >
          {revisionOf ? (
            <>
              <H6>
                Are you sure you want to publish a revision to this collection?
              </H6>
              <p>
                Any datasets you’ve removed will no longer be accessible to
                portal users. Links to deleted datasets from external sites will
                display a message that the dataset has been withdrawn by the
                publisher.
              </p>
            </>
          ) : (
            <>
              <H6>Are you sure you want to publish this collection?</H6>
              <p>
                The datasets, related metadata, and CXG(s) in this collection
                will be viewable and downloadable by all portal users. External
                sites may directly link to the CXG(s).
              </p>
            </>
          )}
          <Policy />
        </AsyncAlert>
      )}
    </>
  );
};

export default PublishCollection;
