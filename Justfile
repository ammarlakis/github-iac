_default:
	@just --choose --unsorted 2>/dev/null || true

check:
	terraform fmt -check template/src
	bash -n template/scripts/create-repo.sh

# Validate schemas, render template variants, and test mocked Terraform plans.
test: check
	python3 -m unittest discover -s tests -p 'test_*.py'
	python3 tests/validate_template.py

fmt:
	prettier . -w
	terraform fmt -recursive template/src
