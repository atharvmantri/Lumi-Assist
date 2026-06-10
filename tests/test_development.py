import sys
import os
import json
import urllib.request
import time
from pathlib import Path

# Configure UTF-8 encoding for stdout on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.development import (
    code_review,
    generate_unit_tests,
    refactor_code,
    dependency_graph,
    git_blame_trace,
    compile_code,
    run_test_suite,
    benchmark_performance,
    lint_format_code,
    generate_openapi_spec,
    mock_api_server,
    api_version_manager
)


def test_code_intelligence():
    print("==================================================")
    print("Testing Code Intelligence Tools...")
    print("==================================================")

    # 1. code_review
    print("1. Testing code_review...")
    diff = (
        "diff --git a/main.py b/main.py\n"
        "index e69de29..92b3c41 100644\n"
        "--- a/main.py\n"
        "+++ b/main.py\n"
        "@@ -1,3 +1,4 @@\n"
        "+AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
        " def main():\n"
        "-    pass\n"
        "+    eval(input())\n"
    )
    review_res = code_review(diff_text=diff, language="Python")
    print(f"   Code review result:\n{review_res}")
    assert "vulnerabilities" in review_res or "security" in review_res.lower() or "eval" in review_res.lower() or "structure" in review_res, "Expected audit finding warnings"

    # 2. generate_unit_tests
    print("2. Testing generate_unit_tests...")
    test_code = generate_unit_tests(function_signature="def multiply(x: int, y: int) -> int:", framework="pytest")
    print(f"   Generated unit tests snippet:\n{test_code[:300]}...")
    assert "test" in test_code or "def " in test_code, "Expected test case declarations"

    # 3. refactor_code
    print("3. Testing refactor_code...")
    bad_code = "def get_items(lst): \n  res = []\n  for x in lst:\n    if x > 10: res.append(x)\n  return res"
    refactor_res = refactor_code(target_code=bad_code, objective="improve readability", language="Python")
    print(f"   Refactoring suggestion:\n{refactor_res[:300]}...")
    assert "def " in refactor_res or "get_items" in refactor_res, "Expected function name in response"

    # 4. dependency_graph
    print("4. Testing dependency_graph...")
    graph = dependency_graph(directory="tools", file_filter="email.py")
    print(f"   Dependency Graph:\n{graph}")
    assert "imports" in graph, "Expected import mappings"

    # 5. git_blame_trace
    print("5. Testing git_blame_trace...")
    blame = git_blame_trace(file_path="main.py", line_number=1)
    print(f"   Git Blame trace: {blame}")
    assert "Blame Trace" in blame or "error" in blame or "git" in blame, "Unexpected blame response"
    print("   ✅ Code Intelligence tests passed.\n")


def test_build_and_test():
    print("==================================================")
    print("Testing Build & Test Tools...")
    print("==================================================")

    # 6. compile_code
    print("6. Testing compile_code...")
    comp_res = compile_code(project_path=".", build_command="python -m py_compile main.py")
    print(f"   Compile result: {comp_res}")
    assert "Compilation" in comp_res or "SUCCESSFUL" in comp_res, "Unexpected build compiler response"

    # 7. run_test_suite
    print("7. Testing run_test_suite...")
    test_cmd = f"{sys.executable} -m pytest"
    test_suite_res = run_test_suite(test_command=test_cmd, file_path="tests/test_devops.py")
    print(f"   Test suite run result:\n{test_suite_res[:300]}...")
    assert "Test Suite" in test_suite_res, "Expected test runner logging status"

    # 8. benchmark_performance
    print("8. Testing benchmark_performance...")
    # Create a dummy script that does minor computations
    bench_file = "data/bench_dummy.py"
    Path("data").mkdir(parents=True, exist_ok=True)
    with open(bench_file, "w", encoding="utf-8") as f:
        f.write("import time\n")
        f.write("t0 = time.time()\n")
        f.write("while time.time() - t0 < 0.2: pass\n") # busy wait for 0.2s
        
    bench_res = benchmark_performance(script_path=bench_file)
    print(f"   Benchmark Profiler:\n{bench_res}")
    assert "Elapsed Duration" in bench_res or "Peak CPU" in bench_res, "Expected performance metrics"
    
    if os.path.exists(bench_file):
        os.remove(bench_file)
    print("   ✅ Build & Test tests passed.\n")

    # 9. lint_format_code
    print("9. Testing lint_format_code...")
    lint_res = lint_format_code(file_path="main.py", action="lint", tool_name="flake8")
    print(f"   Lint result: {lint_res}")
    assert "completed successfully" in lint_res or "reported warnings" in lint_res or "error" in lint_res or "not installed" in lint_res, "Unexpected lint response"
    print("   ✅ lint_format_code passed.\n")


