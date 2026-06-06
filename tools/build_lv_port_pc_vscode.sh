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
CLEANUP_DONE=0
SYMLINK_CREATED=0

cleanup() {
    if [ "$KEEP" != "--keep" ] && [ "$CLEANUP_DONE" -eq 0 ]; then
        if [ -f "$BACKUP" ]; then
            mv -f "$BACKUP" "$TARGET"
            echo "Restored original CMakeLists.txt"
        fi
        if [ "$SYMLINK_CREATED" -eq 1 ] && [ -L "$UI_CUSTOM_LINK" ]; then
            rm "$UI_CUSTOM_LINK"
            echo "Removed temporary ui_custom symlink from submodule."
        fi
        CLEANUP_DONE=1
    fi
}
trap cleanup EXIT

# Backup original CMakeLists.txt if not already backed up
if [ ! -f "$BACKUP" ]; then
    cp "$TARGET" "$BACKUP"
    echo "Backed up original CMakeLists.txt -> CMakeLists.txt.bak"
fi

# Apply override
cp "$OVERRIDE" "$TARGET"
echo "Applied override CMakeLists from parent repo."

# Create a local ui_custom link inside the submodule for custom UI source discovery.
UI_CUSTOM_LINK="$SUBMOD_DIR/ui_custom"
if [ ! -e "$UI_CUSTOM_LINK" ]; then
    ln -s ../../src/ui_custom "$UI_CUSTOM_LINK"
    echo "Created temporary ui_custom symlink in submodule."
    SYMLINK_CREATED=1
else
    SYMLINK_CREATED=0
fi

# Build
mkdir -p "$SUBMOD_DIR/build"
cd "$SUBMOD_DIR/build"
rm -rf ./*
cmake ..
make -j"$(nproc)"

echo "Build finished. Executable (if any) at $SUBMOD_DIR/bin/"

if [ "$KEEP" = "--keep" ]; then
    echo "Kept override in place (use --keep to retain)."
fi

exit 0
