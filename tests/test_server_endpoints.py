"""
Prueba de rutas del servidor FastAPI directamente.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app, get_server_info, list_users, get_all_audits, get_cycles, get_local_ip
from security.models import LoginRequest


class TestServerRoutes(unittest.TestCase):
    def test_01_server_info(self):
        info = get_server_info()
        self.assertEqual(info["status"], "online")
        self.assertEqual(info["port"], 8000)
        self.assertTrue("local_ip" in info)
        self.assertTrue(info["lan_url"].startswith("http://"))

    def test_02_users_and_audits_endpoint(self):
        users = list_users()
        self.assertGreaterEqual(len(users), 1)
        self.assertTrue(any(u["username"] == "daniel.enriquez" for u in users))

        audits = get_all_audits()
        self.assertIsInstance(audits, list)


if __name__ == "__main__":
    unittest.main()
