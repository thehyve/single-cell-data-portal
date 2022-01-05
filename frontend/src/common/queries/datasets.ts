import {
  useMutation,
  useQuery,
  useQueryClient,
  UseQueryResult,
} from "react-query";
import { API_URL } from "src/configs/configs";
import { API } from "../API";
import {
  DatasetAsset,
  DatasetUploadStatus,
  VISIBILITY_TYPE,
} from "../entities";
import { apiTemplateToUrl } from "../utils/apiTemplateToUrl";
import { USE_COLLECTION } from "./collections";
import { DEFAULT_FETCH_OPTIONS, DELETE_FETCH_OPTIONS } from "./common";
import { ENTITIES } from "./entities";

export const USE_DATASET_STATUS = {
  entities: [ENTITIES.DATASET_STATUS],
  id: "dataset",
};

async function fetchDatasetStatus(
  dataset_uuid: string
): Promise<DatasetUploadStatus> {
  const url = apiTemplateToUrl(API_URL + API.DATASET_STATUS, { dataset_uuid });

  return await (await fetch(url, DEFAULT_FETCH_OPTIONS)).json();
}

const REFETCH_INTERVAL_MS = 10 * 1000;

export function useDatasetStatus(
  dataset_uuid: string,
  shouldFetch: boolean
): UseQueryResult<DatasetUploadStatus> {
  return useQuery<DatasetUploadStatus>(
    [USE_DATASET_STATUS, dataset_uuid],
    () => fetchDatasetStatus(dataset_uuid),
    { enabled: shouldFetch, refetchInterval: REFETCH_INTERVAL_MS }
  );
}

export const USE_DELETE_DATASET = {
  entities: [ENTITIES.DATASET],
  id: "dataset",
};

async function deleteDataset(dataset_uuid = ""): Promise<DatasetUploadStatus> {
  if (!dataset_uuid) throw new Error("No dataset id provided");

  const url = apiTemplateToUrl(API_URL + API.DATASET, { dataset_uuid });
  const response = await fetch(url, DELETE_FETCH_OPTIONS);

  if (response.ok) return await response.json();

  throw Error(response.statusText);
}

export function useDeleteDataset(collection_uuid = "") {
  if (!collection_uuid) {
    throw new Error("No collection id given");
  }

  const queryClient = useQueryClient();

  return useMutation(deleteDataset, {
    onSuccess: (uploadStatus: DatasetUploadStatus) => {
      queryClient.invalidateQueries([
        USE_COLLECTION,
        collection_uuid,
        VISIBILITY_TYPE.PRIVATE,
      ]);

      queryClient.cancelQueries([USE_DATASET_STATUS, uploadStatus.dataset_id]);

      queryClient.setQueryData(
        [USE_DATASET_STATUS, uploadStatus.dataset_id],
        uploadStatus
      );
    },
  });
}

/**
 * Query key for /datasets/uuid/assets.
 */
export const USE_DATASETS_ASSETS = {
  entities: [ENTITIES.DATASET],
  id: "datasetAsset",
};

/**
 * Cache-enabled hook for fetching assets for the dataset with the given ID.
 * @param datasetId - ID of dataset to fetch assets of.
 * @param enabled - True if fetch can be invoked.
 * @returns Dataset metadata.
 */
export function useFetchDatasetAssets(
  datasetId: string,
  enabled: boolean
): UseQueryResult<DatasetAsset[]> {
  return useQuery<DatasetAsset[]>(
    [USE_DATASETS_ASSETS, datasetId],
    () => fetchDatasetAssets(datasetId),
    { enabled }
  );
}

/**
 * Fetch assets for the dataset with the given ID.
 * @param datasetId - ID of dataset to fetch assets of.
 * @returns Promise that resolves to dataset metadata.
 */
async function fetchDatasetAssets(datasetId: string): Promise<DatasetAsset[]> {
  const { assets } = await (
    await fetch(
      apiTemplateToUrl(API_URL + API.DATASET_ASSETS, {
        dataset_uuid: datasetId,
      }),
      DEFAULT_FETCH_OPTIONS
    )
  ).json();
  return assets;
}
