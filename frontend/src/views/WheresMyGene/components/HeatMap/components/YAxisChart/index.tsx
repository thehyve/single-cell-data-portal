import { init } from "echarts";
import Image from "next/image";
import { memo, useContext, useEffect, useMemo, useRef, useState } from "react";
import { EMPTY_OBJECT, noop } from "src/common/constants/utils";
import { DispatchContext } from "src/views/WheresMyGene/common/store";
import { resetTissueCellTypes } from "src/views/WheresMyGene/common/store/actions";
import { CellType, Tissue } from "src/views/WheresMyGene/common/types";
import { useDeleteGenesAndCellTypes } from "../../hooks/useDeleteGenesAndCellTypes";
import { useUpdateYAxisChart } from "../../hooks/useUpdateYAxisChart";
import {
  CellTypeMetadata,
  getAllSerializedCellTypeMetadata,
  getHeatmapHeight,
} from "../../utils";
import ReplaySVG from "./icons/replay.svg";
import {
  Container,
  HierarchyLabel,
  HierarchyWrapper,
  ResetImageWrapper,
  TissueName,
  TissueWrapper,
  Wrapper,
} from "./style";

interface Props {
  cellTypes?: CellType[];
  hasDeletedCellTypes: boolean;
  availableCellTypes: CellType[];
  tissue: Tissue;
}

export default memo(function YAxisChart({
  cellTypes = [],
  hasDeletedCellTypes,
  availableCellTypes,
  tissue,
}: Props): JSX.Element {
  const dispatch = useContext(DispatchContext);

  const [isChartInitialized, setIsChartInitialized] = useState(false);

  const { cellTypeIdsToDelete, handleCellTypeClick } =
    useDeleteGenesAndCellTypes();

  const [yAxisChart, setYAxisChart] = useState<echarts.ECharts | null>(null);
  const yAxisRef = useRef<HTMLDivElement>(null);

  const [heatmapHeight, setHeatmapHeight] = useState(
    getHeatmapHeight(cellTypes)
  );

  const textLabelGap = useRef<number | null>(null);

  // Initialize charts
  useEffect(() => {
    const { current: yAxisCurrent } = yAxisRef;

    if (!yAxisCurrent || isChartInitialized) {
      return;
    }

    setIsChartInitialized(true);

    const yAxisChart = init(yAxisCurrent, EMPTY_OBJECT, {
      renderer: "svg",
      useDirtyRect: true,
    });

    yAxisChart.on("finished", () => {
      const { current: currentYAxisChart } = yAxisRef;

      if (!currentYAxisChart) return;

      const gNode = currentYAxisChart.querySelectorAll("g")[1];

      const firstText = gNode.querySelector<SVGTextElement>(":nth-child(1)");
      const secondText = gNode.querySelector<SVGTextElement>(":nth-child(2)");

      if (!firstText || !secondText) {
        textLabelGap.current = null;
        return;
      }

      const gap =
        firstText?.transform.baseVal[0].matrix.f -
        secondText?.transform.baseVal[0].matrix.f;

      if (gap === textLabelGap.current) return;

      textLabelGap.current = gap;
    });

    setYAxisChart(yAxisChart);
  }, [isChartInitialized, textLabelGap]);

  // Update heatmap size
  useEffect(() => {
    setHeatmapHeight(getHeatmapHeight(cellTypes));
  }, [cellTypes]);

  const [, setHandleYAxisChartClick] = useState(
    () => noop as (params: { value: CellTypeMetadata }) => void
  );

  // Bind yAxisChart events
  useEffect(() => {
    setHandleYAxisChartClick(
      (oldHandle: (params: { value: CellTypeMetadata }) => void) => {
        yAxisChart?.off("click", oldHandle);

        yAxisChart?.on("click", newHandle as never);

        return newHandle;
      }
    );

    function newHandle(params: { value: CellTypeMetadata }) {
      /**
       * `value` is set by utils.getAllSerializedCellTypeMetadata()
       */
      const { value } = params;

      handleCellTypeClick(value);
    }
  }, [
    setHandleYAxisChartClick,
    handleCellTypeClick,
    dispatch,
    availableCellTypes,
    yAxisChart,
  ]);

  const cellTypeMetadata = useMemo(() => {
    return getAllSerializedCellTypeMetadata(cellTypes, tissue);
  }, [cellTypes, tissue]);

  useUpdateYAxisChart({
    cellTypeIdsToDelete,
    cellTypeMetadata,
    heatmapHeight,
    yAxisChart,
  });

  return (
    <Wrapper>
      <TissueWrapper height={heatmapHeight}>
        <TissueName>{capitalize(tissue)}</TissueName>
        <HierarchyWrapper>
          <HierarchyLabel
            height={getHierarchyLabelHeight({
              containerHeight: heatmapHeight,
              gap: textLabelGap.current,
              index: 0,
              labelCount: cellTypes.length,
            })}
          />
          <HierarchyLabel
            height={getHierarchyLabelHeight({
              containerHeight: heatmapHeight,
              gap: textLabelGap.current,
              index: 1,
              labelCount: cellTypes.length,
            })}
          />
          <HierarchyLabel
            height={getHierarchyLabelHeight({
              containerHeight: heatmapHeight,
              gap: textLabelGap.current,
              index: 2,
              labelCount: cellTypes.length,
            })}
          />
        </HierarchyWrapper>
        {hasDeletedCellTypes && (
          <ResetImageWrapper onClick={() => handleResetTissue(tissue)}>
            <Image
              src={ReplaySVG.src}
              width="12"
              height="12"
              alt="reset tissue cell types"
            />
          </ResetImageWrapper>
        )}
      </TissueWrapper>
      <Container height={heatmapHeight} ref={yAxisRef} />
    </Wrapper>
  );

  function handleResetTissue(tissue: Tissue) {
    if (!dispatch) return;

    dispatch(resetTissueCellTypes(tissue, availableCellTypes));
  }
});

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

const TEXT_HEIGHT_PX = 14;

function getHierarchyLabelHeight({
  index,
  gap,
  containerHeight,
  labelCount,
}: {
  index: number;
  gap: number | null;
  containerHeight: number;
  labelCount: number;
}): number {
  if (labelCount === 0 || !gap) return 0;
  if (labelCount === 1) return containerHeight;

  if (index === 0 || index === 2) {
    return TEXT_HEIGHT_PX + gap;
  }

  return (TEXT_HEIGHT_PX + gap) * (labelCount - 2);
}
