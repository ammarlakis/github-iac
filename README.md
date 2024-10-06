# GitHub IAC

## Project Overview

This project automates the provisioning and management of GitHub resources using Terraform. Initially, the focus is on creating GitHub repositories, but the project will be extended to manage teams and organization memberships as well. Resources are defined in YAML files for simplicity and flexibility, allowing easy updates, tracking, and the ability to enforce policies later using [OPA](https://www.openpolicyagent.org/docs/latest/terraform/).

### Project Structure

- **src/**: This folder contains the Terraform code that defines how GitHub resources are provisioned. The code reads from the `data/` folder to create the necessary resources.
  
- **data/repositories/**: Contains YAML files representing the GitHub resources to be provisioned. Each YAML file describes a GitHub repository, with the file name matching the repository name.

- **schemas/**: Contains JSON schemas used to validate the YAML files in the `data/` folder. These schemas ensure that the structure of the YAML files is correct before applying changes with Terraform. For example, `repository.schema.json` validates the structure of the repository YAML files.

- **.vscode/**: Contains configuration settings for Visual Studio Code to support automatic YAML validation using the schemas in the `schemas/` folder.

## Prerequisites

- [Terraform CLI](https://www.terraform.io/downloads.html)
- [GitHub Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) with appropriate permissions for managing repositories, teams, and organization memberships.
- Your GitHub organization name or username.
- (Optional) [YAML Extension for VSCode](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) for automatic YAML validation using the provided schemas.

## Setup Instructions

### 1. Configure GitHub Authentication

Before running Terraform, set up authentication with GitHub by exporting your Personal Access Token as an environment variable:

```bash
export GITHUB_TOKEN=your_personal_access_token
export GITHUB_ORG=your_organization_name   # Or your GitHub username if you're not using an org
```

### 2. Define Resources in YAML (`data/`)

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

### 3. YAML Validation with VSCode

For those using Visual Studio Code, automatic validation of the YAML files is supported via the [YAML Extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml). Once the extension is installed, the `.vscode/settings.json` file is configured to validate all YAML files in the `data/repositories/` folder against the `repository.schema.json` schema found in the `schemas/` folder.

To validate the YAML files, make sure you have the extension installed and VSCode will automatically highlight any validation errors in the `data/repositories/` files.

Another way to validate the YAML files is using [ajv-cli](https://github.com/ajv-validator/ajv-cli).

### 4. Running Terraform

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

   Terraform will read the YAML files in the `data/repositories/` folder, provision the corresponding repositories, and store the state accordingly.

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
│   └── repositories
│       ├── my-awesome-repo.yaml    # YAML file representing a GitHub repository
│       └── another-repo.yaml       # YAML file for another repository
├── schemas/
│   └── repository.schema.json      # JSON schema for validating repository YAML files
├── .vscode/
│   └── settings.json               # VSCode settings for YAML validation
└── README.md                       # Project documentation
```

### YAML Structure

Each YAML file should follow this structure for defining repositories:

```yaml
description: <description>        # Optional: Description of the repository
visibility: <public|private>      # Required: Whether the repository is private or public
topics:                           # Optional: List of topics to categorize the repository
  - <topic-1>
  - <topic-2>
permissions:                      # Optional: List of permissions assigned to users and teams
  users:
    pull: 
      - <user-1_id>
      - <user-2_id>
    push:
      - <user-3_id>
    maintain: []
    triage: []
    admin: []
  teams:
    pull:
      - <team-1_id>
    push: []
    maintain: []
    triage: []
    admin:
      - <team-2_id>
      - <team-3_id>
```

### Future Enhancements

- **GitHub Teams**: Define teams and their permissions in YAML files and provision them via Terraform.
- **Organization Membership**: Automate the management of organization members and their roles.
