import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class PluginApiContractTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mko-plugin-api-tests-")
        self.database_path = str(Path(self.tmpdir.name) / "test.db")
        os.environ["DATABASE_PATH"] = self.database_path

        from app.models import database as database_module
        from app.utils.config import config

        database_module.DATABASE_PATH = self.database_path
        database_module.DATABASE_URL = f"sqlite:///{self.database_path}"
        config.set("plugins.storage_dir", str(Path(self.tmpdir.name) / "plugins"))
        config.set("plugins.auto_apply_configmap", False)

        from app import create_app

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

        from app.models.database import db
        from app.models.flask_models import User

        db.create_all()
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("pass")
        user = User(username="user", email="user@example.com", is_admin=False)
        user.set_password("pass")
        db.session.add(admin)
        db.session.add(user)
        db.session.commit()
        self.admin_id = admin.id
        self.user_id = user.id
        self.client = self.app.test_client()

    def tearDown(self):
        from app.models.database import db

        db.session.remove()
        self.ctx.pop()
        self.tmpdir.cleanup()

    def _login(self, user_id: int) -> None:
        with self.client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    def test_list_plugins_returns_stable_success_shape(self):
        self._login(self.admin_id)
        response = self.client.get("/api/plugins")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("plugins", payload)

    def test_admin_required_errors_are_structured(self):
        self._login(self.user_id)
        response = self.client.post("/api/plugins/install", json={})
        self.assertEqual(response.status_code, 403)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], "admin_access_required")
        self.assertIn("retryable", payload["error"])

    def test_execute_requires_confirmation_token_and_reason(self):
        self._login(self.admin_id)
        response = self.client.post("/api/plugins/test/actions/execute", json={})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertIn("required_fields", payload["error"]["details"])

    def test_execute_passes_idempotency_key_to_manager(self):
        self._login(self.admin_id)
        manager = self.app.extensions["plugin_manager"]

        with patch.object(
            manager,
            "execute_action",
            return_value={"plugin_id": "test_plugin", "action_id": "noop", "status": "queued"},
        ) as execute_action:
            response = self.client.post(
                "/api/plugins/test_plugin/actions/execute",
                json={
                    "confirmation_token": "token",
                    "execute_reason": "test",
                    "idempotency_key": "idem-123",
                },
            )
        self.assertEqual(response.status_code, 200)
        execute_action.assert_called_once()
        self.assertEqual(execute_action.call_args.kwargs["idempotency_key"], "idem-123")


if __name__ == "__main__":
    unittest.main()
