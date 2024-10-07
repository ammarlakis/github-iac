# GitHub IAC

## Project Overview

This project automates the provisioning and management of GitHub resources using Terraform. Resources are defined in YAML files for simplicity and flexibility, allowing easy updates, tracking, and the ability to enforce policies later using [OPA](https://www.openpolicyagent.org/docs/latest/terraform/).

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

### 2. Configure GitHub Authentication

Before running Terraform, set up authentication with GitHub by exporting your Personal Access Token as an environment variable:

```bash
export GITHUB_TOKEN=your_personal_access_token
```

Alternatively, you can authenticate using the [GitHub CLI](https://cli.github.com/):
```
gh auth login
```

In deployment pipelines, it's recommended to use [GitHub App authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow).

### 3. Define Resources in YAML (`data/`)

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

### 4. YAML Validation with VSCode

For Visual Studio Code users, automatic validation of YAML files is supported through the [YAML Extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml). Once the extension is installed, the `.vscode/settings.json` file is configured to validate all YAML files in the `data/` folder against the relevant schema found in the `schemas/` folder. Simply install the extension, and VSCode will automatically highlight any validation errors in your YAML files.

Alternatively, you can manually validate YAML files using the [ajv-cli](https://github.com/ajv-validator/ajv-cli).

### 5. Running Terraform

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

### Future Enhancements

- **GitHub Teams**: Define teams and their permissions in YAML files and provision them via Terraform.
