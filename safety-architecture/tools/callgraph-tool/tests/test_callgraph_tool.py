# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import os
import csv
import pytest
import subprocess
import signal
import pickle
import sys
import time
import yaml
import re

ROOT_FOLDER = os.path.dirname(os.path.realpath(__file__))
sys.path.append(ROOT_FOLDER + "/..")
import llvm_parse  # noqa E402
from llvm_parse import Function  # noqa E402
from db import GraphDb  # noqa E402

# To test the deployed version change the location below to point to right file.
CALLGRAPH_PY = ROOT_FOLDER + "/../callgraph-tool.py"
server = None


@pytest.fixture()
def set_up_test_data():
    global server

    print("setup")
    assert subprocess.call(["rm", "-fr", ROOT_FOLDER + "/callgraph_tool_test_data"]) == 0
    assert subprocess.call(["tar",
                            "-xjf",
                            ROOT_FOLDER + "/callgraph_tool_test_data.tar.bz2",
                            "--directory",
                            ROOT_FOLDER]) == 0
    yield "resource"
    print("clean up")
    assert subprocess.call(["rm", "-fr", ROOT_FOLDER + "/callgraph_tool_test_data"]) == 0

    if server is not None:
        server.send_signal(signal.SIGINT)
        server.wait()
        stdout, stderr = server.communicate()
        print(stdout)
        print(stderr)
        server = None


def check_trigger_map(cplusplus=False):

    if not cplusplus:
        callee_1 = Function("function_1")
        callee_2 = Function("function_2")
        callee_3 = Function("function_3")
        callee_4 = Function("function_4")
        callee_5 = Function("function_5")
    else:
        callee_1 = Function("_Z10function_1v")
        callee_2 = Function("_Z10function_2v")
        callee_3 = Function("_Z10function_3v")
        callee_4 = Function("_Z10function_4v")
        callee_5 = Function("_Z10function_5v")

    trigger_call_map = GraphDb(ROOT_FOLDER + "/callgraph_tool_test_data/out_trigger_call_map.pickle")
    trigger_call_map.open()

    assert callee_1 in trigger_call_map["main"]
    assert callee_2 in trigger_call_map["main"]
    assert callee_3 in trigger_call_map["main"]
    assert callee_4 not in trigger_call_map["main"]
    assert callee_5 in trigger_call_map["main"]


def test_callgraph_tool_build(set_up_test_data):
    """
    callgraph-tool.py --build buildlog.txt
    """
    ret = subprocess.call([CALLGRAPH_PY, "--config", "configuration.yaml",
                          "--db", "out_call_graph.pickle", "--trgdb", "out_trigger_call_map.pickle", "--build",
                           "buildlog.txt", "--build_trigger_map", "--fast_build", "--build_exclude", "exclude"],
                          stdout=subprocess.PIPE, cwd=ROOT_FOLDER + "/callgraph_tool_test_data")
    assert ret == 0

    assert os.path.isfile(ROOT_FOLDER + "/callgraph_tool_test_data/main.c.llvm")
    assert os.path.isfile(ROOT_FOLDER + "/callgraph_tool_test_data/function.c.llvm")

    assert os.path.isfile(ROOT_FOLDER + "/callgraph_tool_test_data/out_call_graph.pickle")
    assert os.path.isfile(ROOT_FOLDER + "/callgraph_tool_test_data/out_trigger_call_map.pickle")

    call_graph = GraphDb(ROOT_FOLDER + "/callgraph_tool_test_data/out_call_graph.pickle")
    call_graph.open()

    caller_main = Function("main", source_file="main.c", line_numbers=["9"])
    caller_1 = Function("function_1", source_file="main.c", line_numbers=["3"])
    caller_2 = Function("function_2", source_file="function.c", line_numbers=["13"])

    assert caller_main in call_graph
    assert caller_1 in call_graph
    assert caller_2 in call_graph

    callee_1 = Function("function_1", source_file="main.c", line_numbers=["11"])
    callee_2 = Function("function_2", source_file="main.c", line_numbers=["12"])
    callee_3_function_1 = Function("function_3", source_file="main.c", line_numbers=["5"])
    callee_3_function_2 = Function("function_3", source_file="function.c", line_numbers=["15", "17"])
    callee_4 = Function("function_4")
    callee_5_function_1 = Function("function_5", source_file="main.c", line_numbers=["6"])
    callee_5_function_2 = Function("function_5", source_file="function.c", line_numbers=["16"])

    assert callee_1 in call_graph[caller_main]
    assert callee_1.line_numbers == call_graph[caller_main][call_graph[caller_main].index(callee_1)].line_numbers
    assert callee_2 in call_graph[caller_main]
    assert callee_2.line_numbers == call_graph[caller_main][call_graph[caller_main].index(callee_2)].line_numbers

    assert callee_3_function_1 in call_graph[caller_1]
    assert callee_3_function_1.line_numbers == call_graph[caller_1][call_graph[caller_1].index(
        callee_3_function_1)].line_numbers
    assert callee_5_function_1 in call_graph[caller_1]
    assert callee_5_function_1.line_numbers == call_graph[caller_1][call_graph[caller_1].index(
        callee_5_function_1)].line_numbers

    assert callee_3_function_2 in call_graph[caller_2]
    assert callee_3_function_2.line_numbers == call_graph[caller_2][call_graph[caller_2].index(
        callee_3_function_2)].line_numbers
    assert callee_5_function_2 in call_graph[caller_2]
    assert callee_5_function_2.line_numbers == call_graph[caller_2][call_graph[caller_2].index(
        callee_5_function_2)].line_numbers

    assert callee_4 in call_graph
    assert callee_4 not in call_graph[caller_2]
    assert callee_4 not in call_graph[caller_main]

    excluded_function_2 = Function("excluded_function_2", source_file="excluded/function.c")
    assert excluded_function_2 not in call_graph

    check_trigger_map()


