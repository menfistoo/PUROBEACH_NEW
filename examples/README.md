# Claude Code Workflow Templates

Reusable templates for setting up a comprehensive Claude Code workflow with skills for code review, design review, security review, QA orchestration, and code simplification.

## Quick Start

1. Copy the `claude-workflow-setup/` folder contents to your project root
2. Place command files in `.claude/commands/`
3. Customize `CLAUDE.md.template` for your project
4. (Optional) Configure permissions in `settings.local.json`

## What's Included

### Project Skills (Local Commands)

| Skill | File | Purpose |
|-------|------|---------|
| `/qa` | `commands/qa.md` | Smart QA router - auto-detects changed files and runs appropriate reviews |
| `/simplify` | `commands/code-simplifier.md` | Simplifies complex code for clarity and maintainability |
| `/code-standards` | `commands/code-standards.md` | Reviews code against CLAUDE.md standards |
| `/design-review` | `commands/design-review.md` | Reviews UI changes for design system compliance |
| `/security-review` | `commands/security-review.md` | Security-focused code review |
| `/frontend-design` | `commands/frontend-design.md` | Loads design guidelines for UI work |

### External Skills (Superpowers)

These are external skills you can invoke with `superpowers:skillname`:

| Skill | When to Use |
|-------|-------------|
| `superpowers:brainstorming` | Before ANY creative work - explores requirements first |
| `superpowers:writing-plans` | When you have specs for multi-step tasks |
| `superpowers:executing-plans` | Execute implementation plans with checkpoints |
| `superpowers:systematic-debugging` | Before proposing fixes for any bug |
| `superpowers:verification-before-completion` | Before claiming work is done |
| `superpowers:finishing-a-development-branch` | When ready to merge/PR |

## Guides

- **[SETUP_GUIDE.md](claude-workflow-setup/SETUP_GUIDE.md)** - Installation instructions
- **[WORKFLOW_GUIDE.md](claude-workflow-setup/WORKFLOW_GUIDE.md)** - When to use each skill

## File Structure

```
your-project/
├── .claude/
│   ├── commands/           ← Place skill files here
│   │   ├── qa.md
│   │   ├── code-simplifier.md
│   │   ├── code-standards.md
│   │   ├── design-review.md
│   │   ├── security-review.md
│   │   └── frontend-design.md
│   └── settings.local.json ← Optional: permissions config
├── CLAUDE.md               ← Project-specific instructions
└── ...
```

## Usage Examples

```bash
# Run smart QA (auto-detects what reviews are needed)
/qa

# Simplify complex code
/simplify

# Check code standards
/code-standards

# Review UI changes
/design-review

# Security review
/security-review

# Load design guidelines before UI work
/frontend-design
```

## Customization

Each template is designed to be customized:

1. **CLAUDE.md.template** - Replace `[PROJECT_NAME]` placeholders with your project details
2. **Commands** - Adjust review criteria to match your project's needs
3. **Settings** - Configure which tools each command can use

## License

MIT - Use freely in your projects.
