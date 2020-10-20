# SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
#
# SPDX-License-Identifier: Apache-2.0

SHELL := /bin/bash
LLVM_DIR := /usr/lib/llvm-10
CRIXCG_SRC_DIR := ${CURDIR}/src
CRIXCG_BUILD_DIR := ${CURDIR}/build
PATH := $(LLVM_DIR)/bin:$(PATH)
PYENV_DIR := ${CURDIR}/venv

UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	NPROC := ${shell nproc}
else
	NPROC := ${shell sysctl -n hw.ncpu}
endif

build_analyzer_func = \
	(mkdir -p ${2} \
		&& cd ${2} \
		&&  PATH=${PATH} \
			LLVM_TOOLS_BINARY_DIR=${LLVM_DIR}/bin \
			LLVM_LIBRARY_DIRS=${LLVM_DIR}/lib \
			LLVM_INCLUDE_DIRS=${LLVM_DIR}/include \
			CC=clang CXX=clang++ \
			cmake ${1}	\
				-DCMAKE_BUILD_TYPE=Release \
				-DLLVM_ENABLE_ASSERTIONS=ON \
				-DCMAKE_CXX_FLAGS_RELEASE="-std=c++14 -fno-rtti -fpic -g -Wall" && make -j${NPROC})

GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
NC := \033[0m

define target_success
	@printf "${GREEN}==> Target \"$(1)\" passed${NC}\n\n"
endef

.DEFAULT_GOAL := crix-callgraph

TARGET: ## DESCRIPTION
	@echo "TARGET is here only to provide the header for 'help'"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?##.*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-30s\033[0m %s\n", $$1, $$2}'

LLVM_FIX := sudo apt install clang-10 llvm-10 llvm-10-dev
llvm-check: ## Check LLVM is available
	@if [ ! -d ${LLVM_DIR} ]; then \
		printf "${RED}Error: '${LLVM_DIR}' does not exist${NC}\n"; \
		printf "${YELLOW}Install llvm-10 (${LLVM_FIX}) and try again${NC}\n"; \
		false; \
	fi
	@if [ ! -d ${LLVM_DIR}/lib/cmake/llvm ]; then \
		printf "${RED}Error: '${LLVM_DIR}/lib/cmake/llvm' does not exist${NC}\n"; \
		printf "${YELLOW}Install llvm-10 (${LLVM_FIX}) and try again${NC}\n"; \
		false; \
	fi

install-requirements: ## Install python requirements
	pip3 install -r requirements.txt --no-cache-dir
	$(call target_success,$@)

install-preprequisites:
	sudo apt update
	sudo apt install -y -q python3 \
		build-essential cmake \
		clang-10 python3-clang-10 llvm-10 llvm-10-dev clang-format-10
	@if [ ! -d ${PYENV_DIR} ]; then \
		printf "${YELLOW}Python env directory does not exist${NC}\n"; \
		printf "${YELLOW}Creating python env direcotry ${PYENV_DIR}{$NC}\n"; \
	fi
	python3 -m venv venv
	source venv/bin/activate
	venv/bin/pip3 install -r requirements.txt --no-cache-dir
	$(call target_success,$@)

pre-push: test style clean ## Run tests, style, and clean
	$(call target_success,$@)

test: crix-callgraph ## Build and run tests
	pytest -vx tests/
	$(call target_success,$@)

style-pyc: ## Check with pycodestyle
	pycodestyle --max-line-length 95 --exclude='venv/','clang/','temp/' .
	$(call target_success,$@)

style-cpp: ## Check with clang-format
	scripts/clang_format.sh --warn --style LLVM
	$(call target_success,$@)

style: style-pyc style-cpp ## Check style

crix-callgraph: llvm-check ## Build crix-callgraph
	$(call build_analyzer_func, ${CRIXCG_SRC_DIR}, ${CRIXCG_BUILD_DIR})

clean-pyc: ## Remove Python artifacts
	rm -fr .pytest_cache/
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean: clean-pyc ## Remove all build artifacts
	cd tests/resources/crix-callgraph && make clean
	rm -rf ${CRIXCG_BUILD_DIR}
