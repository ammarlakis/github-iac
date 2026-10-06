"""Render both template modes and test Terraform using a mocked GitHub provider."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile

from jsonschema import Draft7Validator
from referencing import Registry, Resource
import yaml

ROOT = Path(__file__).resolve().parents[1]
root = Path(tempfile.mkdtemp(prefix="github-iac-validation-"))
shutil.copytree(ROOT, root / "template", ignore=shutil.ignore_patterns(".git", ".cocoindex_code", "__pycache__"))
(root / "template/maintenance-only.txt").write_text("Must not be copied.\n")
cache = root / "cache"
cache.mkdir()
env = {**os.environ, "TF_PLUGIN_CACHE_DIR": str(cache)}


def terraform(dest, *args):
    subprocess.run(["terraform", f"-chdir={dest / 'src'}", *args], env=env, check=True)


for org in [False, True]:
    dest = root / ("organization" if org else "personal")
    subprocess.run(["copier", "copy", "--quiet", "--defaults", "--data", "github_owner=example-owner", "--data", f"organization={str(org).lower()}", "--data", f"import_existing={str(org).lower()}", str(root / "template"), str(dest)], check=True)
    assert not (dest / ".github/workflows/template-ci.yaml").exists()
    assert not (dest / ".github/workflows/sync-forks.yaml").exists()
    assert not (dest / "scripts/sync-forks.py").exists()
    assert not (dest / "tests").exists()
    assert not (dest / "copier.yaml").exists()
    assert not (dest / "template").exists()
    assert not (dest / "maintenance-only.txt").exists()
    assert (dest / "README.md").read_text() == (ROOT / "template/README.md").read_text()
    justfile = (dest / "Justfile").read_text()
    assert "copier update --skip-answered" in justfile
    assert "cd src && terraform init" in justfile
    assert "{{args}}" in justfile and "{{target}}" in justfile
    assert "tests/validate_template.py" not in justfile
    assert not (dest / ".cocoindex_code").exists()
    json.loads((dest / ".vscode/settings.json").read_text())
    paths = list((dest / "schemas").glob("*.json"))
    registry = Registry().with_resources((p.as_uri(), Resource.from_contents(json.loads(p.read_text()))) for p in paths)
    for path in (dest / "data").rglob("*.yaml"):
        hint = path.read_text().splitlines()[0]
        assert hint.startswith("# yaml-language-server: $schema="), path
        schema_path = (path.parent / hint.split("=", 1)[1]).resolve()
        schema = json.loads(schema_path.read_text())
        Draft7Validator({**schema, "$id": schema_path.as_uri()}, registry=registry).validate(yaml.safe_load(path.read_text()))
    terraform(dest, "init", "-backend=false", "-input=false", "-no-color")
    terraform(dest, "validate", "-no-color")
    if org:
        continue
    tests = dest / "src/tests"
    tests.mkdir()
    (tests / "defaults.tftest.hcl").write_text('''mock_provider "github" {}
run "no_opt_in" {
  command = plan
  assert {
    condition = length(github_repository_ruleset.policy) == 0 && length(github_actions_repository_permissions.policy) == 0 && length(github_repository_vulnerability_alerts.policy) == 0 && length(github_repository_dependabot_security_updates.policy) == 0
    error_message = "New features must be opt-in."
  }
}
''')
    (dest / "data/defaults.yaml").unlink()
    # Existing generated projects need not have a presets directory.
    (dest / "data/presets/standard.yaml").unlink()
    (dest / "data/presets").rmdir()
    terraform(dest, "test", "-no-color")
    (tests / "defaults.tftest.hcl").unlink()
    defaults = {"has_wiki": False, "actions": {"enabled": True, "allowed_actions": "selected", "allowed_actions_config": {"github_owned_allowed": True}, "default_workflow_permissions": "read"}, "pages": {"build_type": "workflow"}, "security": {"vulnerability_alerts": True}, "rulesets": {"baseline": {"rules": {"deletion": True}}}}
    (dest / "data/defaults.yaml").write_text(yaml.safe_dump(defaults))
    repo = {"visibility": "private", "fork": {"owner": "upstream", "repository": "source"}, "pages": {"cname": "example.org"}, "actions": {"can_approve_pull_request_reviews": False}, "security": {"dependabot_security_updates": True, "secret_scanning": False, "advanced_security": False, "code_security": False, "secret_scanning_push_protection": False, "secret_scanning_ai_detection": False, "secret_scanning_non_provider_patterns": False}, "rulesets": {"main": {"rules": {"non_fast_forward": True, "required_signatures": True, "pull_request": {"required_approving_review_count": 2, "required_review_thread_resolution": True}, "required_status_checks": {"required_checks": [{"context": "test"}]}}}}}
    (dest / "data/repositories/options.yaml").write_text(yaml.safe_dump(repo))
    (dest / "data/repositories/legacy.yaml").write_text(yaml.safe_dump({"visibility": "public", "rulesets": {}, "pages": {"build_type": "legacy", "branch": "gh-pages", "path": "/docs"}}))
    (dest / "data/repositories/disabled.yaml").write_text(yaml.safe_dump({"visibility": "public", "pages": {"enabled": False}, "rulesets": {}, "actions": {"enabled": False}}))
    (dest / "data/repositories/tags.yaml").write_text(yaml.safe_dump({"visibility": "public", "rulesets": {"release": {"target": "tag", "rules": {"deletion": True, "tag_name_pattern": {"operator": "starts_with", "pattern": "v"}}}}}))
    (tests / "features.tftest.hcl").write_text('''mock_provider "github" {}
run "configured_features" {
  command = plan
  assert {
    condition = tobool(github_repository.create["options"].fork) && github_repository.create["options"].source_owner == "upstream" && github_repository.create["options"].has_wiki == false
    error_message = "Fork or shared setting mapping failed."
  }
  assert {
    condition = !contains(keys(github_repository_pages.site), "example") && !contains(keys(github_repository_pages.site), "disabled") && github_repository_pages.site["options"].build_type == "workflow" && github_repository_pages.site["options"].cname == "example.org" && length(github_repository_pages.site["options"].source) == 0 && github_repository_pages.site["legacy"].source[0].branch == "gh-pages" && github_repository_pages.site["legacy"].source[0].path == "/docs"
    error_message = "Pages defaults must require opt-in and respect legacy sources and disabling."
  }
  assert {
    condition = github_actions_repository_permissions.policy["options"].allowed_actions == "selected" && github_actions_repository_permissions.policy["disabled"].enabled == false && github_workflow_repository_permissions.policy["options"].default_workflow_permissions == "read" && github_workflow_repository_permissions.policy["options"].can_approve_pull_request_reviews == false
    error_message = "Actions defaults and overrides were not merged."
  }
  assert {
    condition = github_repository_vulnerability_alerts.policy["options"].enabled && github_repository_dependabot_security_updates.policy["options"].enabled && github_repository.create["options"].security_and_analysis[0].secret_scanning[0].status == "disabled"
    error_message = "Security settings and explicit false must be preserved."
  }
  assert {
    condition = length(github_repository_ruleset.policy) == 3 && github_repository_ruleset.policy["options/main"].rules[0].pull_request[0].required_approving_review_count == 2 && one(github_repository_ruleset.policy["options/main"].rules[0].required_status_checks[0].required_check).context == "test"
    error_message = "Named rulesets, override replacement, reviews or checks failed."
  }
  assert {
    condition = github_repository_ruleset.policy["tags/release"].target == "tag" && github_repository_ruleset.policy["tags/release"].conditions[0].ref_name[0].include[0] == "~ALL" && github_repository_ruleset.policy["tags/release"].rules[0].tag_name_pattern[0].pattern == "v"
    error_message = "Tag ruleset defaults or pattern mapping failed."
  }
}
''')
    terraform(dest, "test", "-no-color")
    (tests / "features.tftest.hcl").unlink()
    (dest / "data/presets").mkdir()
    shutil.copy(ROOT / "template/data/presets/standard.yaml", dest / "data/presets/standard.yaml")
    preset = {"visibility": "private", "has_wiki": True, "topics": ["preset"], "permissions": {"users": {"push": ["contributor"]}}, "actions": {"can_approve_pull_request_reviews": True, "allowed_actions_config": {"github_owned_allowed": False}}, "security": {"dependabot_security_updates": True}, "pages": {"build_type": "legacy", "branch": "gh-pages"}, "rulesets": {"preset": {"rules": {"deletion": True}}}}
    (dest / "data/presets/custom.yaml").write_text(yaml.safe_dump(preset))
    (dest / "data/repositories/preset-only.yaml").write_text(yaml.safe_dump({"preset": "standard"}))
    (dest / "data/repositories/preset-inherited.yaml").write_text(yaml.safe_dump({"preset": "custom"}))
    (dest / "data/repositories/preset-overridden.yaml").write_text(yaml.safe_dump({"preset": "custom", "visibility": "public", "has_wiki": False, "topics": [], "permissions": {}, "actions": {"enabled": False, "can_approve_pull_request_reviews": False}, "security": {"dependabot_security_updates": False}, "pages": {"path": "/docs"}, "rulesets": {}}))
    (tests / "presets.tftest.hcl").write_text('''mock_provider "github" {}
run "presets" {
  command = plan
  assert {
    condition = github_repository.create["preset-only"].visibility == "private" && github_repository.create["preset-only"].allow_squash_merge && !github_repository.create["preset-only"].allow_merge_commit && !contains(keys(github_repository_pages.site), "preset-only")
    error_message = "A preset must supply repository settings without opting into default Pages."
  }
  assert {
    condition = github_repository.create["preset-inherited"].has_wiki && github_repository.create["preset-overridden"].visibility == "public" && !github_repository.create["preset-overridden"].has_wiki && length(github_repository.create["preset-overridden"].topics) == 0 && length(local.repositories["preset-overridden"].permissions) == 0 && one(github_repository_collaborators.users["preset-inherited"].user).username == "contributor"
    error_message = "Preset inheritance and repository scalar, list, and permissions replacement failed."
  }
  assert {
    condition = github_actions_repository_permissions.policy["preset-inherited"].enabled && !github_actions_repository_permissions.policy["preset-inherited"].allowed_actions_config[0].github_owned_allowed && github_workflow_repository_permissions.policy["preset-inherited"].default_workflow_permissions == "read" && github_workflow_repository_permissions.policy["preset-inherited"].can_approve_pull_request_reviews && !github_actions_repository_permissions.policy["preset-overridden"].enabled && !github_workflow_repository_permissions.policy["preset-overridden"].can_approve_pull_request_reviews
    error_message = "Actions must merge defaults, presets, and repository settings, preserving false and replacing nested objects."
  }
  assert {
    condition = github_repository_vulnerability_alerts.policy["preset-inherited"].enabled && github_repository_dependabot_security_updates.policy["preset-inherited"].enabled && !github_repository_dependabot_security_updates.policy["preset-overridden"].enabled
    error_message = "Security settings must merge across all three layers."
  }
  assert {
    condition = github_repository_pages.site["preset-inherited"].build_type == "legacy" && github_repository_pages.site["preset-inherited"].source[0].branch == "gh-pages" && github_repository_pages.site["preset-overridden"].source[0].path == "/docs" && contains(keys(github_repository_ruleset.policy), "preset-inherited/preset") && !contains(keys(github_repository_ruleset.policy), "preset-inherited/baseline") && !contains(keys(github_repository_ruleset.policy), "preset-overridden/preset")
    error_message = "Pages must merge across all three layers and rulesets must be replaced."
  }
}
''')
    terraform(dest, "test", "-no-color")
    (dest / "data/repositories/missing-preset.yaml").write_text(yaml.safe_dump({"preset": "missing"}))
    result = subprocess.run(["terraform", f"-chdir={dest / 'src'}", "test", "-no-color"], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "Invalid index" in result.stderr, result.stdout + result.stderr
# Both optional outputs must be omitted when disabled, independently.
for actions, justfile in [(False, False), (False, True), (True, False)]:
    dest = root / f"optional-actions-{actions}-justfile-{justfile}"
    subprocess.run(["copier", "copy", "--quiet", "--defaults", "--data", "github_owner=example-owner", "--data", f"enable_actions={str(actions).lower()}", "--data", f"add_justfile={str(justfile).lower()}", str(root / "template"), str(dest)], check=True)
    assert (dest / "Justfile").exists() == justfile
    assert (dest / ".github/workflows/add-repository.yaml").exists() == actions
    assert not (dest / ".github/workflows/template-ci.yaml").exists()
    assert not (dest / "maintenance-only.txt").exists()
print(f"Validated templates at {root}")
