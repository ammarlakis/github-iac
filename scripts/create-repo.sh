#!/usr/bin/env bash
set -euo pipefail

REPOS_DIR="$(dirname "$0")/../data/repositories"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Create New Repository ===${NC}\n"

# Repository name
read -rp "Repository name: " repo_name
if [[ -z "$repo_name" ]]; then
    echo "Error: Repository name is required"
    exit 1
fi

# Check if file already exists
repo_file="$REPOS_DIR/$repo_name.yaml"
if [[ -f "$repo_file" ]]; then
    echo "Error: Repository '$repo_name' already exists at $repo_file"
    exit 1
fi

# Visibility
echo -e "\nVisibility options: public, private"
read -rp "Visibility [private]: " visibility
visibility="${visibility:-private}"
if [[ "$visibility" != "public" && "$visibility" != "private" ]]; then
    echo "Error: Visibility must be 'public' or 'private'"
    exit 1
fi

# Description
read -rp "Description: " description

# Topics (comma-separated)
read -rp "Topics (comma-separated, e.g., terraform,automation): " topics_input

# Featured
read -rp "Featured? (y/N): " featured
featured="${featured:-n}"

# Build topics array
topics=()
if [[ "${featured,,}" == "y" || "${featured,,}" == "yes" ]]; then
    topics+=("featured")
fi
if [[ -n "$topics_input" ]]; then
    IFS=',' read -ra input_topics <<< "$topics_input"
    for topic in "${input_topics[@]}"; do
        # Trim whitespace
        topic=$(echo "$topic" | xargs)
        if [[ -n "$topic" ]]; then
            topics+=("$topic")
        fi
    done
fi

# Generate YAML content
echo -e "\n${YELLOW}Generating $repo_file...${NC}\n"

{
    echo "visibility: $visibility"
    if [[ -n "$description" ]]; then
        echo "description: \"$description\""
    fi
    if [[ ${#topics[@]} -gt 0 ]]; then
        echo "topics:"
        for topic in "${topics[@]}"; do
            echo "  - $topic"
        done
    fi
} > "$repo_file"

echo -e "${GREEN}Created:${NC}"
cat "$repo_file"

# Open in IDE
echo -e "\n${BLUE}Opening file in IDE...${NC}"
if command -v code &> /dev/null; then
    code "$repo_file"
elif command -v cursor &> /dev/null; then
    cursor "$repo_file"
elif command -v windsurf &> /dev/null; then
    windsurf "$repo_file"
fi

# Ask to apply
echo ""
read -rp "Do you want to apply changes with Terraform? (y/N): " apply_changes
if [[ "${apply_changes,,}" == "y" || "${apply_changes,,}" == "yes" ]]; then
    echo -e "\n${BLUE}Running terraform apply...${NC}\n"
    cd "$(dirname "$0")/../src"
    terraform apply
else
    echo -e "\n${YELLOW}Skipped terraform apply. Run 'just apply' when ready.${NC}"
fi
