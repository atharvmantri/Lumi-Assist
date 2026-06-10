import sys
import os
import json
from pathlib import Path

# Configure UTF-8 encoding for stdout on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.devops import (
    deploy_infrastructure,
    scale_resources,
    cloud_cost_analyzer,
    manage_s3_bucket,
    lambda_function_manager,
    docker_manager,
    kubernetes_deploy,
    helm_chart_manager,
    container_registry,
    trigger_pipeline,
    parse_logs,
    metric_dashboard,
    alert_manager
)
from tools.git import git_operations


def test_cloud_providers():
    print("==================================================")
    print("Testing Cloud Providers Tools...")
    print("==================================================")

    # 1. deploy_infrastructure (Terraform/CloudFormation/Pulumi)
    print("1. Testing deploy_infrastructure...")
    tf_init = deploy_infrastructure(tool_type="terraform", action="init", variables={"var1": "val1"})
    print(f"   Terraform init output:\n{tf_init}")
    assert "initialized" in tf_init or "Deployment Action" in tf_init, "Unexpected terraform init response"
    
    tf_plan = deploy_infrastructure(tool_type="terraform", action="plan")
    print(f"   Terraform plan output:\n{tf_plan}")
    assert "Plan:" in tf_plan or "Deployment Action" in tf_plan, "Unexpected terraform plan response"

    tf_apply = deploy_infrastructure(tool_type="terraform", action="apply")
    print(f"   Terraform apply output:\n{tf_apply}")
    assert "Apply completed" in tf_apply or "Deployment Action" in tf_apply, "Unexpected terraform apply response"
    print("   ✅ deploy_infrastructure passed.\n")

    # 2. scale_resources
    print("2. Testing scale_resources...")
    scale_res = scale_resources(provider="kubernetes", resource_type="k8s_deployment", resource_name="lumi-deployment", replicas=5)
    print(f"   Kubernetes scale output: {scale_res}")
    assert "scaled" in scale_res or "successful" in scale_res, "Unexpected scaling response"
    print("   ✅ scale_resources passed.\n")

    # 3. cloud_cost_analyzer
    print("3. Testing cloud_cost_analyzer...")
    cost_res = cloud_cost_analyzer(provider="aws")
    print(f"   Cost Analyzer output:\n{cost_res}")
    assert "Total Cost" in cost_res or "AWS Cost" in cost_res, "Unexpected billing summary"
    print("   ✅ cloud_cost_analyzer passed.\n")

    # 4. manage_s3_bucket
    print("4. Testing manage_s3_bucket...")
    bucket_list = manage_s3_bucket(provider="aws", action="list", bucket_name="lumi-assets-bucket")
    print(f"   Bucket listing:\n{bucket_list}")
    assert "production.log" in bucket_list or "Bucket action" in bucket_list, "Unexpected list response"
    
    bucket_create = manage_s3_bucket(provider="aws", action="create", bucket_name="lumi-assets-bucket")
    print(f"   Bucket create output: {bucket_create}")
    assert "created" in bucket_create or "completed" in bucket_create, "Unexpected create response"
    print("   ✅ manage_s3_bucket passed.\n")

    # 5. lambda_function_manager
    print("5. Testing lambda_function_manager...")
    lambda_inv = lambda_function_manager(provider="aws", action="invoke", function_name="lumi-parser", payload='{"msg": "hi"}')
    print(f"   Lambda invocation output:\n{lambda_inv}")
    assert "SUCCESS" in lambda_inv or "Invocation" in lambda_inv, "Unexpected lambda invoke response"
    print("   ✅ lambda_function_manager passed.\n")


