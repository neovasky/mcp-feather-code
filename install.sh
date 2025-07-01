#!/bin/bash
# Feather Code MCP - Interactive Installation Script
# Supports Linux and macOS with automatic dependency detection

set -e

echo "🚀 Feather Code MCP Installation"
echo "================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Detect OS
OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    print_info "Detected Linux system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    print_info "Detected macOS system"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

# Check Python
echo -e "\n🐍 Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python found: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    if [[ $PYTHON_VERSION == 3.* ]]; then
        print_success "Python found: $PYTHON_VERSION"
        PYTHON_CMD="python"
    else
        print_error "Python 3 required, found Python $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.8 or later."
    exit 1
fi

# Check pip
echo -e "\n📦 Checking pip installation..."
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
    print_success "pip3 found"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    print_success "pip found"
else
    print_error "pip not found. Please install pip."
    exit 1
fi

# Install dependencies
echo -e "\n📚 Installing dependencies..."
REQUIREMENTS=(
    "mcp>=1.0.0"
    "PyJWT>=2.8.0"
    "requests>=2.31.0"
    "cryptography>=41.0.0"
)

# Handle different Python environments
INSTALL_FLAGS=""
if [[ "$OS" == "linux" ]]; then
    # Check if we're in a virtual environment
    if [[ -z "${VIRTUAL_ENV}" ]]; then
        # Check for externally-managed-environment (PEP 668)
        if $PIP_CMD install --help | grep -q "break-system-packages"; then
            print_warning "Detected PEP 668 restriction (externally-managed environment)"
            echo "Choose installation method:"
            echo "1) Use --break-system-packages (not recommended for production)"
            echo "2) Create virtual environment (recommended)"
            echo "3) Use system package manager"
            read -p "Enter choice (1-3): " choice
            
            case $choice in
                1)
                    INSTALL_FLAGS="--break-system-packages"
                    print_warning "Using --break-system-packages flag"
                    ;;
                2)
                    echo -e "\n🔧 Creating virtual environment..."
                    $PYTHON_CMD -m venv feather-code-env
                    source feather-code-env/bin/activate
                    print_success "Virtual environment created and activated"
                    ;;
                3)
                    print_info "Please install dependencies manually using your system package manager"
                    print_info "Example for Arch: sudo pacman -S python-requests python-cryptography"
                    exit 0
                    ;;
                *)
                    print_error "Invalid choice"
                    exit 1
                    ;;
            esac
        fi
    else
        print_success "Virtual environment detected: $VIRTUAL_ENV"
    fi
fi

# Install each requirement
for req in "${REQUIREMENTS[@]}"; do
    echo "Installing $req..."
    if $PIP_CMD install $INSTALL_FLAGS "$req"; then
        print_success "Installed $req"
    else
        print_error "Failed to install $req"
        exit 1
    fi
done

# Setup directory
INSTALL_DIR="$HOME/.local/share/feather-code"
echo -e "\n📁 Setting up installation directory..."
mkdir -p "$INSTALL_DIR"

# Copy files
echo "Copying MCP server files..."
cp feather_code.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
if [[ -f ".env.example" ]]; then
    cp .env.example "$INSTALL_DIR/"
fi

# Make executable
chmod +x "$INSTALL_DIR/feather_code.py"
print_success "Files copied to $INSTALL_DIR"

# Create wrapper script
WRAPPER_SCRIPT="$HOME/.local/bin/feather-code"
echo -e "\n🔧 Creating wrapper script..."
mkdir -p "$HOME/.local/bin"

cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Feather Code MCP wrapper script
cd "$INSTALL_DIR"
exec $PYTHON_CMD feather_code.py "\$@"
EOF

chmod +x "$WRAPPER_SCRIPT"
print_success "Wrapper script created at $WRAPPER_SCRIPT"

# Setup environment file
ENV_FILE="$INSTALL_DIR/.env"
echo -e "\n🔐 Setting up authentication..."
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Creating environment file..."
    read -p "Enter GitHub Personal Access Token (or press Enter to skip): " github_pat
    if [[ -n "$github_pat" ]]; then
        echo "GITHUB_PAT=$github_pat" > "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        print_success "GitHub PAT saved to $ENV_FILE"
    else
        cp "$INSTALL_DIR/.env.example" "$ENV_FILE" 2>/dev/null || true
        print_warning "Environment file created. Edit $ENV_FILE to add your GitHub PAT"
    fi
else
    print_info "Environment file already exists at $ENV_FILE"
fi

# Add to PATH if needed
echo -e "\n🛣️  Checking PATH..."
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    print_warning "$HOME/.local/bin is not in your PATH"
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    
    read -p "Would you like to add it automatically? (y/n): " add_path
    if [[ "$add_path" =~ ^[Yy]$ ]]; then
        SHELL_RC="$HOME/.bashrc"
        if [[ "$SHELL" == *"zsh"* ]]; then
            SHELL_RC="$HOME/.zshrc"
        fi
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        print_success "Added to $SHELL_RC (restart your shell or source the file)"
    fi
else
    print_success "PATH is correctly configured"
fi

# Installation complete
echo -e "\n" 
echo "🎉 Installation Complete!"
echo "========================"
print_success "Feather Code MCP is now installed"

echo -e "\n📋 Next steps:"
echo "1. Set up your GitHub authentication in $ENV_FILE"
echo "2. Test the installation: feather-code --help"
echo "3. Add to Claude Code:"
echo "   claude mcp add feather-code $WRAPPER_SCRIPT"

echo -e "\n🔗 Repository detection:"
echo "Run from a git repository or set environment variables:"
echo "export GITHUB_OWNER=your-username"
echo "export GITHUB_REPO=your-repository"

echo -e "\n📚 Documentation:"
echo "Check the README.md for detailed usage instructions"

if [[ -n "${VIRTUAL_ENV}" ]]; then
    echo -e "\n⚠️  Remember to activate your virtual environment:"
    echo "source $VIRTUAL_ENV/bin/activate"
fi

print_success "Installation successful! 🚀"