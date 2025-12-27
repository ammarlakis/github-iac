_default:
	@just --choose --unsorted 2>/dev/null || true

setup:
	cd src && terraform init

plan:
	cd src && terraform plan -out tfplan

apply args='tfplan':
	cd src && terraform apply {{args}}

fmt:
	prettier . -w
	terraform fmt -recursive src

create target:
	./scripts/create-{{target}}.sh
