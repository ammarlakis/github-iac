#!/usr/bin/env python3
"""Bootstrap GitHub Apps and age/SOPS storage using local GitHub CLI authentication."""
import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

import yaml
from jsonschema import validate
from jsonschema.exceptions import ValidationError

NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+\Z")


def run(command, *, content=None, env=None):
    result = subprocess.run(command, input=content, capture_output=True, text=True, env=env)
    if result.returncode:
        # Tool diagnostics can contain credentials or manifest response bodies.
        raise ValueError(f"{command[0]} failed (exit {result.returncode}); check authentication and permissions")
    return result.stdout


def require(*commands):
    for command in commands:
        if shutil.which(command) is None:
            raise ValueError(f"Install {command} before running this command")


def load(path):
    result = yaml.safe_load(path.read_text())
    if not isinstance(result, dict):
        raise ValueError(f"Expected a YAML object in {path}")
    return result


def write_yaml(path, data, schema=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    hint = f"# yaml-language-server: $schema={schema}\n" if schema else ""
    path.write_text(hint + yaml.safe_dump(data, sort_keys=False))


def private_repository(directory, repository):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Use a GitHub repository in owner/name format")
    remote = run(["git", "-C", str(directory), "remote", "get-url", "origin"]).strip()
    if remote.removesuffix(".git") not in [f"git@github.com:{repository}", f"https://github.com/{repository}", f"ssh://git@github.com/{repository}"]:
        raise ValueError("The secrets checkout origin must match the requested GitHub repository")
    info = json.loads(run(["gh", "repo", "view", repository, "--json", "isPrivate"]))
    if info.get("isPrivate") is not True:
        raise ValueError("Encrypted credentials must be stored in a PRIVATE GitHub repository")


def key_path(repository):
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "github-iac/age" / f"{repository.replace('/', '--')}.txt"


def initialize_secrets(directory, repository, identity):
    require("gh", "git", "age-keygen", "sops")
    directory, identity = directory.resolve(), identity.expanduser().resolve()
    private_repository(directory, repository)
    identity.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    check = subprocess.run(["git", "-C", str(identity.parent), "rev-parse", "--show-toplevel"], capture_output=True)
    if check.returncode == 0:
        raise ValueError("The private age key must be outside every Git working tree")
    config_path = directory / "secrets-config.yaml"
    previous = load(config_path) if config_path.exists() else None
    if previous and previous.get("repository") != repository:
        raise ValueError("Existing secrets configuration belongs to a different repository")
    if not previous and (directory / ".sops.yaml").exists():
        raise ValueError("Existing .sops.yaml must be preserved; initialize in a dedicated checkout")
    if not identity.exists():
        if previous:
            raise ValueError("Existing age key is missing; restore it rather than rotating it implicitly")
        run(["age-keygen", "-o", str(identity)])
    identity.chmod(0o600)
    recipient = run(["age-keygen", "-y", str(identity)]).strip()
    if previous and previous.get("age_recipient") != recipient:
        raise ValueError("Existing configuration uses another age key; refusing to replace it")
    write_yaml(config_path, {**(previous or {}), "repository": repository, "age_recipient": recipient})
    if not previous:
        write_yaml(directory / ".sops.yaml", {"creation_rules": [{"path_regex": r"secrets/.*\.enc\.yaml$", "age": recipient}]})
    # Upload through stdin, never a command argument or console output.
    run(["gh", "secret", "set", "SOPS_AGE_KEY", "--repo", repository], content=identity.read_text())
    assets = Path(__file__).parent / "assets"
    for source, target in [(assets / "publish-secrets.yaml", directory / ".github/workflows/publish-secrets.yaml"),
                           (Path(__file__).with_name("publish-secrets.py"), directory / "scripts/publish-secrets.py")]:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"Initialized encrypted storage in {repository}; uploaded SOPS_AGE_KEY.")
    print(f"Keep a secure backup of the private age key: {identity}")


def app_file(root, name):
    if not NAME.fullmatch(name):
        raise ValueError("Invalid app name")
    return root / "data/apps" / f"{name}.yaml"


