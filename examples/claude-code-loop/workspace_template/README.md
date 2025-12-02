# ACE Translation Workspace

This workspace is managed by ACE + Claude Code for translating the ACE framework from Python to TypeScript.

## Structure

- `specs/` - Project specification and coding standards
  - `project.md` - Translation project overview
  - `rules.md` - Coding standards and guidelines
- `source/` - Python source code (cloned from external repo, git ignored)
- `target/` - TypeScript translation output (tracked by git)
- `.agent/` - Claude Code working files (TODO, notes, logs - git ignored)

## Git Repository

This workspace is its own git repository, separate from the ACE framework repo. All translation work is committed here.

### Workflow

1. Translate Python code from `source/` to TypeScript in `target/`
2. Write tests and verify correctness
3. Commit with descriptive message: `git commit -m "Translate module X"`
4. Continue to next module

### Viewing History

```bash
# See all commits
git log --oneline

# See changes in last commit
git show

# See diff between versions
git diff HEAD~1 HEAD
```

## Managed by ACE

This workspace is orchestrated by `ace_loop.py` which:
- Provides tasks from TODO.md
- Injects learned strategies into your context
- Learns from your execution to improve over time