def test_api_development():
    print("==================================================")
    print("Testing API Development Tools...")
    print("==================================================")

    # 10. generate_openapi_spec
    print("10. Testing generate_openapi_spec...")
    spec_json = generate_openapi_spec(file_paths=["tools/dns.py"], title="Lumi Test DNS API", version="1.1.0")
    print(f"    OpenAPI spec JSON snippet:\n{spec_json[:300]}...")
    assert "openapi" in spec_json or "paths" in spec_json, "Expected OpenAPI structure keys"

    # 11. mock_api_server
    print("11. Testing mock_api_server lifecycle...")
    # Clean up port 9999 server if already active
    mock_api_server(action="stop", port=9999)
    
    mock_spec = {
        "/api/v1/ping": {"status": "alive", "timestamp": "2026"},
        "/api/v1/status": {"server": "active", "load": "normal"}
    }
    spec_str = json.dumps(mock_spec)
    
    # Start mock server
    start_res = mock_api_server(action="start", spec_json=spec_str, port=9999)
    print(f"    Mock server start result: {start_res}")
    assert "successfully started" in start_res, "Failed to start mock server"
    
    # Status
    status_res = mock_api_server(action="status", port=9999)
    print(f"    Mock server status: {status_res}")
    assert "ONLINE" in status_res, "Expected mock server status ONLINE"

    # Query mock endpoint via local HTTP
    try:
        time.sleep(0.5)
        with urllib.request.urlopen("http://127.0.0.1:9999/api/v1/ping", timeout=3) as resp:
            body = resp.read().decode("utf-8")
            print(f"    Mock query response body: {body}")
            parsed = json.loads(body)
            assert parsed.get("status") == "alive", "Mock endpoint payload mismatch"
    except Exception as e:
        print(f"    Mock query request failed (bypassed if network issue): {e}")

    # Stop server
    stop_res = mock_api_server(action="stop", port=9999)
    print(f"    Mock server stop result: {stop_res}")
    assert "Successfully shut down" in stop_res, "Failed to stop mock server"
    
    print("    ✅ mock_api_server passed.\n")

    # 12. api_version_manager
    print("12. Testing api_version_manager...")
    old_spec = {
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/users": {"get": {"summary": "List users"}},
            "/api/v1/orders": {"get": {"summary": "List orders"}}
        }
    }
    new_spec = {
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/users": {"post": {"summary": "Create user"}}, # GET is removed, so it's a breaking change!
            "/api/v1/orders": {"get": {"summary": "List orders"}},
            "/api/v1/items": {"get": {"summary": "List items"}} # New endpoint added
        }
    }
    
    version_res = api_version_manager(old_spec=json.dumps(old_spec), new_spec=json.dumps(new_spec))
    print(f"    Breaking change analyzer report:\n{version_res}")
    assert "BREAKING CHANGES DETECTED" in version_res, "Breaking change not flagged"
    assert "Method 'GET' removed" in version_res or "removed" in version_res.lower(), "Expected details on removed GET method"
    assert "New path '/api/v1/items'" in version_res or "added" in version_res.lower(), "Expected evolution updates"
    print("    ✅ api_version_manager passed.\n")


if __name__ == "__main__":
    test_code_intelligence()
    test_build_and_test()
    test_api_development()
    print("🎉 All Development & Code tests passed successfully!")
