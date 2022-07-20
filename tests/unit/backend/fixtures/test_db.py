import numpy as np

from backend.corpora.common.corpora_orm import (
    CollectionVisibility,
    CollectionLinkType,
    DatasetArtifactFileType,
    DbCollection,
    DbCollectionLink,
    DbDataset,
    DbDatasetArtifact,
    DbDatasetProcessingStatus,
    IsPrimaryData,
    UploadStatus,
    ValidationStatus,
    ConversionStatus,
    ProcessingStatus,
    XApproximateDistribution,
)
from backend.scripts.create_db import create_db
from tests.unit.backend.fixtures import config
from backend.corpora.common.entities.tiledb_data import TileDBData, Utils


class TestDatabaseManager:
    is_initialized = False

    @classmethod
    def initialize_db(cls):
        if cls.is_initialized:
            return
        testdb = TestDatabase()
        testdb.create_db()
        testdb.populate_test_data()
        cls.is_initialized = True


class TestDatabase:
    def __init__(self, real_data=False):
        self.real_data = real_data
        location = "./test_tiledb/metadata" # TODO: config this somewhere
        self.db = TileDBData(location)

    def create_db(self):
        create_db()

    def populate_test_data(self):
        self._populate_test_data()

    def _populate_test_data(self):
        self._create_test_collections()
        self._create_test_collection_links()
        self._create_test_datasets()
        self._create_test_dataset_artifacts()
        self._create_test_dataset_processing_status()

    def _create_test_collections(self):
        collection = self.db._create_collection_custom_id(
            id="test_collection_id",
            owner="test_user_id",
            name="test_collection_name",
            description="test_description",
            contact_name="Some Body",
            contact_email="somebody@chanzuckerberg.com",
        )
        self.db.publish_collection(collection)
        self.db.create_revision(collection)

        collection = self.db._create_collection_custom_id(
            id="test_collection_id_public",
            owner="test_user_id",
            name="test_collection_id_public",
            description="test_description",
        )
        self.db.publish_collection(collection)
        rev_id = self.db.create_revision(collection)
        self.db.edit_collection(rev_id, "name", "test_collection_id_public_for_revision_one")
        self.db.edit_collection(rev_id, "owner", "User1")
        self.db.edit_collection(rev_id, "contact_name", "Some Body")
        self.db.edit_collection(rev_id, "contact_email", "somebody@chanzuckerberg.com")

        collection = self.db._create_collection_custom_id(
            id="test_collection_id_not_owner",
            owner="Someone_else",
            name="test_collection_name",
            description="test_description",
        )

        collection = self.db._create_collection_custom_id(
            id="test_collection_with_link",
            owner="test_user_id",
            name="test_collection_name",
            description="test_description",
            contact_name="Some Body",
            contact_email="somebody@chanzuckerberg.com",
        )
        self.db.publish_collection(collection)

        collection = self.db._create_collection_custom_id(
            id="test_collection_with_link_and_dataset_changes",
            owner="test_user_id",
            name="test_collection_name",
            description="test_description",
            contact_name="Some Body",
            contact_email="somebody@chanzuckerberg.com",
        )
        self.db.publish_collection(collection)

    def _create_test_collection_links(self):
        for link_type in CollectionLinkType:
            links = self.db.get_collection("test_collection_id")['links']
            links.append({
                'link_name': f"test_{link_type.value}_link_name",
                'link_url': f"http://test_{link_type.value}_url.place",
                'link_type': link_type.name,
            })
            links.append({
                "link_url": f"http://test_no_link_name_{link_type.value}_url.place",
                "link_type": link_type.name,
            })
            self.db.edit_collection("test_collection_id", "links", links)
                    

            links = self.db.get_collection("test_collection_with_link")['links']
            links.append({
                'link_name': f"test_{link_type.value}_link_name",
                'link_url': f"http://test_link_{link_type.value}_url.place",
                'link_type': link_type.name,
            })
            self.db.edit_collection("test_collection_with_link", "links", links)

            links = self.db.get_collection("test_collection_with_link_and_dataset_changes")['links']
            links.append({
                'link_name': f"test_{link_type.value}_link_name",
                'link_url': f"http://test_link_{link_type.value}_url.place",
                'link_type': link_type.name,
            })
            self.db.edit_collection("test_collection_with_link_and_dataset_changes", "links", links)
            
    def _create_test_datasets(self):
        test_dataset_id = "test_dataset_id"
        self.db._create_collection_custom_id(
            test_dataset_id,
            "test_collection_id",
            dict(
                name="test_dataset_name",
                organism=[{"ontology_term_id": "test_obo", "label": "test_organism"}],
                tissue=[{"ontology_term_id": "test_obo", "label": "test_tissue"}],
                assay=[{"ontology_term_id": "test_obo", "label": "test_assay"}],
                disease=[
                    {"ontology_term_id": "test_obo", "label": "test_disease"},
                    {"ontology_term_id": "test_obp", "label": "test_disease2"},
                    {"ontology_term_id": "test_obq", "label": "test_disease3"},
                ],
                sex=[
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                ethnicity=[{"ontology_term_id": "test_obo", "label": "test_ethnicity"}],
                development_stage=[{"ontology_term_id": "test_obo", "label": "test_development_stage"}],
                explorer_url="test_url",
                cell_type=[{"label": "test_cell_type", "ontology_term_id": "test_opo"}],
                is_primary_data=IsPrimaryData.PRIMARY.name,
                x_normalization="test_x_normalization",
                x_approximate_distribution=XApproximateDistribution.NORMAL.name,
            )
        )
        
        self.db._add_dataset_custom_id(
            "test_dataset_for_revisions_one",
            "test_collection_id_public_for_revision_one",
            dict(
                name="test_dataset_name",
                organism=[{"ontology_term_id": "test_obo", "label": "test_organism"}],
                tissue=[{"ontology_term_id": "test_obo", "label": "test_tissue"}],
                assay=[{"ontology_term_id": "test_obo", "label": "test_assay"}],
                disease=[
                    {"ontology_term_id": "test_obo", "label": "test_disease"},
                    {"ontology_term_id": "test_obp", "label": "test_disease2"},
                    {"ontology_term_id": "test_obq", "label": "test_disease3"},
                ],
                sex=[
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                ethnicity=[{"ontology_term_id": "test_obo", "label": "test_ethnicity"}],
                development_stage=[{"ontology_term_id": "test_obo", "label": "test_development_stage"}],
                explorer_url="test_url",
            )
        )

        self.db._add_dataset_custom_id(
            "test_dataset_for_revisions_two",
            "test_collection_id_public_for_revision_two",
            dict(
                name="test_dataset_name",
                organism=[{"ontology_term_id": "test_obo", "label": "test_organism"}],
                tissue=[{"ontology_term_id": "test_obo", "label": "test_tissue"}],
                assay=[{"ontology_term_id": "test_obo", "label": "test_assay"}],
                disease=[
                    {"ontology_term_id": "test_obo", "label": "test_disease"},
                    {"ontology_term_id": "test_obp", "label": "test_disease2"},
                    {"ontology_term_id": "test_obq", "label": "test_disease3"},
                ],
                sex=[
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                ethnicity=[{"ontology_term_id": "test_obo", "label": "test_ethnicity"}],
                development_stage=[{"ontology_term_id": "test_obo", "label": "test_development_stage"}],
                explorer_url="test_url",
            )
        )

        self.db._add_dataset_custom_id(
            "test_dataset_id_not_owner",
            "test_collection_id_not_owner",
            dict(
                name="test_dataset_name_not_owner",
                organism=[{"ontology_term_id": "test_obo", "label": "test_organism"}],
                tissue=[{"ontology_term_id": "test_obo", "label": "test_tissue"}],
                assay=[{"ontology_term_id": "test_obo", "label": "test_assay"}],
                disease=[
                    {"ontology_term_id": "test_obo", "label": "test_disease"},
                    {"ontology_term_id": "test_obp", "label": "test_disease2"},
                    {"ontology_term_id": "test_obq", "label": "test_disease3"},
                ],
                sex=[
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                ethnicity=[{"ontology_term_id": "test_obo", "label": "test_ethnicity"}],
                development_stage=[{"ontology_term_id": "test_obo", "label": "test_development_stage"}],
                explorer_url="test_url",
                cell_type=[{"label": "test_cell_type", "ontology_term_id": "test_opo"}],
                is_primary_data=IsPrimaryData.PRIMARY.name,
                x_normalization="test_x_normalization",
                x_approximate_distribution=XApproximateDistribution.NORMAL.name,
            )
        )

        self.db._add_dataset_custom_id(
            "test_publish_revision_with_links__revision_dataset",
            "test_collection_id_revision",
            dict(
                name="test_dataset_name_revised",
                organism=[{"ontology_term_id": "test_obo", "label": "test_organism"}],
                tissue=[{"ontology_term_id": "test_obo", "label": "test_tissue"}],
                assay=[{"ontology_term_id": "test_obo", "label": "test_assay"}],
                disease=[
                    {"ontology_term_id": "test_obo", "label": "test_disease"},
                    {"ontology_term_id": "test_obp", "label": "test_disease2"},
                    {"ontology_term_id": "test_obq", "label": "test_disease3"},
                ],
                sex=[
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                ethnicity=[{"ontology_term_id": "test_obo", "label": "test_ethnicity"}],
                development_stage=[{"ontology_term_id": "test_obo", "label": "test_development_stage"}],
                explorer_url="test_url_revised",
                cell_type=[{"label": "test_cell_type", "ontology_term_id": "test_opo"}],
                is_primary_data=IsPrimaryData.PRIMARY.name,
                x_normalization="test_x_normalization",
                x_approximate_distribution=XApproximateDistribution.NORMAL.name,
            )
        )

    def _create_test_dataset_artifacts(self):
        assets = self.db.get_dataset("test_dataset_id")['dataset_assets']
        dataset_artifact = dict(
            id="test_dataset_artifact_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.H5AD.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        dataset_artifact = dict(
            id="test_dataset_artifact_id_cxg",
            filename="test_filename",
            filetype=DatasetArtifactFileType.CXG.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        self.db.edit_dataset("test_dataset_id", "dataset_assets", assets)

        # Revision 1
        assets = self.db.get_dataset("test_dataset_for_revisions_one")['dataset_assets']
        dataset_artifact = dict(
            id="test_dataset_artifact_for_revision_one_CXG_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.CXG.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        dataset_artifact = dict(
            id="test_dataset_artifact_for_revision_one_H5AD_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.H5AD.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        dataset_artifact = dict(
            id="test_dataset_artifact_for_revision_one_RDS_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.RDS.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        self.db.edit_dataset("test_dataset_for_revisions_one", "dataset_assets", assets)

        # Revision 2
        assets = self.db.get_dataset("test_dataset_for_revisions_two")['dataset_assets']
        dataset_artifact = dict(
            id="test_dataset_artifact_for_revision_two_CXG_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.CXG.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        dataset_artifact = dict(
            id="test_dataset_artifact_for_revision_two_H5AD_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.H5AD.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        dataset_artifact = dict(
            id="test_dataset_artifact_for_revision_two_RDS_id",
            filename="test_filename",
            filetype=DatasetArtifactFileType.RDS.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        self.db.edit_dataset("test_dataset_for_revisions_two", "dataset_assets", assets)

        assets = self.db.get_dataset("test_publish_revision_with_links__revision_dataset")['dataset_assets']
        dataset_artifact = dict(
            id="test_publish_revision_with_links__revision_artifact",
            filename="test_filename",
            filetype=DatasetArtifactFileType.H5AD.name,
            user_submitted=True,
            s3_uri=config.real_s3_file if self.real_data else config.fake_s3_file,
        )
        assets.append(dataset_artifact)
        self.db.edit_dataset("test_publish_revision_with_links__revision_dataset", "dataset_assets", assets)

    def _create_test_dataset_processing_status(self):
        dataset_processing_status = dict(
            processing_status=ProcessingStatus.PENDING,
            upload_status=UploadStatus.UPLOADING,
            upload_progress=4 / 9,
            validation_status=ValidationStatus.NA,
            rds_status=ConversionStatus.NA,
            cxg_status=ConversionStatus.NA,
            h5ad_status=ConversionStatus.NA,
        )
        self.db.edit_dataset("test_dataset_id", "processing_status", dataset_processing_status)

        dataset_processing_status = dict(
            processing_status=ProcessingStatus.SUCCESS,
            upload_status=UploadStatus.UPLOADED,
            upload_progress=1,
            validation_status=ValidationStatus.VALID,
            rds_status=ConversionStatus.CONVERTED,
            cxg_status=ConversionStatus.CONVERTED,
            h5ad_status=ConversionStatus.CONVERTED,
        )
        self.db.edit_dataset("test_dataset_for_revisions+one", "processing_status", dataset_processing_status)

        dataset_processing_status = dict(
            processing_status=ProcessingStatus.SUCCESS,
            upload_status=UploadStatus.UPLOADED,
            upload_progress=1,
            validation_status=ValidationStatus.VALID,
            rds_status=ConversionStatus.CONVERTED,
            cxg_status=ConversionStatus.CONVERTED,
            h5ad_status=ConversionStatus.CONVERTED,
        )
        self.db.edit_dataset("test_dataset_for_revisions_two", "processing_status", dataset_processing_status)

        dataset_processing_status = dict(
            processing_status=ProcessingStatus.SUCCESS,
            upload_status=UploadStatus.UPLOADED,
            upload_progress=1,
            validation_status=ValidationStatus.VALID,
            rds_status=ConversionStatus.CONVERTED,
            cxg_status=ConversionStatus.CONVERTED,
            h5ad_status=ConversionStatus.CONVERTED,
        )
        self.db.edit_dataset("test_publish_revision_with_links__revision_dataset", "processing_status", dataset_processing_status)

        dataset_processing_status = dict(
            processing_status=ProcessingStatus.PENDING,
            upload_status=UploadStatus.UPLOADED,
            upload_progress=1,
            validation_status=ValidationStatus.VALID,
            rds_status=ConversionStatus.CONVERTED,
            cxg_status=ConversionStatus.CONVERTED,
            h5ad_status=ConversionStatus.CONVERTED,
        )
        self.db.edit_dataset("test_dataset_id_not_owner", "processing_status", dataset_processing_status)
