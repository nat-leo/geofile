#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-venv}"

# Color output for better readability
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# 1. Pick a Python executable
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    log_error "Python not found in PATH"
    exit 1
fi

log_info "Using: $PYTHON ($("$PYTHON" --version))"

# 2. Check if venv already exists
if [[ -d "$VENV_DIR" ]]; then
    log_warn "Virtual environment already exists at '$VENV_DIR'"
    read -rp "Recreate it? [y/N] " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        log_info "Using existing virtual environment"
    fi
fi

# 3. Create the virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    log_info "Creating virtual environment at '$VENV_DIR'..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# 4. Activate it depending on OS
case "$OSTYPE" in
    darwin*|linux*)
        # macOS or Linux (including WSL)
        # venv layout: venv/bin/activate
        ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
        ;;

    msys*|cygwin*|mingw*)
        # Git Bash / MSYS / MINGW on Windows
        # venv layout: venv/Scripts/activate
        ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
        ;;

    *)
        log_error "Unsupported OSTYPE: $OSTYPE"
        exit 1
        ;;
esac

if [[ ! -f "$ACTIVATE_SCRIPT" ]]; then
    log_error "Activation script not found at: $ACTIVATE_SCRIPT"
    exit 1
fi

# shellcheck source=/dev/null
source "$ACTIVATE_SCRIPT"

log_info "Virtual environment activated: $VIRTUAL_ENV"

# 5. Upgrade pip, setuptools, and wheel
log_info "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# 6. Install the project and dependencies
log_info "Installing project in editable mode with dev dependencies..."
if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]]; then
    pip install -e ".[dev]"
    log_info "✓ Development environment ready!"
else
    log_error "No pyproject.toml or setup.py found in current directory"
    exit 1
fi

# 7. Display helpful information
echo ""
log_info "To activate this environment in the future, run:"
case "$OSTYPE" in
    msys*|cygwin*|mingw*)
        echo "  source $VENV_DIR/Scripts/activate"
        ;;
    *)
        echo "  source $VENV_DIR/bin/activate"
        ;;
esac
echo ""
log_info "To deactivate, run: deactivate"