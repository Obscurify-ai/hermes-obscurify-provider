#!/usr/bin/env bash
# Live end-to-end check in a throwaway Hermes home. Makes a few cheap billable requests.
# Usage: OBSCURIFY_API_KEY=sk-obs1_... HERMES=/path/to/hermes tests/e2e.sh
set -euo pipefail
HERMES=${HERMES:-hermes}
here=$(cd "$(dirname "$0")/.." && pwd)
export HERMES_HOME=$(mktemp -d)
work=$(mktemp -d)
cleanup() {
  # -z starts a gateway with --idle-exit; stop it now rather than waiting.
  [ -f "$HERMES_HOME/gateway.pid" ] && kill "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["pid"])' "$HERMES_HOME/gateway.pid")" 2>/dev/null && sleep 2 || true
  rm -rf "$HERMES_HOME" "$work"
}
trap cleanup EXIT
mkdir -p "$HERMES_HOME/plugins/model-providers"
ln -s "$here/obscurify-provider" "$HERMES_HOME/plugins/model-providers/obscurify-provider"

"$HERMES" plugins validate "$here/obscurify-provider" | tail -1

# A brand-new Hermes home can lose the very first turn while its gateway starts, so allow one retry.
out=$("$HERMES" -z "Reply with exactly: ok" --provider obscurify -m meta-llama/llama-3.3-70b-instruct 2>&1) \
  || out=$("$HERMES" -z "Reply with exactly: ok" --provider obscurify -m meta-llama/llama-3.3-70b-instruct 2>&1)
[[ "$out" == *ok* ]] && echo "PASS plain chat" || { echo "FAIL plain chat: $out"; exit 1; }

cd "$work"
"$HERMES" -z "Create a file named hello.txt in the current directory containing exactly: obscurify works. Then reply DONE." \
  --provider obscurify -m deepseek/deepseek-v4-flash --yolo >/dev/null
grep -q "obscurify works" hello.txt && echo "PASS tool call (file written)" || { echo "FAIL tool call"; exit 1; }
