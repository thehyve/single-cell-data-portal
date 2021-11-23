import { Menu, MenuItem } from "@blueprintjs/core";
import {
  IItemListRendererProps,
  IItemRendererProps,
  MultiSelect,
} from "@blueprintjs/select";
import { forwardRef, useEffect, useState } from "react";
import { FixedSizeList } from "react-window";
import { Gene } from "../../common/types";
import GENES from "../../mocks/lung_tissue_genes.json";

interface Props {
  onGenesChange: (selectedGenes: Gene[]) => void;
}

interface ExtendedItemRendererProps extends IItemRendererProps {
  item: Gene;
  isSelected: boolean;
}

export default function GeneSearchBar({ onGenesChange }: Props): JSX.Element {
  const [selectedGenes, setSelectedGenes] = useState<Gene[]>(
    GENES.slice(0, 100)
  );
  // const [selectedGenes, setSelectedGenes] = useState<Gene[]>([]);

  useEffect(() => {
    onGenesChange(selectedGenes);
  }, [onGenesChange, selectedGenes]);

  return (
    <MultiSelect
      itemPredicate={itemPredicate}
      onItemSelect={handleItemSelect}
      onRemove={handleItemRemove}
      items={GENES}
      itemRenderer={renderItem}
      tagRenderer={TagRenderer}
      itemsEqual={areGenesEqual}
      selectedItems={selectedGenes}
      itemListRenderer={itemListRenderer}
    />
  );

  function itemListRenderer(listProps: IItemListRendererProps<Gene>) {
    const {
      filteredItems,
      renderItem: propRenderItem,
      itemsParentRef,
    } = listProps;

    return (
      <FixedSizeList
        // eslint-disable-next-line react/display-name
        innerElementType={forwardRef((props, ref) => {
          return <Menu ulRef={itemsParentRef} ref={ref} {...props} />;
        })}
        height={300}
        overscanCount={5}
        width="100%"
        itemCount={filteredItems.length}
        itemSize={24}
      >
        {(props) => {
          const { index, style } = props;

          return propRenderItem({ ...filteredItems[index], style }, index);
        }}
      </FixedSizeList>
    );
  }

  function handleItemSelect(gene: Gene) {
    if (isGeneSelected(gene)) {
      handleItemRemove(gene);
    } else {
      setSelectedGenes((prevSelectedGenes) => [...prevSelectedGenes, gene]);
    }
  }

  function handleItemRemove(gene: Gene) {
    setSelectedGenes(
      selectedGenes.filter((selectedGene) => selectedGene.id !== gene.id)
    );
  }

  function renderItem(gene: Gene, itemRendererProps: IItemRendererProps) {
    return ItemRenderer({
      isSelected: isGeneSelected(gene),
      item: gene,
      ...itemRendererProps,
    });
  }

  function isGeneSelected(gene: Gene): boolean {
    return Boolean(
      selectedGenes.find((selectedGene) => selectedGene.id === gene.id)
    );
  }
}

function ItemRenderer({
  item,
  handleClick,
  query,
  isSelected,
}: ExtendedItemRendererProps): JSX.Element | null {
  const { name, style } = item;

  return (
    <MenuItem
      active={isSelected}
      key={name}
      onClick={handleClick}
      text={highlightText(name, query)}
      style={{ ...style }}
    />
  );
}

function itemPredicate(query: string, item: Gene) {
  return item.name.toLowerCase().indexOf(query.toLowerCase()) >= 0;
}

function highlightText(text: string, query: string) {
  let lastIndex = 0;
  const words = query
    .split(/\s+/)
    .filter((word) => word.length > 0)
    .map(escapeRegExpChars);
  if (words.length === 0) {
    return [text];
  }
  const regexp = new RegExp(words.join("|"), "gi");
  const tokens: React.ReactNode[] = [];
  // eslint-disable-next-line no-constant-condition -- expected use
  while (true) {
    const match = regexp.exec(text);
    if (!match) {
      break;
    }
    const wordLength = match[0].length;
    const before = text.slice(lastIndex, regexp.lastIndex - wordLength);
    if (before.length > 0) {
      tokens.push(before);
    }
    lastIndex = regexp.lastIndex;
    tokens.push(<strong key={lastIndex}>{match[0]}</strong>);
  }
  const rest = text.slice(lastIndex);
  if (rest.length > 0) {
    tokens.push(rest);
  }
  return tokens;
}

function escapeRegExpChars(text: string) {
  return text.replace(/([.*+?^=!:${}()|[\]/\\])/g, "\\$1");
}

function TagRenderer({ name }: Gene) {
  return name;
}

function areGenesEqual(geneA: Gene, geneB: Gene) {
  // Compare only the names (ignoring case) just for simplicity.
  return geneA.id.toLowerCase() === geneB.id.toLowerCase();
}
