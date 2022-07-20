"""
Destroys and recreates database.
"""

from backend.corpora.common.entities.tiledb_data import TileDBData


def create_db():
    location = "tests/unit/backend/fixtures/test_tiledb/metadata" # TODO: config this somewhere
    print("Destroying db")
    TileDBData.destroy_db(location)
    print("Recreating db")
    TileDBData.init_db(location)


if __name__ == "__main__":
    create_db()