def test_containers_and_orchestration():
    print("==================================================")
    print("Testing Containers & Orchestration Tools...")
    print("==================================================")

    # 6. docker_manager
    print("6. Testing docker_manager...")
    dock_list = docker_manager(action="list")
    print(f"   Docker list output:\n{dock_list}")
    assert "CONTAINER ID" in dock_list or "Docker operation" in dock_list, "Unexpected docker ps response"

    dock_build = docker_manager(action="build", image_name="lumi-test:1.0", dockerfile_dir=".")
    print(f"   Docker build output:\n{dock_build}")
    assert "built" in dock_build or "Docker operation" in dock_build, "Unexpected docker build response"
    print("   ✅ docker_manager passed.\n")

    # 7. kubernetes_deploy
    print("7. Testing kubernetes_deploy...")
    k8s_pods = kubernetes_deploy(action="get_pods", namespace="kube-system")
    print(f"   Kubernetes pods list:\n{k8s_pods}")
    assert "lumi-api" in k8s_pods or "Kubernetes operation" in k8s_pods or "READY" in k8s_pods, "Unexpected get pods response"
    
    k8s_status = kubernetes_deploy(action="status", deployment_name="lumi-api")
    print(f"   Kubernetes deployment status:\n{k8s_status}")
    assert "lumi-api" in k8s_status or "Kubernetes operation" in k8s_status, "Unexpected status response"
    print("   ✅ kubernetes_deploy passed.\n")

    # 8. helm_chart_manager
    print("8. Testing helm_chart_manager...")
    helm_list = helm_chart_manager(action="list")
    print(f"   Helm releases list:\n{helm_list}")
    assert "nginx-ingress" in helm_list or "Helm operation" in helm_list, "Unexpected helm list response"
    print("   ✅ helm_chart_manager passed.\n")

    # 9. container_registry
    print("9. Testing container_registry...")
    reg_login = container_registry(action="login", registry_url="docker.io")
    print(f"   Registry login output: {reg_login}")
    assert "Login" in reg_login or "completed" in reg_login, "Unexpected registry response"
    print("   ✅ container_registry passed.\n")


def test_monitoring_and_cicd():
    print("==================================================")
    print("Testing CI/CD & Monitoring Tools...")
    print("==================================================")

    # 10. trigger_pipeline
    print("10. Testing trigger_pipeline...")
    pipe_res = trigger_pipeline(platform="github", repo="owner/repo", workflow_id="main.yml")
    print(f"    Trigger pipeline result: {pipe_res}")
    assert "SUCCESS" in pipe_res or "Successfully" in pipe_res, "Unexpected pipeline trigger response"
    print("    ✅ trigger_pipeline passed.\n")

    # 11. parse_logs
    print("11. Testing parse_logs...")
    # Create a dummy log file
    log_file = "data/test_log_file.log"
    Path("data").mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("[2026-06-10 12:00:00] INFO: Application startup complete.\n")
        f.write("[2026-06-10 12:01:05] WARNING: CPU usage exceeded 80% threshold.\n")
        f.write("[2026-06-10 12:02:10] ERROR: Database connection timeout on localhost:5432\n")
        f.write("[2026-06-10 12:03:00] INFO: Retrying connection to database...\n")
        f.write("[2026-06-10 12:03:05] ERROR: Connection failed. Server unreachable.\n")

    parsed = parse_logs(log_file_path=log_file, severity="ERROR")
    print(f"    Log parsing output:\n{parsed}")
    assert "ERROR=2" in parsed, "Error severity count mismatch"
    assert "localhost:5432" in parsed or "Server unreachable" in parsed, "Failed to capture error log text"
    
    parsed_pat = parse_logs(log_file_path=log_file, pattern="cpu")
    print(f"    Regex pattern match parsing:\n{parsed_pat}")
    assert "WARNING=1" in parsed_pat, "Regex matching warning count mismatch"
    
    # Cleanup log file
    if os.path.exists(log_file):
        os.remove(log_file)
    print("    ✅ parse_logs passed.\n")

    # 12. metric_dashboard
    print("12. Testing metric_dashboard...")
    metrics = metric_dashboard(platform="prometheus", query="up")
    print(f"    Metric query output:\n{metrics}")
    assert "Telemetry" in metrics or "Query Result" in metrics, "Unexpected metrics dashboard report"
    print("    ✅ metric_dashboard passed.\n")

    # 13. alert_manager
    print("13. Testing alert_manager...")
    alert_res = alert_manager(platform="pagerduty", action="create", title="Disk usage critical (>90%)", severity="critical")
    print(f"    Alert manager output: {alert_res}")
    assert "SUCCESS" in alert_res or "Successfully" in alert_res, "Unexpected alert response"
    print("    ✅ alert_manager passed.\n")


def test_git_operations():
    print("==================================================")
    print("Testing Git Operations Tool...")
    print("==================================================")

    # 14. git_operations
    print("14. Testing git_operations (Pull Request simulation)...")
    git_pr = git_operations(action="create_pr", pr_title="Update server configs", branch="feature/devops-configs")
    print(f"    Git PR output:\n{git_pr}")
    assert "Simulated Pull Request" in git_pr or "Pull Request" in git_pr, "Unexpected git operations output"
    
    print("    ✅ git_operations passed.\n")


if __name__ == "__main__":
    test_cloud_providers()
    test_containers_and_orchestration()
    test_monitoring_and_cicd()
    test_git_operations()
    print("🎉 All Cloud & DevOps tests passed successfully!")
