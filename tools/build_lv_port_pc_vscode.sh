#!/usr/bin/env bash
set -euo pipefail

# Build helper that temporarily applies the parent-repo CMake override
# Usage: tools/build_lv_port_pc_vscode.sh [--keep]

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SUBMOD_DIR="$ROOT_DIR/tools/lv_port_pc_vscode"
OVERRIDE="$ROOT_DIR/tools/overrides/lv_port_pc_vscode/CMakeLists.override"
TARGET="$SUBMOD_DIR/CMakeLists.txt"
BACKUP="$SUBMOD_DIR/CMakeLists.txt.bak"

if [ ! -f "$OVERRIDE" ]; then
    echo "Override file not found: $OVERRIDE"
    exit 1
fi
if [ ! -d "$SUBMOD_DIR" ]; then
    echo "Submodule dir not found: $SUBMOD_DIR"
    exit 1
fi

KEEP=${1:-}

# Backup original CMakeLists.txt if not already backed up
if [ ! -f "$BACKUP" ]; then
    cp "$TARGET" "$BACKUP"
    echo "Backed up original CMakeLists.txt -> CMakeLists.txt.bak"
fi

# Apply override
cp "$OVERRIDE" "$TARGET"
echo "Applied override CMakeLists from parent repo."

# Build
mkdir -p "$SUBMOD_DIR/build"
cd "$SUBMOD_DIR/build"
rm -rf ./*
cmake ..
make -j"$(nproc)"

echo "Build finished. Executable (if any) at $SUBMOD_DIR/bin/"

if [ "$KEEP" != "--keep" ]; then
    # Restore original
    if [ -f "$BACKUP" ]; then
        mv -f "$BACKUP" "$TARGET"
        echo "Restored original CMakeLists.txt"
    fi
else
    echo "Kept override in place (use --keep to retain)."
fi

exit 0
