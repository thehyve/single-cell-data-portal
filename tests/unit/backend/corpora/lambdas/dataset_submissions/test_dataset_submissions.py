from unittest import TestCase
from unittest.mock import patch, Mock

from backend.corpora.common.corpora_orm import generate_uuid
from backend.corpora.common.utils.exceptions import CorporaException
from backend.corpora.dataset_submissions.app import dataset_submissions_handler


class TestDatasetSubmissions(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.collection_uuid = generate_uuid()
        cls.incoming_curator_tag = "my_dataset.h5ad"
        cls.user_name = "user_name"
        cls.dataset_uuid = "12341234-1234-1234-1234-123412341234"
        cls.dataset_uuid_in_s3 = f"{cls.dataset_uuid}.h5ad"

    def _test_missing_fields(self, **kwargs):
        s3_event = create_s3_event(**kwargs)
        with self.assertRaises(CorporaException):
            dataset_submissions_handler(s3_event, None)

    def test__missing_curator_file_name__raises_error(self):
        self._test_missing_fields(key=f"{self.user_name}/{self.collection_uuid}/")

    def test__missing_extension__raise_error(self):
        self._test_missing_fields(key=f"{self.user_name}/{self.collection_uuid}/{self.dataset_uuid}")

    def test__missing_collection_uuid__raises_error(self):
        self._test_missing_fields(key=f"{self.user_name}/should_have_been_a_uuid/{self.incoming_curator_tag}")

    def test__missing_username__raises_error(self):
        self._test_missing_fields(key=f"{self.collection_uuid}/{self.incoming_curator_tag}")

    def test__bad_extension__raises_error(self):
        self._test_missing_fields(key=f"{self.user_name}/{self.collection_uuid}/{self.dataset_uuid}$h5ad")

    def _test_types(self):
        types = [f"{self.incoming_curator_tag}", f"{self.dataset_uuid_in_s3}"]
        for t in types:
            with self.subTest(t):
                s3_event = create_s3_event(key=f"{self.user_name}/{self.collection_uuid}/{t}")
                with self.assertRaises(CorporaException):
                    dataset_submissions_handler(s3_event, None)

    @patch("backend.corpora.dataset_submissions.app.get_dataset_info")
    def test__non_existent_collection__raises_error(self, mock_get_dataset_info):
        mock_get_dataset_info.return_value = None, None
        self._test_types()

    @patch("backend.corpora.dataset_submissions.app.get_dataset_info")
    def test__non_owner__raises_error(self, mock_get_dataset_info):
        mock_get_dataset_info.return_value = "not_owner", self.dataset_uuid
        self._test_types()

    @patch("backend.corpora.dataset_submissions.app.get_dataset_info")
    @patch("backend.corpora.dataset_submissions.app.upload")
    def test__owner__upload(self, mock_upload: Mock, mock_get_dataset_info: Mock):
        types = [f"{self.incoming_curator_tag}", f"{self.dataset_uuid_in_s3}"]
        for t in types:
            s3_event = create_s3_event(key=f"{self.user_name}/{self.collection_uuid}/{t}")
            mock_upload.return_value = None
            mock_get_dataset_info.return_value = self.user_name, self.dataset_uuid
            dataset_submissions_handler(s3_event, None)
            mock_upload.assert_called()


def create_s3_event(bucket_name: str = "some_bucket", key: str = "", size: int = 0) -> dict:
    """
    Returns an S3 event dictionary with only the keys that the dataset submissions handler cares about
    :param bucket_name:
    :param key:
    :param size:
    :return:
    """
    return {"Records": [{"s3": {"bucket": {"name": bucket_name}, "object": {"key": key, "size": size}}}]}
