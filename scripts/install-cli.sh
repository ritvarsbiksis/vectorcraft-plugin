#!/bin/bash
# Installs vectorcraft-cli (the command-line tool that runs the VectorCraft MCP server) from the
# official GitHub release of storytold/vectorcraft, verified against the release's SHA256SUMS.txt.
#
#   bash install-cli.sh                      # version 0.16.0
#   bash install-cli.sh --version latest     # newest release (GitHub API)
#   bash install-cli.sh --version 0.17.0
#   bash install-cli.sh --zip FILE --sums SHA256SUMS.txt   # offline: an archive you already have
#
# Installs into ${VECTORCRAFT_INSTALL_DIR:-~/.local/share/vectorcraft-cli}/<release folder>/ and links
# ${VECTORCRAFT_BIN_DIR:-~/.local/bin}/vectorcraft-cli to it. Running it again is safe: an installed,
# working copy of the same version is kept (use --force to reinstall).
#
# macOS: the vectorcraft-cli-<version>-macos-universal.zip asset (~110 MB).
# Linux x86_64 / aarch64 / riscv64: there is no separate CLI asset, so this downloads the full
# vectorcraft-<version>-linux-<arch>.tar.gz (~125 MB) and extracts only bin/vectorcraft-cli and its
# license files. The .deb / .rpm packages install the app and the CLI as /usr/bin/vectorcraft-cli instead.
# Windows: install the MSI; it puts vectorcraft-cli.exe in C:\Program Files\VectorCraft\.
set -euo pipefail

REPO="storytold/vectorcraft"
DEFAULT_VERSION="0.16.0"

INSTALL_DIR="${VECTORCRAFT_INSTALL_DIR:-${HOME:?HOME is not set}/.local/share/vectorcraft-cli}"
BIN_DIR="${VECTORCRAFT_BIN_DIR:-$HOME/.local/bin}"
VERSION=""
ARCHIVE=""
SUMS=""
FORCE=0

die() {
  echo "install-cli: $*" >&2
  exit 1
}
say() { echo "install-cli: $*"; }

usage() {
  sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed -e '$d' -e 's/^# \{0,1\}//'
  cat <<EOF
Options:
  --version X|latest   release to install (default $DEFAULT_VERSION)
  --zip FILE           use this release archive instead of downloading it (alias: --archive)
  --sums FILE          the release's SHA256SUMS.txt (required with --zip)
  --install-dir DIR    where release folders go (env VECTORCRAFT_INSTALL_DIR)
  --bin-dir DIR        where the vectorcraft-cli link goes (env VECTORCRAFT_BIN_DIR)
  --force              reinstall even if this version is already installed
EOF
}

while (($#)); do
  case "$1" in
    --version) VERSION="${2:?--version needs a value}"; shift 2 ;;
    --version=*) VERSION="${1#*=}"; shift ;;
    --zip | --archive) ARCHIVE="${2:?$1 needs a file}"; shift 2 ;;
    --zip=* | --archive=*) ARCHIVE="${1#*=}"; shift ;;
    --sums) SUMS="${2:?--sums needs a file}"; shift 2 ;;
    --sums=*) SUMS="${1#*=}"; shift ;;
    --install-dir) INSTALL_DIR="${2:?--install-dir needs a folder}"; shift 2 ;;
    --bin-dir) BIN_DIR="${2:?--bin-dir needs a folder}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "unknown option '$1' (try --help)" ;;
  esac
done

if [[ -n "$ARCHIVE" && -z "$SUMS" ]]; then die "--zip needs --sums SHA256SUMS.txt (the archive is always verified)"; fi
if [[ -n "$SUMS" && -z "$ARCHIVE" ]]; then die "--sums is only used with --zip"; fi
if [[ -n "$ARCHIVE" ]]; then
  [[ -f "$ARCHIVE" ]] || die "archive not found: $ARCHIVE"
  [[ -f "$SUMS" ]] || die "checksum file not found: $SUMS"
fi

