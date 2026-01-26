# Claude Code Workflow Setup Guide

Complete guide for setting up a comprehensive Claude Code workflow in your project.

## Prerequisites

- Claude Code CLI installed
- Git repository initialized

## Installation Steps

### Step 1: Create Directory Structure

```bash
mkdir -p .claude/commands
```

### Step 2: Copy Command Files

Copy all `.md` files from `commands/` to `.claude/commands/`:

```bash
cp examples/claude-workflow-setup/commands/*.md .claude/commands/
```

### Step 3: Create CLAUDE.md

Copy and customize the template:

```bash
cp examples/claude-workflow-setup/CLAUDE.md.template CLAUDE.md
```

Then edit `CLAUDE.md` to match your project:
- Replace `[PROJECT_NAME]` with your project name
- Update tech stack information
- Add project-specific conventions
- Define your file structure

### Step 4: (Optional) Configure Permissions

Copy the settings template:

```bash
cp examples/claude-workflow-setup/settings.local.json.template .claude/settings.local.json
```

This pre-configures tool permissions for the workflow commands.

## Verification

Test that skills are properly installed:

```bash
# List available commands
claude /help

# Test QA router
claude /qa

# Test code review
claude /code-standards
```

## File Locations Summary

| File | Location | Purpose |
|------|----------|---------|
| `qa.md` | `.claude/commands/` | Smart QA router |
| `code-simplifier.md` | `.claude/commands/` | Code simplification |
| `code-standards.md` | `.claude/commands/` | Code standards review |
| `design-review.md` | `.claude/commands/` | Design review |
| `security-review.md` | `.claude/commands/` | Security review |
| `frontend-design.md` | `.claude/commands/` | Frontend guidelines |
| `CLAUDE.md` | Project root | Project instructions |
| `settings.local.json` | `.claude/` | Permissions config |

## Customization

### Adding Project-Specific Rules

Edit your command files to add project-specific rules:

```markdown
## Project-Specific Checks

### [Your Rule Name]
- [Description]
- [What to look for]
- [How to flag violations]
```

### Modifying Review Criteria

Each review command has configurable criteria. Edit the relevant `.md` file to:
- Add/remove checks
- Change severity levels
- Modify output format

### Integrating with CI/CD

You can run these reviews in CI:

```yaml
# GitHub Actions example
- name: Code Review
  run: |
    claude --print /code-standards > code-review.md
    # Parse and fail if blockers found
```

## Troubleshooting

### Command Not Found

Ensure the command file:
1. Is in `.claude/commands/`
2. Has `.md` extension
3. Has proper frontmatter with `---` delimiters

### Permission Denied

Check `settings.local.json` has the required tool permissions:

```json
{
  "permissions": {
    "allow": ["Read", "Glob", "Grep", "Bash(git *)"]
  }
}
```

### Git Context Missing

The commands use git to detect changed files. Ensure:
1. You're in a git repository
2. You have commits to compare against
3. Your branch is tracking a remote

## Next Steps

1. Read [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) to learn when to use each skill
2. Customize CLAUDE.md for your project
3. Run `/qa` on your current changes to test the workflow
