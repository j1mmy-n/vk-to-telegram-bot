#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$PROJECT_DIR/.env"

show_usage() {
    cat <<'EOF'
Usage:
  ./update.sh             Update using the BOT_VERSION from .env
  ./update.sh latest      Set BOT_VERSION=latest and update
  ./update.sh 1.1.2       Set BOT_VERSION=1.1.2 and update

The script preserves .env, Docker volumes, bot state, and logs.
EOF
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: required command '$1' was not found." >&2
        exit 1
    fi
}

set_bot_version() {
    version="$1"
    temporary_file="$ENV_FILE.tmp"

    if grep -q '^BOT_VERSION=' "$ENV_FILE"; then
        awk -v version="$version" '
            BEGIN { updated = 0 }
            /^BOT_VERSION=/ {
                print "BOT_VERSION=" version
                updated = 1
                next
            }
            { print }
            END {
                if (!updated) {
                    print "BOT_VERSION=" version
                }
            }
        ' "$ENV_FILE" >"$temporary_file"
    else
        cp "$ENV_FILE" "$temporary_file"
        printf '\nBOT_VERSION=%s\n' "$version" >>"$temporary_file"
    fi

    chmod --reference="$ENV_FILE" "$temporary_file" 2>/dev/null || true
    mv "$temporary_file" "$ENV_FILE"
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    show_usage
    exit 0
fi

if [ "$#" -gt 1 ]; then
    show_usage >&2
    exit 1
fi

require_command git
require_command docker

cd "$PROJECT_DIR"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env was not found in $PROJECT_DIR." >&2
    echo "Create it from .env.example and fill in your tokens first." >&2
    exit 1
fi

if [ "$#" -eq 1 ]; then
    set_bot_version "$1"
    echo "BOT_VERSION was set to '$1' in .env."
fi

current_version=$(
    sed -n 's/^BOT_VERSION=//p' "$ENV_FILE" | tail -n 1
)
current_version=${current_version:-latest}

if [ "$current_version" != "latest" ]; then
    echo "Using pinned BOT_VERSION=$current_version from .env."
    echo "Run './update.sh latest' if you want to follow the latest stable image."
fi

echo "Updating repository..."
git pull --ff-only

echo "Pulling Docker image..."
docker compose pull

echo "Restarting bot..."
docker compose up -d --remove-orphans

echo "Done. Current containers:"
docker compose ps