def test_callgraph_tool_client_server(set_up_test_data):
    """
    callgraph-tool.py -s and callgraph-tool -c --map_trigger
    """
    global server

    server = subprocess.Popen([CALLGRAPH_PY, "-s", "--config",
                              "configuration.yaml", "--db", "call_graph.pickle", "--trgdb", "trigger_call_map.pickle"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=ROOT_FOLDER + "/callgraph_tool_test_data")

    wait_count = 5
    while wait_count > 0:
        if os.path.isfile("/tmp/callgraph-tool.service"):
            break
        time.sleep(1)
        wait_count -= 1

    assert os.path.isfile("/tmp/callgraph-tool.service")

    for function in ["function_1", "function_2", "function_3", "function_5"]:
        client = subprocess.Popen([CALLGRAPH_PY, "--client", "--config",
                                  "configuration.yaml", "--map_trigger=" + function], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=ROOT_FOLDER + "/callgraph_tool_test_data")

        client.wait()
        stdout, stderr = client.communicate()
        print(stdout)
        print(stderr)
        assert client.returncode == 0

        assert str(stdout).find("main") != -1

    for function in ["function_4", "main", "foo"]:
        client = subprocess.Popen([CALLGRAPH_PY, "--client", "--config",
                                  "configuration.yaml", "--map_trigger=" + function], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=ROOT_FOLDER + "/callgraph_tool_test_data")

        client.wait()
        stdout, stderr = client.communicate()
        print(stdout)
        print(stderr)
        assert client.returncode == 0

        assert str(stdout).find("main") == -1

    server.send_signal(signal.SIGINT)
    server.wait()

    stdout, stderr = server.communicate()
    print(stdout)
    print(stderr)

    assert server.returncode == 0

    server = None


def test_help():
    """
    Test help functionality
    """
    # First test that help output is printed with --help argument
    cmd = [CALLGRAPH_PY, "--help"]
    pipe = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8")
    assert pipe.returncode == 0
    help_text = pipe.stdout

    # Make sure some text is returned
    assert len(help_text) >= 2415


def test_callgraph_vfswrite(set_up_test_data):
    """
    Test callgraph-tool to create graph between two kernel functions
    """
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "-p", "vfs_write..__x64_sys_write"],
                                    cwd=ROOT_FOLDER + "/../",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    output = process_result.stdout.decode("utf-8")
    test = "vfs_write <- ksys_write <- __do_sys_write <- __se_sys_write <- __x64_sys_write\n"
    assert output == test


def test_callgraph_path_with_indirects(set_up_test_data):
    """
    callgraph-tool.py -p show_smaps_rollup..seq_read
    """
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "-p", "show_smaps_rollup..seq_read"],
                                    cwd=ROOT_FOLDER + "/..",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    output = process_result.stdout.decode("utf-8")
    assert output == "show_smaps_rollup <- seq_operations.show <- seq_read\n"


def test_callgraph_path_ignore_indirects(set_up_test_data):
    """
    callgraph-tool.py --db minimal_indirect.pickle -p show_smaps_rollup..seq_read --no_indirect
    """
    # to avoid a long-running test, use a limited pickle file
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "--db", ROOT_FOLDER + "/callgraph_tool_test_data/minimal_indirect.pickle",
                                     "-p", "show_smaps_rollup..seq_read", "--no_indirect"],
                                    cwd=ROOT_FOLDER + "/..",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    output = process_result.stdout.decode("utf-8")
    assert output == "Can't find code path between show_smaps_rollup..seq_read\n"


