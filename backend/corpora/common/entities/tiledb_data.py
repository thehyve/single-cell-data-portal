import os
import shutil
import numpy as np
import tiledb
import uuid
import ast
import time

"""
SCHEMA WITH TILEDB VERSIONING:

s3://single-cell-corpus/

    metadata/ [GROUP]
        collections [ARRAY]
            - uuid
            - owner
            - published
            - revision_of
            - datasets
            - other metadata
        datasets [ARRAY]
            - uuid
            - name
            - other metadata

    datasets/<UUID>/
        artifacts/
        <UUID>.h5ad
        <UUID>.rds
        <UUID>.cxg
    wmg/<SNAPSHOT>/
    soma/<SNAPSHOT>/
"""

class Utils():
    attrs = {
        "collections": [
            # API
            "name",
            "description",
            "contact_name",
            "contact_email",
            "links",
            "datasets",
            "curator_name",
            "created_at",
            "updated_at",
            "published_at",
            "publisher_metadata",
            # internal TileDB schema
            "published",
            "revision_of",
            "owner",
        ],
        "datasets": [

        ]
    }
       
    attrs_to_parse = {
        "collections":   [
            "links",
            "datasets",
            "publisher_metadata"
        ],
        "datasets": [

        ]
    }
  
    @staticmethod
    def new_id():
        return uuid.uuid4().hex

    # TODO: figure out actual list and dict support in TileDB
    @staticmethod
    def parse_stored_data(data: dict, array: str) -> dict:
        for a in Utils.attrs_to_parse[array]:
            data[a] = ast.literal_eval(data[a])
        return data

    @staticmethod
    def pack_input_data(data: dict, array: str) -> dict:
        for a in Utils.attrs_to_parse[array]:
            data[a] = str(data[a])
        return data




