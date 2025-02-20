import { ElementHandle } from "playwright";
import { ROUTES } from "src/common/constants/routes";
import {
  describeIfDevStagingProd,
  goToPage,
  tryUntil,
} from "tests/utils/helpers";
import { TEST_URL } from "../common/constants";
import { getTestID, getText } from "../utils/selectors";

const GENE_LABELS_ID = "gene-labels";
const CELL_TYPE_LABELS_ID = "cell-type-labels";
const ADD_TISSUE_ID = "add-tissue";
const ADD_GENE_ID = "add-gene";

describeIfDevStagingProd("Where's My Gene", () => {
  it("renders the getting started UI", async () => {
    await goToPage(`${TEST_URL}${ROUTES.WHERE_IS_MY_GENE}`);

    // Getting Started section
    await expect(page).toHaveSelector(getText("Getting Started"));
    await expect(page).toHaveSelector(
      getText(
        "Use the Add Tissue and Add Gene buttons to find where genes are expressed, powered by data from the"
      )
    );
    // Beta callout
    await expect(page).toHaveSelector(getText("This feature is in beta"));

    // Filters Panel
    // (thuang): `*` is for intermediate match
    // https://playwright.dev/docs/selectors#intermediate-matches

    async function getTissueSelectorButton() {
      return page.$(getTestID(ADD_TISSUE_ID));
    }

    async function getGeneSelectorButton() {
      return page.$(getTestID(ADD_GENE_ID));
    }

    await clickUntilOptionsShowUp(getTissueSelectorButton);
    await selectFirstOption();

    await clickUntilOptionsShowUp(getGeneSelectorButton);
    await selectFirstOption();

    const filtersPanel = await page.$("*css=div >> text=Filters");

    await expect(filtersPanel).toHaveSelector(getText("Dataset"));
    await expect(filtersPanel).toHaveSelector(getText("Disease"));
    await expect(filtersPanel).toHaveSelector(getText("Ethnicity"));
    await expect(filtersPanel).toHaveSelector(getText("Sex"));

    // Info Panel
    const InfoPanel = await page.$("*css=div >> text=Info");

    await expect(InfoPanel).toHaveSelector(getText("Gene Expression"));
    await expect(InfoPanel).toHaveSelector(getText("Expressed in Cells (%)"));
    await expect(InfoPanel).toHaveSelector(getText("Methodology"));
    await expect(InfoPanel).toHaveSelector(
      getText("After filtering cells with low coverage ")
    );
    await expect(InfoPanel).toHaveSelector(getText("Source Data"));
  });

  test("Filters and Heatmap", async () => {
    await goToPage(`${TEST_URL}${ROUTES.WHERE_IS_MY_GENE}`);

    async function getTissueSelectorButton() {
      return page.$(getTestID(ADD_TISSUE_ID));
    }

    async function getGeneSelectorButton() {
      return page.$(getTestID(ADD_GENE_ID));
    }

    await clickUntilOptionsShowUp(getTissueSelectorButton);
    await selectFirstOption();

    await clickUntilOptionsShowUp(getGeneSelectorButton);
    await selectFirstOption();

    await tryUntil(async () => {
      const canvases = await page.$$("canvas");
      await expect(canvases.length).not.toBe(0);
    });

    const sexSelector = await getSexSelector();

    if (!sexSelector) throw Error("No sexSelector found");

    const selectedSexesBefore = await sexSelector.$$(".MuiChip-root");

    await expect(selectedSexesBefore.length).toBe(0);

    await clickUntilOptionsShowUp(getSexSelectorButton);

    await selectFirstOption();

    const selectedSexesAfter = await sexSelector.$$(".MuiChip-root");

    await expect(selectedSexesAfter.length).toBe(1);

    async function getFiltersPanel() {
      return page.$(getTestID("filters-panel"));
    }

    async function getSexSelector() {
      const filtersPanel = await getFiltersPanel();

      if (!filtersPanel) {
        throw Error("Filters panel not found");
      }

      return filtersPanel.$("*css=div >> text=Sex");
    }

    async function getSexSelectorButton() {
      const filtersPanel = await getFiltersPanel();

      if (!filtersPanel) {
        throw Error("Filters panel not found");
      }

      await filtersPanel.$("*css=div >> text=Sex");
      return filtersPanel.$("*css=button >> text=Sex");
    }
  });

  test("Hierarchical Clustering", async () => {
    await goToPage(`${TEST_URL}${ROUTES.WHERE_IS_MY_GENE}`);

    async function getTissueSelectorButton() {
      return page.$(getTestID(ADD_TISSUE_ID));
    }

    async function getGeneSelectorButton() {
      return page.$(getTestID(ADD_GENE_ID));
    }

    const TISSUE_COUNT = 1;
    const GENE_COUNT = 3;

    await clickUntilOptionsShowUp(getTissueSelectorButton);
    await selectFirstNOptions(TISSUE_COUNT);

    await clickUntilOptionsShowUp(getGeneSelectorButton);
    await selectFirstNOptions(GENE_COUNT);

    const beforeGeneNames = await getNames(`${getTestID(GENE_LABELS_ID)} text`);

    const beforeCellTypeNames = await getNames(
      `${getTestID(CELL_TYPE_LABELS_ID)} text`
    );

    expect(beforeGeneNames.length).toBe(GENE_COUNT);
    expect(beforeCellTypeNames.length).toBeGreaterThan(0);

    const cellTypeSortDropdown = await page.locator(
      getTestID("cell-type-sort-dropdown")
    );
    await cellTypeSortDropdown.click();
    await selectNthOption(2);

    const geneSortDropdown = await page.locator(
      getTestID("gene-sort-dropdown")
    );
    await geneSortDropdown.click();
    await selectNthOption(2);

    const afterGeneNames = await getNames(`${getTestID(GENE_LABELS_ID)} text`);

    const afterCellTypeNames = await getNames(
      `${getTestID(CELL_TYPE_LABELS_ID)} text`
    );

    await tryUntil(async () => {
      expect(afterGeneNames.length).toBe(beforeGeneNames.length);
      expect(afterCellTypeNames.length).toBe(beforeCellTypeNames.length);

      expect(afterGeneNames).not.toEqual(beforeGeneNames);
      expect(afterCellTypeNames).not.toEqual(beforeCellTypeNames);
    });
  });

  test("delete genes and cell types", async () => {
    await goToPage(`${TEST_URL}${ROUTES.WHERE_IS_MY_GENE}`);

    async function getTissueSelectorButton() {
      return page.$(getTestID(ADD_TISSUE_ID));
    }

    async function getGeneSelectorButton() {
      return page.$(getTestID(ADD_GENE_ID));
    }

    await clickUntilOptionsShowUp(getTissueSelectorButton);
    await selectFirstNOptions(1);

    await clickUntilOptionsShowUp(getGeneSelectorButton);
    await selectFirstNOptions(3);

    await tryUntil(async () => {
      const canvases = await page.$$("canvas");
      await expect(canvases.length).not.toBe(0);
    });

    const beforeGeneNames = await getNames(`${getTestID(GENE_LABELS_ID)} text`);
    const beforeCellTypeNames = await getNames(
      `${getTestID(CELL_TYPE_LABELS_ID)} text`
    );

    await page.click(getText(beforeGeneNames[0]));
    await page.click(getText(beforeCellTypeNames[0]));

    await tryUntil(async () => {
      await page.focus(getTestID(GENE_LABELS_ID));
      await page.keyboard.press("Backspace");

      const afterGeneNames = await getNames(
        `${getTestID(GENE_LABELS_ID)} text`
      );
      const afterCellTypeNames = await getNames(
        `${getTestID(CELL_TYPE_LABELS_ID)} text`
      );

      expect(afterGeneNames.length).toBe(beforeGeneNames.length - 1);

      // (thuang): We need to half the cellTypeName count, because it's grabbing
      // Cell Count text elements as well.
      expect(afterCellTypeNames.length / 2).toBe(
        beforeCellTypeNames.length / 2 - 1
      );

      expect(afterGeneNames).not.toEqual(beforeGeneNames);
      expect(afterCellTypeNames).not.toEqual(beforeCellTypeNames);
    });

    const RESET_CELL_TYPES_BUTTON_ID = "reset-cell-types";

    await tryUntil(async () => {
      await page.click(getTestID(RESET_CELL_TYPES_BUTTON_ID));

      const resetCellTypesButton = await page.$(
        getTestID(RESET_CELL_TYPES_BUTTON_ID)
      );

      expect(resetCellTypesButton).toBe(null);
    });

    await tryUntil(async () => {
      const afterCellTypeNames = await getNames(
        `${getTestID(CELL_TYPE_LABELS_ID)} text`
      );

      expect(afterCellTypeNames.length).toBe(beforeCellTypeNames.length);
      expect(afterCellTypeNames).toEqual(beforeCellTypeNames);
    });
  });
});

async function getNames(selector: string): Promise<string[]> {
  const geneLabelsLocator = await page.locator(selector);

  await tryUntil(async () => {
    const names = await geneLabelsLocator.allTextContents();
    expect(typeof names[0]).toBe("string");
  });

  return geneLabelsLocator.allTextContents();
}

async function clickUntilOptionsShowUp(
  getTarget: () => Promise<ElementHandle<SVGElement | HTMLElement> | null>
) {
  await tryUntil(async () => {
    const target = await getTarget();

    if (!target) throw Error("no target");

    await target.click();
    const tooltip = await page.$("[role=tooltip]");

    if (!tooltip) throw Error("no tooltip");

    const options = await tooltip.$$("[role=option]");

    if (!options?.length) throw Error("no options");
  });
}

// (thuang): This only works when a dropdown is open
async function selectFirstOption() {
  await selectFirstNOptions(1);
}

async function selectFirstNOptions(count: number) {
  for (let i = 0; i < count; i++) {
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
  }

  await page.keyboard.press("Escape");
}

async function selectNthOption(number: number) {
  for (let i = 0; i < number; i++) {
    await page.keyboard.press("ArrowDown");
  }

  await page.keyboard.press("Enter");
  await page.keyboard.press("Escape");
}
