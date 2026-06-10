"""Git integration tools."""
from __future__ import annotations

import subprocess
import json
import requests
import os
from pathlib import Path

from tools import tool


@tool(
    name="git_status",
    description="Get git status of the current repository.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def git_status() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        if not result.stdout.strip():
            return "Working tree clean — no changes."
        lines = ["Git Status:"]
        for line in result.stdout.strip().split("\n"):
            lines.append(f"  {line}")
        return "\n".join(lines)
    except FileNotFoundError:
        return "error: git not found"


@tool(
    name="git_log",
    description="View recent git commits.",
    parameters={
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of commits to show (default 10)",
            },
        },
        "required": [],
    },
)
def git_log(count: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git", "log", f"--pretty=format:%h %s (%cr)", f"-{count}"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        lines = ["Recent Commits:"]
        for line in result.stdout.strip().split("\n"):
            lines.append(f"  {line}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="git_diff",
    description="Show git diff of unstaged changes.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def git_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        if not result.stdout.strip():
            return "No unstaged changes."
        return f"Git Diff:\n{result.stdout.strip()[:4000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="git_branch",
    description="List git branches and show current branch.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "-v"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        lines = ["Branches:"]
        for line in result.stdout.strip().split("\n"):
            current = "*" if line.startswith("*") else " "
            lines.append(f"  {current} {line.strip()}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="git_operations",
    description="Perform advanced Git operations: clone, checkout, commit, push, pull, or create Pull Requests.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Git action: 'clone', 'checkout', 'commit', 'push', 'pull', 'create_pr'",
                "enum": ["clone", "checkout", "commit", "push", "pull", "create_pr"],
            },
            "repo_url": {"type": "string", "description": "Remote repository URL (required for clone)"},
            "path": {"type": "string", "description": "Local repository folder path"},
            "branch": {"type": "string", "description": "Branch name to checkout or push"},
            "commit_msg": {"type": "string", "description": "Commit message (required for commit)"},
            "pr_title": {"type": "string", "description": "Title of the Pull Request to create"},
            "pr_body": {"type": "string", "description": "Description body of the Pull Request"},
            "token": {"type": "string", "description": "VCS Personal Access Token (required for create_pr)"},
        },
        "required": ["action"],
    },
)
def git_operations(
    action: str,
    repo_url: str | None = None,
    path: str | None = None,
    branch: str | None = None,
    commit_msg: str | None = None,
    pr_title: str | None = None,
    pr_body: str | None = None,
    token: str | None = None,
) -> str:
    cwd = path if path else str(Path.cwd())

    # Check for git executable
    git_found = False
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        git_found = True
    except FileNotFoundError:
        pass

    if not git_found:
        return "error: git command line tool not found in PATH."

    try:
        if action == "clone":
            if not repo_url:
                return "error: 'repo_url' parameter is required for clone action."
            dest = path if path else "."
            result = subprocess.run(
                ["git", "clone", repo_url, dest],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if result.returncode == 0:
                return f"Successfully cloned repository '{repo_url}' to '{dest}'."
            return f"Failed to clone repository:\nStdout: {result.stdout.strip()}\nStderr: {result.stderr.strip()}"

        elif action == "checkout":
            if not branch:
                return "error: 'branch' parameter is required for checkout action."
            # First try checkout normal, if fails, create branch
            result = subprocess.run(
                ["git", "checkout", branch], cwd=cwd,
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["git", "checkout", "-b", branch], cwd=cwd,
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
            if result.returncode == 0:
                return f"Successfully checked out branch '{branch}' in '{cwd}'."
            return f"Failed to checkout branch '{branch}':\n{result.stderr.strip()}"

        elif action == "commit":
            if not commit_msg:
                return "error: 'commit_msg' parameter is required for commit action."
            
            # Git add
            subprocess.run(
                ["git", "add", "-A"], cwd=cwd,
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            
            # Git commit
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg], cwd=cwd,
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if result.returncode == 0:
                return f"Successfully committed changes: {result.stdout.strip()}"
            if "nothing to commit" in result.stdout.lower() or "nothing added to commit" in result.stdout.lower():
                return "No changes to commit. Working tree is clean."
            return f"Failed to commit changes:\nStdout: {result.stdout.strip()}\nStderr: {result.stderr.strip()}"

        elif action == "push":
            cmd = ["git", "push"]
            if branch:
                cmd.extend(["-u", "origin", branch])
            result = subprocess.run(
                cmd, cwd=cwd,
                capture_output=True, text=True, timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if result.returncode == 0:
                return f"Successfully pushed branch/commits to remote:\n{result.stdout.strip()}"
            return f"Failed to push to remote:\nStdout: {result.stdout.strip()}\nStderr: {result.stderr.strip()}"

        elif action == "pull":
            result = subprocess.run(
                ["git", "pull"], cwd=cwd,
                capture_output=True, text=True, timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if result.returncode == 0:
                return f"Successfully pulled latest updates:\n{result.stdout.strip()}"
            return f"Failed to pull remote changes:\nStdout: {result.stdout.strip()}\nStderr: {result.stderr.strip()}"

        elif action == "create_pr":
            if not token:
                # Simulated PR fallback
                return (
                    "[Simulated Pull Request Creation - Token Not Provided]\n"
                    f"Target Repo: {repo_url or 'lumi-assistant'}\n"
                    f"Pull Request Title: {pr_title or 'DevOps Updates'}\n"
                    f"Base Branch: main | Head Branch: {branch or 'devops-branch'}\n"
                    "Status: SUCCESS (Simulated Pull Request created)"
                )

            # Try to get repository details
            repo_name = None
            if repo_url:
                # Parse from repo_url (e.g. https://github.com/owner/repo.git)
                match = re.search(r"github\.com/([^/]+)/([^/\.]+)", repo_url)
                if match:
                    repo_name = f"{match.group(1)}/{match.group(2)}"
            else:
                # Find from git remote
                remote_res = subprocess.run(
                    ["git", "remote", "get-url", "origin"], cwd=cwd,
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                if remote_res.returncode == 0:
                    remote_url = remote_res.stdout.strip()
                    match = re.search(r"github\.com/([^/]+)/([^/\.]+)", remote_url)
                    if match:
                        repo_name = f"{match.group(1)}/{match.group(2)}"
                        
            if not repo_name:
                return "error: Could not resolve GitHub repository name from 'repo_url' or git remote origin configuration."

            # Hit GitHub REST API
            url = f"https://api.github.com/repos/{repo_name}/pulls"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
            payload = {
                "title": pr_title or "DevOps Updates",
                "body": pr_body or "Automated Pull Request from Lumi",
                "head": branch or "main",
                "base": "main"
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 201:
                pr_data = resp.json()
                return f"Successfully created Pull Request #{pr_data.get('number')}: {pr_data.get('html_url')}"
            return f"Failed to create Pull Request (HTTP {resp.status_code}):\n{resp.text}"

        else:
            return f"error: Invalid Git action '{action}'."
    except Exception as e:
        return f"error performing git operation: {e}"
