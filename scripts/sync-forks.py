#!/usr/bin/env python3
"""Preview or fast-forward explicitly enabled forks using GitHub CLI."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import yaml


NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
OWNER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")


def sync_commands(root, repository=None):
    answers = yaml.safe_load((root / ".copier-answers.yml").read_text())
    owner = answers["github_owner"]
    if not isinstance(owner, str) or not OWNER.fullmatch(owner):
        raise ValueError("Invalid github_owner in Copier answers")
    commands = []
    for path in sorted((root / "data/repositories").glob("*.yaml")):
        if repository is not None and path.stem != repository:
            continue
        config = yaml.safe_load(path.read_text()) or {}
        fork = config.get("fork", {})
        sync = fork.get("sync", {})
        if sync.get("enabled") is not True:
            continue
        source_owner, source_repo = fork["owner"], fork["repository"]
        if not OWNER.fullmatch(source_owner) or not NAME.fullmatch(source_repo) or not NAME.fullmatch(path.stem):
            raise ValueError(f"Invalid fork name in {path}")
        command = ["gh", "repo", "sync", f"{owner}/{path.stem}", "--source", f"{source_owner}/{source_repo}"]
        if "branch" in sync:
            branch = sync["branch"]
            if not isinstance(branch, str) or not branch or branch.startswith("-") or any(c.isspace() for c in branch):
                raise ValueError(f"Invalid sync branch in {path}")
            command += ["--branch", branch]
        commands.append(command)
    if repository is not None and not (root / "data/repositories" / f"{repository}.yaml").is_file():
        raise ValueError(f"Unknown repository: {repository}")
    return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repository", help="Limit syncing to one configured repository")
    parser.add_argument("--apply", action="store_true", help="Perform the sync; otherwise only print planned commands")
    args = parser.parse_args(argv)
    try:
        commands = sync_commands(args.root, args.repository)
    except (OSError, KeyError, TypeError, AttributeError, ValueError, yaml.YAMLError) as error:
        print(f"Invalid fork configuration: {error}", file=sys.stderr)
        return 1
    if not commands:
        print("No forks have syncing enabled.")
        return 0
    if args.apply and not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        print("Set GH_TOKEN with write access to the selected forks before applying.", file=sys.stderr)
        return 1
    failures = 0
    for command in commands:
        print(shlex.join(command), flush=True)
        if args.apply:
            # Deliberately omit --force: divergent branches must not be overwritten.
            try:
                result = subprocess.run(command, check=False)
            except OSError as error:
                print(str(error), file=sys.stderr)
                failures += 1
            else:
                failures += result.returncode != 0
    if failures:
        print(f"{failures} sync(s) failed. Inspect divergence, permissions, and rulesets; no force sync was attempted.", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
