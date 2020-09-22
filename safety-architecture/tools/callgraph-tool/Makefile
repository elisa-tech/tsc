SHELL := /bin/bash
LLVM_DIR := /usr/lib/llvm-10/
CRIXCG_SRC_DIR := ${CURDIR}/src
CRIXCG_BUILD_DIR := ${CURDIR}/build

UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	NPROC := ${shell nproc}
else
	NPROC := ${shell sysctl -n hw.ncpu}
endif

build_analyzer_func = \
	(mkdir -p ${2} \
		&& cd ${2} \
		&& PATH=${LLVM_DIR}/bin:${PATH} \
			LLVM_TOOLS_BINARY_DIR=${LLVM_DIR}/bin \
			LLVM_LIBRARY_DIRS=${LLVM_DIR}/lib \
			LLVM_INCLUDE_DIRS=${LLVM_DIR}/include \
			CC=clang CXX=clang++ \
			cmake ${1}	\
				-DCMAKE_BUILD_TYPE=Release \
				-DLLVM_ENABLE_ASSERTIONS=ON \
				-DCMAKE_CXX_FLAGS_RELEASE="-std=c++14 -fno-rtti -fpic -g -Wall" && make -j${NPROC})

define target_success
	@printf "\033[32m==> Target \"$(1)\" passed\033[0m\n\n"
endef

.DEFAULT_GOAL := crix-callgraph

TARGET: ## DESCRIPTION
	@echo "TARGET is here only to provide the header for 'help'"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?##.*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-30s\033[0m %s\n", $$1, $$2}'

llvm-check:
	@if [ ! -d ${LLVM_DIR} ]; then \
		echo "Error: '${CLANG_BIN_DIR}' does not exist."; \
		echo -e "Install clang-10 (sudo apt install clang-10) and try again."; \
		false; \
	fi

install-requirements: ## Install python requirements
	pip3 install -r requirements.txt --no-cache-dir
	$(call target_success,$@)

pre-push: test style clean ## Run tests, style, and clean
	$(call target_success,$@)

test: crix-callgraph ## Build and run tests
	pytest -vx tests/
	$(call target_success,$@)

style-pyc: # Check with pycodestyle
	pycodestyle --max-line-length 95 --exclude='venv/','clang/','temp/' .
	$(call target_success,$@)

style: style-pyc # Check style

crix-callgraph: llvm-check ## Build crix-callgraph
	$(call build_analyzer_func, ${CRIXCG_SRC_DIR}, ${CRIXCG_BUILD_DIR})

clean-pyc: ## Remove Python artifacts
	rm -fr .pytest_cache/
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean: clean-pyc ## Remove all build artifacts
	cd tests/resources && make clean
	rm -rf ${CRIXCG_BUILD_DIR}
