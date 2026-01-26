# When to Use Each Skill

This guide helps you choose the right skill for your task.

## Quick Reference

| Task | Use This |
|------|----------|
| Starting a new feature | `superpowers:brainstorming` → `superpowers:writing-plans` |
| Fixing a bug | `superpowers:systematic-debugging` |
| Working on UI | `/frontend-design` first |
| Code complete, need review | `/qa` (auto-routes to needed reviews) |
| Before committing | `superpowers:verification-before-completion` |
| Ready for PR | `superpowers:finishing-a-development-branch` |

---

## Complete Workflows

### New Feature Workflow

```
1. superpowers:brainstorming           ← Explore requirements & design
2. superpowers:writing-plans           ← Create implementation plan
3. superpowers:test-driven-development ← Write tests first (optional)
4. superpowers:executing-plans         ← Implement with checkpoints
5. /qa                                 ← Auto-run needed reviews
6. superpowers:verification-before-completion ← Verify before claiming done
7. superpowers:finishing-a-development-branch ← Prepare for merge/PR
```

### Bug Fix Workflow

```
1. superpowers:systematic-debugging    ← Find root cause first!
2. [Fix the bug]
3. /qa                                 ← Auto-run needed reviews
4. superpowers:verification-before-completion ← Verify fix works
5. Commit
```

### UI Feature Workflow

```
1. superpowers:brainstorming           ← Explore UI requirements
2. /frontend-design                    ← Load design guidelines
3. [Implement UI]
4. /qa                                 ← Auto-runs design + code reviews
5. superpowers:verification-before-completion
6. Commit
```

### Quick Fix Workflow (Small Changes)

```
1. [Make the change]
2. /qa                                 ← Quick check
3. Commit
```

---

## Starting Work

### New Feature

| Situation | Use This | Why |
|-----------|----------|-----|
| Unclear requirements | `superpowers:brainstorming` | Explores and clarifies before coding |
| Clear requirements | `superpowers:writing-plans` | Creates implementation plan |
| Multi-step implementation | `superpowers:executing-plans` | Executes plan with checkpoints |

### Bug Report

| Situation | Use This | Why |
|-----------|----------|-----|
| Any bug | `superpowers:systematic-debugging` | Finds root cause before fixing |
| Simple typo | Fix directly | No debugging needed |

### UI Work

| Situation | Use This | Why |
|-----------|----------|-----|
| Creating/editing UI | `/frontend-design` | Loads design system guidelines |
| Design decisions | `superpowers:brainstorming` | Explores options before committing |

---

## During Work

### Implementation

| Situation | Use This | Why |
|-----------|----------|-----|
| Following a plan | `superpowers:executing-plans` | Tracks progress with checkpoints |
| Parallel independent tasks | `superpowers:subagent-driven-development` | Runs tasks concurrently |
| Writing tests first | `superpowers:test-driven-development` | TDD workflow |

### Code Quality

| Situation | Use This | Why |
|-----------|----------|-----|
| File getting large | `/simplify` | Identifies simplification opportunities |
| Need standards check | `/code-standards` | Checks CLAUDE.md compliance |

---

## Finishing Work

### Quality Assurance

| Situation | Use This | Why |
|-----------|----------|-----|
| Code complete | `/qa` | **Best default** - auto-detects needed reviews |
| Only Python changed | `/code-standards` | Focused code review |
| Only UI changed | `/design-review` | Focused design review |
| Security-sensitive code | `/security-review` | Focused security review |
| Complex code added | `/simplify` | Identify simplification opportunities |

### Before Commit

| Situation | Use This | Why |
|-----------|----------|-----|
| About to commit | `superpowers:verification-before-completion` | Runs final verification |
| Ready for PR | `superpowers:finishing-a-development-branch` | Prepares PR, handles merge |
| Need code review | `superpowers:requesting-code-review` | Requests formal review |

---

## Manual Reviews (When /qa Isn't Enough)

`/qa` auto-routes to the right reviews, but sometimes you need manual control:

| Situation | Use This |
|-----------|----------|
| Deep code standards check | `/code-standards` |
| Security concerns | `/security-review` |
| UI polish needed | `/design-review` |
| Simplify specific code | `/simplify` |

---

## Project Skills vs Superpowers

### Project Skills (in .claude/commands/)

Local commands customized for your project:

| Command | Description |
|---------|-------------|
| `/qa` | Smart router - detects files and runs needed reviews |
| `/simplify` | Simplifies complex code |
| `/code-standards` | Checks CLAUDE.md compliance |
| `/design-review` | Reviews UI changes |
| `/security-review` | Security-focused review |
| `/frontend-design` | Loads design guidelines |

### Superpowers (External Skills)

General-purpose skills that work across projects:

| Skill | Purpose |
|-------|---------|
| `superpowers:brainstorming` | Explore requirements before coding |
| `superpowers:writing-plans` | Create implementation plans |
| `superpowers:executing-plans` | Execute plans with checkpoints |
| `superpowers:subagent-driven-development` | Parallel task execution |
| `superpowers:systematic-debugging` | Root cause analysis |
| `superpowers:test-driven-development` | TDD workflow |
| `superpowers:verification-before-completion` | Pre-commit verification |
| `superpowers:finishing-a-development-branch` | PR/merge workflow |
| `superpowers:requesting-code-review` | Request formal review |
| `superpowers:receiving-code-review` | Handle review feedback |

---

## Decision Tree

```
Is this a new feature?
├─ Yes → Use brainstorming → writing-plans → executing-plans
└─ No
    Is this a bug?
    ├─ Yes → Use systematic-debugging first
    └─ No
        Is this UI work?
        ├─ Yes → Use /frontend-design first
        └─ No
            Is code complete?
            ├─ Yes → Use /qa (auto-routes reviews)
            │         └─ Then verification-before-completion
            └─ No → Continue working
```

---

## Common Mistakes to Avoid

1. **Jumping to fix bugs** - Always use `systematic-debugging` first
2. **Skipping verification** - Always run `verification-before-completion` before claiming done
3. **Running wrong review** - Use `/qa` to auto-detect instead of guessing
4. **Starting UI without guidelines** - Always load `/frontend-design` first
5. **Implementing without planning** - Use `brainstorming` and `writing-plans` for features
