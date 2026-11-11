"""Shell completion scripts, printed by `todo completion <shell>`."""

ZSH = r"""#compdef todo
# zsh completion for `todo`. Install once:
#   mkdir -p ~/.oh-my-zsh/custom/completions
#   todo completion zsh > ~/.oh-my-zsh/custom/completions/_todo
# (any directory on $fpath works), then open a new shell.

_todo_tags() {
  local -a tags
  tags=(${(f)"$(command todo tags 2>/dev/null)"})
  # -V keeps most-used-first order; -M matches case-insensitively, since
  # `todo add` ignores case when it looks tags up.
  (( $#tags )) && compadd -V tags -M 'm:{a-zA-Z}={A-Za-z}' -- $tags
}

_todo() {
  if (( CURRENT == 2 )); then
    local -a cmds=(
      'add:add a task, e.g. todo add Fix the build @chorus +++'
      'tags:list the tags in use'
      'completion:print a shell completion script'
    )
    _describe -t commands 'command' cmds
    compadd -- --group -h --help
    return
  fi
  case $words[2] in
    add)
      if [[ $words[CURRENT-1] == (-p|--priority) ]]; then
        compadd -- 1 2 3 4
      elif [[ $words[CURRENT-1] == (-t|--tag) ]]; then
        _todo_tags
      elif compset -P '[@#]'; then
        _todo_tags
      elif [[ $PREFIX == -* ]]; then
        compadd -- -t --tag -p --priority
      fi
      ;;
    completion) compadd zsh ;;
  esac
}

# Works both as an autoloaded file on $fpath and when sourced.
if [[ $funcstack[1] == _todo ]]; then
  _todo "$@"
else
  compdef _todo todo
fi
"""

SCRIPTS = {"zsh": ZSH}
