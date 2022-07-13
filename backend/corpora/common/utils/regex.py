USERNAME_REGEX = r"(?P<username>[\w\-\|]+)"
ID_REGEX = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
EXTENSION_REGEX = r"(?P<extension>h5ad)"
DATASET_ID_REGEX = f"(?P<dataset_id>{ID_REGEX})"
COLLECTION_ID_REGEX = f"(?P<collection_id>{ID_REGEX})"
CURATOR_TAG_PREFIX_REGEX = r"(?P<tag_prefix>.*)"
