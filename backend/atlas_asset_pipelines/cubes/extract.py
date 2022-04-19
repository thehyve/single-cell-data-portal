import pandas as pd
import tiledb


def extract_var_data(tdb_group, ctx):
    """
    Extract var (gene) data from the concatenated corpus
    """
    with tiledb.open(f"{tdb_group}/var", ctx=ctx) as var:
        gene_ontology_term_ids = var.query(dims=["gene_ontology_term_id"], attrs=["var_idx"], use_arrow=False).df[:]
        gene_ontology_term_ids.sort_values(by="var_idx", inplace=True)

    return gene_ontology_term_ids


def extract_obs_data(tdb_group, cube_dims):
    with tiledb.open(f"{tdb_group}/obs") as obs:
        cell_labels = obs.query(use_arrow=False).df[:]
    cell_labels.sort_values(by=["obs_idx"], inplace=True, ignore_index=True)

    cell_labels = pd.DataFrame(
        data={k: cell_labels[k].astype("category") for k in cube_dims},
        index=cell_labels.obs_idx,
    )
    return cell_labels
