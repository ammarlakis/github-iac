import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft7Validator
from referencing import Registry, Resource
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_forks", ROOT / "scripts/sync-forks.py")
sync_forks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_forks)


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = list((ROOT / "schemas").glob("*.json"))
        registry = Registry().with_resources((p.as_uri(), Resource.from_contents(json.loads(p.read_text()))) for p in paths)
        cls.validators = {}
        for path in paths:
            schema = json.loads(path.read_text())
            Draft7Validator.check_schema(schema)
            cls.validators[path.stem] = Draft7Validator({**schema, "$id": path.as_uri()}, registry=registry)

    def validate(self, data):
        self.validators["repository.schema"].validate(data)

    def test_existing_repository_and_defaults(self):
        self.validate({"visibility": "private"})
        self.validators["repository-defaults.schema"].validate({})
        self.validators["repository-defaults.schema"].validate({"actions": {"enabled": False}, "pages": {"build_type": "workflow"}})

    def test_invalid_options(self):
        invalid = [
            {"actions": {"allowed_actions": "anything"}},
            {"actions": {"allowed_actions": "selected"}},
            {"actions": {"allowed_actions": "all", "allowed_actions_config": {"github_owned_allowed": True}}},
            {"security": {"vulnerability_alerts": "true"}},
            {"security": {"dependabot_security_updates": True, "vulnerability_alerts": False}},
            {"rulesets": {"main": {"rules": {"pull_request": {"required_approving_review_count": -1}}}}},
            {"rulesets": {"tags": {"target": "tag", "rules": {"pull_request": {}}}}},
            {"fork": {"owner": "example", "repository": "repo", "sync": {"enabled": "true"}}},
        ]
        for extra in invalid:
            with self.subTest(extra=extra):
                self.assertFalse(self.validators["repository.schema"].is_valid({"visibility": "private", **extra}))
        self.assertFalse(self.validators["repository-defaults.schema"].is_valid({"fork": {"owner": "example", "repository": "repo"}}))

    def test_ruleset_security_and_fork(self):
        self.validate({"visibility": "private", "fork": {"owner": "upstream", "repository": "repo", "sync": {"enabled": True, "branch": "main"}}, "security": {"vulnerability_alerts": True, "dependabot_security_updates": True}, "rulesets": {"main": {"rules": {"non_fast_forward": True, "pull_request": {"required_review_thread_resolution": True}, "required_status_checks": {"required_checks": [{"context": "test"}]}}}}})


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data/repositories").mkdir(parents=True)
        (self.root / ".copier-answers.yml").write_text("github_owner: owner\n")

    def repo(self, name, data):
        (self.root / "data/repositories" / f"{name}.yaml").write_text(yaml.safe_dump(data))

    def test_only_explicitly_enabled_forks(self):
        self.repo("original", {"visibility": "public"})
        self.repo("off", {"fork": {"owner": "source", "repository": "off", "sync": {"enabled": False}}})
        self.repo("on", {"fork": {"owner": "source", "repository": "upstream", "sync": {"enabled": True, "branch": "main"}}})
        self.assertEqual(sync_forks.sync_commands(self.root), [["gh", "repo", "sync", "owner/on", "--source", "source/upstream", "--branch", "main"]])

    def test_preview_and_missing_token_do_not_write(self):
        self.repo("repo", {"fork": {"owner": "source", "repository": "repo", "sync": {"enabled": True}}})
        with patch.object(sync_forks.subprocess, "run") as run, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sync_forks.main(["--root", str(self.root)]), 0)
            self.assertEqual(sync_forks.main(["--root", str(self.root), "--apply"]), 1)
            run.assert_not_called()

    def test_failed_sync_does_not_force_or_stop_other_forks(self):
        for name in ["a", "b"]:
            self.repo(name, {"fork": {"owner": "source", "repository": name, "sync": {"enabled": True}}})
        with patch.object(sync_forks.subprocess, "run") as run, patch.dict(os.environ, {"GH_TOKEN": "test"}, clear=True):
            run.return_value.returncode = 1
            self.assertEqual(sync_forks.main(["--root", str(self.root), "--apply"]), 1)
            self.assertEqual(run.call_count, 2)
            for call in run.call_args_list:
                self.assertNotIn("--force", call.args[0])

    def test_no_opt_in_needs_no_token(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sync_forks.main(["--root", str(self.root), "--apply"]), 0)


if __name__ == "__main__":
    unittest.main()
