# wt

A wrapper around `git worktree` to simplify managing multiple worktrees for a single bare-cloned repository.

## Setup

1. Copy or symlink `wt` to a directory on your `PATH`:

   ```sh
   ln -s "$(pwd)/wt" /usr/local/bin/wt
   ```

2. Make it executable:

   ```sh
   chmod +x wt
   ```

3. Point `wt` at a bare-cloned repository:

   ```sh
   wt configure /path/to/your/bare-repo
   ```

   This writes the `WT_BASE` export to your `~/.zshrc` and sets it in the current shell. Only one repository can be configured at a time — running `configure` again replaces the previous setting.

   If you don't have a bare clone yet:

   ```sh
   git clone --bare <url> /path/to/your/bare-repo
   ```

## Usage

```text
wt <command> [options] [branch/worktree name or substring]
```

| Command | Description |
|---|---|
| `wt configure <path>` | Point wt at a bare-cloned repository. |
| `wt add <branch>` | Create a new worktree for the given branch (existing or new). |
| `wt del [-f] <worktree>` | Remove a worktree. Use `-f` to force if dirty or locked. |
| `wt list` | List all existing worktrees. |
| `wt rebase [<remote-branch>]` | Fetch origin and rebase the current worktree. Defaults to `origin/main`. Automatically prepends `origin/` if omitted. |
| `wt <worktree>` | Open the matching worktree in VS Code (falls back to `cd`). |

Branch and worktree arguments accept unique substrings — you don't need to type the full name.

## Examples

```sh
# Configure wt to use a bare repo
wt configure $HOME/workspace/cxue-platform-component

# Create a worktree for an existing branch
wt add feature/login

# Create a worktree using a substring match
wt add login

# Open a worktree
wt login

# Rebase the current worktree onto origin/main
wt rebase

# Rebase onto a different branch
wt rebase branch-name-substring

# Remove a worktree
wt del login
```