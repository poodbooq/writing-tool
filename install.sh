#!/usr/bin/env bash
set -euo pipefail

REPO="poodbooq/writing-tool"
BRANCH="main"
INSTALL_DIR="${HOME}/.local/bin"

echo "==> Installing writing-tool (wt)..."

# Check Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.11+ is required but not found." >&2
    exit 1
fi

# Create project directory
PROJECT_DIR="${HOME}/.writing-tool"
if [ -d "$PROJECT_DIR" ]; then
    echo "==> Updating existing installation at ${PROJECT_DIR}..."
else
    echo "==> Creating ${PROJECT_DIR}..."
    mkdir -p "$PROJECT_DIR"
fi

# Download the repo archive
ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.zip"
TMP_DIR="$(mktemp -d)"
trap "rm -rf '$TMP_DIR'" EXIT

echo "==> Downloading from ${REPO}..."
if command -v curl &>/dev/null; then
    curl -fsSL "$ARCHIVE_URL" -o "${TMP_DIR}/repo.zip"
elif command -v wget &>/dev/null; then
    wget -q "$ARCHIVE_URL" -O "${TMP_DIR}/repo.zip"
else
    echo "Error: curl or wget required." >&2
    exit 1
fi

# Extract
echo "==> Extracting..."
if command -v unzip &>/dev/null; then
    unzip -qo "${TMP_DIR}/repo.zip" -d "$TMP_DIR"
else
    echo "Error: unzip required." >&2
    exit 1
fi

SRC_DIR="${TMP_DIR}/writing-tool-${BRANCH}"
if [ ! -d "$SRC_DIR" ]; then
    # If branch is main, the dir might be writing-tool-main
    SRC_DIR="${TMP_DIR}/writing-tool-main"
fi
if [ ! -d "$SRC_DIR" ]; then
    # Fallback: find the only subdirectory
    SRC_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d ! -path "$TMP_DIR" | head -1)"
fi

# Copy source files (overwrite)
cp -r "$SRC_DIR/"* "$PROJECT_DIR/"
cp "$SRC_DIR/"{.gitignore,pyproject.toml,justfile,README.md,SKILL.md} "$PROJECT_DIR/" 2>/dev/null || true

# Set up virtual environment
echo "==> Setting up virtual environment..."
cd "$PROJECT_DIR"
"$PYTHON" -m venv .venv
.venv/bin/pip install -q -e "." 2>/dev/null || .venv/bin/pip install -q -e ".[dev]"

# Symlink to PATH
mkdir -p "$INSTALL_DIR"
SYMLINK="${INSTALL_DIR}/wt"
ln -sf "$(realpath .venv/bin/wt)" "$SYMLINK"
echo "==> Installed wt to ${SYMLINK}"

# Verify
if command -v wt &>/dev/null; then
    echo "==> wt $(wt --version 2>/dev/null || echo 'installed') — ready to use"
else
    echo "==> Make sure ${INSTALL_DIR} is in your PATH:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "Quick start:"
echo "  cd my-novel"
echo "  wt init --skill"
echo "  wt extract scene-001.md"
echo "  wt show \"Maxim\""