def validate_app(root, config):
    validate(config, json.loads((root / "schemas/app.schema.json").read_text()))
    if config.get("publisher") and config.get("manifest", {}).get("default_permissions", {}).get("secrets") != "write":
        raise ValueError("A publishing app must request secrets: write")


def publisher_metadata(directory, name, config):
    if not config.get("publisher"):
        return
    vault = load(directory / "secrets-config.yaml")
    prefix = config.get("secrets", {}).get("prefix", re.sub(r"[^A-Z0-9_]", "_", name.upper()))
    destination = config.get("secrets", {}).get("repository", vault["repository"])
    if destination != vault["repository"]:
        raise ValueError("Publisher credentials must target the private secrets repository")
    existing = vault.get("publisher", {})
    if existing and existing.get("app_id") != config.get("app_id"):
        raise ValueError("Another publisher is already configured; refusing to replace it")
    vault["publisher"] = {"app_id": config["app_id"], "repository": destination, "private_key_secret": f"{prefix}_PRIVATE_KEY", "webhook_secret": f"{prefix}_WEBHOOK_SECRET", "client_secret": f"{prefix}_CLIENT_SECRET"}
    if config.get("installation_id"):
        vault["publisher"]["installation_id"] = config["installation_id"]
    write_yaml(directory / "secrets-config.yaml", vault)


def manifest_for(config, callback):
    manifest = dict(config["manifest"])
    if "redirect_url" in manifest:
        raise ValueError("redirect_url is supplied by the local bootstrap callback")
    manifest["redirect_url"] = callback
    return manifest


def registration_code(manifest, owner, organization, timeout=600):
    state = secrets.token_urlsafe(32)
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            # Callback URLs contain one-time codes; never log them.
            pass

        def do_GET(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.send_error(403)
                return
            parsed = urlparse(self.path)
            if parsed.path == f"/start/{state}":
                endpoint = f"https://github.com/organizations/{owner}/settings/apps/new" if organization else "https://github.com/settings/apps/new"
                action = endpoint + "?" + urlencode({"state": state})
                body = f'<form method="post" action="{html.escape(action, quote=True)}"><input type="hidden" name="manifest" value="{html.escape(json.dumps(manifest), quote=True)}"><button>Register GitHub App</button></form>'
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body.encode())
            elif parsed.path == "/callback":
                query = parse_qs(parsed.query)
                code = query.get("code", [""])[0]
                if query.get("state", [""])[0] != state or not re.fullmatch(r"[A-Za-z0-9_-]+", code):
                    self.send_error(403)
                    return
                result["code"] = code
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Registration approved. Return to your terminal.")
            else:
                self.send_error(404)

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        manifest["redirect_url"] = f"http://127.0.0.1:{server.server_port}/callback"
        url = f"http://127.0.0.1:{server.server_port}/start/{state}"
        print(f"Approve app registration in your browser: {url}")
        webbrowser.open(url)
        deadline = time.monotonic() + timeout
        server.timeout = 1
        while "code" not in result and time.monotonic() < deadline:
            server.handle_request()
    if "code" not in result:
        raise ValueError("App registration timed out; no app credentials were captured")
    return result["code"]


def store_credentials(directory, name, credentials, destination, prefix):
    config = load(directory / "secrets-config.yaml")
    private_repository(directory, config["repository"])
    if not REPOSITORY.fullmatch(destination) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", prefix) or prefix.startswith("GITHUB_"):
        raise ValueError("Invalid secret destination or prefix")
    if not isinstance(credentials.get("pem"), str) or not credentials["pem"]:
        raise ValueError("GitHub did not return an app private key")
    values = {
        f"{prefix}_{suffix}": credentials[key]
        for key, suffix in [("pem", "PRIVATE_KEY"), ("webhook_secret", "WEBHOOK_SECRET"), ("client_secret", "CLIENT_SECRET")]
        if isinstance(credentials.get(key), str) and credentials[key]
    }
    document = {"repositories": {destination: {"secrets": values}}}
    ciphertext = run(["sops", "encrypt", "--age", config["age_recipient"], "--input-type", "yaml", "--output-type", "yaml", "/dev/stdin"], content=yaml.safe_dump(document))
    target = directory / "secrets/apps" / f"{name}.enc.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusively create: re-registration must never overwrite existing credentials.
    with target.open("x") as output:
        output.write(ciphertext)
    return target


