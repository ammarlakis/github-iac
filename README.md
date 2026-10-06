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

The YAML filename is the name of the fork in your account. Omit `fork` for original repositories. Forks still use the project's shared repository settings. This requires GitHub provider 6.8 or later within version 6.

For an existing fork, add its YAML and import it before applying:

```bash
terraform -chdir=src import 'github_repository.create["devcards.devtech.tools"]' devcards.devtech.tools
terraform -chdir=src import 'github_repository_collaborators.users["devcards.devtech.tools"]' devcards.devtech.tools
```

Review the plan: changing a fork's upstream can require replacement. The template's optional bulk-import discovery still excludes forks; add them explicitly with their upstream information.

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