# ---- platform -----------------------------------------------------------------------------------
os="$(uname -s)"
arch="$(uname -m)"
case "$os" in
  Darwin) platform=macos ;;
  Linux)
    platform=linux
    case "$arch" in
      x86_64 | amd64) arch=x86_64 ;;
      aarch64 | arm64) arch=aarch64 ;;
      riscv64) arch=riscv64 ;;
      *) die "no VectorCraft Linux build for '$arch' (released: x86_64, aarch64, riscv64). Build it from source: https://github.com/$REPO/blob/main/docs/mcp.md" ;;
    esac
    ;;
  MINGW* | MSYS* | CYGWIN* | Windows_NT)
    cat >&2 <<EOF
install-cli: on Windows, install VectorCraft with the MSI from
  https://github.com/$REPO/releases
(vectorcraft-<version>-windows-x64.msi, or -arm64 / -x86). It puts the CLI at
  C:\\Program Files\\VectorCraft\\vectorcraft-cli.exe
Set the plugin's cli_path option to that path, then run /reload-plugins.
EOF
    exit 1
    ;;
  *) die "unsupported system '$os'. See https://github.com/$REPO/releases or build from source." ;;
esac

# ---- version ------------------------------------------------------------------------------------
if [[ -z "$VERSION" && -n "$ARCHIVE" ]]; then
  # Take it from the archive's name, e.g. vectorcraft-cli-0.16.0-macos-universal.zip.
  VERSION="$(basename "$ARCHIVE" | sed -nE 's/^vectorcraft(-cli)?-([0-9][0-9A-Za-z.+-]*)-(macos|linux)-.*/\2/p')"
fi
VERSION="${VERSION:-$DEFAULT_VERSION}"
if [[ "$VERSION" == latest ]]; then
  [[ -z "$ARCHIVE" ]] || die "--version latest cannot be used with --zip"
  say "asking GitHub for the latest release..."
  VERSION="$(curl -fsSL -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$REPO/releases/latest" |
    sed -nE 's/^[[:space:]]*"tag_name":[[:space:]]*"([^"]+)".*/\1/p' | head -n1)" ||
    die "could not reach the GitHub API; pass --version X"
  [[ -n "$VERSION" ]] || die "could not read the latest release tag; pass --version X"
fi
VERSION="${VERSION#v}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.+-][0-9A-Za-z.+-]*)?$ ]] || die "'$VERSION' does not look like a version"

if [[ "$platform" == macos ]]; then
  FOLDER="vectorcraft-cli-$VERSION-macos-universal"
  ASSET="$FOLDER.zip"
  BIN_REL="vectorcraft-cli"
else
  FOLDER="vectorcraft-$VERSION-linux-$arch"
  ASSET="$FOLDER.tar.gz"
  BIN_REL="bin/vectorcraft-cli"
fi
BASE_URL="https://github.com/$REPO/releases/download/v$VERSION"
TARGET="$INSTALL_DIR/$FOLDER"
TARGET_BIN="$TARGET/$BIN_REL"
LINK="$BIN_DIR/vectorcraft-cli"

if [[ -n "$ARCHIVE" && "$(basename "$ARCHIVE")" != "$ASSET" ]]; then
  die "expected the archive to be named $ASSET for this system (got $(basename "$ARCHIVE"))"
fi

link_bin() {
  mkdir -p "$BIN_DIR"
  if [[ -e "$LINK" && ! -L "$LINK" ]]; then
    die "$LINK exists and is not a symlink; move it away (or pass --bin-dir) and run this again"
  fi
  ln -sfn "$TARGET_BIN" "$LINK"
}

installed_version() { "$1" --version 2>/dev/null | head -n1 || true; }

