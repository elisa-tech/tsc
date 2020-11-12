# SPDX-FileCopyrightText: 2020 callgraph-tool authors. All rights reserved
#
# SPDX-License-Identifier: LicenseRef-LLVM

set (AnalyzerSourceCodes
	Common.cc
	Analyzer.cc
	CallGraph.cc
	VirtualCallTargets.cc
	)

set(CMAKE_MACOSX_RPATH 0)

# Build executable
set (EXECUTABLE_OUTPUT_PATH ${ANALYZER_BINARY_DIR})
link_directories (${ANALYZER_BINARY_DIR}/lib)
add_executable(crix-callgraph ${AnalyzerSourceCodes})
target_link_libraries(crix-callgraph
	LLVMAsmParser 
	LLVMSupport 
	LLVMCore 
	LLVMAnalysis
	LLVMIRReader
	LLVMipo
	LLVMPasses
	)
