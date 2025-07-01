# Feather Code MCP Server

A comprehensive GitHub integration for Claude Desktop using the Model Context Protocol (MCP). Access all GitHub features directly from Claude with 15 powerful tools.

## Features

- 🚀 **15 GitHub Tools** - Complete GitHub API coverage
- 🔍 **Auto-detection** - Automatically detects repository from git
- 🔐 **Flexible Auth** - PAT, GitHub App, and file-based tokens
- 📦 **Zero Config** - Works out of the box in any git repository
- ✅ **MCP Compliant** - Built with official MCP SDK

## Installation

### Quick Install (Recommended)

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/feather-code/main/install.sh | bash
```

**Windows:**
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/yourusername/feather-code/main/install.bat -OutFile install.bat
.\install.bat
```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/feather-code.git
   cd feather-code
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up authentication:
   ```bash
   export GITHUB_PAT=your_github_personal_access_token
   ```

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "feather-code": {
      "command": "python3",
      "args": ["/path/to/feather-code/feather_code.py"]
    }
  }
}
```

### Standalone

Run from any git repository:
```bash
cd /your/github/repo
python3 /path/to/feather_code.py
```

## Tools Available

### Repository Management
- **`get_repository_info`** - Get comprehensive repository details
- **`get_repository_languages`** - Get language breakdown
- **`get_repository_topics`** - Get repository topics/tags

### Issues
- **`list_issues`** - List and filter repository issues
- **`create_issue`** - Create new issues with labels
- **`update_issue`** - Update existing issues
- **`get_issue`** - Get detailed issue information
- **`add_issue_comment`** - Add comments to issues

### Pull Requests
- **`get_pull_requests`** - List and filter pull requests
- **`create_pull_request`** - Create new pull requests
- **`get_pull_request`** - Get detailed PR information

### Code & Repository
- **`list_branches`** - List repository branches
- **`get_commits`** - Get commit history with filters
- **`get_file_content`** - Read file contents from repository
- **`search_code`** - Search code within repository

## Authentication

### Personal Access Token (Recommended)

1. Create a token at https://github.com/settings/tokens/new
2. Select scopes: `repo`, `read:org` (for private repos)
3. Set the token:
   ```bash
   export GITHUB_PAT=ghp_your_token_here
   ```

### Token File
```bash
echo "ghp_your_token_here" > ~/.github_token
export GITHUB_PAT_FILE=~/.github_token
```

### GitHub App (Advanced)
```bash
export GITHUB_APP_ID=123456
export GITHUB_INSTALLATION_ID=789012
export GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
```

## Configuration

All configuration is done through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_OWNER` | Repository owner | Auto-detected from git |
| `GITHUB_REPO` | Repository name | Auto-detected from git |
| `GITHUB_PAT` | Personal access token | - |
| `GITHUB_PAT_FILE` | Path to token file | - |
| `GITHUB_APP_ID` | GitHub App ID | - |
| `GITHUB_INSTALLATION_ID` | App installation ID | - |
| `GITHUB_PRIVATE_KEY_PATH` | App private key path | - |
| `GITHUB_API_URL` | GitHub API URL | https://api.github.com |

## Examples

### Create an issue from Claude
```
User: Create a new issue titled "Bug: Login not working" with the bug label

Claude: I'll create that issue for you.
[Uses create_issue tool]

Created issue #123: "Bug: Login not working"
```

### Search for code
```
User: Find all files that contain "authentication"

Claude: I'll search for files containing "authentication".
[Uses search_code tool]

Found 5 files containing "authentication":
- src/auth/login.py
- src/auth/middleware.py
...
```

## Development

### Running Tests
```bash
python3 test_comprehensive.py
python3 validate_production_ready.py
```

### Building from Source
```bash
pip install -e .
```

## Troubleshooting

### "Repository not detected"
- Ensure you're in a git repository with a GitHub remote
- Or set `GITHUB_OWNER` and `GITHUB_REPO` environment variables

### "Authentication failed"
- Check your GitHub token has the required scopes
- Ensure the token is not expired
- Try using a PAT instead of GitHub App auth

### "Tool not found"
- Update to the latest version
- Check Claude Desktop has reloaded the MCP configuration

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- 📖 [Documentation](https://github.com/yourusername/feather-code/wiki)
- 🐛 [Report Issues](https://github.com/yourusername/feather-code/issues)
- 💬 [Discussions](https://github.com/yourusername/feather-code/discussions)