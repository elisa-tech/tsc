# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

define target_success
	@printf "\033[32m==> Target \"$(1)\" passed\033[0m\n\n"
endef

.DEFAULT_GOAL := help

TARGET: ## DESCRIPTION
	@echo "TARGET is here only to provide the header for 'help'"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?##.*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-30s\033[0m %s\n", $$1, $$2}'

install-requirements:  ## Install all requirements
	pip3 install -r requirements.txt --no-cache-dir
	$(call target_success,$@)

pre-push: test style clean ## Run tests, pycodestyle, and clean
	$(call target_success,$@)

test: ## Run tests
	./tests/resources/generate_compile_commands.sh
	cd ./tests/resources && ./generate_expected_output.sh
	pytest -vx tests/
	$(call target_success,$@)

style: ## Check with pycodestyle
	pycodestyle --max-line-length 95 --exclude='venv/','clang/','temp/' .
	$(call target_success,$@)

reuse-lint: ## Check with reuse lint
	reuse lint
	$(call target_success,$@)

coverage: ## Check test coverage
	pytest --cov-report=term --cov=./ --cov-config=.coveragerc tests/

clean: clean-pyc clean-test ## Remove all artifacts
	$(call target_success,$@)

clean-test: ## Remove test and coverage artifacts
	rm -f .coverage
	rm -fr .pytest_cache/
	rm -fr tests/resources/*.json
	rm -fr tests/resources/*.csv

clean-pyc: ## Remove Python artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

