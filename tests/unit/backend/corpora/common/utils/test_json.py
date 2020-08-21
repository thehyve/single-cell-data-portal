import datetime
import json
import unittest
from enum import Enum

from sqlalchemy import Column, String

from backend.corpora.common.corpora_orm import Base
from backend.corpora.common.entities.entity import Entity
from backend.corpora.common.utils.json import CustomJSONEncoder


class DBTest(Base):
    __tablename__ = "test"
    id = Column(String, primary_key=True)
    name = Column(String)


class TestCustomJSONEncoder(unittest.TestCase):
    def test_datetime(self):
        test_datetime_value = datetime.datetime.fromtimestamp(0)
        expected_datetime = str(test_datetime_value.timestamp())
        self._verify_json_encoding(test_datetime_value, expected_datetime)

    def test_timedelta(self):
        time_1 = datetime.datetime.fromtimestamp(0)
        time_2 = datetime.datetime.fromtimestamp(10)
        test_timedelta_value = time_1 - time_2
        expected_timedelta = f'"{test_timedelta_value}"'
        self._verify_json_encoding(test_timedelta_value, expected_timedelta)

    def test_enum(self):
        class EnumClass(Enum):
            TEST = "test"

        test_enum_value = EnumClass.TEST
        expected_enum = f'"{test_enum_value.name}"'
        self._verify_json_encoding(test_enum_value, expected_enum)

    def test_base(self):
        params = dict(id="foo", name=None)
        test_base = DBTest(**params)
        expected_base = json.dumps(params, sort_keys=True)
        self._verify_json_encoding(test_base, expected_base)
        self.assertDictEqual({k: v for k, v in test_base}, params)

    def test_entity(self):
        params = dict(id="foo", name="bar")
        test_entity = Entity(DBTest(**params))
        expected_entity = json.dumps(params, sort_keys=True)
        self._verify_json_encoding(test_entity, expected_entity)

    def test_unsupported_type(self):
        class Unsupported:
            foo = "bar"

        test_unsupported_type = Unsupported()
        with self.assertRaises(TypeError):
            json.dumps(test_unsupported_type, cls=CustomJSONEncoder)

    def _verify_json_encoding(self, test_value, expected_value):
        actual_value = json.dumps(test_value, cls=CustomJSONEncoder, sort_keys=True)
        self.assertEqual(expected_value, actual_value)
