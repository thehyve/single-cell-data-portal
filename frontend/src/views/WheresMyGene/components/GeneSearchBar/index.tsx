import { Intent } from "@blueprintjs/core";
import { LoadingIndicator } from "czifui";
import React, { useCallback, useContext, useMemo } from "react";
import { EVENTS } from "src/common/analytics/events";
import { usePrimaryFilterDimensions, useFilterDimensions } from "src/common/queries/wheresMyGene";
import Toast from "src/views/Collection/components/Toast";
import { DispatchContext, StateContext } from "../../common/store";
import { selectGenes, selectTissues } from "../../common/store/actions";
import { Gene } from "../../common/types";
import Organism from "./components/Organism";
import QuickSelect from "./components/QuickSelect";
import { ActionWrapper, Container, LoadingIndicatorWrapper } from "./style";
interface Tissue {
  name: string;
}

export default function GeneSearchBar(): JSX.Element {
  const dispatch = useContext(DispatchContext);
  const { selectedGenes, selectedTissues, selectedOrganismId } =
    useContext(StateContext);

  const { data, isLoading } = usePrimaryFilterDimensions();
  const { data: filterDimensions } = useFilterDimensions();
  const { tissue_terms } = filterDimensions;
  //console.log(tissue_terms)
  const { genes: rawGenes } = data || {};

  const { tissues: rawTissues } = data || {};
  let tissues = useMemo(() => {
    if (!rawTissues) return [];

    const temp = rawTissues[selectedOrganismId || ""] || [];
    const tissue_term_names = tissue_terms.map((tissue)=>tissue.name);
    return temp.filter((tissue) => !tissue.name.includes("(cell culture)") && tissue_term_names.includes(tissue.name));
  }, [rawTissues, selectedOrganismId, tissue_terms]);

  const genes: Gene[] = useMemo(() => {
    if (!rawGenes) return [];

    return rawGenes[selectedOrganismId || ""] || [];
  }, [rawGenes, selectedOrganismId]);



  /**
   * NOTE: key is gene name in lowercase
   */
  const genesByName = useMemo(() => {
    return genes.reduce((acc, gene) => {
      return acc.set(gene.name.toLowerCase(), gene);
    }, new Map<Gene["name"], Gene>());
  }, [genes]);

  /**
   * NOTE: key is tissue name in lowercase
   */
  const tissuesByName = useMemo(() => {
    return tissues.reduce((acc, tissue) => {
      return acc.set(tissue.name.toLowerCase(), tissue);
    }, new Map<Tissue["name"], Tissue>());
  }, [tissues]);

  const selectedTissueOptions: Tissue[] = useMemo(() => {
    return selectedTissues.map((tissue: string) => {
      return tissuesByName.get(tissue.toLowerCase()) as Tissue;
    });
  }, [selectedTissues, tissuesByName]);

  const selectedGeneOptions: Gene[] = useMemo(() => {
    return selectedGenes.map((gene: string) => {
      return genesByName.get(gene.toLowerCase()) as Gene;
    });
  }, [selectedGenes, genesByName]);

  const handleGeneNotFound = useCallback((geneName: string): void => {
    Toast.show({
      intent: Intent.DANGER,
      message: `Gene not found: ${geneName}`,
    });
  }, []);

  return (
    <Container>
      <ActionWrapper>
        <Organism isLoading={isLoading} />

        <QuickSelect
          items={tissues}
          itemsByName={tissuesByName}
          multiple
          selected={selectedTissueOptions}
          setSelected={handleSelectTissues}
          label="Add Tissue"
          dataTestId="add-tissue"
          placeholder="Search"
          isLoading={isLoading}
          analyticsEvent={EVENTS.WMG_SELECT_TISSUE}
        />

        <QuickSelect
          items={genes}
          itemsByName={genesByName}
          selected={selectedGeneOptions}
          multiple
          setSelected={handleSelectGenes}
          onItemNotFound={handleGeneNotFound}
          label="Add Gene"
          dataTestId="add-gene"
          placeholder="Search or paste comma separated gene names"
          isLoading={isLoading}
          analyticsEvent={EVENTS.WMG_SELECT_GENE}
        />

        {isLoading && (
          <LoadingIndicatorWrapper>
            <LoadingIndicator sdsStyle="tag" />
          </LoadingIndicatorWrapper>
        )}
      </ActionWrapper>
    </Container>
  );

  function handleSelectTissues(tissues: Tissue[]) {
    if (!dispatch) return;

    dispatch(selectTissues(tissues.map((tissue) => tissue.name)));
  }

  function handleSelectGenes(genes: Gene[]) {
    if (!dispatch) return;

    dispatch(selectGenes(genes.map((gene) => gene.name)));
  }
}
