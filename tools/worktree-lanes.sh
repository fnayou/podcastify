#!/usr/bin/env bash
# Worktree lanes on a development machine - guide: docs/worktree-lanes.md
#
#   tools/worktree-lanes.sh install   install / re-assert everything, then verify
#   tools/worktree-lanes.sh verify    verify only; changes nothing
#
# Run from the PRIMARY checkout. Safe to re-run on a machine that already has
# some or all of it: every step asserts a state rather than assuming one.
#
# HOST TOOLING, deliberately: worktrunk, herdr and fzf manage this machine's
# checkouts and terminal, so there is no container they could run in.
#
# What it installs and why:
#   herdr, worktrunk, fzf, jq   Homebrew formulae. herdr is the terminal; `wt` is
#                               worktrunk; the plugin's pickers need fzf and jq.
#   herdr-worktrunk plugin      at ONE audited commit, never a branch. Anyone can
#                               publish a herdr plugin without review. Bumping the
#                               commit is a re-audit, not an edit.
#   hook approvals              worktrunk asks once per machine before running
#                               project hooks, and DECLINING skips them while the
#                               operation continues - so the merge refusal in
#                               .config/wt.toml would do nothing.
set -euo pipefail

# The audited plugin commit. A change here is a new audit.
PLUGIN_SOURCE="devashish2203/herdr-worktrunk"
PLUGIN_ID="worktrunk"
PLUGIN_REF="77e91a9b5429c0296cd883300b4b1d4664e9edd6"

# Worktrunk versions the refusals in .config/wt.toml were MEASURED against:
# pre-commit runs before the squash, and pre-merge after the rebase but before
# the target moves. That ordering is worktrunk's, not ours, and a release could
# change it. An unlisted version fails verify instead of being assumed safe.
# Adding one is a re-measurement (guide, "Measuring a new worktrunk version").
WT_SUPPORTED=("0.81.0")

FORMULAE=(herdr worktrunk fzf jq)

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

ok() { printf 'ok   %s\n' "$*"; }
fail() { printf 'FAIL %s\n' "$*" >&2; err=1; }
die() { printf 'FAIL %s\n' "$*" >&2; exit 1; }

# The primary checkout, not a linked worktree: approvals and the plugin are per
# machine, and lanes are created FROM here.
assert_primary_checkout() {
  local common git_dir
  common="$(git -C "$repo_root" rev-parse --path-format=absolute --git-common-dir)"
  git_dir="$(git -C "$repo_root" rev-parse --path-format=absolute --git-dir)"
  [ "$common" = "$git_dir" ] \
    || die "run this from the primary checkout, not a linked worktree ($repo_root)."
}

install_formulae() {
  command -v brew >/dev/null || die "Homebrew is required: https://brew.sh"
  local f
  for f in "${FORMULAE[@]}"; do
    if brew list --versions "$f" >/dev/null 2>&1; then
      ok "$f already installed ($(brew list --versions "$f"))"
    else
      HOMEBREW_NO_AUTO_UPDATE=1 brew install "$f"
      ok "$f installed ($(brew list --versions "$f"))"
    fi
  done
}

# The installed plugin, as herdr reports it: "<resolved commit> <managed path>
# <enabled>", or nothing when it is not installed.
plugin_state() {
  herdr plugin list --json 2>/dev/null | jq -r --arg id "$PLUGIN_ID" '
    .result.plugins[]? | select(.plugin_id == $id)
    | "\(.source.resolved_commit // "") \(.source.managed_path // "") \(.enabled)"'
}

install_plugin() {
  local state commit
  state="$(plugin_state)"
  commit="${state%% *}"
  if [ "$commit" = "$PLUGIN_REF" ]; then
    ok "herdr plugin ${PLUGIN_ID} already at the audited commit"
  else
    if [ -n "$state" ]; then
      echo "-> herdr plugin ${PLUGIN_ID} is at '${commit:-unknown}', re-installing the audited commit"
      herdr plugin uninstall "$PLUGIN_ID" >/dev/null
    fi
    herdr plugin install "$PLUGIN_SOURCE" --ref "$PLUGIN_REF" --yes >/dev/null
    ok "herdr plugin ${PLUGIN_ID} installed at ${PLUGIN_REF:0:12}"
  fi
  herdr plugin enable "$PLUGIN_ID" >/dev/null 2>&1 || true

  # Show worktrunk's hook output when a lane is created, instead of closing the
  # picker pane over it. Written only if the operator has no config yet.
  local config_dir
  config_dir="$(herdr plugin config-dir "$PLUGIN_ID")"
  mkdir -p "$config_dir"
  if [ ! -f "$config_dir/config.toml" ]; then
    printf '%s\n' \
      '# Written by tools/worktree-lanes.sh. Yours to edit.' \
      '# Keep the picker open after creating a lane so the hook output can be read.' \
      'hold_on_create = true' >"$config_dir/config.toml"
    ok "plugin config written: $config_dir/config.toml"
  else
    ok "plugin config left as it is: $config_dir/config.toml"
  fi
}

