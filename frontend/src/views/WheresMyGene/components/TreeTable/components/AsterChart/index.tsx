import { Container, FirstPart } from "./style";

interface Props {
  colorValue: number;
  degreeValue: number;
}

export default function AsterChart({
  colorValue,
  degreeValue,
}: Props): JSX.Element {
  return (
    <Container>
      <FirstPart colorValue={colorValue} degreeValue={degreeValue} />
    </Container>
  );
}
