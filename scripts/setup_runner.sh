#!/usr/bin/env bash
# Set up a GitHub Actions self-hosted runner on the home server.
#
# Usage:
#   bash scripts/setup_runner.sh <REGISTRATION_TOKEN>
#
# Get the token from:
#   GitHub → repository → Settings → Actions → Runners → New self-hosted runner
#   (token is valid for 1 hour)
#
# After running this script, set the DEPLOY_DIR variable in GitHub:
#   GitHub → repository → Settings → Variables → Actions → New repository variable
#   Name: DEPLOY_DIR
#   Value: /absolute/path/to/this/project/on/the/server

set -euo pipefail

REPO_URL="https://github.com/THKhai/AI-assistant"
RUNNER_DIR="$HOME/actions-runner"

# ── Validate args ──

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <REGISTRATION_TOKEN>"
  echo ""
  echo "Get token from:"
  echo "  $REPO_URL/settings/actions/runners/new"
  exit 1
fi

TOKEN="$1"

# ── Check dependencies ──

for cmd in curl tar docker git; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is not installed"
    exit 1
  fi
done

# ── Fetch latest runner version ──

echo "Fetching latest runner version..."
RUNNER_VERSION=$(curl -sf https://api.github.com/repos/actions/runner/releases/latest \
  | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')

if [ -z "$RUNNER_VERSION" ]; then
  echo "Error: could not fetch runner version from GitHub API"
  exit 1
fi

echo "Runner version: $RUNNER_VERSION"

# ── Download and extract ──

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

ARCHIVE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
echo "Downloading $ARCHIVE..."
curl -fSL -o "$ARCHIVE" \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${ARCHIVE}"

tar xzf "$ARCHIVE"
rm "$ARCHIVE"

# ── Configure runner ──

echo ""
echo "Configuring runner..."
./config.sh \
  --url "$REPO_URL" \
  --token "$TOKEN" \
  --name "homeserver" \
  --labels "self-hosted,homeserver,linux" \
  --work "_work" \
  --unattended

# ── Install as systemd service ──

echo ""
echo "Installing systemd service..."
sudo ./svc.sh install
sudo ./svc.sh start

echo ""
echo "============================================"
echo "Runner installed and running."
echo ""
echo "Next step — set DEPLOY_DIR in GitHub:"
echo "  $REPO_URL/settings/variables/actions"
echo "  Name:  DEPLOY_DIR"
echo "  Value: $(pwd | sed 's|/actions-runner||')/home-assistant"
echo "    (adjust to actual project path if different)"
echo ""
echo "Useful commands:"
echo "  sudo $RUNNER_DIR/svc.sh status   — check runner status"
echo "  sudo $RUNNER_DIR/svc.sh stop     — stop runner"
echo "  sudo $RUNNER_DIR/svc.sh start    — start runner"
echo "  journalctl -u actions.runner.*   — view logs"
echo "============================================"
