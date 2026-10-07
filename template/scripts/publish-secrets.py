#!/usr/bin/env python3
"""Publish SOPS-encrypted repository secrets using a short-lived GitHub App token."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

import yaml

REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+\Z")
SECRET = re.compile(r"[A-Z_][A-Z0-9_]*\Z")


def run(command, *, content=None, env=None):
    result = subprocess.run(command, input=content, capture_output=True, text=True, env=env)
    if result.returncode:
        raise ValueError(f"{command[0]} failed; check key access and permissions (diagnostics suppressed)")
    return result.stdout


def encrypted_document(path):
    encrypted = yaml.safe_load(path.read_text())
    if not isinstance(encrypted, dict) or not isinstance(encrypted.get("sops"), dict):
        raise ValueError(f"Expected a SOPS-encrypted document: {path.name}")
    return yaml.safe_load(run(["sops", "decrypt", str(path)]))


def read_secrets(root):
    entries = {}
    for path in sorted((root / "secrets").rglob("*.enc.yaml")):
        document = encrypted_document(path)
        if not isinstance(document, dict) or set(document) != {"repositories"} or not isinstance(document["repositories"], dict):
            raise ValueError(f"Invalid encrypted secret inventory: {path.name}")
        for repository, config in document["repositories"].items():
            if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
                raise ValueError("Invalid destination repository")
            if not isinstance(config, dict) or set(config) != {"secrets"} or not isinstance(config["secrets"], dict):
                raise ValueError("Expected a secrets mapping for each destination")
            for name, value in config["secrets"].items():
                if not isinstance(name, str) or not SECRET.fullmatch(name) or name.startswith("GITHUB_"):
                    raise ValueError("Invalid repository secret name")
                if not isinstance(value, str) or not value:
                    raise ValueError("Secret values must be nonempty strings")
                key = repository, name
                if key in entries:
                    raise ValueError(f"Duplicate destination secret: {repository}/{name}")
                entries[key] = value
    return entries


def base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def installation_token(publisher, private_key):
    for name in ["app_id", "installation_id"]:
        if not isinstance(publisher.get(name), int) or isinstance(publisher[name], bool) or publisher[name] < 1:
            raise ValueError(f"Publisher {name} must be a positive integer")
    now = int(time.time())
    header = base64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    payload = base64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(publisher["app_id"])}).encode())
    unsigned = f"{header}.{payload}"
    # The only plaintext disk material is a temporary, mode-0600 signing key.
    with tempfile.NamedTemporaryFile(mode="w") as pem:
        pem.write(private_key)
        pem.flush()
        signature = subprocess.run(["openssl", "dgst", "-sha256", "-sign", pem.name], input=unsigned.encode(), capture_output=True)
    if signature.returncode:
        raise ValueError("Could not sign publisher authentication token")
    jwt = f"{unsigned}.{base64url(signature.stdout)}"
    request = Request(f"https://api.github.com/app/installations/{publisher['installation_id']}/access_tokens", method="POST",
                      data=json.dumps({"permissions": {"secrets": "write"}}).encode(),
                      headers={"Authorization": f"Bearer {jwt}", "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "github-iac-secrets"})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    return result["token"]


def publish(root, apply=False):
    config = yaml.safe_load((root / "secrets-config.yaml").read_text())
    repository = config["repository"]
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Invalid secrets repository")
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_REPOSITORY") != repository:
        raise ValueError("Workflow repository must match the private secrets repository")
    info = json.loads(run(["gh", "repo", "view", repository, "--json", "isPrivate"]))
    if info.get("isPrivate") is not True:
        raise ValueError("Refusing to publish from a public secrets repository")
    entries = read_secrets(root)
    # Validate every document before obtaining a token or writing any secret.
    for destination, name in entries:
        print(f"{'Publish' if apply else 'Would publish'} {destination}/{name}")
    if not apply or not entries:
        return
    publisher = config.get("publisher", {})
    source = (publisher.get("repository"), publisher.get("private_key_secret"))
    if source not in entries:
        raise ValueError("Publisher private key is missing from the encrypted inventory")
    token = installation_token(publisher, entries[source])
    # App private keys permit authentication to every installation; do not copy
    # the publisher's own credentials to destination repositories.
    publisher_keys = {source[1], publisher.get("webhook_secret"), publisher.get("client_secret")}
    env = {**os.environ, "GH_TOKEN": token}
    failures = 0
    try:
        for (destination, name), value in entries.items():
            if destination == source[0] and name in publisher_keys:
                continue
            try:
                run(["gh", "secret", "set", name, "--repo", destination], content=value, env=env)
            except ValueError:
                failures += 1
                print(f"Failed to publish {destination}/{name}", file=sys.stderr)
    finally:
        # Revoke even when an upload fails. Never expose the token in arguments.
        run(["gh", "api", "--method", "DELETE", "/installation/token"], env=env)
    if failures:
        raise ValueError(f"{failures} secret upload(s) failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true", help="Upload values; otherwise list destinations only")
    args = parser.parse_args(argv)
    try:
        publish(args.root.resolve(), args.apply)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        # Decryption/API errors must not expose plaintext credentials.
        print("Secret publishing failed. Check encrypted inventory, age key, and publisher app permissions.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