approve_hooks() {
  (cd "$repo_root" && wt config approvals add --yes >/dev/null)
  ok "worktrunk project hooks approved for this machine"
}

verify() {
  err=0
  local f
  for f in herdr wt fzf jq; do
    command -v "$f" >/dev/null && ok "$f on PATH" || fail "$f is not on PATH - run: task worktree:install"
  done
  [ "$err" -eq 0 ] || return 1

  local wt_version supported=0 v
  wt_version="$(wt --version 2>/dev/null | sed -nE 's/^wt v?([0-9][0-9.]*).*/\1/p')"
  for v in "${WT_SUPPORTED[@]}"; do
    [ "$wt_version" = "$v" ] && supported=1
  done
  if [ "$supported" -eq 1 ]; then
    ok "worktrunk ${wt_version} is a version the merge refusal was measured against"
  else
    fail "worktrunk '${wt_version:-unknown}' is not a measured version (measured: ${WT_SUPPORTED[*]})."
    printf '%s\n' \
      "   The merge refusal depends on worktrunk running pre-commit before the squash" \
      "   and pre-merge before the target moves; that is unproven on this version." \
      "   Install a measured version, or measure both refusals on this one (guide," \
      "   \"Measuring a new worktrunk version\") and add it to WT_SUPPORTED." >&2
  fi

  # The plugin: the audited commit, enabled, and its managed checkout unmodified
  # - a resolved commit says what was fetched, not what is on disk now.
  local commit path enabled
  # shellcheck disable=SC2046  # three space-free fields, split on purpose
  set -- $(plugin_state) "" "" ""
  commit="$1" path="$2" enabled="$3"
  if [ "$commit" != "$PLUGIN_REF" ]; then
    fail "herdr plugin ${PLUGIN_ID} is at '${commit:-not installed}', not the audited ${PLUGIN_REF:0:12}"
  elif [ "$enabled" != "true" ]; then
    fail "herdr plugin ${PLUGIN_ID} is installed but disabled"
  elif [ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ] \
    || [ "$(git -C "$path" rev-parse HEAD 2>/dev/null)" != "$PLUGIN_REF" ]; then
    fail "herdr plugin ${PLUGIN_ID}'s files at $path differ from the audited commit"
  else
    ok "herdr plugin ${PLUGIN_ID} is the audited commit, unmodified"
  fi

  # Approvals, then the refusals themselves: run the hooks and require them to
  # refuse. A guard that is only configured has not been shown to guard.
  local approvals
  approvals="$(cd "$repo_root" && wt config approvals list 2>&1)"
  if printf '%s\n' "$approvals" | sed -n '/^UNAPPROVED/,$p' | grep -q '❯'; then
    fail "worktrunk project hooks are not all approved - run: task worktree:install"
  else
    ok "worktrunk project hooks approved"
  fi
  # --yes so an unapproved hook cannot sit on a prompt here; approval is the
  # check above, and this one is about what the hooks DO.
  local hook
  for hook in pre-commit pre-merge; do
    if (cd "$repo_root" && wt hook "$hook" --yes >/dev/null 2>&1); then
      fail "worktrunk ${hook} hook did NOT refuse - a local merge would go through"
    else
      ok "worktrunk ${hook} hook refuses"
    fi
  done

  printf '   versions: %s - %s - fzf %s - %s\n' \
    "$(herdr --version 2>/dev/null)" "$(wt --version 2>/dev/null)" \
    "$(fzf --version 2>/dev/null | cut -d' ' -f1)" "$(jq --version 2>/dev/null)"
  return "$err"
}

case "${1:-}" in
  install)
    assert_primary_checkout
    install_formulae
    install_plugin
    approve_hooks
    verify
    ;;
  verify)
    verify
    ;;
  *)
    echo "usage: $(basename "$0") install|verify" >&2
    exit 2
    ;;
esac