finish() {
  link_bin
  local v
  v="$(installed_version "$LINK")"
  [[ -n "$v" ]] || die "installed, but '$LINK --version' did not run. Check $TARGET_BIN."
  say "installed $v"
  say "  binary: $TARGET_BIN"
  say "  link:   $LINK"
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
      if [[ "$BIN_DIR" == "$HOME/.local/bin" ]]; then
        say "note: $BIN_DIR is not on your PATH. The plugin looks there anyway; add it to PATH to use vectorcraft-cli in a shell."
      else
        say "note: $BIN_DIR is not on your PATH and the plugin does not search it: set the plugin's cli_path option to $LINK."
      fi
      ;;
  esac
  say "run /reload-plugins in Claude Code to start the vectorcraft MCP server."
}

# ---- already installed? -------------------------------------------------------------------------
if ((!FORCE)) && [[ -x "$TARGET_BIN" ]]; then
  current="$(installed_version "$TARGET_BIN")"
  if [[ "$current" == *"$VERSION"* ]]; then
    say "$current is already installed in $TARGET (use --force to reinstall)"
    finish
    exit 0
  fi
fi

# ---- download and verify ------------------------------------------------------------------------
sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    die "neither shasum nor sha256sum is available to verify the download"
  fi
}

mkdir -p "$INSTALL_DIR"
WORK="$(mktemp -d "$INSTALL_DIR/.install.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

if [[ -z "$ARCHIVE" ]]; then
  command -v curl >/dev/null 2>&1 || die "curl is required to download the release"
  say "downloading $ASSET (v$VERSION) from github.com/$REPO..."
  curl -fL --retry 3 --progress-bar -o "$WORK/SHA256SUMS.txt" "$BASE_URL/SHA256SUMS.txt" ||
    die "could not download $BASE_URL/SHA256SUMS.txt (does release v$VERSION exist?)"
  # The checksum list must name the asset before the large download starts.
  grep -qE "[[:space:]]\*?$ASSET\$" "$WORK/SHA256SUMS.txt" ||
    die "release v$VERSION has no $ASSET (see https://github.com/$REPO/releases/tag/v$VERSION)"
  curl -fL --retry 3 --progress-bar -o "$WORK/$ASSET" "$BASE_URL/$ASSET" ||
    die "could not download $BASE_URL/$ASSET"
  ARCHIVE="$WORK/$ASSET"
  SUMS="$WORK/SHA256SUMS.txt"
fi

expected="$(awk -v a="$ASSET" '{ f = $2; sub(/^\*/, "", f); if (f == a) { print tolower($1); exit } }' "$SUMS")"
[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || die "$(basename "$SUMS") has no SHA-256 for $ASSET"
actual="$(sha256 "$ARCHIVE")"
if [[ "$actual" != "$expected" ]]; then
  die "SHA-256 mismatch for $ASSET: expected $expected, got $actual. Not installing."
fi
say "verified SHA-256 of $ASSET"

# ---- extract ------------------------------------------------------------------------------------
STAGE="$WORK/stage"
mkdir -p "$STAGE"
if [[ "$platform" == macos ]]; then
  command -v unzip >/dev/null 2>&1 || die "unzip is required"
  unzip -q "$ARCHIVE" "$FOLDER/*" -d "$STAGE" || die "could not extract $ASSET"
else
  # Only the CLI and its license/notice files, not the GUI app.
  tar -xzf "$ARCHIVE" -C "$STAGE" "$FOLDER/bin/vectorcraft-cli" ||
    die "$ASSET has no $FOLDER/bin/vectorcraft-cli"
  tar -xzf "$ARCHIVE" -C "$STAGE" "$FOLDER/share/doc" 2>/dev/null ||
    say "note: no license files found in $ASSET (share/doc); continuing"
fi
[[ -f "$STAGE/$FOLDER/$BIN_REL" ]] || die "$ASSET does not contain $FOLDER/$BIN_REL"
chmod +x "$STAGE/$FOLDER/$BIN_REL"
v="$(installed_version "$STAGE/$FOLDER/$BIN_REL")"
[[ -n "$v" ]] || die "the extracted vectorcraft-cli does not run on this machine ($os $arch)"

rm -rf "$TARGET"
mv "$STAGE/$FOLDER" "$TARGET"
finish
