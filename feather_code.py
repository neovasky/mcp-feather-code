#!/usr/bin/env python3
"""
Feather Code - Lightweight GitHub MCP Server
Built with the official Model Context Protocol SDK
"""

import os
import sys
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone, timedelta

# GitHub API dependencies
import jwt
import requests
from cryptography.hazmat.primitives import serialization

# MCP SDK imports - following official patterns
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configure logging to stderr (required for stdio servers)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

logger = logging.getLogger("feather-code")

class GitHubClient:
    """GitHub API client with environment-based configuration"""
    
    def __init__(self):
        # Auto-detect repository from git
        self.repo_owner = os.getenv('GITHUB_OWNER')
        self.repo_name = os.getenv('GITHUB_REPO')
        
        if not self.repo_owner or not self.repo_name:
            detected = self._detect_git_repo()
            if detected:
                if not self.repo_owner:
                    self.repo_owner = detected[0]
                if not self.repo_name:
                    self.repo_name = detected[1]
                logger.info(f"Auto-detected repository: {self.repo_owner}/{self.repo_name}")
        
        # Authentication
        self.pat = os.getenv('GITHUB_PAT')
        if not self.pat and os.getenv('GITHUB_PAT_FILE'):
            try:
                pat_file = os.path.expanduser(os.getenv('GITHUB_PAT_FILE'))
                with open(pat_file, 'r') as f:
                    self.pat = f.read().strip()
                logger.info("Loaded GitHub PAT from file")
            except Exception as e:
                logger.warning(f"Could not read PAT file: {e}")
        
        # GitHub App authentication
        self.app_id = os.getenv('GITHUB_APP_ID')
        self.installation_id = os.getenv('GITHUB_INSTALLATION_ID')
        self.private_key_path = os.getenv('GITHUB_PRIVATE_KEY_PATH')
        
        # API configuration
        self.api_base = os.getenv('GITHUB_API_URL', 'https://api.github.com')
        
    def _detect_git_repo(self) -> Optional[Tuple[str, str]]:
        """Detect GitHub repository from current git directory"""
        try:
            # Get the git remote URL
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            url = result.stdout.strip()
            
            # Parse GitHub URLs
            if 'github.com' in url:
                # Handle HTTPS URLs
                if url.startswith('https://'):
                    parts = url.replace('https://github.com/', '').replace('.git', '').split('/')
                # Handle SSH URLs
                elif url.startswith('git@'):
                    parts = url.replace('git@github.com:', '').replace('.git', '').split('/')
                # Handle git:// URLs
                elif url.startswith('git://'):
                    parts = url.replace('git://github.com/', '').replace('.git', '').split('/')
                else:
                    return None
                
                if len(parts) >= 2:
                    return (parts[0], parts[1])
        except subprocess.TimeoutExpired:
            logger.warning("Git command timed out")
        except subprocess.CalledProcessError:
            logger.debug("Not in a git repository or no remote origin")
        except Exception as e:
            logger.debug(f"Error detecting git repo: {e}")
        
        return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'feather-code-mcp/1.0.0'
        }
        
        if self.pat:
            headers['Authorization'] = f'token {self.pat}'
        elif all([self.app_id, self.installation_id, self.private_key_path]):
            try:
                token = self._get_app_token()
                headers['Authorization'] = f'token {token}'
            except Exception as e:
                logger.warning(f"GitHub App auth failed: {e}")
        
        return headers
    
    def _get_app_token(self) -> str:
        """Get installation token for GitHub App"""
        # Read private key
        with open(os.path.expanduser(self.private_key_path), 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        # Generate JWT
        now = datetime.now(timezone.utc)
        payload = {
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=10)).timestamp()),
            'iss': self.app_id
        }
        
        jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
        
        # Exchange JWT for installation token
        response = requests.post(
            f"{self.api_base}/app/installations/{self.installation_id}/access_tokens",
            headers={
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github.v3+json'
            },
            timeout=10
        )
        
        if response.status_code == 201:
            return response.json()['token']
        else:
            raise Exception(f"Failed to get installation token: {response.status_code}")
    
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request to GitHub"""
        url = f"{self.api_base}{endpoint}"
        
        # Set default timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
            
        try:
            return requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                **kwargs
            )
        except requests.exceptions.Timeout:
            raise Exception("GitHub API request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception("Failed to connect to GitHub API")

# Create server instance
server = Server(
    "feather-code",
    version="1.0.0",
)

# Create GitHub client instance
github = GitHubClient()

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema.
    """
    return [
        types.Tool(
            name="get_repository_info",
            description="Get information about the current GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "Repository owner (optional, uses env/git if not provided)"
                    },
                    "repo": {
                        "type": "string", 
                        "description": "Repository name (optional, uses env/git if not provided)"
                    }
                },
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="list_issues",
            description="List issues in a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Filter by issue state",
                        "default": "open"
                    },
                    "labels": {
                        "type": "string",
                        "description": "Comma-separated list of labels to filter by"
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Number of issues per page (max 100)",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="create_issue",
            description="Create a new issue in a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Issue title"
                    },
                    "body": {
                        "type": "string",
                        "description": "Issue body/description"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels to add to the issue"
                    },
                    "assignees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Usernames to assign to the issue"
                    }
                },
                "required": ["title"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_pull_requests",
            description="List pull requests in a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Filter by PR state",
                        "default": "open"
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["created", "updated", "popularity", "long-running"],
                        "description": "Sort order",
                        "default": "created"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "Sort direction",
                        "default": "desc"
                    }
                },
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="update_issue",
            description="Update an existing GitHub issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_number": {
                        "type": "integer",
                        "description": "Issue number to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New issue title"
                    },
                    "body": {
                        "type": "string",
                        "description": "New issue body/description"
                    },
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed"],
                        "description": "Issue state"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels to set on the issue"
                    },
                    "assignees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Usernames to assign to the issue"
                    }
                },
                "required": ["issue_number"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_issue",
            description="Get details of a specific GitHub issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_number": {
                        "type": "integer",
                        "description": "Issue number to retrieve"
                    }
                },
                "required": ["issue_number"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="create_pull_request",
            description="Create a new pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Pull request title"
                    },
                    "body": {
                        "type": "string",
                        "description": "Pull request description"
                    },
                    "head": {
                        "type": "string",
                        "description": "Branch name containing changes"
                    },
                    "base": {
                        "type": "string",
                        "description": "Target branch (default: repository default branch)",
                        "default": "main"
                    },
                    "draft": {
                        "type": "boolean",
                        "description": "Create as draft PR",
                        "default": False
                    }
                },
                "required": ["title", "head"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_pull_request",
            description="Get details of a specific pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request number to retrieve"
                    }
                },
                "required": ["pr_number"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="list_branches",
            description="List branches in a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "protected": {
                        "type": "boolean",
                        "description": "Filter by protection status"
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Number of branches per page (max 100)",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_commits",
            description="List commits in a GitHub repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "sha": {
                        "type": "string",
                        "description": "Branch or commit SHA to start from"
                    },
                    "path": {
                        "type": "string",
                        "description": "Filter commits by file path"
                    },
                    "author": {
                        "type": "string",
                        "description": "Filter by commit author"
                    },
                    "since": {
                        "type": "string",
                        "description": "ISO 8601 date - only commits after this date"
                    },
                    "until": {
                        "type": "string",
                        "description": "ISO 8601 date - only commits before this date"
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Number of commits per page (max 100)",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_file_content",
            description="Get content of a file from the repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path in the repository"
                    },
                    "ref": {
                        "type": "string",
                        "description": "Branch, tag, or commit SHA (default: default branch)"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="search_code",
            description="Search for code in the repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filter by filename"
                    },
                    "extension": {
                        "type": "string",
                        "description": "Filter by file extension"
                    },
                    "path": {
                        "type": "string",
                        "description": "Filter by path"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="add_issue_comment",
            description="Add a comment to an issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_number": {
                        "type": "integer",
                        "description": "Issue number to comment on"
                    },
                    "body": {
                        "type": "string",
                        "description": "Comment body"
                    }
                },
                "required": ["issue_number", "body"],
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_repository_languages",
            description="Get programming languages used in the repository",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_repository_topics",
            description="Get topics/tags associated with the repository",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: Dict[str, Any]
) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
    """
    Handle tool execution requests.
    Tools should return TextContent, ImageContent, or EmbeddedResource.
    """
    try:
        # Validate tool name first
        valid_tools = [
            "get_repository_info", "list_issues", "create_issue", "get_pull_requests",
            "update_issue", "get_issue", "create_pull_request", "get_pull_request",
            "list_branches", "get_commits", "get_file_content", "search_code",
            "add_issue_comment", "get_repository_languages", "get_repository_topics"
        ]
        if name not in valid_tools:
            return [types.TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'. Available tools: {', '.join(valid_tools)}"
            )]
        
        # Determine repository owner and name
        owner = arguments.get('owner', github.repo_owner)
        repo = arguments.get('repo', github.repo_name)
        
        # Validate repository information
        if not owner or not repo:
            return [types.TextContent(
                type="text",
                text="Error: Repository not specified. Set GITHUB_OWNER/GITHUB_REPO environment variables or run from a git repository."
            )]
        
        # Check authentication
        if not github.pat and not all([github.app_id, github.installation_id, github.private_key_path]):
            return [types.TextContent(
                type="text",
                text="Error: No GitHub authentication configured. Set GITHUB_PAT or configure GitHub App credentials."
            )]
        
        # Execute the appropriate tool
        if name == "get_repository_info":
            result = await get_repository_info(owner, repo)
        elif name == "list_issues":
            result = await list_issues(owner, repo, arguments)
        elif name == "create_issue":
            result = await create_issue(owner, repo, arguments)
        elif name == "get_pull_requests":
            result = await get_pull_requests(owner, repo, arguments)
        elif name == "update_issue":
            result = await update_issue(owner, repo, arguments)
        elif name == "get_issue":
            result = await get_issue(owner, repo, arguments)
        elif name == "create_pull_request":
            result = await create_pull_request(owner, repo, arguments)
        elif name == "get_pull_request":
            result = await get_pull_request(owner, repo, arguments)
        elif name == "list_branches":
            result = await list_branches(owner, repo, arguments)
        elif name == "get_commits":
            result = await get_commits(owner, repo, arguments)
        elif name == "get_file_content":
            result = await get_file_content(owner, repo, arguments)
        elif name == "search_code":
            result = await search_code(owner, repo, arguments)
        elif name == "add_issue_comment":
            result = await add_issue_comment(owner, repo, arguments)
        elif name == "get_repository_languages":
            result = await get_repository_languages(owner, repo)
        elif name == "get_repository_topics":
            result = await get_repository_topics(owner, repo)
        
        # Return result as formatted JSON text
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"GitHub API error: {e}"
        if e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = f"GitHub API error: {error_detail.get('message', str(e))}"
            except:
                pass
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]
        
    except Exception as e:
        error_msg = f"Error executing tool '{name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [types.TextContent(type="text", text=error_msg)]

