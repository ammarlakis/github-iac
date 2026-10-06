# GitHub IAC

A Copier template for managing GitHub repositories, teams, and organization membership with Terraform and YAML. It supports reusable repository presets, rulesets, Actions permissions, Pages, and security settings.

Create a project with:

```sh
copier copy https://github.com/ammarlakis/github-iac myproject/
```

See the [generated project guide](template/README.md) for configuration, authentication, and Terraform usage. Generated projects include `just update` to run `copier update --skip-answered`. Set `add_justfile=false` when copying to omit that Justfile.

## Repository layout

- `copier.yaml` defines template questions and selects `template/` as the source directory.
- `template/` contains all files distributed to generated projects, including its own optional Justfile.
- `Justfile`, `tests/`, and `.github/` at the repository root are maintenance tools. Copier does not copy them.

Add new project files under `template/`; keep maintenance files at the root. The generated directory layout stays the same when existing projects update through Copier.

## Development

Install Terraform, Copier, PyYAML, and jsonschema. Just is optional; it provides these maintenance commands:

```sh
just check  # Terraform formatting and shell syntax
just test   # Schema checks, template rendering, and mocked Terraform plans
just fmt    # Format with Prettier and Terraform (requires Prettier)
```

Without Just, run:

```sh
terraform fmt -check template/src
bash -n template/scripts/create-repo.sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/validate_template.py
```

Validation renders personal and organization projects, checks optional Justfile and workflow generation, validates schema hints, and tests preset inheritance and repository features. Terraform downloads providers but the mocked plans make no GitHub changes.
