# MyHospital worktree + Zellij helpers (fish)
#
# These are the short commands the harness docs refer to (zorch / zimpl / zls /
# zkillwt / wtlist / wtcreate / wtjoin). Source this file once from your fish
# config so they are always available:
#
#     # ~/.config/fish/config.fish
#     source /home/dax/Documents/arabica/roast/scripts/fish/myhospital-zellij.fish
#
# Then reload:  exec fish
#
# Design notes:
# - The workspace root is derived from THIS file's location (scripts/fish/../..),
#   so nothing is hardcoded. Override with `set -gx MYHOSPITAL_ROOT <path>`.
# - Helpers only OPEN Zellij sessions; they never create a worktree (use
#   `wtcreate`) and never auto-start a dev server (the layout opens shells only).
# - 1 worktree = 2 sessions: orchestrator (mh-<slug>-orch-<tool>) and
#   implementer (mh-<slug>-impl-<tool>).

if not set -q MYHOSPITAL_ROOT
    set -gx MYHOSPITAL_ROOT (path resolve (status dirname)/../..)
end

function _mh_root --description 'Print the MyHospital workspace root'
    echo $MYHOSPITAL_ROOT
end

function wtlist --description 'List MyHospital task worktrees'
    command python $MYHOSPITAL_ROOT/scripts/worktree.py list $argv
end

function wtcreate --description 'Create a worktree: wtcreate <slug> <slot> [extra worktree.py flags]'
    if test (count $argv) -lt 2
        echo "usage: wtcreate <slug> <slot> [extra worktree.py create flags]" >&2
        echo "  e.g. wtcreate bed 1" >&2
        echo "       wtcreate bed 1 --skip-db-sync --skip-fe-install   # light" >&2
        return 2
    end
    command python $MYHOSPITAL_ROOT/scripts/worktree.py create --slug $argv[1] --slot $argv[2] $argv[3..-1]
end

function _mh_open_session --description 'internal: open a worktree Zellij session'
    # args: role(orch|impl) default_tool slug [tool]
    set -l role $argv[1]
    set -l default_tool $argv[2]
    set -l slug $argv[3]
    set -l tool $argv[4]
    if test -z "$slug"
        echo "usage: z$role <slug> [tool=$default_tool]" >&2
        return 2
    end
    test -z "$tool"; and set tool $default_tool
    set -l wt $MYHOSPITAL_ROOT/worktrees/$slug
    if not test -d $wt
        echo "Worktree '$slug' not found at $wt" >&2
        echo "  Create it first:   wtcreate $slug <slot>" >&2
        echo "  Or see existing:   wtlist" >&2
        return 1
    end
    if not type -q zellij
        echo "zellij is not installed / not on PATH." >&2
        return 127
    end
    set -l session mh-$slug-$role-$tool
    set -l layout $MYHOSPITAL_ROOT/scripts/zellij/myhospital-$role.kdl
    pushd $wt
    if zellij list-sessions -n 2>/dev/null | string match -q -r "^$session\b"
        zellij attach $session
    else
        zellij --session $session --layout $layout
    end
    popd
end

function zorch --description 'Open orchestrator Zellij session: zorch <slug> [tool=claude]'
    _mh_open_session orch claude $argv
end

function zimpl --description 'Open implementer Zellij session: zimpl <slug> [tool=opencode]'
    _mh_open_session impl opencode $argv
end

function zls --description 'List MyHospital (mh-*) Zellij sessions'
    if not type -q zellij
        echo "zellij is not installed / not on PATH." >&2
        return 127
    end
    set -l raw (zellij list-sessions 2>/dev/null | string replace -ra '\x1b\[[0-9;]*m' '')
    set -l hits
    for line in $raw
        set -l name (string split -f1 ' ' -- $line)
        string match -q 'mh-*' -- $name; and set -a hits $line
    end
    if test (count $hits) -gt 0
        printf '%s\n' $hits
    else
        echo "(no mh-* worktree sessions)"
    end
end

function zkillwt --description 'Kill all Zellij sessions for a worktree slug: zkillwt <slug>'
    set -l slug $argv[1]
    if test -z "$slug"
        echo "usage: zkillwt <slug>" >&2
        return 2
    end
    if not type -q zellij
        echo "zellij is not installed / not on PATH." >&2
        return 127
    end
    set -l raw (zellij list-sessions 2>/dev/null | string replace -ra '\x1b\[[0-9;]*m' '')
    set -l killed 0
    for line in $raw
        set -l name (string split -f1 ' ' -- $line)
        if string match -q "mh-$slug-*" -- $name
            echo "killing $name"
            zellij delete-session --force $name 2>/dev/null; or zellij kill-session $name 2>/dev/null
            set killed (math $killed + 1)
        end
    end
    test $killed -eq 0; and echo "No Zellij sessions for slug '$slug'."
end

function wtjoin --description 'Join an existing worktree (validate + show open commands): wtjoin <slug> [orch_tool] [impl_tool]'
    set -l slug $argv[1]
    if test -z "$slug"
        echo "usage: wtjoin <slug> [orch_tool=claude] [impl_tool=opencode]" >&2
        return 2
    end
    if not test -d $MYHOSPITAL_ROOT/worktrees/$slug
        echo "Worktree '$slug' does not exist. Existing worktrees:" >&2
        wtlist
        return 1
    end
    set -l orch claude
    set -l impl opencode
    test -n "$argv[2]"; and set orch $argv[2]
    test -n "$argv[3]"; and set impl $argv[3]
    echo "Worktree '$slug' is ready. Open its two sessions:"
    echo "  zorch $slug $orch"
    echo "  zimpl $slug $impl"
end
