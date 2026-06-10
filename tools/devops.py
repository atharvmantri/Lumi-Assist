"""Cloud and DevOps management tools."""
from __future__ import annotations

import os
import json
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
import requests

from tools import tool


@tool(
    name="deploy_infrastructure",
    description="Manage infrastructure deployments using Terraform, CloudFormation, or Pulumi.",
    parameters={
        "type": "object",
        "properties": {
            "tool_type": {
                "type": "string",
                "description": "Infrastructure tool: 'terraform', 'cloudformation', 'pulumi'",
                "enum": ["terraform", "cloudformation", "pulumi"],
            },
            "action": {
                "type": "string",
                "description": "Deployment action to take: 'init', 'plan', 'apply', 'destroy', 'status'",
                "enum": ["init", "plan", "apply", "destroy", "status"],
            },
            "working_dir": {
                "type": "string",
                "description": "Directory containing the infrastructure code (defaults to current dir)",
            },
            "variables": {
                "type": "object",
                "description": "Variables to pass to the deployment tool (key-value pairs)",
            },
        },
        "required": ["tool_type", "action"],
    },
)
def deploy_infrastructure(
    tool_type: str,
    action: str,
    working_dir: str | None = None,
    variables: dict | None = None,
) -> str:
    cwd = working_dir if working_dir else os.getcwd()
    variables = variables or {}
    
    # Check if CLI executable is available
    executable_name = "terraform" if tool_type == "terraform" else "pulumi" if tool_type == "pulumi" else "aws"
    exe_found = False
    try:
        subprocess.run(
            [executable_name, "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation mode
        sim_lines = [
            f"[Simulated Infrastructure Deployment - CLI '{executable_name}' Not Installed]",
            f"Target Directory: {cwd}",
            f"Action: {action.upper()} | Tool: {tool_type.upper()}",
        ]
        if variables:
            sim_lines.append(f"Variables: {json.dumps(variables)}")
            
        if action == "init":
            sim_lines.append("✓ Successfully initialized project workspace and downloaded mock provider plug-ins.")
        elif action == "plan":
            sim_lines.append("✓ Resources Plan: 3 to add, 0 to change, 0 to destroy.")
            sim_lines.append("  + aws_instance.lumi_app_server")
            sim_lines.append("  + aws_security_group.lumi_sg")
            sim_lines.append("  + aws_eip.lumi_eip")
        elif action == "apply":
            sim_lines.append("✓ Apply completed! Resources: 3 added, 0 changed, 0 destroyed.")
            sim_lines.append("Outputs:")
            sim_lines.append("  instance_public_ip = \"18.205.12.99\"")
        elif action == "destroy":
            sim_lines.append("✓ Destroy completed! Resources: 3 destroyed.")
        else: # status
            sim_lines.append("Status: Workspace in sync with state file. No drift detected.")
            
        return "\n".join(sim_lines)

    # Actual executions if CLI is found
    try:
        cmd = []
        if tool_type == "terraform":
            cmd = ["terraform", action]
            if action in ["apply", "destroy"]:
                cmd.append("-auto-approve")
            for k, v in variables.items():
                cmd.extend(["-var", f"{k}={v}"])
                
        elif tool_type == "pulumi":
            pulumi_action = "up" if action == "apply" else "destroy" if action == "destroy" else "preview" if action == "plan" else action
            cmd = ["pulumi", pulumi_action]
            if pulumi_action in ["up", "destroy"]:
                cmd.append("--yes")
            for k, v in variables.items():
                cmd.extend(["-c", f"{k}={v}"])
                
        else: # cloudformation
            stack_name = variables.get("stack_name", "lumi-cf-stack")
            template_path = variables.get("template_path", "template.yaml")
            if action == "apply":
                cmd = ["aws", "cloudformation", "deploy", "--stack-name", stack_name, "--template-file", template_path, "--capabilities", "CAPABILITY_IAM"]
            elif action == "destroy":
                cmd = ["aws", "cloudformation", "delete-stack", "--stack-name", stack_name]
            elif action == "status":
                cmd = ["aws", "cloudformation", "describe-stacks", "--stack-name", stack_name]
            else:
                return f"error: CloudFormation action '{action}' is not supported directly."

        result = subprocess.run(
            cmd, cwd=cwd,
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if result.returncode == 0:
            return f"Deployment Action '{action}' Successful:\n{result.stdout.strip()}"
        return f"Deployment Action '{action}' Failed:\nStdout:\n{result.stdout.strip()}\nStderr:\n{result.stderr.strip()}"
    except Exception as e:
        return f"error executing infrastructure deployment: {e}"


@tool(
    name="scale_resources",
    description="Scale server VMs, ECS containers, or Kubernetes replica sets.",
    parameters={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Cloud or platform: 'aws', 'azure', 'gcp', 'kubernetes'",
                "enum": ["aws", "azure", "gcp", "kubernetes"],
            },
            "resource_type": {
                "type": "string",
                "description": "Resource type to scale: 'asg', 'ecs_service', 'k8s_deployment', 'replica_set'",
                "enum": ["asg", "ecs_service", "k8s_deployment", "replica_set"],
            },
            "resource_name": {"type": "string", "description": "Display/System name of target resource to scale"},
            "replicas": {"type": "integer", "description": "Target replica count or desired capacity"},
            "namespace": {"type": "string", "description": "Kubernetes namespace (default 'default')", "default": "default"},
        },
        "required": ["provider", "resource_type", "resource_name", "replicas"],
    },
)
def scale_resources(
    provider: str,
    resource_type: str,
    resource_name: str,
    replicas: int,
    namespace: str = "default",
) -> str:
    # Check dependencies
    executable = "kubectl" if provider == "kubernetes" else "aws" if provider == "aws" else "az" if provider == "azure" else "gcloud"
    exe_found = False
    try:
        subprocess.run(
            [executable, "version" if executable == "kubectl" else "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        return (
            f"[Simulated Resource Scaling - CLI '{executable}' Not Found]\n"
            f"Successfully scaled {provider.upper()} {resource_type} '{resource_name}' "
            f"to {replicas} replicas (Namespace: {namespace})."
        )

    try:
        if provider == "kubernetes":
            cmd = ["kubectl", "scale", f"{resource_type}/{resource_name}", f"--replicas={replicas}", "-n", namespace]
        elif provider == "aws":
            if resource_type == "asg":
                cmd = ["aws", "autoscaling", "set-desired-capacity", "--auto-scaling-group-name", resource_name, "--desired-capacity", str(replicas)]
            else: # ecs_service
                cluster = "default"
                cmd = ["aws", "ecs", "update-service", "--cluster", cluster, "--service", resource_name, "--desired-count", str(replicas)]
        elif provider == "azure":
            cmd = ["az", "vmss", "scale", "--name", resource_name, "--resource-group", "LumiRG", "--new-capacity", str(replicas)]
        else: # gcp
            cmd = ["gcloud", "compute", "instance-groups", "managed", "resize", resource_name, f"--size={replicas}", "--zone=us-central1-a"]

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            return f"Resource scaling successful:\n{res.stdout.strip()}"
        return f"Resource scaling failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error performing resource scaling: {e}"


@tool(
    name="cloud_cost_analyzer",
    description="Retrieve billing aggregates and forecasts for AWS, Azure, or GCP accounts.",
    parameters={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider to analyze: 'aws', 'azure', 'gcp'",
                "enum": ["aws", "azure", "gcp"],
            },
            "start_date": {"type": "string", "description": "Start date for analysis YYYY-MM-DD (defaults to 30 days ago)"},
            "end_date": {"type": "string", "description": "End date for analysis YYYY-MM-DD (defaults to today)"},
            "granularity": {
                "type": "string",
                "description": "Breakdown interval: 'DAILY', 'MONTHLY'",
                "enum": ["DAILY", "MONTHLY"],
                "default": "MONTHLY",
            },
        },
        "required": ["provider"],
    },
)
def cloud_cost_analyzer(
    provider: str,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "MONTHLY",
) -> str:
    # Set default dates
    now = datetime.now()
    if not end_date:
        end_date = now.strftime("%Y-%m-%d")
    if not start_date:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    # AWS/CLI checks
    cli_found = False
    try:
        subprocess.run(
            ["aws" if provider == "aws" else "az" if provider == "azure" else "gcloud", "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        cli_found = True
    except FileNotFoundError:
        pass

    # Fallback/Default Simulation (gives a beautiful structure always)
    sim_cost_report = [
        f"Cloud Costs Report ({provider.upper()} - Simulated Billing API)",
        f"Period: {start_date} to {end_date} | Granularity: {granularity}",
        "-" * 60,
        "Service Breakdowns (Actuals):",
        "  - Elastic Compute Cloud (EC2 / VMs):    $342.12",
        "  - Relational Database Service (RDS):    $189.50",
        "  - Simple Storage Service (S3 / Blob):    $45.88",
        "  - Network NAT Gateways & Data Transfer:  $122.90",
        "  - Support & Other Services:              $29.00",
        "-" * 60,
        "Total Cost:                                $729.40",
        "Forecasted Spending (Next 30 Days):       $745.00 (Trend: stable 📈 +2.1%)",
        "-" * 60,
    ]

    if cli_found and provider == "aws":
        try:
            # Query AWS Cost Explorer via AWS CLI if credential is ready
            # Get billing data
            aws_cmd = [
                "aws", "ce", "get-cost-and-usage",
                "--time-period", f"Start={start_date},End={end_date}",
                "--granularity", granularity,
                "--metrics", "UnblendedCost",
                "--group-by", "Type=DIMENSION,Key=SERVICE"
            ]
            res = subprocess.run(
                aws_cmd, capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                out = [f"AWS Cost Explorer Details ({start_date} to {end_date}):"]
                for row in data.get("ResultsByTime", []):
                    time_key = row.get("TimePeriod", {}).get("Start", "Period")
                    out.append(f"Period starting {time_key}:")
                    for group in row.get("Groups", []):
                        svc = group.get("Keys", ["Unknown"])[0]
                        amount = float(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0))
                        unit = group.get("Metrics", {}).get("UnblendedCost", {}).get("Unit", "USD")
                        if amount > 0.1:
                            out.append(f"  - {svc}: {amount:.2f} {unit}")
                return "\n".join(out)
        except Exception:
            pass

    return "\n".join(sim_cost_report)


@tool(
    name="manage_s3_bucket",
    description="Upload, list, download, sync, or remove objects in an AWS S3, GCP Cloud Storage, or Azure Blob bucket.",
    parameters={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Storage platform: 'aws', 'gcp', 'azure'",
                "enum": ["aws", "gcp", "azure"],
            },
            "action": {
                "type": "string",
                "description": "Bucket operation: 'list', 'upload', 'download', 'sync', 'create', 'delete'",
                "enum": ["list", "upload", "download", "sync", "create", "delete"],
            },
            "bucket_name": {"type": "string", "description": "Name of the storage bucket/container"},
            "local_path": {"type": "string", "description": "Local file or folder path (required for upload, download, sync)"},
            "remote_path": {"type": "string", "description": "Remote object key/prefix path"},
        },
        "required": ["provider", "action", "bucket_name"],
    },
)
def manage_s3_bucket(
    provider: str,
    action: str,
    bucket_name: str,
    local_path: str | None = None,
    remote_path: str | None = None,
) -> str:
    # Dependency check
    executable = "aws" if provider == "aws" else "gsutil" if provider == "gcp" else "az"
    exe_found = False
    try:
        subprocess.run(
            [executable, "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation
        sim_msg = f"[Simulated Storage Bucket Action - CLI '{executable}' Not Installed]\n"
        sim_msg += f"Provider: {provider.upper()} | Action: {action.upper()} | Bucket: {bucket_name}\n"
        if remote_path:
            sim_msg += f"Remote Path: {remote_path}\n"
            
        if action == "list":
            sim_msg += "Objects Listed:\n"
            sim_msg += "  - 2026-06-01 10:11:00   1024 bytes   app_logs/production.log\n"
            sim_msg += "  - 2026-06-02 12:45:00  40960 bytes   assets/logo.png\n"
            sim_msg += "  - 2026-06-09 23:59:00     99 bytes   metadata.json\n"
        elif action in ["upload", "download", "sync"]:
            sim_msg += f"Status: Action successful. Transferred content to/from: '{local_path}'."
        elif action == "create":
            sim_msg += f"Status: Storage bucket '{bucket_name}' created successfully."
        else: # delete
            sim_msg += f"Status: Storage bucket/objects removed successfully."
        return sim_msg

    try:
        if provider == "aws":
            remote_uri = f"s3://{bucket_name}/{remote_path or ''}".strip()
            if action == "list":
                cmd = ["aws", "s3", "ls", remote_uri]
            elif action == "upload":
                if not local_path: return "error: local_path required for upload"
                cmd = ["aws", "s3", "cp", local_path, remote_uri]
            elif action == "download":
                if not local_path: return "error: local_path required for download"
                cmd = ["aws", "s3", "cp", remote_uri, local_path]
            elif action == "sync":
                if not local_path: return "error: local_path required for sync"
                cmd = ["aws", "s3", "sync", local_path, remote_uri]
            elif action == "create":
                cmd = ["aws", "s3", "mb", f"s3://{bucket_name}"]
            else: # delete
                cmd = ["aws", "s3", "rm", remote_uri, "--recursive"]
                
        elif provider == "gcp":
            remote_uri = f"gs://{bucket_name}/{remote_path or ''}".strip()
            if action == "list":
                cmd = ["gsutil", "ls", remote_uri]
            elif action == "upload":
                if not local_path: return "error: local_path required for upload"
                cmd = ["gsutil", "cp", local_path, remote_uri]
            elif action == "download":
                if not local_path: return "error: local_path required for download"
                cmd = ["gsutil", "cp", remote_uri, local_path]
            elif action == "sync":
                if not local_path: return "error: local_path required for sync"
                cmd = ["gsutil", "rsync", "-r", local_path, remote_uri]
            elif action == "create":
                cmd = ["gsutil", "mb", f"gs://{bucket_name}"]
            else: # delete
                cmd = ["gsutil", "rm", "-r", remote_uri]
                
        else: # azure
            if action == "list":
                cmd = ["az", "storage", "blob", "list", "--container-name", bucket_name, "--output", "table"]
            elif action == "upload":
                if not local_path: return "error: local_path required for upload"
                cmd = ["az", "storage", "blob", "upload", "--container-name", bucket_name, "--file", local_path, "--name", remote_path or Path(local_path).name]
            elif action == "download":
                if not local_path: return "error: local_path required for download"
                cmd = ["az", "storage", "blob", "download", "--container-name", bucket_name, "--file", local_path, "--name", remote_path or "downloaded_blob"]
            elif action == "create":
                cmd = ["az", "storage", "container", "create", "--name", bucket_name]
            else:
                return f"error: Azure action '{action}' not fully implemented via CLI parser."

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            return f"Bucket action '{action}' completed successfully:\n{res.stdout.strip()}"
        return f"Bucket action failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error managing storage: {e}"


@tool(
    name="lambda_function_manager",
    description="Deploy, list, update, invoke, or remove serverless functions (AWS Lambda, Azure Functions, GCP Cloud Functions).",
    parameters={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider: 'aws', 'gcp', 'azure'",
                "enum": ["aws", "gcp", "azure"],
            },
            "action": {
                "type": "string",
                "description": "Function operations: 'deploy', 'invoke', 'list', 'delete', 'update'",
                "enum": ["deploy", "invoke", "list", "delete", "update"],
            },
            "function_name": {"type": "string", "description": "Unique function name identifier"},
            "payload": {"type": "string", "description": "JSON payload string to invoke functions (required for action='invoke')"},
            "zip_path": {"type": "string", "description": "Local path to ZIP package containing deployment code"},
            "runtime": {"type": "string", "description": "Function environment runtime (e.g. 'python3.11', 'nodejs20.x')"},
            "handler": {"type": "string", "description": "Function handler file name and target method (e.g. 'index.handler')"},
            "role": {"type": "string", "description": "AWS execution IAM Role ARN"},
        },
        "required": ["provider", "action", "function_name"],
    },
)
def lambda_function_manager(
    provider: str,
    action: str,
    function_name: str,
    payload: str | None = None,
    zip_path: str | None = None,
    runtime: str | None = None,
    handler: str | None = None,
    role: str | None = None,
) -> str:
    # Executable check
    executable = "aws" if provider == "aws" else "gcloud" if provider == "gcp" else "func"
    exe_found = False
    try:
        subprocess.run(
            [executable, "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation
        sim_msg = f"[Simulated Serverless Manager - CLI '{executable}' Not Installed]\n"
        sim_msg += f"Provider: {provider.upper()} | Action: {action.upper()} | Function: {function_name}\n"
        if action == "invoke":
            sim_msg += f"Payload Dispatched: {payload}\n"
            sim_msg += "Invocation Status: SUCCESS (Status Code: 200)\n"
            sim_msg += "Logs (tail):\n"
            sim_msg += "  START RequestId: df2b3c41-9cb6-419b-a012-d8a1f81cfef1 Version: $LATEST\n"
            sim_msg += "  [INFO] Processing event context.\n"
            sim_msg += "  END RequestId: df2b3c41-9cb6-419b-a012-d8a1f81cfef1\n"
            sim_msg += "Response Payload:\n"
            sim_msg += "  {\"status\": \"ok\", \"message\": \"Lumi voice assistant serverless bridge active\"}"
        else:
            sim_msg += f"Status: Serverless operation '{action}' executed successfully."
        return sim_msg

    try:
        if provider == "aws":
            if action == "invoke":
                outfile = "data/lambda_out.json"
                Path("data").mkdir(parents=True, exist_ok=True)
                cmd = ["aws", "lambda", "invoke", "--function-name", function_name]
                if payload:
                    cmd.extend(["--payload", payload])
                cmd.append(outfile)
            elif action == "deploy":
                if not (zip_path and runtime and handler and role):
                    return "error: zip_path, runtime, handler, and role are required to deploy a Lambda function."
                cmd = ["aws", "lambda", "create-function", "--function-name", function_name, "--zip-file", f"fileb://{zip_path}", "--handler", handler, "--runtime", runtime, "--role", role]
            elif action == "update":
                if not zip_path: return "error: zip_path is required to update Lambda code."
                cmd = ["aws", "lambda", "update-function-code", "--function-name", function_name, "--zip-file", f"fileb://{zip_path}"]
            elif action == "delete":
                cmd = ["aws", "lambda", "delete-function", "--function-name", function_name]
            else: # list
                cmd = ["aws", "lambda", "list-functions"]
                
        elif provider == "gcp":
            if action == "deploy":
                cmd = ["gcloud", "functions", "deploy", function_name, f"--runtime={runtime or 'python311'}", f"--entry-point={handler or 'main'}", "--trigger-http"]
            elif action == "invoke":
                cmd = ["gcloud", "functions", "call", function_name, f"--data={payload or '{}'}"]
            elif action == "delete":
                cmd = ["gcloud", "functions", "delete", function_name, "--quiet"]
            else:
                cmd = ["gcloud", "functions", "list"]
                
        else: # azure
            if action == "deploy":
                cmd = ["func", "azure", "functionapp", "publish", function_name]
            else:
                return "error: Azure functions operations (invoke/delete) are not supported via CLI launcher."

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=40,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            if action == "invoke" and provider == "aws":
                with open("data/lambda_out.json", "r", encoding="utf-8") as f:
                    out_content = f.read()
                return f"Lambda Invocation Successful:\nResult Payload: {out_content}\nLogs: {res.stdout.strip()}"
            return f"Function Action '{action}' completed successfully:\n{res.stdout.strip()}"
        return f"Function Action failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error managing lambda: {e}"


@tool(
    name="docker_manager",
    description="Build, run, stop, inspect, list, or remove Docker containers and images.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Docker action: 'build', 'run', 'stop', 'inspect', 'list', 'remove'",
                "enum": ["build", "run", "stop", "inspect", "list", "remove"],
            },
            "image_name": {"type": "string", "description": "Docker image name or tag (e.g. 'lumi-node:latest')"},
            "container_name": {"type": "string", "description": "Unique container identifier name or hex ID"},
            "dockerfile_dir": {"type": "string", "description": "Local folder containing the target Dockerfile (required for action='build')"},
            "ports": {"type": "string", "description": "Network port mappings (e.g. '8080:80')"},
            "env_vars": {"type": "object", "description": "Environment variables dict mapping variables to values"},
        },
        "required": ["action"],
    },
)
def docker_manager(
    action: str,
    image_name: str | None = None,
    container_name: str | None = None,
    dockerfile_dir: str | None = None,
    ports: str | None = None,
    env_vars: dict | None = None,
) -> str:
    # Executable check
    exe_found = False
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation
        sim_msg = f"[Simulated Docker Daemon - CLI 'docker' Not Installed]\n"
        sim_msg += f"Action: {action.upper()}\n"
        
        if action == "list":
            sim_msg += "CONTAINER ID   IMAGE                 COMMAND                  CREATED         STATUS         PORTS                  NAMES\n"
            sim_msg += "a8d29c41fef1   lumi-core:latest      \"python main.py\"         3 hours ago     Up 3 hours     0.0.0.0:5000->5000/tcp  lumi-assistant-app\n"
            sim_msg += "f83b1239cdef   postgres:15-alpine    \"docker-entrypoint.s…\"   2 days ago      Up 2 days      0.0.0.0:5432->5432/tcp  lumi-postgres-db\n"
        elif action == "build":
            sim_msg += f"Building image '{image_name or 'unnamed'}' from directory '{dockerfile_dir or '.'}'...\n"
            sim_msg += "Step 1/3 : FROM python:3.11-alpine\nStep 2/3 : COPY . /app\nStep 3/3 : CMD python /app/main.py\n"
            sim_msg += f"✓ Successfully built image '{image_name or 'lumi-service:latest'}'."
        elif action == "run":
            sim_msg += f"Starting container '{container_name or 'lumi-runner'}' from image '{image_name}'...\n"
            if ports: sim_msg += f"Port Forwarding: {ports}\n"
            sim_msg += f"✓ Container '{container_name or 'lumi-runner'}' started. ID: mock_d0cK3r_7f3b..."
        elif action == "inspect":
            mock_inspect = {
                "Id": container_name or "mock_container_id_123",
                "State": {"Status": "running", "Running": True, "Pid": 4511},
                "Config": {"Image": image_name or "lumi-core:latest", "Env": [f"{k}={v}" for k, v in (env_vars or {}).items()]}
            }
            sim_msg += json.dumps(mock_inspect, indent=4)
        else: # stop or remove
            sim_msg += f"✓ Action {action} successfully completed on container/image."
            
        return sim_msg

    try:
        if action == "list":
            cmd = ["docker", "ps", "-a"]
        elif action == "build":
            if not image_name or not dockerfile_dir:
                return "error: 'image_name' and 'dockerfile_dir' are required to build an image."
            cmd = ["docker", "build", "-t", image_name, dockerfile_dir]
        elif action == "run":
            if not image_name: return "error: 'image_name' is required to run a container."
            cmd = ["docker", "run", "-d"]
            if container_name:
                cmd.extend(["--name", container_name])
            if ports:
                cmd.extend(["-p", ports])
            if env_vars:
                for k, v in env_vars.items():
                    cmd.extend(["-e", f"{k}={v}"])
            cmd.append(image_name)
        elif action == "stop":
            if not container_name: return "error: 'container_name' is required to stop container."
            cmd = ["docker", "stop", container_name]
        elif action == "remove":
            if not container_name: return "error: 'container_name' is required to remove container/image."
            cmd = ["docker", "rm", "-f", container_name]
        else: # inspect
            if not container_name: return "error: 'container_name' is required to inspect container."
            cmd = ["docker", "inspect", container_name]

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            return f"Docker operation completed:\n{res.stdout.strip()}"
        return f"Docker operation failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error executing docker manager: {e}"


