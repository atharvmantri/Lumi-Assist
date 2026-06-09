"""GitHub CLI integration — repos, issues, PRs, gist."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="github_search",
    description="Search GitHub repositories by query. Returns top results.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g. 'python web scraper stars:>1000')",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10)",
            },
        },
        "required": ["query"],
    },
)
def github_search(query: str, limit: int = 10) -> str:
    try:
        result = subprocess.run(
            ["gh", "search", "repos", query, "--limit", str(limit), "--json", "name,owner,description,stargazersCount,url"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            if "command not found" in result.stderr.lower() or "not recognized" in result.stderr.lower():
                return "error: GitHub CLI (gh) not installed. Install from https://cli.github.com/"
            return f"error: {result.stderr.strip()}"

        import json
        repos = json.loads(result.stdout)
        lines = [f"GitHub search for '{query}' ({len(repos)} results):"]
        for r in repos:
            stars = r.get("stargazersCount", 0)
            lines.append(f"  {'★' * min(5, max(1, stars // 1000))} {r['owner']['login']}/{r['name']} ({stars} stars)")
            if r.get("description"):
                lines.append(f"    {r['description'][:100]}")
            lines.append(f"    {r['url']}")
        return "\n".join(lines)
    except FileNotFoundError:
        return "error: GitHub CLI (gh) not installed"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="github_repo_info",
    description="Get information about a GitHub repository (stars, forks, issues, description).",
    parameters={
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in owner/name format (e.g. 'torvalds/linux')",
            },
        },
        "required": ["repo"],
    },
)
def github_repo_info(repo: str) -> str:
    try:
        result = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "name,owner,description,stargazersCount,forkCount,openIssueCount,url,createdAt,updatedAt"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"

        import json
        r = json.loads(result.stdout)
        return (
            f"{r['owner']['login']}/{r['name']}\n"
            f"  {r.get('description', 'No description')}\n"
            f"  Stars: {r.get('stargazersCount', 0)}\n"
            f"  Forks: {r.get('forkCount', 0)}\n"
            f"  Open issues: {r.get('openIssueCount', 0)}\n"
            f"  Created: {r.get('createdAt', '?')[:10]}\n"
            f"  Updated: {r.get('updatedAt', '?')[:10]}\n"
            f"  {r.get('url', '')}"
        )
    except Exception as e:
        return f"error: {e}"


@tool(
    name="github_clone",
    description="Clone a GitHub repository to the local machine.",
    parameters={
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository URL or owner/name (e.g. 'https://github.com/owner/repo' or 'owner/repo')",
            },
            "directory": {
                "type": "string",
                "description": "Directory to clone into (default: current directory)",
            },
        },
        "required": ["repo"],
    },
)
def github_clone(repo: str, directory: str = "") -> str:
    try:
        cmd = ["gh", "repo", "clone", repo]
        if directory:
            cmd.append(directory)
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return f"error cloning: {result.stderr.strip()[:200]}"
        return f"Cloned {repo} successfully"
    except Exception as e:
        return f"error: {e}"
