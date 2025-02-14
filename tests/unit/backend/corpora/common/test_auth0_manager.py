import time
from multiprocessing import Process
import unittest
from random import randint
from unittest.mock import MagicMock

import requests
from flask import Flask, request, make_response

from backend.corpora.common.auth0_manager import auth0_management_session


class TestSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = randint(10000, 20000)
        app = Flask("server_app")

        @app.get("/")
        def health():
            return make_response("", 200)

        @app.get("/test-refresh")
        def test_refresh():
            token = request.headers.get("Authorization")
            if token == "Bearer good":
                return make_response("", 200)
            else:
                return make_response("", 401)

        cls.server = Process(target=app.run, kwargs=dict(port=cls.port, debug=False))
        cls.server.start()
        for _ in range(10):
            try:
                response = requests.get(f"http://localhost:{cls.port}/")
                response.raise_for_status()
            except Exception:
                time.sleep(0.1)
            else:
                break

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.join()

    def test_session_refresh(self):
        auth0_management_session.domain = "http://localhost:5000"
        auth0_management_session.get_auth0_management_token = MagicMock(return_value="Bearer good")
        auth0_management_session.headers["Authorization"] = "Bearer bad"
        response = auth0_management_session.session.get(f"http://localhost:{self.port}/test-refresh")
        response.raise_for_status()
        auth0_management_session.get_auth0_management_token.assert_called_once()
        self.assertEqual(auth0_management_session.headers["Authorization"], "Bearer good")