def bootstrap_app(root, name, directory):
    require("gh", "git", "sops")
    path = app_file(root, name)
    config = load(path)
    validate_app(root, config)
    if config.get("app_id"):
        raise ValueError("This app is already registered; bootstrap will not recreate it")
    if (directory / "secrets/apps" / f"{name}.enc.yaml").exists():
        raise ValueError("Encrypted app credentials already exist; recover app metadata instead of recreating the app")
    vault = load(directory / "secrets-config.yaml")
    private_repository(directory, vault["repository"])
    answers = load(root / ".copier-answers.yml")
    owner = answers["github_owner"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", owner):
        raise ValueError("Invalid github_owner")
    destination = config.get("secrets", {}).get("repository", vault["repository"])
    if config.get("publisher") and (destination != vault["repository"] or vault.get("publisher")):
        raise ValueError("Publisher must be the first publisher and store credentials in the private secrets repository")
    prefix = config.get("secrets", {}).get("prefix", re.sub(r"[^A-Z0-9_]", "_", name.upper()))
    if prefix.startswith("GITHUB_") or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", prefix):
        raise ValueError("Set a valid secrets.prefix that does not start with reserved GITHUB_")
    manifest = manifest_for(config, "http://127.0.0.1/callback")
    code = registration_code(manifest, owner, answers.get("organization", False))
    credentials = json.loads(run(["gh", "api", "--method", "POST", f"/app-manifests/{code}/conversions"]))
    destination = config.get("secrets", {}).get("repository", vault["repository"])
    prefix = config.get("secrets", {}).get("prefix", re.sub(r"[^A-Z0-9_]", "_", name.upper()))
    config.update({"app_id": credentials["id"], "slug": credentials["slug"]})
    write_yaml(path, config, "../../schemas/app.schema.json")
    encrypted = store_credentials(directory, name, credentials, destination, prefix)
    publisher_metadata(directory, name, config)
    print(f"Registered {name}; credentials encrypted in {encrypted}.")
    print(f"Install with selected repository access: https://github.com/apps/{credentials['slug']}/installations/new")
    print(f"Then record the installation ID: python scripts/github-apps.py record-installation {name} INSTALLATION_ID --secrets-directory {directory}")


def adopt_app(root, name, directory, app_id, slug, private_key_file, client_secret_file=None, webhook_secret_file=None):
    require("gh", "git", "sops", "openssl")
    path = app_file(root, name)
    config = load(path)
    if app_id < 1 or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError("Invalid app ID or slug")
    if config.get("app_id") not in [None, app_id]:
        raise ValueError("This definition already belongs to another app")
    config.update({"app_id": app_id, "slug": slug})
    validate_app(root, config)
    vault = load(directory / "secrets-config.yaml")
    destination = config.get("secrets", {}).get("repository", vault["repository"])
    if config.get("publisher"):
        if destination != vault["repository"]:
            raise ValueError("Publisher credentials must target the private secrets repository")
        if vault.get("publisher", {}).get("app_id", app_id) != app_id:
            raise ValueError("Another publisher is already configured; refusing to replace it")
    private_key_file = private_key_file.expanduser().resolve()
    if private_key_file.is_relative_to(root.resolve()) or private_key_file.is_relative_to(directory.resolve()):
        raise ValueError("Keep plaintext private keys outside both repositories")
    private_key_file.chmod(0o600)
    run(["openssl", "pkey", "-in", str(private_key_file), "-noout"])
    credentials = {"pem": private_key_file.read_text()}
    for key, file in [("client_secret", client_secret_file), ("webhook_secret", webhook_secret_file)]:
        if file:
            credentials[key] = file.expanduser().read_text().strip()
    prefix = config.get("secrets", {}).get("prefix", re.sub(r"[^A-Z0-9_]", "_", name.upper()))
    encrypted = store_credentials(directory, name, credentials, destination, prefix)
    write_yaml(path, config, "../../schemas/app.schema.json")
    publisher_metadata(directory, name, config)
    print(f"Adopted existing app {name}; credentials encrypted in {encrypted}.")


def effective_repositories(root):
    defaults_path = root / "data/defaults.yaml"
    defaults = load(defaults_path) if defaults_path.exists() else {}
    for path in sorted((root / "data/repositories").glob("*.yaml")):
        repo = load(path)
        preset = load(root / "data/presets" / f"{repo['preset']}.yaml") if "preset" in repo else {}
        yield path.stem, {**defaults, **preset, **repo}


def import_assignments(root, name):
    config = load(app_file(root, name))
    installation = config.get("installation_id")
    if not isinstance(installation, int) or isinstance(installation, bool) or installation < 1:
        raise ValueError("Record a valid installation_id before importing")
    require("gh", "terraform")
    repositories = [repository for repository, config in effective_repositories(root) if name in config.get("apps", [])]
    if not repositories:
        return
    try:
        installed = json.loads(run(["gh", "api", "--paginate", "--slurp", f"/user/installations/{installation}/repositories?per_page=100"]))
    except ValueError as error:
        raise ValueError("Cannot read installation assignments; check user access. For GitHub CLI OAuth authentication, run gh auth refresh -h github.com -s read:user") from error
    for repository in repositories:
        address = f'github_app_installation_repository.app[{json.dumps(repository + "/" + name)}]'
        # Check membership so newly assigned repositories can be created by apply.
        if not any(repo["name"] == repository for page in installed for repo in page["repositories"]):
            print(f"{repository}: not currently assigned; Terraform apply will add it.")
            continue
        state = run(["terraform", f"-chdir={root / 'src'}", "state", "list"])
        if address in state.splitlines():
            continue
        subprocess.run(["terraform", f"-chdir={root / 'src'}", "import", address, f"{installation}:{repository}"], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-secrets")
    init.add_argument("directory", type=Path, help="Local checkout of a private secrets repository")
    init.add_argument("--repository", required=True, help="owner/name of the private repository")
    init.add_argument("--key-file", type=Path)
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("name")
    bootstrap.add_argument("--secrets-directory", type=Path, required=True)
    adopt = commands.add_parser("adopt")
    adopt.add_argument("name")
    adopt.add_argument("--secrets-directory", type=Path, required=True)
    adopt.add_argument("--app-id", type=int, required=True)
    adopt.add_argument("--slug", required=True)
    adopt.add_argument("--private-key-file", type=Path, required=True)
    adopt.add_argument("--client-secret-file", type=Path)
    adopt.add_argument("--webhook-secret-file", type=Path)
    record = commands.add_parser("record-installation")
    record.add_argument("name")
    record.add_argument("installation_id", type=int)
    record.add_argument("--secrets-directory", type=Path)
    imports = commands.add_parser("import")
    imports.add_argument("name")
    args = parser.parse_args(argv)
    try:
        if args.command == "init-secrets":
            initialize_secrets(args.directory, args.repository, args.key_file or key_path(args.repository))
        elif args.command == "bootstrap":
            bootstrap_app(args.root, args.name, args.secrets_directory.resolve())
        elif args.command == "adopt":
            adopt_app(args.root, args.name, args.secrets_directory.resolve(), args.app_id, args.slug, args.private_key_file, args.client_secret_file, args.webhook_secret_file)
        elif args.command == "record-installation":
            if args.installation_id < 1:
                raise ValueError("installation_id must be positive")
            path = app_file(args.root, args.name)
            config = load(path)
            validate_app(args.root, config)
            if config.get("publisher"):
                if args.secrets_directory is None:
                    raise ValueError("A publishing app needs --secrets-directory to record its installation")
                vault = load(args.secrets_directory / "secrets-config.yaml")
                private_repository(args.secrets_directory, vault["repository"])
            config["installation_id"] = args.installation_id
            write_yaml(path, config, "../../schemas/app.schema.json")
            if args.secrets_directory:
                publisher_metadata(args.secrets_directory, args.name, config)
        elif args.command == "import":
            import_assignments(args.root, args.name)
    except (OSError, ValueError, KeyError, TypeError, ValidationError, yaml.YAMLError, subprocess.CalledProcessError) as error:
        print(f"App setup failed: {error}" if isinstance(error, ValueError) else "App setup failed; check configuration and tool authentication.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
