#!/usr/bin/env bash
# Starts a dedicated server, waits for the ready line, sends `stop`, then checks the log.
# Inputs arrive as SB_* environment variables from action.yml.
set -uo pipefail

cd "$SB_DIR" || exit 1
log="$SB_LOG"
rm -f console "$log"
mkfifo console

finish() { # result, exit code
  echo "result=$1" >> "$GITHUB_OUTPUT"
  echo "log-path=$(realpath "$log")" >> "$GITHUB_OUTPUT"
  exit "$2"
}

# setsid gives the server its own process group, so the cleanup step can kill all of it.
setsid bash -c "$SB_COMMAND" < console > "$log" 2>&1 &
server=$!
echo "$server" > "$SB_PIDFILE"
exec 3> console

result=timeout
for ((i = 0; i < SB_TIMEOUT; i++)); do
  if grep -qF -- "$SB_READY" "$log"; then result=ready; break; fi
  if ! kill -0 "$server" 2>/dev/null; then result=exited; break; fi
  sleep 1
done
# A server that printed the ready line and then exited still counts as ready.
if [ "$result" = exited ] && grep -qF -- "$SB_READY" "$log"; then result=ready; fi

if [ "$result" != ready ]; then
  tail -n 200 "$log"
  echo "Server did not finish loading ($result)." >&2
  finish "$result" 1
fi

echo stop >&3
for _ in $(seq 1 120); do
  kill -0 "$server" 2>/dev/null || break
  sleep 1
done
if kill -0 "$server" 2>/dev/null; then
  echo "Server ignored stop for 120 seconds." >&2
  finish timeout 1
fi

if [ -n "$SB_FAIL" ] && grep -En -- "$SB_FAIL" "$log"; then
  echo 'The log matches a fail pattern.' >&2
  finish ready 1
fi
if [ -n "$SB_EXPECT" ] && ! grep -Eq -- "$SB_EXPECT" "$log"; then
  tail -n 200 "$log"
  echo 'The log does not match the expect pattern.' >&2
  finish ready 1
fi
echo 'Server booted and stopped cleanly.'
finish ready 0