def test_callgraph_tool_build_trigger_map(set_up_test_data):
    """
    callgraph-tool.py --build_trigger_map
    """
    proc = subprocess.run([CALLGRAPH_PY, "--config", "configuration.yaml",
                           "--db", "call_graph.pickle", "--trgdb", "out_trigger_call_map.pickle",
                           "--build_trigger_map"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=ROOT_FOLDER + "/callgraph_tool_test_data")
    print(proc.stdout.decode("utf-8"))
    print(proc.stderr.decode("utf-8"))

    assert proc.returncode == 0

    assert os.path.isfile(ROOT_FOLDER + "/callgraph_tool_test_data/out_trigger_call_map.pickle")

    check_trigger_map()


def test_callgraph_tool_ftrace_enrich(set_up_test_data):
    """
    callgraph-tool.py --config configuration.yaml --db call_graph.pickle --ftrace ftrace.log --ftrace_enrich
    """
    proc = subprocess.run([CALLGRAPH_PY, "--config", "configuration.yaml",
                           "--db", "call_graph.pickle", "--ftrace", "ftrace.log", "--ftrace_enrich"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=ROOT_FOLDER + "/callgraph_tool_test_data")
    print(proc.stdout.decode("utf-8"))
    print(proc.stderr.decode("utf-8"))

    assert proc.returncode == 0

    assert os.path.isfile(ROOT_FOLDER + "/callgraph_tool_test_data/call_graph.pickle.ftrace")

    call_graph = GraphDb(ROOT_FOLDER + "/callgraph_tool_test_data/call_graph.pickle.ftrace")
    call_graph.open()

    caller_main = Function("main")
    caller_1 = Function("function_1")
    caller_2 = Function("function_2")
    caller_4 = Function("function_4")

    assert caller_main in call_graph
    assert caller_1 in call_graph
    assert caller_2 in call_graph
    assert caller_4 in call_graph

    callee_1 = Function("function_1")
    callee_2 = Function("function_2")
    callee_3 = Function("function_3")
    callee_4 = Function("function_4")
    callee_5 = Function("function_5")

    assert callee_1 in call_graph[caller_main]
    assert callee_2 in call_graph[caller_main]
    assert callee_4 in call_graph[caller_main]

    assert callee_3 in call_graph[caller_1]
    assert callee_5 in call_graph[caller_1]

    assert callee_3 in call_graph[caller_2]
    assert callee_5 in call_graph[caller_2]

    assert callee_1 in call_graph[caller_4]

    assert callee_4 not in call_graph[caller_2]


def test_callgraph_multipath(set_up_test_data):
    """
    Test callgraph-tool to create graph between two kernel functions
    """
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "--multipath", "function_3", "--config", "configuration.yaml",
                                    "--db", "call_graph.pickle"],
                                    cwd=ROOT_FOLDER + "/callgraph_tool_test_data",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    output = process_result.stdout.decode("utf-8")

    test = """\x1b[38;5;206mmain: \x1b[0mfunction_3 <- function_1 <- main\n"""
    assert output == test


def test_callgraph_search_graph(set_up_test_data):
    """
    Test callgraph-tool to create graph between two kernel functions
    """
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "--graph", "function_1",
                                    "--db", "call_graph.pickle"],
                                    cwd=ROOT_FOLDER + "/callgraph_tool_test_data",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    output = process_result.stdout.decode("utf-8")

    test = """\x1b[37;1mfunction_1 -> function_3, function_5\x1b[0m\n  function_3 -> \n  function_5 -> \n"""
    assert output == test


def test_callgraph_search_inverse_graph(set_up_test_data):
    """
    Test callgraph-tool to create graph between two kernel functions
    """
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "--inverse_graph", "function_1",
                                    "--db", "call_graph.pickle"],
                                    cwd=ROOT_FOLDER + "/callgraph_tool_test_data",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    output = process_result.stdout.decode("utf-8")

    test = """\x1b[37;1mfunction_1 <- main\x1b[0m\n  main <- main.main\n"""
    assert output == test


def test_callgraph_view_graph(set_up_test_data):
    process_result = subprocess.run([CALLGRAPH_PY,
                                     "--graph", "main",
                                     "--db", "call_graph.pickle",
                                     "--view", "--view_type", "dot",
                                    "--coverage_file", "coverage_file.txt"],
                                    cwd=ROOT_FOLDER + "/callgraph_tool_test_data",
                                    stdout=subprocess.PIPE)
    assert process_result.returncode == 0
    dotfile = ROOT_FOLDER + "/callgraph_tool_test_data/callgraph.dot"
    assert os.path.isfile(dotfile)
    matches = [re.findall(r'color=\"green\"', line) for line in open(dotfile)]
    assert len(matches) > 0


if __name__ == "__main__":
    pytest.main([__file__])
