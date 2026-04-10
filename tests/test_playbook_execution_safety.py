import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _FakePopen:
    def __init__(self, *args, **kwargs):
        self._buffer = io.StringIO("PLAY [all]\\nTASK [noop]\\nok\\n")
        self.stdout = self
        self._terminated = False
        self._killed = False
        self._return_code = None

    def readline(self):
        line = self._buffer.readline()
        if line == "" and self._return_code is None:
            self._return_code = 0
        return line

    def poll(self):
        return self._return_code

    def wait(self, timeout=None):
        if self._return_code is None:
            self._return_code = 0
        return self._return_code

    def terminate(self):
        self._terminated = True
        self._return_code = -15

    def kill(self):
        self._killed = True
        self._return_code = -9


class _RunningProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self._return_code = None

    def poll(self):
        return self._return_code

    def wait(self, timeout=None):
        if self._return_code is None:
            self._return_code = -15
        return self._return_code

    def terminate(self):
        self.terminated = True
        self._return_code = -15

    def kill(self):
        self.killed = True
        self._return_code = -9


class PlaybookExecutionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mko-playbook-tests-")
        self.database_path = str(Path(self.tmpdir.name) / "test.db")
        os.environ["DATABASE_PATH"] = self.database_path

        from app.utils.config import config
        from app.models import database as database_module

        database_module.DATABASE_PATH = self.database_path
        database_module.DATABASE_URL = f"sqlite:///{self.database_path}"
        config.set("playbooks.execution_timeout_seconds", 120)

        from app import create_app

        self.app = create_app()
        self.ctx = self.app.app_context()
        self.ctx.push()

        from app.models.database import db
        from app.models.flask_models import User, Node

        db.create_all()
        user = User(username="admin", email="admin@example.com", is_admin=True)
        user.set_password("test123")
        db.session.add(user)
        db.session.flush()

        node = Node(hostname="node-1", ip_address="10.0.0.1", ssh_user="ubuntu", ssh_port=22)
        db.session.add(node)
        db.session.commit()

        self.user_id = user.id

    def tearDown(self):
        from app.models.database import db

        db.session.remove()
        self.ctx.pop()
        self.tmpdir.cleanup()

    def _create_execution(self, status="pending"):
        from app.models.database import db
        from app.models.flask_models import PlaybookExecution

        execution = PlaybookExecution(
            execution_name="test-execution",
            execution_type="custom",
            targets='[{"type":"all_nodes"}]',
            yaml_content="---\\n- hosts: all\\n  tasks:\\n    - debug:\\n        msg: test\\n",
            status=status,
            created_by=self.user_id,
        )
        db.session.add(execution)
        db.session.commit()
        return execution.id

    def test_cancel_execution_sets_cancel_requested_and_terminates_process(self):
        from app.models.database import db
        from app.models.flask_models import PlaybookExecution
        from app.services.playbook_service import PlaybookService

        execution_id = self._create_execution(status="running")
        service = PlaybookService()
        process = _RunningProcess()
        service._register_running_process(execution_id, process)

        self.assertTrue(service.cancel_execution(execution_id))
        execution = db.session.get(PlaybookExecution, execution_id)
        self.assertEqual(execution.status, "cancel_requested")
        self.assertTrue(process.terminated)

    def test_worker_marks_pre_cancelled_execution_as_cancelled(self):
        from app.models.database import db
        from app.models.flask_models import PlaybookExecution
        from app.services.playbook_service import PlaybookService

        execution_id = self._create_execution(status="cancel_requested")
        service = PlaybookService()
        service._execute_playbook_thread(self.app, execution_id)

        execution = db.session.get(PlaybookExecution, execution_id)
        self.assertEqual(execution.status, "cancelled")
        self.assertFalse(execution.success)

    def test_worker_executes_with_context_and_completes(self):
        from app.models.database import db
        from app.models.flask_models import PlaybookExecution
        from app.services.playbook_service import PlaybookService

        execution_id = self._create_execution(status="pending")
        service = PlaybookService()

        with patch("app.services.playbook_service.subprocess.Popen", return_value=_FakePopen()):
            service._execute_playbook_thread(self.app, execution_id)

        execution = db.session.get(PlaybookExecution, execution_id)
        self.assertEqual(execution.status, "completed")
        self.assertTrue(execution.success)
        self.assertEqual(execution.progress_percent, 100)


if __name__ == "__main__":
    unittest.main()
