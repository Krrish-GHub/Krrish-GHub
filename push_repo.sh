#!/usr/bin/env bash
# Run this script in the repo folder to init and push to GitHub.
# Usage: ./push_repo.sh <github-username> <repo-name> (defaults to Krrish-Ghub Krrish-Ghub)

USER=${1:-Krrish-Ghub}
REPO=${2:-Krrish-Ghub}

set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed; please install git first"
  exit 1
fi

if [ -d .git ]; then
  echo "Repository already initialized"
else
  git init
  git add .
  git commit -m "Add profile ASCII art + colored snake generator"
fi

# prefer gh if available
if command -v gh >/dev/null 2>&1; then
  if ! gh auth status >/dev/null 2>&1; then
    echo "Please run: gh auth login" >&2
    exit 1
  fi
  gh repo create "${USER}/${REPO}" --public --source=. --remote=origin --push --confirm || true
  echo "Pushed via gh"
else
  echo "gh CLI not found; pushing via HTTPS. You will be prompted for credentials (use PAT as password)."
  git branch -M main
  git remote add origin "https://github.com/${USER}/${REPO}.git" || true
  git push -u origin main
fi

echo "Done. Open https://github.com/${USER}/${REPO}" 