async def get_repository_info(owner: str, repo: str) -> Dict[str, Any]:
    """Get repository information"""
    response = github.request('GET', f'/repos/{owner}/{repo}')
    
    if response.status_code == 404:
        raise Exception(f"Repository '{owner}/{repo}' not found")
    elif response.status_code == 403:
        raise Exception("API rate limit exceeded or insufficient permissions")
    elif response.status_code != 200:
        response.raise_for_status()
    
    data = response.json()
    
    # Return cleaned repository information
    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "private": data["private"],
        "html_url": data["html_url"],
        "default_branch": data["default_branch"],
        "language": data["language"],
        "stargazers_count": data["stargazers_count"],
        "watchers_count": data["watchers_count"],
        "forks_count": data["forks_count"],
        "open_issues_count": data["open_issues_count"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "pushed_at": data["pushed_at"],
        "topics": data.get("topics", []),
        "license": data["license"]["name"] if data.get("license") else None
    }

async def list_issues(owner: str, repo: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List repository issues"""
    query_params = {
        "state": params.get("state", "open"),
        "per_page": min(params.get("per_page", 30), 100)  # Enforce max limit
    }
    
    if params.get("labels"):
        query_params["labels"] = params["labels"]
    
    response = github.request('GET', f'/repos/{owner}/{repo}/issues', params=query_params)
    
    if response.status_code != 200:
        response.raise_for_status()
    
    issues = response.json()
    
    # Return cleaned issue data (exclude pull requests)
    result = []
    for issue in issues:
        # Skip pull requests (they appear in issues endpoint too)
        if "pull_request" in issue:
            continue
            
        result.append({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "html_url": issue["html_url"],
            "user": issue["user"]["login"],
            "labels": [label["name"] for label in issue["labels"]],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "comments": issue["comments"],
            "body": (issue["body"][:200] + "...") if issue.get("body") and len(issue["body"]) > 200 else issue.get("body", "")
        })
    
    return result

async def create_issue(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new issue"""
    # Validate required fields
    if not params.get("title"):
        raise ValueError("Issue title is required")
    
    data = {
        "title": params["title"],
        "body": params.get("body", "")
    }
    
    # Add optional fields
    if params.get("labels"):
        data["labels"] = params["labels"]
    if params.get("assignees"):
        data["assignees"] = params["assignees"]
    
    response = github.request('POST', f'/repos/{owner}/{repo}/issues', json=data)
    
    if response.status_code == 404:
        raise Exception(f"Repository '{owner}/{repo}' not found")
    elif response.status_code == 422:
        error_data = response.json()
        raise ValueError(f"Invalid issue data: {error_data.get('message', 'Unknown error')}")
    elif response.status_code != 201:
        response.raise_for_status()
    
    issue = response.json()
    
    return {
        "number": issue["number"],
        "title": issue["title"],
        "html_url": issue["html_url"],
        "state": issue["state"],
        "created_at": issue["created_at"],
        "message": "Issue created successfully"
    }

async def get_pull_requests(owner: str, repo: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List pull requests"""
    query_params = {
        "state": params.get("state", "open"),
        "sort": params.get("sort", "created"),
        "direction": params.get("direction", "desc")
    }
    
    response = github.request('GET', f'/repos/{owner}/{repo}/pulls', params=query_params)
    
    if response.status_code != 200:
        response.raise_for_status()
    
    prs = response.json()
    
    return [{
        "number": pr["number"],
        "title": pr["title"],
        "state": pr["state"],
        "html_url": pr["html_url"],
        "user": pr["user"]["login"],
        "created_at": pr["created_at"],
        "updated_at": pr["updated_at"],
        "draft": pr.get("draft", False),
        "merged": pr.get("merged", False),
        "merged_at": pr.get("merged_at"),
        "head": pr["head"]["ref"],
        "base": pr["base"]["ref"],
        "body": (pr["body"][:200] + "...") if pr.get("body") and len(pr["body"]) > 200 else pr.get("body", "")
    } for pr in prs]

async def update_issue(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing issue"""
    issue_number = params["issue_number"]
    
    data = {}
    if params.get("title"):
        data["title"] = params["title"]
    if params.get("body"):
        data["body"] = params["body"]
    if params.get("state"):
        data["state"] = params["state"]
    if params.get("labels"):
        data["labels"] = params["labels"]
    if params.get("assignees"):
        data["assignees"] = params["assignees"]
    
    response = github.request('PATCH', f'/repos/{owner}/{repo}/issues/{issue_number}', json=data)
    
    if response.status_code == 404:
        raise Exception(f"Issue #{issue_number} not found")
    elif response.status_code != 200:
        response.raise_for_status()
    
    issue = response.json()
    
    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "html_url": issue["html_url"],
        "updated_at": issue["updated_at"],
        "message": "Issue updated successfully"
    }

async def get_issue(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get details of a specific issue"""
    issue_number = params["issue_number"]
    
    response = github.request('GET', f'/repos/{owner}/{repo}/issues/{issue_number}')
    
    if response.status_code == 404:
        raise Exception(f"Issue #{issue_number} not found")
    elif response.status_code != 200:
        response.raise_for_status()
    
    issue = response.json()
    
    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "html_url": issue["html_url"],
        "user": issue["user"]["login"],
        "labels": [label["name"] for label in issue["labels"]],
        "assignees": [assignee["login"] for assignee in issue["assignees"]],
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "comments": issue["comments"],
        "body": issue["body"]
    }

async def create_pull_request(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new pull request"""
    # Get repository info to determine default branch
    repo_response = github.request('GET', f'/repos/{owner}/{repo}')
    if repo_response.status_code == 200:
        default_branch = repo_response.json().get("default_branch", "main")
    else:
        default_branch = "main"
    
    data = {
        "title": params["title"],
        "head": params["head"],
        "base": params.get("base", default_branch)
    }
    
    if params.get("body"):
        data["body"] = params["body"]
    if params.get("draft"):
        data["draft"] = params["draft"]
    
    response = github.request('POST', f'/repos/{owner}/{repo}/pulls', json=data)
    
    if response.status_code == 422:
        error_data = response.json()
        raise ValueError(f"Invalid pull request data: {error_data.get('message', 'Unknown error')}")
    elif response.status_code != 201:
        response.raise_for_status()
    
    pr = response.json()
    
    return {
        "number": pr["number"],
        "title": pr["title"],
        "html_url": pr["html_url"],
        "state": pr["state"],
        "draft": pr.get("draft", False),
        "head": pr["head"]["ref"],
        "base": pr["base"]["ref"],
        "created_at": pr["created_at"],
        "message": "Pull request created successfully"
    }

async def get_pull_request(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get details of a specific pull request"""
    pr_number = params["pr_number"]
    
    response = github.request('GET', f'/repos/{owner}/{repo}/pulls/{pr_number}')
    
    if response.status_code == 404:
        raise Exception(f"Pull request #{pr_number} not found")
    elif response.status_code != 200:
        response.raise_for_status()
    
    pr = response.json()
    
    return {
        "number": pr["number"],
        "title": pr["title"],
        "state": pr["state"],
        "html_url": pr["html_url"],
        "user": pr["user"]["login"],
        "draft": pr.get("draft", False),
        "merged": pr.get("merged", False),
        "mergeable": pr.get("mergeable"),
        "head": {
            "ref": pr["head"]["ref"],
            "sha": pr["head"]["sha"]
        },
        "base": {
            "ref": pr["base"]["ref"],
            "sha": pr["base"]["sha"]
        },
        "created_at": pr["created_at"],
        "updated_at": pr["updated_at"],
        "merged_at": pr.get("merged_at"),
        "body": pr["body"]
    }

async def list_branches(owner: str, repo: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List repository branches"""
    query_params = {
        "per_page": min(params.get("per_page", 30), 100)
    }
    
    if params.get("protected") is not None:
        query_params["protected"] = params["protected"]
    
    response = github.request('GET', f'/repos/{owner}/{repo}/branches', params=query_params)
    
    if response.status_code != 200:
        response.raise_for_status()
    
    branches = response.json()
    
    return [{
        "name": branch["name"],
        "commit": {
            "sha": branch["commit"]["sha"],
            "url": branch["commit"]["url"]
        },
        "protected": branch.get("protected", False)
    } for branch in branches]

async def get_commits(owner: str, repo: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List repository commits"""
    query_params = {
        "per_page": min(params.get("per_page", 30), 100)
    }
    
    # Add optional filters
    for param in ["sha", "path", "author", "since", "until"]:
        if params.get(param):
            query_params[param] = params[param]
    
    response = github.request('GET', f'/repos/{owner}/{repo}/commits', params=query_params)
    
    if response.status_code != 200:
        response.raise_for_status()
    
    commits = response.json()
    
    return [{
        "sha": commit["sha"],
        "message": commit["commit"]["message"],
        "author": {
            "name": commit["commit"]["author"]["name"],
            "email": commit["commit"]["author"]["email"],
            "date": commit["commit"]["author"]["date"]
        },
        "committer": {
            "name": commit["commit"]["committer"]["name"],
            "email": commit["commit"]["committer"]["email"],
            "date": commit["commit"]["committer"]["date"]
        },
        "html_url": commit["html_url"],
        "stats": commit.get("stats", {}),
        "files": len(commit.get("files", []))
    } for commit in commits]

async def get_file_content(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get content of a file from the repository"""
    path = params["path"]
    query_params = {}
    
    if params.get("ref"):
        query_params["ref"] = params["ref"]
    
    response = github.request('GET', f'/repos/{owner}/{repo}/contents/{path}', params=query_params)
    
    if response.status_code == 404:
        raise Exception(f"File '{path}' not found")
    elif response.status_code != 200:
        response.raise_for_status()
    
    file_data = response.json()
    
    # Handle directory vs file
    if isinstance(file_data, list):
        # It's a directory
        return {
            "type": "directory",
            "path": path,
            "contents": [{
                "name": item["name"],
                "type": item["type"],
                "size": item.get("size"),
                "html_url": item["html_url"]
            } for item in file_data]
        }
    else:
        # It's a file
        import base64
        content = ""
        if file_data.get("content"):
            try:
                content = base64.b64decode(file_data["content"]).decode('utf-8')
            except UnicodeDecodeError:
                content = "[Binary file - content not displayable]"
        
        return {
            "type": "file",
            "name": file_data["name"],
            "path": file_data["path"],
            "size": file_data["size"],
            "sha": file_data["sha"],
            "html_url": file_data["html_url"],
            "download_url": file_data.get("download_url"),
            "content": content[:2000] + "..." if len(content) > 2000 else content
        }

async def search_code(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for code in the repository"""
    query = f"{params['query']} repo:{owner}/{repo}"
    
    # Add optional filters to query
    if params.get("filename"):
        query += f" filename:{params['filename']}"
    if params.get("extension"):
        query += f" extension:{params['extension']}"
    if params.get("path"):
        query += f" path:{params['path']}"
    
    response = github.request('GET', '/search/code', params={"q": query})
    
    if response.status_code != 200:
        response.raise_for_status()
    
    results = response.json()
    
    return {
        "total_count": results["total_count"],
        "items": [{
            "name": item["name"],
            "path": item["path"],
            "sha": item["sha"],
            "html_url": item["html_url"],
            "score": item["score"]
        } for item in results.get("items", [])]
    }

async def add_issue_comment(owner: str, repo: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a comment to an issue"""
    issue_number = params["issue_number"]
    
    data = {
        "body": params["body"]
    }
    
    response = github.request('POST', f'/repos/{owner}/{repo}/issues/{issue_number}/comments', json=data)
    
    if response.status_code == 404:
        raise Exception(f"Issue #{issue_number} not found")
    elif response.status_code != 201:
        response.raise_for_status()
    
    comment = response.json()
    
    return {
        "id": comment["id"],
        "html_url": comment["html_url"],
        "user": comment["user"]["login"],
        "created_at": comment["created_at"],
        "body": comment["body"],
        "message": "Comment added successfully"
    }

async def get_repository_languages(owner: str, repo: str) -> Dict[str, int]:
    """Get programming languages used in the repository"""
    response = github.request('GET', f'/repos/{owner}/{repo}/languages')
    
    if response.status_code != 200:
        response.raise_for_status()
    
    languages = response.json()
    
    # Calculate percentages
    total_bytes = sum(languages.values())
    if total_bytes > 0:
        return {
            "languages": {
                lang: {
                    "bytes": bytes_count,
                    "percentage": round((bytes_count / total_bytes) * 100, 2)
                }
                for lang, bytes_count in languages.items()
            },
            "total_bytes": total_bytes
        }
    else:
        return {"languages": {}, "total_bytes": 0}

async def get_repository_topics(owner: str, repo: str) -> Dict[str, List[str]]:
    """Get topics/tags associated with the repository"""
    response = github.request('GET', f'/repos/{owner}/{repo}/topics', 
                             headers={**github._get_headers(), 'Accept': 'application/vnd.github.mercy-preview+json'})
    
    if response.status_code != 200:
        response.raise_for_status()
    
    topics_data = response.json()
    
    return {
        "topics": topics_data.get("names", []),
        "count": len(topics_data.get("names", []))
    }

async def main():
    """Main entry point for the MCP server"""
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="feather-code",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())