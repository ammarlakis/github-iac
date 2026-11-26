import json
from pathlib import Path
import unittest

from jsonschema.validators import validator_for
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = list((ROOT / "template/schemas").rglob("*.json"))
        registry = Registry().with_resources((p.as_uri(), Resource.from_contents(json.loads(p.read_text()))) for p in paths)
        cls.validators = {}
        for path in paths:
            schema = json.loads(path.read_text())
            validator = validator_for(schema)
            validator.check_schema(schema)
            cls.validators[path.relative_to(ROOT / "template/schemas").with_suffix("").as_posix()] = validator({**schema, "$id": path.as_uri()}, registry=registry)

    def validate(self, data):
        self.validators["repository.schema"].validate(data)

    def test_existing_repository_and_defaults(self):
        self.validate({"visibility": "private"})
        self.validators["repository-defaults.schema"].validate({})
        self.validators["repository-defaults.schema"].validate({"actions": {"enabled": False}, "pages": {"build_type": "workflow"}})

    def test_presets(self):
        self.validate({"preset": "standard"})
        self.validate({"preset": "standard", "visibility": "public"})
        preset_validator = self.validators["repository-preset.schema"]
        preset_validator.validate({"has_wiki": False})
        preset_validator.validate({"visibility": "private", "permissions": {"users": {"push": ["example"]}}})
        self.validate({})
        self.validate({"description": "Uses default visibility"})
        for data in [{"preset": ""}, {"preset": "../standard"}, {"preset": 1}]:
            with self.subTest(data=data):
                self.assertFalse(self.validators["repository.schema"].is_valid(data))
        for data in [{"preset": "other"}, {"unknown": True}, {"visibility": "invalid"}, {"actions": {"enabled": "false"}}]:
            with self.subTest(data=data):
                self.assertFalse(preset_validator.is_valid(data))

    def test_apps(self):
        self.validate({"preset": "standard", "apps": ["bot"]})
        self.validators["repository-preset.schema"].validate({"apps": []})
        self.validators["repository-defaults.schema"].validate({"apps": ["bot"]})
        validator = self.validators["app.schema"]
        validator.validate({"installation_id": 123})
        validator.validate({"manifest": {"name": "Bot", "url": "https://example.com", "default_permissions": {"contents": "read"}}, "publisher": False})
        for data in [{}, {"installation_id": -1}, {"manifest": {"name": "Bot"}}, {"manifest": {"name": "Bot", "url": "http://example.com"}}, {"installation_id": 1, "pem": "plaintext"}]:
            with self.subTest(data=data):
                self.assertFalse(validator.is_valid(data))
        self.assertFalse(self.validators["repository.schema"].is_valid({"visibility": "private", "apps": ["bot", "bot"]}))

    def test_shared_settings_and_schema_boundaries(self):
        shared = {"has_wiki": False, "apps": ["bot"], "actions": {"allowed_actions": "selected", "allowed_actions_config": {"github_owned_allowed": True}}, "rulesets": {"main": {"rules": {"deletion": True}}}}
        for name in ["repository.schema", "repository-preset.schema", "repository-defaults.schema"]:
            validator = self.validators[name]
            data = {**shared, **({"visibility": "private"} if name == "repository.schema" else {})}
            with self.subTest(schema=name):
                validator.validate(data)
                self.assertFalse(validator.is_valid({**data, "unknown": True}))
                self.assertFalse(validator.is_valid({**data, "has_wiki": "false"}))
                self.assertFalse(validator.is_valid({**data, "actions": {"unknown": True}}))
        defaults = self.validators["repository-defaults.schema"]
        self.assertFalse(defaults.is_valid({"preset": "standard"}))
        self.assertFalse(defaults.is_valid({"fork": {"owner": "upstream", "repository": "repo"}}))
        for field, value in {"visibility": "private", "description": "Example", "topics": [], "permissions": {}}.items():
            with self.subTest(field=field):
                defaults.validate({field: value})
        self.validators["repository-preset.schema"].validate({"fork": {"owner": "upstream", "repository": "repo"}, "description": "Example", "topics": [], "permissions": {}})

    def test_invalid_options(self):
        invalid = [
            {"actions": {"allowed_actions": "anything"}},
            {"actions": {"allowed_actions": "selected"}},
            {"actions": {"allowed_actions": "all", "allowed_actions_config": {"github_owned_allowed": True}}},
            {"security": {"vulnerability_alerts": "true"}},
            {"security": {"dependabot_security_updates": True, "vulnerability_alerts": False}},
            {"rulesets": {"main": {"rules": {"pull_request": {"required_approving_review_count": -1}}}}},
            {"rulesets": {"tags": {"target": "tag", "rules": {"pull_request": {}}}}},
            {"fork": {"owner": "example", "repository": "repo", "sync": {"enabled": True}}},
        ]
        for extra in invalid:
            with self.subTest(extra=extra):
                self.assertFalse(self.validators["repository.schema"].is_valid({"visibility": "private", **extra}))

    def test_ruleset_security_and_fork(self):
        self.validate({"visibility": "private", "fork": {"owner": "upstream", "repository": "repo"}, "security": {"vulnerability_alerts": True, "dependabot_security_updates": True}, "rulesets": {"main": {"rules": {"non_fast_forward": True, "pull_request": {"required_review_thread_resolution": True}, "required_status_checks": {"required_checks": [{"context": "test"}]}}}}})


if __name__ == "__main__":
    unittest.main()
