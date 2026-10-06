# GitHub IAC

## Project Overview

This project automates the provisioning and management of GitHub resources using Terraform. Resources are defined in YAML files for simplicity and flexibility, allowing easy updates, tracking, and the ability to extend the logic around managing these files.

### Project Structure

- **src/**: This folder contains the Terraform code that defines how GitHub resources are provisioned. The code reads from the `data/` folder to create the necessary resources.
- **data/repositories/**: Contains YAML files representing the repositories to be provisioned. Each YAML file describes a GitHub repository, with the file name matching the repository name.

- **data/teams/**: Contains YAML files representing the teams to be provisioned. Each YAML file describes a GitHub team, with the file name matching the team name.

- **data/membership.yaml**: A YAML file that assigns users to roles in the organization.

- **schemas/**: Contains JSON schemas used to validate the YAML files in the `data/` folder. These schemas ensure that the structure of the YAML files is correct before applying changes with Terraform. For example, `repository.schema.json` validates the structure of the repository YAML files.

- **.vscode/**: Contains configuration settings for Visual Studio Code to support automatic YAML validation using the schemas in the `schemas/` folder.

### Folder Structure

```
.
├── src/
│   ├── locals.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── repositories.tf
│   ├── terraform.tf
│   └── variables.tf
├── data/
│   ├── repositories
│   │   ├── my-awesome-repo.yaml    # YAML file representing a GitHub repository
│   │   └── another-repo.yaml       # YAML file for another repository
│   ├── teams
│   │   ├── team-rocket.yaml        # YAML file representing a GitHub team
│   │   └── team-plasma.yaml        # YAML file for a better team
│   └── membership.yaml             # YAML file containing organization membership assignment
├── schemas/
│   ├── repository.schema.json      # JSON schema for validating repository YAML files
│   ├── membership.schema.json      # JSON schema for validating membership YAML file
│   └── team.schema.json            # JSON schema for validating team YAML files
├── .vscode/
│   └── settings.json               # VSCode settings for YAML validation
└── README.md                       # Project documentation
```

## Prerequisites

- [Terraform CLI](https://www.terraform.io/downloads.html)
- [GitHub Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) with appropriate permissions for managing repositories, teams, and organization memberships.
- [Copier](https://copier.readthedocs.io/en/stable/) to copy this template.
- (Optional) [YAML Extension for VSCode](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) for automatic YAML validation using the provided schemas.

## Setup Instructions

### 1. Provisioning the Template

To use this project template, you can copy it using Copier:

```bash
copier copy https://github.com/ammarlakis/github-iac myproject/
```

During the setup, you'll be asked several questions:

- **github_owner**: Your GitHub username or organization name
- **organization**: Whether this is for managing an organization (enables teams and membership management)
- **enable_actions**: Whether to create GitHub Actions workflows
- **import_existing**: Whether to import existing repositories from your GitHub account/organization

### 2. Importing Existing Repositories

If you choose to import existing repositories during setup, the template will include Terraform configuration that:

1. Uses the `github_repositories` data source to fetch all active repositories (excluding archived and forked repos)
2. Uses Terraform's native `import` blocks to import existing repositories into state
3. Generates YAML configuration files for each repository under `data/repositories/`

After the template is generated, run the following commands to complete the import:

```bash
cd myproject/src
terraform init
terraform apply  # This will import existing repos and generate YAML files
```

After the initial import, you can remove the `import.tf` and `import_generate.tf` files from the `src/` directory since they are only needed for the initial setup. The generated YAML files will remain and can be modified as needed.

### 3. Configure GitHub Authentication

Before running Terraform, set up authentication with GitHub by exporting your Personal Access Token as an environment variable:

```bash
export GITHUB_TOKEN=your_personal_access_token
```

Alternatively, you can authenticate using the [GitHub CLI](https://cli.github.com/):

```
gh auth login
```

In deployment pipelines, it's recommended to use [GitHub App authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow).

### 4. Define Resources in YAML (`data/`)

#### Repositories

Each YAML file in the `data/repositories/` folder represents a GitHub repository. The name of the YAML file should match the repository name you want to create.

For example, to create a repository called `my-awesome-repo`, create a file named `my-awesome-repo.yaml` in the `data/repositories/` folder with the following content:

```yaml
description: "This is an awesome repository"
visibility: private # or public
topics:
  - terraform
  - automation
```

The YAML files can be easily updated to reflect changes to the repositories you want to manage, such as updating descriptions, visibility, and topics.

#### Repository settings

Repository YAML supports optional `has_issues`, `has_projects`, `has_wiki`, `homepage_url`, `allow_auto_merge`, `allow_merge_commit`, `allow_rebase_merge`, `allow_squash_merge`, and `delete_branch_on_merge` fields. `has_issues` defaults to `true`; omitted settings otherwise retain the GitHub provider's behavior. Existing repositories do not need to repeat these options.

For example, a repository can use squash-only merging:

```yaml
# yaml-language-server: $schema=../../schemas/repository.schema.json
visibility: private
has_issues: true
has_projects: false
has_wiki: false
homepage_url: ""
allow_auto_merge: true
allow_merge_commit: false
allow_rebase_merge: false
allow_squash_merge: true
delete_branch_on_merge: true
```

The example files and generated repository YAML start with a schema hint. With the recommended Red Hat YAML extension installed, VS Code uses that relative schema path for validation and completion, including when opening a file outside the project workspace. See the [extension's schema association documentation](https://github.com/redhat-developer/vscode-yaml#associating-schemas).

#### Forks

Specify an upstream repository to create or manage a fork:

```yaml
visibility: public
fork:
  owner: devtech-mena
  repository: devcards.devtech.tools
```

The YAML filename is the name of the fork in your account. Omit `fork` for original repositories. Forks still use the project's shared repository settings. This template requires GitHub provider 6.13 or later within version 6.

For an existing fork, add its YAML and import it before applying:

```bash
terraform -chdir=src import 'github_repository.create["devcards.devtech.tools"]' devcards.devtech.tools
terraform -chdir=src import 'github_repository_collaborators.users["devcards.devtech.tools"]' devcards.devtech.tools
```

Review the plan: changing a fork's upstream can require replacement. The template's optional bulk-import discovery still excludes forks; add them explicitly with their upstream information.

#### Shared defaults, Actions, and Pages

Use `data/defaults.yaml` for shared repository settings. Repository YAML overrides those values. `actions` and `security` objects merge one level deep; nested objects and the entire `rulesets` map are replaced when specified on a repository. Use `rulesets: {}` to opt out of inherited rulesets. Omitted settings are not managed by the new policy resources.

```yaml
# yaml-language-server: $schema=../schemas/repository-defaults.schema.json
allow_squash_merge: true
allow_merge_commit: false
allow_rebase_merge: false
actions:
  enabled: true
  allowed_actions: selected
  allowed_actions_config:
    github_owned_allowed: true
    verified_allowed: false
    patterns_allowed: ["my-org/*"]
  default_workflow_permissions: read
  can_approve_pull_request_reviews: false
pages:
  build_type: workflow
```

Actions also supports `allowed_actions: all` or `local_only`, disabling Actions with `enabled: false`, and `sha_pinning_required`. Organization policies may further restrict repository permissions. Pages defaults only apply to repositories that declare a `pages` object; they do not create sites for every repository. Use `pages: {}` to opt in, or `pages: {enabled: false}` to disable a configured site. Workflow deployments omit a source branch. Legacy deployments retain `branch` (default `master`) and `path` (default `/`). The existing inline Pages resource is retained for state compatibility.

#### Rulesets

Configure named repository rulesets instead of legacy branch-protection resources:

```yaml
# yaml-language-server: $schema=../../schemas/repository.schema.json
visibility: public
rulesets:
  main:
    target: branch
    enforcement: active
    include: ["~DEFAULT_BRANCH"]
    exclude: []
    rules:
      deletion: true
      non_fast_forward: true
      required_linear_history: true
      pull_request:
        required_approving_review_count: 1
        dismiss_stale_reviews_on_push: true
        require_code_owner_review: true
        required_review_thread_resolution: true
      required_status_checks:
        strict_required_status_checks_policy: true
        required_checks:
          - context: test
```

Each map key is the ruleset name. Defaults are `target: branch`, `enforcement: active`, and the default branch; tag rulesets default to all tags. Supported rules include creation/update/deletion restrictions, force-push protection, linear history, signatures, pull-request reviews and merge methods, status checks, deployments, merge queues, and branch/tag/commit patterns. `bypass_actors` specifies GitHub actor IDs, types, and bypass modes. The schema lists the supported fields; this is not a generic wrapper for every ruleset API option.

GitHub applies overlapping rulesets together. Plan and account restrictions still apply. Conversation resolution is part of the pull-request rule, unlike the standalone legacy setting. See [GitHub's ruleset comparison](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) and [migration guidance](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/converting-branch-protections-to-rulesets). Import an existing ruleset by its GitHub ID before applying to avoid creating a duplicate:

```bash
terraform -chdir=src import 'github_repository_ruleset.policy["my-repo/main"]' my-repo:12345
```

This template does not delete existing branch protections or convert them automatically.

#### Repository security

Security options are explicit booleans under `security`:

```yaml
# yaml-language-server: $schema=../../schemas/repository.schema.json
visibility: public
security:
  vulnerability_alerts: true
  dependabot_security_updates: true
  secret_scanning: true
  secret_scanning_push_protection: true
```

The template also supports `advanced_security`, `code_security`, `secret_scanning_ai_detection`, and `secret_scanning_non_provider_patterns`. Omit `advanced_security` on public repositories, where GitHub already enables it. Availability depends on GitHub licensing, repository visibility, and organization policy. Dependabot security updates require vulnerability alerts. Explicit `false` disables a managed feature; omission leaves it unmanaged unless inherited from defaults. Alerts and Dependabot updates use dedicated Terraform resources. These features require GitHub provider 6.13 or later within version 6.

#### Fork synchronization

Forks are not synced automatically unless enabled in their own YAML:

```yaml
# yaml-language-server: $schema=../../schemas/repository.schema.json
visibility: public
fork:
  owner: upstream-owner
  repository: upstream-repo
  sync:
    enabled: true
    branch: main
```

Preview with `python scripts/sync-forks.py`; add `--repository my-fork` to select one fork. Install `PyYAML>=6,<7` and GitHub CLI locally. `--apply` performs the sync and requires `GH_TOKEN` (or `GITHUB_TOKEN`) with write access to the selected forks. The optional branch is used in both repositories; without it, GitHub CLI uses the upstream default branch.

When template Actions are enabled, the generated `sync-forks.yaml` workflow runs daily at 04:17 UTC and on manual dispatch. Set the controller repository's `FORK_SYNC_TOKEN` Actions secret to a token scoped to the opted-in destination forks, with Contents write access (and Workflows write when syncing workflow files). Its built-in token cannot write to other repositories. A run with no opted-in forks does nothing and needs no sync token.

Syncing uses [GitHub CLI's fast-forward-only behavior](https://cli.github.com/manual/gh_repo_sync), never `--force`. Divergence, permission failures, or ruleset restrictions fail the run for review while allowing the remaining configured forks to be attempted. It does not automatically merge conflicts, rebase commits, or bypass protections. `fork.sync` cannot be set through shared defaults.

#### Membership

To assign membership in your organiztion, update the `admins` or `members` list with the usernames you want to assign. For example:

```yaml
admins:
  - ammarlakis
members:
  - yamanlk
```

#### Teams

To create a team, create a new YAML file under `data/teams` where the name of the file is the name of the team.

For example, to create a team called `team-rocket`, create a file named `team-rocket.yaml` in the `data/teams/` folder with the following contents:

```yaml
description: "Prepare for trouble! And make it double!"
privacy: "secret"
membership:
  maintainers:
    - ammarlakis
  members:
    - yamanlk
```

### 5. YAML Validation with VSCode

For Visual Studio Code users, automatic validation of YAML files is supported through the [YAML Extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml). Once the extension is installed, the `.vscode/settings.json` file is configured to validate all YAML files in the `data/` folder against the relevant schema found in the `schemas/` folder. Simply install the extension, and VSCode will automatically highlight any validation errors in your YAML files.

Alternatively, you can manually validate YAML files using the [ajv-cli](https://github.com/ajv-validator/ajv-cli).

### 6. Running Terraform

1. Navigate to the `src/` directory:

   ```bash
   cd src/
   ```

2. Initialize Terraform:

   ```bash
   terraform init
   ```

3. Apply the configuration to provision the repositories:

   ```bash
   terraform apply
   ```

   Terraform will read the YAML files in the `data/` folder, provision the corresponding repositories and teams, assign users membership, and store the state accordingly.

## Future Improvements

1. **Enhanced Security and Compliance**:
   - Implement [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) to enforce security and compliance policies on resources before they are created.
2. **Additional Resource Types**:

   - Extend support to manage other GitHub resources like Applications.

3. **GitHub App Authentication**:

   - Improve automation in CI/CD pipelines by integrating GitHub App authentication, enhancing security and reducing reliance on personal tokens.

4. **CI/CD Integration**:

   - Integrate a CI/CD pipeline to automatically validate YAML structure and apply Terraform changes when files are updated.

5. **Resource Diffing and Drift Detection**:

   - Add logic to detect and report configuration drift, notifying when resources in GitHub differ from the expected state in Terraform.

6. **Better Error Handling and Logging**:

   - Enhance error messages and logs for better debugging and monitoring, possibly integrating with monitoring tools.

7. **Template Management**:
   - Use a templating tool like [Copier](https://copier.readthedocs.io/en/stable/) to enable users to create new projects with this template and customize resources based on pre-defined configurations.

## License

This project is licensed under the MIT License.

## Support Me

I create open-source code and write articles on [my website](https://ammarlakis.com) and [GitHub](https://github.com/ammarlakis), covering topics like automation, platform engineering, and smart home technology.

If you’d like to support my work (or treat my cat to a tuna can!), you can do so here:

[![Buy my cat a tuna can 😸](https://img.buymeacoffee.com/button-api/?text=Buy%20my%20cat%20a%20tuna%20can&emoji=%F0%9F%98%B8&slug=ammarlakis&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff)](https://www.buymeacoffee.com/ammarlakis)

## Template development checks

In the `github-iac` template source checkout, install Copier, Terraform, GitHub CLI, PyYAML, and jsonschema, then run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/validate_template.py
```

The integration check renders personal and organization templates, validates schema hints, and runs mocked Terraform plans. It downloads providers but makes no GitHub changes. Test files and local search indexes are excluded from generated projects.
