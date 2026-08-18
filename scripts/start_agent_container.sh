#!/bin/sh

set -u

checker_pid=""
agent_pid=""
stopping=0

stop_children() {
    stopping=1
    if [ -n "$agent_pid" ]; then
        kill -TERM "$agent_pid" 2>/dev/null || true
    fi
    if [ -n "$checker_pid" ]; then
        kill -TERM "$checker_pid" 2>/dev/null || true
    fi
}

trap stop_children INT TERM

checker_data_dir="${AIG_API_CHECKER_DATA_DIR:-/api-checker-data}"
case "$checker_data_dir" in
    /api-checker-data|/api-checker-data/*) ;;
    *)
        echo "[agent-container] AIG_API_CHECKER_DATA_DIR must be /api-checker-data or a child path" >&2
        exit 1
        ;;
esac

mkdir -p "$checker_data_dir"
chown -R agent:agent /api-checker-data

echo "[agent-container] starting API Checker"
gosu agent:agent /app/api-checker-venv/bin/python \
    -m uvicorn services.api_checker.server:app \
    --host 0.0.0.0 --port 8000 --no-access-log &
checker_pid=$!

while [ "$stopping" -eq 0 ] && kill -0 "$checker_pid" 2>/dev/null; do
    if [ -z "$agent_pid" ] || ! kill -0 "$agent_pid" 2>/dev/null; then
        if [ -n "$agent_pid" ]; then
            wait "$agent_pid"
            agent_status=$?
            echo "[agent-container] Agent exited with status $agent_status; retrying" >&2
            agent_pid=""
            sleep 2 &
            wait $! 2>/dev/null || true
        fi
        if [ "$stopping" -eq 0 ]; then
            echo "[agent-container] starting Agent"
            gosu agent:agent /app/agent &
            agent_pid=$!
        fi
    fi
    sleep 1 &
    wait $! 2>/dev/null || true
done

requested_stop=$stopping
checker_status=0
if [ -n "$checker_pid" ]; then
    if [ "$stopping" -eq 0 ]; then
        wait "$checker_pid"
        checker_status=$?
        echo "[agent-container] API Checker exited with status $checker_status" >&2
    else
        wait "$checker_pid" 2>/dev/null || true
    fi
    checker_pid=""
fi

stop_children
if [ -n "$agent_pid" ]; then
    wait "$agent_pid" 2>/dev/null || true
fi

if [ "$requested_stop" -eq 1 ]; then
    exit 0
fi
if [ "$checker_status" -eq 0 ]; then
    checker_status=1
fi
exit "$checker_status"