class TileDBData():
    # for testing purposes
    @staticmethod
    def init_db(location):
        # create group
        if os.path.exists(location):
            shutil.rmtree(location)

        tiledb.group_create(location)

        # create collections array
        # TODO: figure out ideal domain and tile
        # TODO: should we use more than one dimension?
        dim1 = tiledb.Dim(name="id", domain=(None, None), tile=2, dtype="S0")
        dom = tiledb.Domain(dim1)

        a1 = tiledb.Attr(name="owner", dtype="U1")
        a2 = tiledb.Attr(name="published", dtype=np.int32) # 0=private, 1=published, -1=deleted
        a3 = tiledb.Attr(name="name", dtype="U1")
        a4 = tiledb.Attr(name="description", dtype="U1")
        a5 = tiledb.Attr(name="contact_name", dtype="U1")
        a6 = tiledb.Attr(name="contact_email", dtype="U1")
        a7 = tiledb.Attr(name="links", dtype="U1")
        a8 = tiledb.Attr(name="datasets", dtype="U1")
        a9 = tiledb.Attr(name="revision_of", dtype="U1")
        a10 = tiledb.Attr(name="curator_name", dtype="U1")
        a11 = tiledb.Attr(name="created_at", dtype=np.float32)
        a12 = tiledb.Attr(name="updated_at", dtype=np.float32)
        a13 = tiledb.Attr(name="publisher_metadata", dtype="U1")

        schema = tiledb.ArraySchema(domain=dom, sparse=True, attrs=[a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13])
        array = location + "/collections"
        tiledb.Array.create(array, schema)

        # create datasets array
        # TODO: add more attributes as needed
        a1 = tiledb.Attr(name="name", dtype="U1")
        a2 = tiledb.Attr(name="artifact_id", dtype="U1")
        schema = tiledb.ArraySchema(domain=dom, sparse=True, attrs=[a1, a2])
        array = location + "/datasets"
        tiledb.Array.create(array, schema)

    # for testing purposes
    @staticmethod
    def destroy_db(location):
        shutil.rmtree(location)

    def __init__(self, location):
        self.location = location

    def create_collection(
        self,
        name: str = "",
        description: str = "",
        owner: str = "",
        contact_name: str = "",
        contact_email: str = "",
        curator_name: str = "",
        links: list = None,
    ):
        id = Utils.new_id()
        with tiledb.open(self.location + "/collections", "w") as A:
            A[id] = Utils.pack_input_data({
                "published": False,
                "name": name,
                "description": description,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "links": links, 
                "owner": owner,
                "datasets": [],
                "revision_of": "",
                "curator_name": curator_name,
                "created_at": time.time(),
                "updated_at": time.time(),
                "publisher_metadata": None
            }, "collections")
        return id

    def get_collection(self, id):
        with tiledb.open(self.location + "/collections", 'r') as A:
            return A[id]

    def get_all_collections(self):
        with tiledb.open(self.location + "/collections", mode="r") as A:
            qc = tiledb.QueryCondition(f"published == 1")
            q = A.query(attr_cond=qc)
            res = q.df[:].to_dict("records")
            for i in res:
                res[i]['publisher_metadata'] = ast.literal_eval(res[i]['publisher_metadata'])
            return res

    def get_published_collections(self, user_id, from_date, to_date):
        with tiledb.open(self.location + "/collections", mode="r") as A:
            qc = tiledb.QueryCondition(f"owner == {user_id} and created_at >= {from_date} and created_at <= {to_date} and published == 1")
            q = A.query(attr_cond=qc)["created_at", "id"]
            res = q.df[:].to_dict("records")
            return res

    def get_attribute(self, id, attr):
        coll = self.get_collection(id)
        data = coll[attr][0]
        if attr in Utils.attrs_to_parse["collections"]:
            data = ast.literal_eval(data)
        return data

    def edit_collection(self, id, key, val):
        new_data = None
        with tiledb.open(self.location + "/collections", "r") as A:
            data = A[id]
            new_data = {}
            for attr in Utils.attrs["collections"]:
                new_data[attr] = data[attr][0]
            new_data[key] = val
            new_data["updated_at"] = time.time()
            new_data = Utils.pack_input_data(new_data, "collections")
            
        with tiledb.open(self.location + "/collections", "w") as A:
            A[id] = new_data

    def publish_collection(self, id):
        self.edit_collection(id, "published", 1)

    def add_dataset(self, coll_id, name, artifact_id):
        id = Utils.new_id()
        datasets = self.get_attribute(coll_id, "datasets")
        datasets.append(id)
        self.edit_collection(coll_id, "datasets", datasets)
        with tiledb.open(self.location + "/datasets", "w") as A:
            A[id] = Utils.pack_input_data({
                "name": name,
                "artifact_id": artifact_id
            }, "datasets")
        return id

    def get_dataset(self, id):
        with tiledb.open(self.location + "/datasets", 'r') as A:
            return A[id]

    def edit_dataset(self, id, key, val):
        new_data = None
        with tiledb.open(self.location + "/datasets", "r") as A:
            data = A[id]
            new_data = {}
            for attr in Utils.attrs["datasets"]:
                new_data[attr] = data[attr][0]
            new_data[key] = val
            
        with tiledb.open(self.location + "/datasets", "w") as A:
            A[id] = new_data

    def delete_dataset(self, coll_id: str, dataset_id: str):
        datasets = self.get_attribute(coll_id, "datasets")
        datasets.remove(dataset_id)
        self.edit_collection(coll_id, "datasets", datasets)
    
    def get_datasets(self, coll_id):
        ids = self.get_attribute(coll_id, "datasets")
        data = []
        with tiledb.open(self.location + "/datasets", 'r') as A:
            for id in ids:
                data.append(A[id])
        return data

    # TODO: maybe we also want the ability to read and revert based on timestamp, not just number of versions
    def read_collection_history(self, id, steps_back):
        fragments_info = tiledb.array_fragments(self.location + "/collections")
        if steps_back > len(fragments_info):
            raise IndexError("too many steps back in time")
        steps_idx = len(fragments_info) - steps_back - 1
        times = fragments_info.timestamp_range[steps_idx]

        with tiledb.open(self.location + "/collections", 'r', timestamp=times) as A:
            return A[id]

    def revert_collection_history(self, id, steps_back):
        fragments_info = tiledb.array_fragments(self.location + "/collections")
        if steps_back > len(fragments_info):
            raise IndexError("too many steps back in time")
        steps_idx = len(fragments_info) - steps_back - 1
        times = fragments_info.timestamp_range[steps_idx]

        data = None
        with tiledb.open(self.location + "/collections", 'r', timestamp=times) as A:
            data = A[id]

        # overwrite with old data
        new_data = {}
        for attr in Utils.attrs["collections"]:
            new_data[attr] = data[attr][0]
        new_data["updated_at"] = time.time()
        new_data = Utils.pack_input_data(new_data, "collections")
        with tiledb.open(self.location + "/collections", 'w') as A:
            A[id] = new_data

    def read_dataset_history(self, id, steps_back):
        fragments_info = tiledb.array_fragments(self.location + "/datasets")
        if steps_back > len(fragments_info):
            raise IndexError("too many steps back in time")
        steps_idx = len(fragments_info) - steps_back - 1
        times = fragments_info.timestamp_range[steps_idx]

        with tiledb.open(self.location + "/datasets", 'r', timestamp=times) as A:
            return A[id]

    def revert_dataset_history(self, id, steps_back):
        fragments_info = tiledb.array_fragments(self.location + "/datasets")
        if steps_back > len(fragments_info):
            raise IndexError("too many steps back in time")
        steps_idx = len(fragments_info) - steps_back - 1
        times = fragments_info.timestamp_range[steps_idx]

        data = None
        with tiledb.open(self.location + "/datasets", 'r', timestamp=times) as A:
            data = A[id]

        # overwrite with old data
        new_data = {
            "name": data['name'][0],
            "artifact_id": data['artifact_id'][0]
        }
        with tiledb.open(self.location + "/datasets", 'w') as A:
            A[id] = new_data

    def create_revision(self, coll_id):
        id = Utils.new_id()
        coll = self.get_collection(coll_id)
        data = {}
        for attr in Utils.attrs["collections"]:
            data[attr] = coll[attr][0]
        data['revision_of'] = coll_id
        data["published"] = 0
        with tiledb.open(self.location + "/collections", "w") as A:
            A[id] = data
        return id

    def publish_revision(self, id):
        # get revision data
        revision = self.get_collection(id)
        data = {}
        for attr in Utils.attrs["collections"]:
            data[attr] = revision[attr][0]
        data['published'] = 0
        data['revision_of'] = ""
        # write data to existing revision_of collection
        revision_of = revision["revision_of"][0]
        with tiledb.open(self.location + "/collections", "w") as A:
            A[revision_of] = data
        # delete the revision
        self.delete_collection(id)

    def delete_collection(self, id):
        self.edit_collection(id, "published", -1)

    # TODO: functions for handling dataset artifacts (non-TileDB files)
