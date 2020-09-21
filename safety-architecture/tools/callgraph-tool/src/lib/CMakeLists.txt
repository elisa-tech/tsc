set (AnalyzerSourceCodes
	Common.h
	Common.cc
	Analyzer.h
	Analyzer.cc
	CallGraph.h
	CallGraph.cc
	)

set(CMAKE_MACOSX_RPATH 0)

# Build libraries.
# add_library (AnalyzerObj OBJECT ${AnalyzerSourceCodes})
# add_library (Analyzer SHARED $<TARGET_OBJECTS:AnalyzerObj>)
# add_library (AnalyzerStatic STATIC $<TARGET_OBJECTS:AnalyzerObj>)

# Build executable.
set (EXECUTABLE_OUTPUT_PATH ${ANALYZER_BINARY_DIR})
link_directories (${ANALYZER_BINARY_DIR}/lib)
add_executable(crix-callgraph ${AnalyzerSourceCodes})
target_link_libraries(crix-callgraph
	LLVMAsmParser 
	LLVMSupport 
	LLVMCore 
	LLVMAnalysis
	LLVMIRReader
#	AnalyzerStatic
	)
