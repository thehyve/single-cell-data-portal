import json
import unittest
from unittest.mock import patch, Mock

from backend.corpora.common.corpora_orm import (
    CollectionVisibility,
    ProcessingStatus,
    DatasetArtifactFileType,
    DbDataset,
)
from tests.unit.backend.corpora.api_server.base_api_test import BaseAuthAPITest, mock_assert_authorized_token
from tests.unit.backend.fixtures.config import fake_s3_file


class TestAuthToken(BaseAuthAPITest):
    @patch("backend.corpora.lambdas.api.v1.curation.collections.collection_id.datasets.upload_s3.sts_client")
    def test__generate_s3_credentials__OK(self, sts_client: Mock):
        def _test(token, is_super_curator: bool = False):
            sts_client.assume_role_with_web_identity = Mock(
                return_value={
                    "Credentials": {
                        "AccessKeyId": "test_key",
                        "SecretAccessKey": "test_session_token",
                        "SessionToken": "test_session_token",
                    }
                }
            )
            collection = self.generate_collection(self.session)
            headers = {"Authorization": f"Bearer {token}"}

            response = self.app.get(
                f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials", headers=headers
            )
            self.assertEqual(200, response.status_code)
            token_sub = mock_assert_authorized_token(token)["sub"]
            self.assertEqual(response.json["Bucket"], "cellxgene-dataset-submissions-test")
            if is_super_curator:
                self.assertEqual(response.json["UploadKeyPrefix"], f"super/{collection.id}/")
            else:
                self.assertEqual(response.json["UploadKeyPrefix"], f"{token_sub}/{collection.id}/")

        with self.subTest("collection owner"):
            _test("owner")

        with self.subTest("super curator"):
            _test("super", is_super_curator=True)

    def test__generate_s3_credentials__Not_Owner(self):
        collection = self.generate_collection(self.session, owner="not_test_user")
        response = self.app.get(
            f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials", headers=self.make_owner_header()
        )
        self.assertEqual(403, response.status_code, msg=response.data)

    def test__generate_s3_credentials__Not_Private(self):
        collection = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC.name)
        response = self.app.get(
            f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials", headers=self.make_owner_header()
        )
        self.assertEqual(403, response.status_code)

    def test__generate_s3_credentials__No_Auth(self):
        collection = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC.name)
        response = self.app.get(f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials")
        self.assertEqual(401, response.status_code)


class TestPostCollection(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__create_collection__no_auth(self):
        response = self.app.post("/curation/v1/collections", data=json.dumps(self.test_collection))
        self.assertEqual(401, response.status_code)

    def test__create_collection__OK(self):
        response = self.app.post(
            "/curation/v1/collections", headers=self.make_owner_header(), data=json.dumps(self.test_collection)
        )
        self.assertEqual(201, response.status_code)

    def test__create_collection__InvalidParameters(self):
        tests = [
            (
                dict(
                    name="",
                    description="",
                    contact_name="",
                    contact_email="@email.com",
                    links=[{"link_type": "DOI", "link_url": "bad_doi"}],
                ),
                [
                    {"name": "contact_email", "reason": "Invalid format."},
                    {"name": "description", "reason": "Cannot be blank."},
                    {"name": "name", "reason": "Cannot be blank."},
                    {"name": "contact_name", "reason": "Cannot be blank."},
                    {"link_type": "DOI", "reason": "Invalid DOI"},
                ],
            ),
            (
                dict(
                    name="not blank",
                    description="description",
                    contact_name="some name",
                    contact_email="robot@email.com",
                    links=[
                        {"link_type": "DOI", "link_url": "doi:duplicated"},
                        {"link_type": "DOI", "link_url": "doi:duplicated"},
                    ],
                ),
                [{"link_type": "DOI", "reason": "Can only specify a single DOI"}],
            ),
        ]
        for body, expected_errors in tests:
            with self.subTest(body):
                response = self.app.post(
                    "/curation/v1/collections", headers=self.make_owner_header(), data=json.dumps(body)
                )
                self.assertEqual(400, response.status_code)
                for error in expected_errors:
                    self.assertIn(error, response.json["detail"])


class TestGetCollections(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__get_collections_no_auth__OK(self):
        res_no_auth = self.app.get("/curation/v1/collections")
        self.assertEqual(200, res_no_auth.status_code)
        self.assertEqual(6, len(res_no_auth.json["collections"]))
        [self.assertEqual("PUBLIC", c["visibility"]) for c in res_no_auth.json["collections"]]

    def test__get_collections_with_auth__OK(self):
        res_auth = self.app.get("/curation/v1/collections", headers=self.make_owner_header())
        self.assertEqual(200, res_auth.status_code)
        self.assertEqual(6, len(res_auth.json["collections"]))

    def test__get_collections_no_auth_visibility_private__OK(self):
        params = {"visibility": "PRIVATE"}
        res_private = self.app.get("/curation/v1/collections", query_string=params)
        self.assertEqual(401, res_private.status_code)

    def test__get_collections_no_auth_visibility_public__OK(self):
        params = {"visibility": "PUBLIC"}
        res_public = self.app.get("/curation/v1/collections", query_string=params)
        self.assertEqual(200, res_public.status_code)
        self.assertEqual(6, len(res_public.json["collections"]))

    def test__get_only_public_collections_with_auth__OK(self):
        params = {"visibility": "PUBLIC"}
        res = self.app.get("/curation/v1/collections", query_string=params, headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual(6, len(res.json["collections"]))
        [self.assertEqual("PUBLIC", c["visibility"]) for c in res.json["collections"]]

    def test__get_only_private_collections_with_auth__OK(self):
        second_collection = self.generate_collection(self.session)
        for status in (ProcessingStatus.PENDING, ProcessingStatus.SUCCESS):
            self.generate_dataset(
                self.session,
                collection_id=second_collection.id,
                processing_status={"processing_status": status},
            ).id
        params = {"visibility": "PRIVATE"}
        res = self.app.get("/curation/v1/collections", query_string=params, headers=self.make_owner_header())
        with self.subTest("Summary collection-level processing statuses are accurate"):
            for collection in res.json["collections"]:
                if collection["id"] == second_collection.id:
                    self.assertEqual(collection["processing_status"], "PENDING")
                else:
                    self.assertEqual(collection["processing_status"], "SUCCESS")
        self.assertEqual(200, res.status_code)
        self.assertEqual(2, len(res.json["collections"]))
        [self.assertEqual("PRIVATE", c["visibility"]) for c in res.json["collections"]]

    def test__no_tombstoned_collections_or_datasets_included(self):
        second_collection = self.generate_collection(
            self.session, tombstone=False, name="second collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=second_collection.id)
        self.generate_dataset(self.session, collection_id=second_collection.id, tombstone=True)
        tombstoned_collection = self.generate_collection(
            self.session, tombstone=True, name="second collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=tombstoned_collection.id, tombstone=True)

        res = self.app.get("/curation/v1/collections", headers=self.make_owner_header())

        contains_tombstoned_collection_flag = False
        for collection in res.json["collections"]:
            if collection["id"] == second_collection.id:
                self.assertEqual(1, len(collection["datasets"]))
            if collection["id"] == tombstoned_collection.id:
                contains_tombstoned_collection_flag = True
        self.assertEqual(False, contains_tombstoned_collection_flag)


class TestGetCollectionID(BaseAuthAPITest):
    expected_body = {
        "collection_url": "http://frontend.corporanet.local:3000/collections/test_collection_id",
        "contact_email": "somebody@chanzuckerberg.com",
        "contact_name": "Some Body",
        "curator_name": "",
        "datasets": [
            {
                "assay": [{"label": "test_assay", "ontology_term_id": "test_obo"}],
                "cell_count": None,
                "cell_type": [{"label": "test_cell_type", "ontology_term_id": "test_opo"}],
                "curator_tag": None,
                "dataset_assets": [{"filename": "test_filename", "filetype": "H5AD"}],
                "development_stage": [{"label": "test_development_stage", "ontology_term_id": "test_obo"}],
                "disease": [
                    {"label": "test_disease", "ontology_term_id": "test_obo"},
                    {"label": "test_disease2", "ontology_term_id": "test_obp"},
                    {"label": "test_disease3", "ontology_term_id": "test_obq"},
                ],
                "ethnicity": [{"label": "test_ethnicity", "ontology_term_id": "test_obo"}],
                "explorer_url": "test_url",
                "id": "test_dataset_id",
                "is_primary_data": "PRIMARY",
                "mean_genes_per_cell": 0.0,
                "name": "test_dataset_name",
                "organism": [{"label": "test_organism", "ontology_term_id": "test_obo"}],
                "processing_status": "PENDING",
                "revised_at": None,
                "revision": 0,
                "schema_version": "2.0.0",
                "sex": [
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                "tissue": [{"label": "test_tissue", "ontology_term_id": "test_obo"}],
                "tombstone": False,
                "x_approximate_distribution": "NORMAL",
                "x_normalization": "test_x_normalization",
            }
        ],
        "description": "test_description",
        "id": "test_collection_id",
        "links": [
            {"link_name": "test_doi_link_name", "link_type": "DOI", "link_url": "http://test_doi_url.place"},
            {"link_name": None, "link_type": "DOI", "link_url": "http://test_no_link_name_doi_url.place"},
            {
                "link_name": "test_raw_data_link_name",
                "link_type": "RAW_DATA",
                "link_url": "http://test_raw_data_url.place",
            },
            {"link_name": None, "link_type": "RAW_DATA", "link_url": "http://test_no_link_name_raw_data_url.place"},
            {
                "link_name": "test_protocol_link_name",
                "link_type": "PROTOCOL",
                "link_url": "http://test_protocol_url.place",
            },
            {"link_name": None, "link_type": "PROTOCOL", "link_url": "http://test_no_link_name_protocol_url.place"},
            {
                "link_name": "test_lab_website_link_name",
                "link_type": "LAB_WEBSITE",
                "link_url": "http://test_lab_website_url.place",
            },
            {
                "link_name": None,
                "link_type": "LAB_WEBSITE",
                "link_url": "http://test_no_link_name_lab_website_url.place",
            },
            {"link_name": "test_other_link_name", "link_type": "OTHER", "link_url": "http://test_other_url.place"},
            {"link_name": None, "link_type": "OTHER", "link_url": "http://test_no_link_name_other_url.place"},
            {
                "link_name": "test_data_source_link_name",
                "link_type": "DATA_SOURCE",
                "link_url": "http://test_data_source_url.place",
            },
            {
                "link_name": None,
                "link_type": "DATA_SOURCE",
                "link_url": "http://test_no_link_name_data_source_url.place",
            },
        ],
        "name": "test_collection_name",
        "published_at": None,
        "publisher_metadata": None,
        "revised_at": None,
        "revision_of": None,
        "tombstone": False,
        "visibility": "PUBLIC",
    }

    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__get_public_collection_verify_body_is_reshaped_correctly__OK(self):
        dataset = self.session.query(DbDataset).filter(DbDataset.id == "test_dataset_id").one_or_none()
        self.assertIsInstance(dataset.organism, list)
        # Make this entry a dict instead of a list to test ability of the handler to reshape to list/array
        dataset.organism = dataset.organism[0]
        self.session.flush()
        dataset_modified = self.session.query(DbDataset).filter(DbDataset.id == "test_dataset_id").one_or_none()
        self.assertIsInstance(dataset_modified.organism, dict)

        res = self.app.get("/curation/v1/collections/test_collection_id")
        self.assertEqual(200, res.status_code)
        res_body = res.json
        del res_body["created_at"]  # too finicky; ignore
        self.assertTrue("access_type" not in res_body)
        self.assertDictEqual(self.expected_body, res_body)  # Confirm dict has been packaged in list

    def test__get_private_collection__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_revision")
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_revision", res.json["id"])
        self.assertTrue("access_type" not in res.json)

    def test__get_nonexistent_collection__Not_Found(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_nonexistent")
        self.assertEqual(404, res.status_code)

    def test__get_tombstoned_collection__Not_Found(self):
        tombstoned_collection = self.generate_collection(
            self.session, tombstone=True, name="tombstoned collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=tombstoned_collection.id, tombstone=True)
        res = self.app.get(f"/curation/v1/collections/{tombstoned_collection.id}")
        self.assertEqual(404, res.status_code)

    def test__get_collection_with_tombstoned_datasets__OK(self):
        collection = self.generate_collection(
            self.session, tombstone=False, name="collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=collection.id, tombstone=False)
        self.generate_dataset(self.session, collection_id=collection.id, tombstone=True)
        res = self.app.get(f"/curation/v1/collections/{collection.id}")
        self.assertEqual(1, len(res.json["datasets"]))

    def test__get_public_collection_with_auth_access_type_write__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id", res.json["id"])
        self.assertEqual("WRITE", res.json["access_type"])

    def test__get_public_collection_with_auth_access_type_read__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_not_owner", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_not_owner", res.json["id"])
        self.assertEqual("READ", res.json["access_type"])

    def test__get_private_collection_with_auth_access_type_write__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_revision", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_revision", res.json["id"])
        self.assertEqual("WRITE", res.json["access_type"])


class TestPatchCollectionID(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection",
            description="description",
            contact_name="john doe",
            contact_email="johndoe@email.com",
        )
        self.generate_collection(
            self.session,
            id="test_curator_tag_collection_id",
            visibility=CollectionVisibility.PUBLIC.name,
            owner="owner",
            name="test_collection_name",
            description="test_description",
            data_submission_policy_version="0",
            contact_name="Some Body",
            contact_email="somebody@chanzuckerberg.com",
        )
        self.generate_dataset(
            self.session,
            id="test_curator_tag",
            curator_tag="curator_tag",
            revision=0,
            name="test_dataset_name",
            schema_version="2.0.0",
            collection_id="test_curator_tag_collection_id",
            artifacts=[
                dict(
                    filename="test_filename",
                    filetype=DatasetArtifactFileType.H5AD.name,
                    user_submitted=True,
                    s3_uri=fake_s3_file,
                )
            ],
        )

    def test__update_collection__no_auth(self):
        collection_id = self.generate_collection(self.session).id
        response = self.app.patch(f"/curation/v1/collections/{collection_id}", data=json.dumps(self.test_collection))
        self.assertEqual(401, response.status_code)

    def test__update_collection__OK(self):
        collection_id = self.generate_collection(self.session).id
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            data=json.dumps(self.test_collection),
            headers=self.make_owner_header(),
        )
        self.assertEqual(200, response.status_code)

    @patch("backend.corpora.common.entities.Collection.get_doi")
    # Patch Collection.get_doi to ensure the additional collection.update call is made in the update_collection method
    def test__update_collection_partial_data__OK(self, get_doi: Mock):
        get_doi.return_value = "stub:doi"
        links = [{"link_name": "name", "link_type": "RAW_DATA", "link_url": "http://test_link.place"}]
        name = "partial updates test collection"
        description = "some description"
        contact_name = "first last"
        contact_email = "first@email.top_level_domain"

        # Update the name ONLY
        new_name = "partial updates 2"
        collection = self.generate_collection(
            self.session,
            name=name,
            description=description,
            contact_name=contact_name,
            contact_email=contact_email,
            links=links,
        )
        collection_id = collection.id

        metadata = {"name": new_name}
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            data=json.dumps(metadata),
            headers=self.make_owner_header(),
        )
        self.assertEqual(200, response.status_code)
        response = self.app.get(f"curation/v1/collections/{collection_id}")
        self.assertEqual(response.json["name"], new_name)
        self.assertEqual(response.json["description"], description)
        self.assertEqual(response.json["contact_name"], contact_name)
        self.assertEqual(response.json["contact_email"], contact_email)
        self.assertEqual(response.json["links"], links)

    @patch("backend.corpora.common.entities.Collection.get_doi")
    # Patch Collection.get_doi to ensure the additional collection.update call is made in the update_collection method
    def test__update_collection__links_management__OK(self, get_doi: Mock):
        get_doi.return_value = "stub:doi"
        links = [
            {"link_name": "name", "link_type": "RAW_DATA", "link_url": "http://test_link.place"},
            {"link_name": "second link name", "link_type": "RAW_DATA", "link_url": "http://other_test_link.place"},
        ]
        new_links = [
            {"link_name": "new link", "link_type": "RAW_DATA", "link_url": "http://brand_new_link.place"},
            {"link_name": "new link 2", "link_type": "RAW_DATA", "link_url": "http://brank_new_link_two.place"},
        ]
        name = "partial updates test collection"

        links_configurations = (
            ("With links already in place; new links replace old", links, new_links, 200, new_links),
            ("With no links in place; new links get added", None, new_links, 200, new_links),
            ("With links in place, but empty request; links persist", links, None, 200, links),
            ("With links in place, empty array passed; BAD REQUEST 400", links, [], 400, links),
        )

        for test_title, initial_links, new_links, expected_status_code, expected_links in links_configurations:
            with self.subTest(test_title):
                collection_id = self.generate_collection(self.session, name=name, links=initial_links).id
                original_collection = self.app.get(f"curation/v1/collections/{collection_id}").json
                self.assertEqual(initial_links if initial_links else [], original_collection["links"])
                metadata = {"links": new_links} if new_links is not None else {}
                response = self.app.patch(
                    f"/curation/v1/collections/{collection_id}",
                    data=json.dumps(metadata),
                    headers=self.make_owner_header(),
                )
                self.assertEqual(expected_status_code, response.status_code)
                if expected_status_code == 200:
                    self.assertEqual(name, response.json["name"])
                    self.assertEqual(expected_links, response.json["links"])

    def test__update_collection__Not_Owner(self):
        collection_id = self.generate_collection(self.session, owner="someone else").id
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            data=json.dumps(self.test_collection),
            headers=self.make_owner_header(),
        )
        self.assertEqual(403, response.status_code)

    def test__update_collection__Super_Curator(self):
        collection_id = self.generate_collection(self.session).id
        headers = self.make_super_curator_header()
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}", data=json.dumps(self.test_collection), headers=headers
        )
        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()
