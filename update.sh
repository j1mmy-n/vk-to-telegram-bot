#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$PROJECT_DIR/.env"

show_usage() {
    cat <<'EOF'
Usage:
  ./update.sh                  Update repository and Docker image
  ./update.sh latest           Set BOT_VERSION=latest and update
  ./update.sh 1.1.5            Set BOT_VERSION=1.1.5 and update
  ./update.sh --no-git         Update Docker image without git pull
  ./update.sh --no-git latest  Set BOT_VERSION=latest without git pull and update

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

skip_git=0
version=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h | --help)
            show_usage
            exit 0
            ;;
        --no-git)
            skip_git=1
            ;;
        -*)
            echo "Error: unknown option '$1'." >&2
            show_usage >&2
            exit 1
            ;;
        *)
            if [ -n "$version" ]; then
                echo "Error: only one version argument is allowed." >&2
                show_usage >&2
                exit 1
            fi
            version="$1"
            ;;
    esac
    shift
done

if [ "$skip_git" -eq 0 ]; then
    require_command git
fi
require_command docker

cd "$PROJECT_DIR"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env was not found in $PROJECT_DIR." >&2
    echo "Create it from .env.example and fill in your tokens first." >&2
    exit 1
fi

if [ -n "$version" ]; then
    set_bot_version "$version"
    echo "BOT_VERSION was set to '$version' in .env."
fi

current_version=$(
    sed -n 's/^BOT_VERSION=//p' "$ENV_FILE" | tail -n 1
)
current_version=${current_version:-latest}

if [ "$current_version" != "latest" ]; then
    echo "Using pinned BOT_VERSION=$current_version from .env."
    echo "Run './update.sh latest' if you want to follow the latest stable image."
fi

if [ "$skip_git" -eq 0 ]; then
    echo "Updating repository..."
    git pull --ff-only
else
    echo "Skipping git pull (--no-git)."
fi

echo "Pulling Docker image..."
docker compose pull

echo "Restarting bot..."
docker compose up -d --remove-orphans

echo "Done. Current containers:"
docker compose ps
