import cloneDeep from "lodash/cloneDeep";
import {
  CellTypeMetadata,
  deserializeCellTypeMetadata,
} from "../../components/HeatMap/utils";
import { CellTypeSummary, Organism, Tissue } from "../types";

export interface PayloadAction<Payload> {
  type: keyof typeof REDUCERS;
  payload: Payload;
}

export interface State {
  cellTypeIdsToDelete: CellTypeMetadata[];
  genesToDelete: string[];
  selectedGenes: string[];
  selectedCellTypeIds: {
    [tissue: Tissue]: string[];
  };
  selectedOrganism: Organism | null;
  selectedTissues: string[];
}

// (thuang): If you have derived states based on the state, use `useMemo`
// to cache the derived states instead of putting them in the state.
export const INITIAL_STATE: State = {
  cellTypeIdsToDelete: [],
  genesToDelete: [],
  selectedCellTypeIds: {},
  selectedGenes: [],
  selectedOrganism: null,
  selectedTissues: [],
};

export const REDUCERS = {
  deleteSelectedGenesAndSelectedCellTypeIds,
  resetGenesToDeleteAndCellTypeIdsToDelete,
  resetTissueCellTypes,
  selectCellTypeIds,
  selectGenes,
  selectOrganism,
  selectTissues,
  tissueCellTypesFetched,
  toggleCellTypeIdToDelete,
  toggleGeneToDelete,
};

export function reducer(state: State, action: PayloadAction<unknown>): State {
  const { type } = action;

  const handler = REDUCERS[type];

  if (!handler) {
    throw new Error(`Unknown action type: ${type}`);
  }

  /**
   * (thuang): Figuring out the typing here is more work than its rewards
   * Ideally we'll use Redux Toolkit's `createSlice` here, but I think that's
   * too heavy for now
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return handler(state, action as any);
}

/**
 * Individual action type reducers below. Please add their corresponding action
 * creators in `./actions.ts`
 */

function deleteSelectedGenesAndSelectedCellTypeIds(
  state: State,
  _: PayloadAction<null>
): State {
  const { genesToDelete, cellTypeIdsToDelete } = state;

  if (!genesToDelete.length && !cellTypeIdsToDelete.length) {
    return state;
  }

  const { selectedGenes, selectedCellTypeIds } = state;

  const newSelectedGenes = genesToDelete.length
    ? deleteByItems<State["selectedGenes"][number]>(
        selectedGenes,
        genesToDelete
      )
    : selectedGenes;

  const newSelectedCellTypeIds = cellTypeIdsToDelete.length
    ? deleteSelectedCellTypeIdsByMetadata(
        selectedCellTypeIds,
        cellTypeIdsToDelete
      )
    : selectedCellTypeIds;

  return {
    ...state,
    cellTypeIdsToDelete: [],
    genesToDelete: [],
    selectedCellTypeIds: newSelectedCellTypeIds,
    selectedGenes: newSelectedGenes,
  };
}

function selectOrganism(
  state: State,
  action: PayloadAction<Organism | null>
): State {
  return {
    ...state,
    selectedOrganism: action.payload,
  };
}

function selectGenes(
  state: State,
  action: PayloadAction<State["selectedGenes"]>
): State {
  return {
    ...state,
    cellTypeIdsToDelete: [],
    genesToDelete: [],
    selectedGenes: action.payload,
  };
}

function selectCellTypeIds(
  state: State,
  action: PayloadAction<State["selectedCellTypeIds"]>
): State {
  return {
    ...state,
    selectedCellTypeIds: action.payload,
  };
}

function selectTissues(
  state: State,
  action: PayloadAction<State["selectedTissues"]>
): State {
  return {
    ...state,
    selectedTissues: action.payload,
  };
}

function toggleGeneToDelete(
  state: State,
  action: PayloadAction<string>
): State {
  if (state.genesToDelete.includes(action.payload)) {
    return {
      ...state,
      genesToDelete: deleteByItems<string>(state.genesToDelete, [
        action.payload,
      ]),
    };
  }

  return {
    ...state,
    genesToDelete: [...state.genesToDelete, action.payload],
  };
}

function toggleCellTypeIdToDelete(
  state: State,
  action: PayloadAction<CellTypeMetadata>
): State {
  if (state.cellTypeIdsToDelete.includes(action.payload)) {
    return {
      ...state,
      cellTypeIdsToDelete: deleteByItems<CellTypeMetadata>(
        state.cellTypeIdsToDelete,
        [action.payload]
      ),
    };
  }

  return {
    ...state,
    cellTypeIdsToDelete: [...state.cellTypeIdsToDelete, action.payload],
  };
}

function deleteByItems<Item>(collection: Item[], collectionToDelete: Item[]) {
  return collection.filter((item) => !collectionToDelete.includes(item));
}

function resetGenesToDeleteAndCellTypeIdsToDelete(
  state: State,
  _: PayloadAction<null>
): State {
  return {
    ...state,
    cellTypeIdsToDelete: [],
    genesToDelete: [],
  };
}

function deleteSelectedCellTypeIdsByMetadata(
  selectedCellTypeIds: State["selectedCellTypeIds"],
  cellTypeMetadata: CellTypeMetadata[]
): State["selectedCellTypeIds"] {
  const newSelectedCellTypeIds = cloneDeep(selectedCellTypeIds);

  const cellTypeIdsToDeleteByTissue = cellTypeMetadata.reduce(
    (memo, metadata) => {
      const { tissue, id } = deserializeCellTypeMetadata(metadata);
      const cellTypeIds = memo[tissue] || [];
      memo[tissue] = [...cellTypeIds, id];

      return memo;
    },
    {} as State["selectedCellTypeIds"]
  );

  for (const [tissue, cellTypeIdsToDelete] of Object.entries(
    cellTypeIdsToDeleteByTissue
  )) {
    const tissueCellTypeIds = newSelectedCellTypeIds[tissue] || [];

    newSelectedCellTypeIds[tissue] = tissueCellTypeIds.filter(
      (id) => !cellTypeIdsToDelete.includes(id)
    );
  }

  return newSelectedCellTypeIds;
}

function tissueCellTypesFetched(
  state: State,
  action: PayloadAction<{
    tissue: Tissue;
    cellTypeSummaries: CellTypeSummary[];
  }>
): State {
  const { tissue, cellTypeSummaries } = action.payload;

  const newCellTypeIds = cellTypeSummaries.map((summary) => summary.id);

  return {
    ...state,
    selectedCellTypeIds: {
      ...state.selectedCellTypeIds,
      [tissue]: newCellTypeIds,
    },
  };
}

function resetTissueCellTypes(
  state: State,
  action: PayloadAction<{
    tissue: Tissue;
    cellTypeSummaries: CellTypeSummary[];
  }>
): State {
  return tissueCellTypesFetched(state, action);
}
