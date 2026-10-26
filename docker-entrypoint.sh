#!/bin/sh
# Runs inside the api container only.
#
# The model cache and uploads are bind-mounted from the project's own .data/
# directory, so nothing persists in Docker's managed storage outside the repo.
# On Linux Docker may create those host folders as root; fix ownership once,
# then drop privileges. Using exec keeps uvicorn as PID 1 so SIGTERM (docker
# stop) shuts it down cleanly instead of waiting for the timeout.
set -eu

mkdir -p /models/hf /data/uploads

if [ "$(id -u)" = "0" ]; then
    if [ "$(stat -c '%U' /models/hf 2>/dev/null || echo '')" != "app" ] \
       || [ "$(stat -c '%U' /data 2>/dev/null || echo '')" != "app" ]; then
        chown -R app:app /models/hf /data 2>/dev/null || true
    fi
    if command -v setpriv >/dev/null 2>&1; then
        exec setpriv --reuid=app --regid=app --init-groups "$@"
    fi
    exec su app -s /bin/sh -c 'exec "$@"' sh "$@"
fi

exec "$@"
