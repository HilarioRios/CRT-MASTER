#!/usr/bin/env bash
# Regression test for ~/.claude/hooks/guard-dangerous-bash.sh.
# Run this any time the hook script changes: bash docs/AI-SYSTEM/hooks-regression-test.sh
#
# Each case is written to a temp file and piped in, rather than embedded
# directly in this script's own shell commands — the hook also guards THIS
# session's Bash tool calls, so a literal "rm -rf /" etc. in the command
# text you type would trip the hook on the verification command itself.
set -uo pipefail
HOOK="$HOME/.claude/hooks/guard-dangerous-bash.sh"
PAYLOAD="$(mktemp)"
trap 'rm -f "$PAYLOAD"' EXIT
pass=0; fail=0

check() {
  local desc="$1" cmd="$2" want_deny="$3"
  printf '{"tool_name":"Bash","tool_input":{"command":%s}}' "$(printf '%s' "$cmd" | jq -Rs .)" > "$PAYLOAD"
  local decision
  decision=$(cat "$PAYLOAD" | "$HOOK" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [ "$want_deny" = "deny" ] && [ "$decision" = "deny" ]; then
    echo "PASS (blocked as expected): $desc"; pass=$((pass+1))
  elif [ "$want_deny" = "allow" ] && [ "$decision" != "deny" ]; then
    echo "PASS (allowed as expected): $desc"; pass=$((pass+1))
  else
    echo "FAIL: $desc -> got decision='$decision'"; fail=$((fail+1))
  fi
}

# --- original happy-path cases ---
check "rm -rf on root-ish path"        'rm -rf /'                                  deny
check "rm -rf on home"                 'rm -rf ~'                                  deny
check "rm -rf wildcard from root"      'rm -rf /*'                                 deny
check "rm -rf node_modules (safe)"     'rm -rf node_modules'                       allow
check "rm -rf ./dist (safe)"           'rm -rf ./dist'                             allow
check "git push --force"               'git push --force origin main'             deny
check "git push --force-with-lease"    'git push --force-with-lease'               deny
check "normal git push"                'git push origin main'                     allow
check "git reset --hard"               'git reset --hard HEAD~3'                  deny
check "git reset soft (safe)"          'git reset --soft HEAD~1'                   allow
check "git clean -fd"                  'git clean -fd'                            deny
check "DROP DATABASE"                  'psql -c "DROP DATABASE prod;"'            deny
check "DROP TABLE"                     'mysql -e "DROP TABLE users;"'              deny
check "select is safe"                 'psql -c "SELECT * FROM users;"'           allow
check "overwrite .env"                 'echo foo > .env'                          deny
check "overwrite .env.production"      'printf "x" > .env.production'             deny
check "append safe to .env.example"    'echo foo >> .env.example'                 allow
check "rm single .env"                 'rm .env'                                  deny
check "git add .env"                   'git add .env'                             deny
check "git commit staged .env"         'git commit -am "oops with .env inside"'   allow
check "unrelated ls"                   'ls -la'                                   allow

# --- bypass classes found in code review (2026-09-30) ---
check "quoted rm -rf root, double quotes"   'rm -rf "/"'                            deny
check "quoted rm -rf root, single quotes"   "rm -rf '/'"                            deny
check "quoted rm -rf HOME var"              'rm -rf "$HOME"'                        deny
check "rm -rf tilde with trailing slash"    'rm -rf ~/'                             deny
check "sh -c wrapped rm -rf root"           'sh -c "rm -rf /"'                      deny
check "bash -c wrapped rm -rf root"         'bash -c "rm -rf /"'                    deny
check "eval wrapped rm -rf root"            'eval "rm -rf /"'                       deny
check "mixed-case DROP"                     'psql -c "DROP table users;"'           deny
check "force push with -f"                  'git push -f origin main'               deny
check "force-ish branch name not a flag"    'git push origin --force-feature-branch' allow
check "rm relative-path .env"               'rm ./config/.env'                      deny
check "rm absolute-path .env"               'rm /Users/hilario/project/.env'        deny
check "overwrite path-prefixed .env"        'echo x > ./config/.env'                deny
check "git add path-prefixed .env"          'git add ./config/.env'                 deny
check "rm relative .env.example (safe)"     'rm ./config/.env.example'              allow

# --- second-round bypass classes found by the independent reviewer re-check (2026-09-30) ---
check "backtick command substitution"       'rm -rf `echo /`'                       deny
check "dollar-paren command substitution"   'rm -rf $(echo /)'                      deny
check "backslash-escaped slash"             'rm -rf \/'                             deny
check "dynamic non-root path (safe)"        'rm -rf $(pwd)/node_modules'            allow

echo "---"
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
