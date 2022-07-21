from backend.common.entities import Dataset
from tests.unit.backend.base_test_dataset import TestDataset
from tests.unit.backend.utils import BogusDatasetParams


class TestListDataset(TestDataset):
    def test__list__ok(self):
        generate = 2
        generated_ids = [Dataset.create(self.session, **BogusDatasetParams.get()).id for _ in range(generate)]
        dataset = Dataset.list(self.session)
        self.assertTrue(set(generated_ids).issubset([d.id for d in dataset]))
