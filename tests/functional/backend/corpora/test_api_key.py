import unittest

from tests.functional.backend.common import BaseFunctionalTestCase


class TestApiKey(BaseFunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_api_key_crud(self):
        headers = {"Cookie": f"cxguser={self.curator_cookie}", "Content-Type": "application/json"}

        def _cleanup():
            self.session.delete(f"{self.api}/dp/v1/auth/key", headers=headers)

        self.addCleanup(_cleanup)

        response = self.session.get(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(404, response.status_code)

        response = self.session.post(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(201, response.status_code)
        key_1 = response.json()["key"]

        response = self.session.post(
            f"{self.api}/curation/v1/auth/token",
            headers={"x-api-key": f"{key_1}", "Content-Type": "application/json"},
        )
        self.assertEqual(201, response.status_code)
        access_token = response.json()["access_token"]
        self.assertTrue(access_token)

        response = self.session.get(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(200, response.status_code)

        response = self.session.post(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(201, response.status_code)
        key_2 = response.json()["key"]
        self.assertNotEqual(key_1, key_2)

        response = self.session.get(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(200, response.status_code)

        response = self.session.delete(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(202, response.status_code)

        response = self.session.delete(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(404, response.status_code)

        response = self.session.get(f"{self.api}/dp/v1/auth/key", headers=headers)
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