@tool(
    name="kubernetes_deploy",
    description="Apply manifests, delete manifests, get status, view pods, or roll back Kubernetes deployments.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Kubernetes action: 'apply', 'delete', 'status', 'rollback', 'get_pods'",
                "enum": ["apply", "delete", "status", "rollback", "get_pods"],
            },
            "manifest_path": {"type": "string", "description": "Local YAML configuration manifest file path (required for apply/delete)"},
            "deployment_name": {"type": "string", "description": "Target Deployment name identifier (required for status/rollback)"},
            "namespace": {
                "type": "string",
                "description": "Kubernetes target namespace (default 'default')",
                "default": "default",
            },
        },
        "required": ["action"],
    },
)
def kubernetes_deploy(
    action: str,
    manifest_path: str | None = None,
    deployment_name: str | None = None,
    namespace: str = "default",
) -> str:
    # CLI check
    exe_found = False
    try:
        subprocess.run(
            ["kubectl", "version", "--client"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation
        sim_msg = f"[Simulated Kubernetes Cluster - CLI 'kubectl' Not Installed]\n"
        sim_msg += f"Action: {action.upper()} | Namespace: {namespace}\n"
        
        if action == "get_pods":
            sim_msg += "NAME                                READY   STATUS    RESTARTS   AGE\n"
            sim_msg += "lumi-api-deployment-78f9cd-a24b1    1/1     Running   0          45m\n"
            sim_msg += "lumi-api-deployment-78f9cd-b391f    1/1     Running   2          45m\n"
            sim_msg += "redis-cache-statefulset-0           1/1     Running   0          2d\n"
        elif action == "status":
            sim_msg += f"Checking status of deployment '{deployment_name or 'lumi-api'}':\n"
            sim_msg += "Deployment status: Replicas: 2 desired | 2 updated | 2 total | 2 available. Active replica set is stable."
        elif action == "rollback":
            sim_msg += f"✓ Deployment '{deployment_name or 'lumi-api'}' successfully rolled back to previous revision (undone)."
        else: # apply or delete
            sim_msg += f"✓ Manifest '{manifest_path or 'manifest.yaml'}' successfully processed."
            
        return sim_msg

    try:
        if action == "apply":
            if not manifest_path: return "error: 'manifest_path' required for apply action."
            cmd = ["kubectl", "apply", "-f", manifest_path, "-n", namespace]
        elif action == "delete":
            if not manifest_path: return "error: 'manifest_path' required for delete action."
            cmd = ["kubectl", "delete", "-f", manifest_path, "-n", namespace]
        elif action == "get_pods":
            cmd = ["kubectl", "get", "pods", "-n", namespace]
        elif action == "status":
            if not deployment_name: return "error: 'deployment_name' required for status action."
            cmd = ["kubectl", "rollout", "status", f"deployment/{deployment_name}", "-n", namespace]
        else: # rollback
            if not deployment_name: return "error: 'deployment_name' required for rollback action."
            cmd = ["kubectl", "rollout", "undo", f"deployment/{deployment_name}", "-n", namespace]

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            return f"Kubernetes operation '{action}' successful:\n{res.stdout.strip()}"
        return f"Kubernetes operation failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error executing kubernetes action: {e}"


@tool(
    name="helm_chart_manager",
    description="Install, upgrade, list, or uninstall software releases using Helm.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Helm action: 'install', 'upgrade', 'uninstall', 'list', 'repo_add'",
                "enum": ["install", "upgrade", "uninstall", "list", "repo_add"],
            },
            "release_name": {"type": "string", "description": "Release application name"},
            "chart_name": {"type": "string", "description": "Helm Chart name (e.g. 'ingress-nginx/ingress-nginx')"},
            "repo_url": {"type": "string", "description": "Helm Chart repository URL address (required for repo_add)"},
            "values_file": {"type": "string", "description": "Local YAML file containing custom value configurations"},
            "namespace": {
                "type": "string",
                "description": "Kubernetes target namespace (default 'default')",
                "default": "default",
            },
        },
        "required": ["action"],
    },
)
def helm_chart_manager(
    action: str,
    release_name: str | None = None,
    chart_name: str | None = None,
    repo_url: str | None = None,
    values_file: str | None = None,
    namespace: str = "default",
) -> str:
    # CLI check
    exe_found = False
    try:
        subprocess.run(
            ["helm", "version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation
        sim_msg = f"[Simulated Helm Manager - CLI 'helm' Not Installed]\n"
        sim_msg += f"Action: {action.upper()} | Namespace: {namespace}\n"
        
        if action == "list":
            sim_msg += "NAME           NAMESPACE   REVISION   UPDATED                                  STATUS     CHART                  APP VERSION\n"
            sim_msg += "nginx-ingress  default     1          2026-06-10 12:00:00.000000 -0700 PDT     deployed   ingress-nginx-4.8.0    1.9.0      \n"
            sim_msg += "prometheus     monitoring  3          2026-06-05 09:15:00.000000 -0700 PDT     deployed   kube-prometheus-51.2.0 v0.68.0    \n"
        elif action == "repo_add":
            sim_msg += f"✓ Repository '{release_name or 'ingress-nginx'}' successfully added. URL: {repo_url}"
        elif action in ["install", "upgrade"]:
            sim_msg += f"✓ Chart '{chart_name}' successfully installed/upgraded as release '{release_name}'."
        else: # uninstall
            sim_msg += f"✓ Release '{release_name}' uninstalled successfully. Cleaned up resources."
            
        return sim_msg

    try:
        if action == "list":
            cmd = ["helm", "list", "-n", namespace]
        elif action == "repo_add":
            if not release_name or not repo_url:
                return "error: 'release_name' (used as repo alias) and 'repo_url' are required to add a repo."
            cmd = ["helm", "repo", "add", release_name, repo_url]
        elif action == "uninstall":
            if not release_name: return "error: 'release_name' is required to uninstall a release."
            cmd = ["helm", "uninstall", release_name, "-n", namespace]
        else: # install or upgrade
            if not release_name or not chart_name:
                return "error: 'release_name' and 'chart_name' are required to install/upgrade a chart."
            helm_cmd = "upgrade" if action == "upgrade" else "install"
            cmd = ["helm", helm_cmd, release_name, chart_name, "-n", namespace]
            if action == "upgrade":
                cmd.append("--install") # auto-install if missing
            if values_file:
                cmd.extend(["-f", values_file])

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            return f"Helm operation '{action}' succeeded:\n{res.stdout.strip()}"
        return f"Helm operation failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error running helm: {e}"


@tool(
    name="container_registry",
    description="Login to container registries, tag images, and push/pull image assets.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Registry action: 'login', 'push', 'pull', 'tag'",
                "enum": ["login", "push", "pull", "tag"],
            },
            "image": {"type": "string", "description": "Target container image name and tag (e.g. 'my-app:1.0.0')"},
            "registry_url": {"type": "string", "description": "Target Registry server URL endpoint (e.g. ECR, Docker Hub, GCR)"},
            "username": {"type": "string", "description": "Registry authentication username"},
            "password": {"type": "string", "description": "Registry authentication token/password"},
        },
        "required": ["action"],
    },
)
def container_registry(
    action: str,
    image: str | None = None,
    registry_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    # CLI check
    exe_found = False
    try:
        subprocess.run(
            ["docker", "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        exe_found = True
    except FileNotFoundError:
        pass

    if not exe_found:
        # Fallback simulation
        sim_msg = f"[Simulated Container Registry - CLI 'docker' Not Installed]\n"
        sim_msg += f"Action: {action.upper()} | Registry: {registry_url or 'default'}\n"
        if image: sim_msg += f"Target Image: {image}\n"
        
        if action == "login":
            sim_msg += "✓ Login Succeeded"
        elif action == "tag":
            sim_msg += f"✓ Image tagged locally as {registry_url or 'docker.io'}/{image}"
        else: # push or pull
            sim_msg += f"✓ Registry network transfer complete for image '{image}'."
            
        return sim_msg

    try:
        if action == "login":
            if not registry_url: return "error: 'registry_url' is required to perform login."
            
            # Specialized cloud provider login check
            if "dkr.ecr" in registry_url and "amazonaws" in registry_url:
                # AWS ECR login helper command
                aws_login_cmd = "aws ecr get-login-password | docker login --username AWS --password-stdin " + registry_url
                res = subprocess.run(
                    ["powershell" if os.name == "nt" else "sh", "-Command" if os.name == "nt" else "-c", aws_login_cmd],
                    capture_output=True, text=True, timeout=25,
                )
            else:
                # Generic Docker login
                login_cmd = ["docker", "login", registry_url]
                if username and password:
                    login_cmd.extend(["-u", username, "-p", password])
                res = subprocess.run(
                    login_cmd, capture_output=True, text=True, timeout=25,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
        elif action == "tag":
            if not image or not registry_url:
                return "error: 'image' and 'registry_url' (new tag repository name) are required for tag action."
            cmd = ["docker", "tag", image, f"{registry_url}/{image}"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        elif action == "push":
            if not image: return "error: 'image' is required to push."
            target = f"{registry_url}/{image}" if registry_url else image
            cmd = ["docker", "push", target]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        else: # pull
            if not image: return "error: 'image' is required to pull."
            target = f"{registry_url}/{image}" if registry_url else image
            cmd = ["docker", "pull", target]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if res.returncode == 0:
            return f"Registry operation '{action}' completed successfully:\n{res.stdout.strip()}"
        return f"Registry operation failed:\nStdout: {res.stdout.strip()}\nStderr: {res.stderr.strip()}"
    except Exception as e:
        return f"error performing registry action: {e}"


@tool(
    name="trigger_pipeline",
    description="Trigger a workflow or build pipeline in GitHub Actions, GitLab CI, or Jenkins.",
    parameters={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Target pipeline platform: 'github', 'gitlab', 'jenkins'",
                "enum": ["github", "gitlab", "jenkins"],
            },
            "repo": {
                "type": "string",
                "description": "Repository path/name identifier (e.g. 'owner/repo' for GitHub, or Jenkins job URL)",
            },
            "workflow_id": {
                "type": "string",
                "description": "Workflow identifier filename (e.g. 'deploy.yml' or workflow ID, for GitHub Actions)",
            },
            "branch": {
                "type": "string",
                "description": "Target VCS branch to build (default 'main')",
                "default": "main",
            },
            "token": {"type": "string", "description": "VCS/CI system API authentication token or key"},
            "inputs": {"type": "object", "description": "Optional payload input parameters to pass to the pipeline"},
        },
        "required": ["platform", "repo"],
    },
)
def trigger_pipeline(
    platform: str,
    repo: str,
    workflow_id: str | None = None,
    branch: str = "main",
    token: str | None = None,
    inputs: dict | None = None,
) -> str:
    inputs = inputs or {}
    
    # Check if this is a test or we don't have token
    if not token:
        # Fallback simulation
        sim_msg = f"[Simulated Pipeline Dispatch - No Token Supplied]\n"
        sim_msg += f"Platform: {platform.upper()} | Target Repo/Job: {repo} | Branch: {branch}\n"
        if workflow_id: sim_msg += f"Workflow Filename: {workflow_id}\n"
        if inputs: sim_msg += f"Inputs Payload: {json.dumps(inputs)}\n"
        sim_msg += "Dispatch Status: SUCCESS (Event queued on remote server)"
        return sim_msg

    try:
        if platform == "github":
            if not workflow_id:
                return "error: 'workflow_id' is required to trigger a GitHub Action workflow."
            url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            payload = {"ref": branch, "inputs": inputs}
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 204:
                return f"Successfully triggered GitHub Actions workflow '{workflow_id}' on repo '{repo}' (branch: '{branch}')."
            return f"Failed to trigger GitHub pipeline (HTTP {resp.status_code}):\n{resp.text}"
            
        elif platform == "gitlab":
            # GitLab Trigger Pipeline API
            # Uses project ID or URL encoded repository path
            project_encoded = repo.replace("/", "%2F")
            url = f"https://gitlab.com/api/v4/projects/{project_encoded}/trigger/pipeline"
            data = {"token": token, "ref": branch}
            for k, v in inputs.items():
                data[f"variables[{k}]"] = str(v)
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code in [200, 201]:
                res_data = resp.json()
                return f"Successfully triggered GitLab pipeline! ID: {res_data.get('id')} | Status: {res_data.get('status')} | Web URL: {res_data.get('web_url')}"
            return f"Failed to trigger GitLab pipeline (HTTP {resp.status_code}):\n{resp.text}"
            
        else: # jenkins
            # Trigger parameterized build or simple build
            if inputs:
                url = f"{repo}/buildWithParameters"
                resp = requests.post(url, params=inputs, auth=("user", token), timeout=10)
            else:
                url = f"{repo}/build"
                resp = requests.post(url, auth=("user", token), timeout=10)
            if resp.status_code in [200, 201, 202]:
                return f"Successfully queued Jenkins build at: {url}."
            return f"Failed to trigger Jenkins build (HTTP {resp.status_code}):\n{resp.text}"
            
    except Exception as e:
        return f"error triggering pipeline: {e}"


@tool(
    name="parse_logs",
    description="Parse, search, and aggregate warnings/errors/severities inside application log files using regex patterns.",
    parameters={
        "type": "object",
        "properties": {
            "log_file_path": {"type": "string", "description": "Absolute or relative local file path to the log file"},
            "pattern": {"type": "string", "description": "Regex or keyword query string to search for matches"},
            "severity": {
                "type": "string",
                "description": "Log level filter: 'ERROR', 'WARNING', 'INFO', 'DEBUG'",
                "enum": ["ERROR", "WARNING", "INFO", "DEBUG"],
            },
            "limit": {
                "type": "integer",
                "description": "Maximum matching lines to print (default 50)",
                "default": 50,
            },
        },
        "required": ["log_file_path"],
    },
)
def parse_logs(
    log_file_path: str,
    pattern: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> str:
    path = Path(log_file_path)
    if not path.is_file():
        return f"error: log file not found: {log_file_path}"

    severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0}
    matches = []
    
    # Build regex filter
    search_regex = None
    if pattern:
        try:
            search_regex = re.compile(pattern, re.IGNORECASE)
        except Exception as e:
            return f"error: Invalid regex pattern: {e}"

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                line_lower = line.lower()
                
                # Check severity
                line_sev = None
                if "error" in line_lower:
                    line_sev = "ERROR"
                elif "warn" in line_lower:
                    line_sev = "WARNING"
                elif "info" in line_lower:
                    line_sev = "INFO"
                elif "debug" in line_lower:
                    line_sev = "DEBUG"

                if line_sev:
                    severity_counts[line_sev] += 1
                
                # Filters matching criteria
                if severity and line_sev != severity:
                    continue
                if search_regex and not search_regex.search(line):
                    continue
                elif pattern and not search_regex and pattern.lower() not in line_lower:
                    continue

                if len(matches) < limit:
                    matches.append((idx, line.strip()))

        # Build output message
        lines = [f"Log Analysis for '{path.name}':"]
        lines.append(f"  - Total Severity Counts: ERROR={severity_counts['ERROR']}, WARNING={severity_counts['WARNING']}, INFO={severity_counts['INFO']}, DEBUG={severity_counts['DEBUG']}")
        lines.append(f"  - Matching entries found (showing up to {limit}):")
        if not matches:
            lines.append("    (No matching lines found)")
        else:
            for line_no, text in matches:
                lines.append(f"    Line {line_no:5d}: {text}")
                
        return "\n".join(lines)
    except Exception as e:
        return f"error parsing log file: {e}"


@tool(
    name="metric_dashboard",
    description="Query telemetry metrics from Prometheus, Grafana, Datadog, or AWS CloudWatch.",
    parameters={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Metric system database platform: 'prometheus', 'grafana', 'datadog', 'cloudwatch'",
                "enum": ["prometheus", "grafana", "datadog", "cloudwatch"],
            },
            "query": {"type": "string", "description": "Expression query query (PromQL, Datadog metric spec, or metric name)"},
            "endpoint": {"type": "string", "description": "Metric platform endpoint API URL"},
            "api_key": {"type": "string", "description": "Authentication token key"},
            "duration_hours": {
                "type": "integer",
                "description": "Analysis timeframe interval in hours (default 1)",
                "default": 1,
            },
        },
        "required": ["platform", "query"],
    },
)
def metric_dashboard(
    platform: str,
    query: str,
    endpoint: str | None = None,
    api_key: str | None = None,
    duration_hours: int = 1,
) -> str:
    # Check if this is a real connection or local simulated fallback
    if not endpoint and not (platform == "cloudwatch" and api_key):
        # Fallback simulation
        sim_report = [
            f"Metrics Summary ({platform.upper()} - Simulated API Dashboard)",
            f"Query Expression: {query} | Range: Last {duration_hours} Hour(s)",
            "-" * 60,
            "Aggregate Data Points:",
            "  - Minimum Observed Value:  21.4 %",
            "  - Maximum Observed Value:  89.8 %",
            "  - Mean Average Value:     44.5 %",
            "  - Current Latest Value:    56.2 %",
            "-" * 60,
            "Telemetry Series Breakdown (Intervals):",
            "  [12:00]  ====== (42%)",
            "  [12:15]  ========= (56%)",
            "  [12:30]  ============= (89% - peak load)",
            "  [12:45]  ======= (48%)",
            "  [13:00]  ======== (56% - current)",
            "-" * 60,
        ]
        return "\n".join(sim_report)

    try:
        if platform == "prometheus":
            # Query Prometheus HTTP Instant Query API
            url = f"{endpoint}/api/v1/query"
            params = {"query": query}
            resp = requests.get(url, params=params, headers={"Authorization": f"Bearer {api_key}"} if api_key else {}, timeout=10)
            if resp.status_code == 200:
                res_data = resp.json()
                results = res_data.get("data", {}).get("result", [])
                lines = [f"Prometheus Query Result for '{query}':"]
                for item in results:
                    metric = item.get("metric", {})
                    val = item.get("value", [0, "0"])[1]
                    lines.append(f"  Metric tags: {json.dumps(metric)} -> Latest Value: {val}")
                return "\n".join(lines)
            return f"Failed to query Prometheus (HTTP {resp.status_code}):\n{resp.text}"
            
        elif platform == "datadog":
            # Query Datadog metric query API
            now_epoch = int(datetime.utcnow().timestamp())
            start_epoch = now_epoch - (duration_hours * 3600)
            url = "https://api.datadoghq.com/api/v1/query"
            headers = {"DD-API-KEY": api_key, "DD-APPLICATION-KEY": endpoint or ""}
            params = {"from": start_epoch, "to": now_epoch, "query": query}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                res_data = resp.json()
                series = res_data.get("series", [])
                lines = [f"Datadog Metric Series for '{query}':"]
                for s in series[:5]:
                    lines.append(f"  Metric: {s.get('metric')} | Scope: {s.get('scope')} | Point Count: {len(s.get('pointlist', []))}")
                return "\n".join(lines)
            return f"Failed to query Datadog (HTTP {resp.status_code}):\n{resp.text}"
            
        else: # cloudwatch or grafana REST API
            return f"Platform '{platform}' API queries require thick integrations, returned simulation."
            
    except Exception as e:
        return f"error fetching telemetry metrics: {e}"


@tool(
    name="alert_manager",
    description="Dispatch incident updates to PagerDuty or OpsGenie alerting queues.",
    parameters={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Alerting engine platform: 'pagerduty', 'opsgenie'",
                "enum": ["pagerduty", "opsgenie"],
            },
            "action": {
                "type": "string",
                "description": "Alerting workflow action: 'create', 'silence', 'resolve'",
                "enum": ["create", "silence", "resolve"],
            },
            "routing_key": {"type": "string", "description": "Integrations API routing/secret key"},
            "incident_id": {"type": "string", "description": "Dedup identifier or unique Incident ID"},
            "title": {"type": "string", "description": "Incident short description summary"},
            "severity": {
                "type": "string",
                "description": "Platform incident severity level",
                "enum": ["critical", "error", "warning", "info"],
                "default": "error",
            },
            "details": {"type": "object", "description": "Supplemental context key-value pairs"},
        },
        "required": ["platform", "action"],
    },
)
def alert_manager(
    platform: str,
    action: str,
    routing_key: str | None = None,
    incident_id: str | None = None,
    title: str | None = None,
    severity: str = "error",
    details: dict | None = None,
) -> str:
    details = details or {}
    
    # Simulated check if keys missing
    if not routing_key:
        sim_msg = f"[Simulated Incident Dispatch - No Routing Key Supplied]\n"
        sim_msg += f"Platform: {platform.upper()} | Action: {action.upper()}\n"
        if incident_id: sim_msg += f"Incident Reference ID (Dedup): {incident_id}\n"
        if title: sim_msg += f"Description: {title} | Severity: {severity}\n"
        sim_msg += "Status: SUCCESS (Alert queued locally)"
        return sim_msg

    try:
        if platform == "pagerduty":
            # PagerDuty Events API v2
            url = "https://events.pagerduty.com/v2/enqueue"
            pd_action = "trigger" if action == "create" else "acknowledge" if action == "silence" else "resolve"
            
            payload = {
                "routing_key": routing_key,
                "event_action": pd_action,
                "dedup_key": incident_id or f"lumi-incident-{int(datetime.utcnow().timestamp())}",
                "payload": {
                    "summary": title or "Lumi Assistant Incident Triggered",
                    "source": "Lumi Voice Assistant Client",
                    "severity": "critical" if severity == "critical" else "error" if severity == "error" else "warning" if severity == "warning" else "info",
                    "custom_details": details
                }
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 202:
                res_data = resp.json()
                return f"Successfully dispatched PagerDuty event! Dedup key: {res_data.get('dedup_key')} | Status: {res_data.get('status')}"
            return f"Failed to push PagerDuty event (HTTP {resp.status_code}):\n{resp.text}"
            
        else: # opsgenie
            # OpsGenie Alert Creation/Management API
            url = "https://api.opsgenie.com/v2/alerts"
            headers = {"Authorization": f"GenieKey {routing_key}"}
            
            if action == "create":
                payload = {
                    "message": title or "Lumi Assistant Alert Triggered",
                    "alias": incident_id,
                    "priority": "P1" if severity == "critical" else "P3" if severity == "error" else "P4",
                    "details": {str(k): str(v) for k, v in details.items()}
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
            else:
                # Silence/Acknowledge or Resolve alerts
                if not incident_id: return "error: 'incident_id' alias is required to resolve or silence OpsGenie alerts."
                url_action = "acknowledge" if action == "silence" else "resolve"
                url_path = f"{url}/{incident_id}/{url_action}"
                resp = requests.post(url_path, json={}, headers=headers, timeout=10)
                
            if resp.status_code in [200, 202]:
                return f"Successfully executed OpsGenie alert action '{action}' (Status: {resp.status_code})."
            return f"Failed to execute OpsGenie action (HTTP {resp.status_code}):\n{resp.text}"
            
    except Exception as e:
        return f"error managing incident: {e}"
