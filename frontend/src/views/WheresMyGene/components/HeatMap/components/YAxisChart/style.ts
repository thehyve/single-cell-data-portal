import styled from "styled-components";
import { X_AXIS_CHART_HEIGHT_PX, Y_AXIS_CHART_WIDTH_PX } from "../../utils";

const Y_AXIS_TISSUE_WIDTH_PX = 110;

export const Wrapper = styled.div`
  display: flex;
  margin-bottom: ${X_AXIS_CHART_HEIGHT_PX}px;
  margin-right: ${Y_AXIS_TISSUE_WIDTH_PX}px;
  width: ${Y_AXIS_CHART_WIDTH_PX}px;
`;

const TISSUE_BORDER_WIDTH_PX = 5;

export const TissueWrapper = styled.div`
  ${yAxisHeight}

  display: flex;
  background-color: white;
  border-right: ${TISSUE_BORDER_WIDTH_PX}px solid black;
  width: ${Y_AXIS_TISSUE_WIDTH_PX}px;
  padding-left: ${TISSUE_BORDER_WIDTH_PX}px;
  position: relative;
`;

export const TissueName = styled.div`
  text-orientation: sideways;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-size: 12px;
  font-weight: bold;
  text-align: center;
`;

export const Container = styled.div`
  ${yAxisHeight}

  background-color: white;
  width: ${Y_AXIS_CHART_WIDTH_PX}px;
`;

export const ResetImageWrapper = styled.div`
  margin-top: 3px;
  cursor: pointer;
`;

function yAxisHeight({ height }: { height: number }) {
  return `
    height: ${height - X_AXIS_CHART_HEIGHT_PX}px;
  `;
}

// GET THE F VALUE
// GET THE F VALUE
// GET THE F VALUE
// GET THE F VALUE
// temp1.transform.baseVal[0].matrix.f

export const HierarchyWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

export const HierarchyLabel = styled.div`
  background-color: pink;
  width: 25px;

  ${({ height }: { height: number }) => `
    height: ${height}px;
  `}
`;
