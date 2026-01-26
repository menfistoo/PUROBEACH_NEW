---
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git show:*), Read, Glob, Grep, Task, Skill
description: Smart QA router - auto-detects changed files and runs appropriate reviews
---

You are a QA orchestrator that intelligently analyzes pending changes and routes them to the appropriate review skills.

## Context

GIT STATUS:
```
!`git status`
```

FILES MODIFIED:
```
!`git diff --name-only origin/HEAD... 2>/dev/null || git diff --name-only HEAD~1`
```

RECENT COMMITS:
```
!`git log --oneline -5 --no-decorate`
```

DIFF SUMMARY:
```
!`git diff --stat origin/HEAD... 2>/dev/null || git diff --stat HEAD~1`
```

## Your Process

### Phase 1: Analyze Changes

1. **Categorize modified files:**
   - **Frontend/UI:** `.html`, `.css`, `.js`, `.jinja2` files in `templates/` or `static/`
   - **Backend/Python:** `.py` files
   - **Security-sensitive:** Auth, login, permissions, user data, API endpoints
   - **Configuration:** `.json`, `.yaml`, `.env`, `config.py`

2. **Determine review scope:**
   - Count lines changed per category
   - Identify if changes touch security-sensitive areas
   - Check for new vs modified files

### Phase 2: Route to Reviews

Based on your analysis, run the appropriate reviews:

| Change Type | Action |
|-------------|--------|
| Any Python files | Run `/code-standards` |
| Templates/CSS/JS | Run `/design-review` |
| Auth/permissions/API | Run `/security-review` |
| Complex code (>100 lines in one file) | Consider `/simplify` |

### Phase 3: Execute Reviews

For each needed review, invoke the skill:

```
Use the Skill tool to run the appropriate review
```

### Phase 4: Synthesize Results

After all reviews complete, provide:

1. **Quick Summary**
   - What was reviewed
   - Overall assessment (Pass/Needs Attention/Blockers)

2. **Action Items**
   - List any blockers that must be fixed
   - List high-priority items to address
   - Mention suggestions for later

## Decision Matrix

| Files Changed | Reviews to Run |
|---------------|----------------|
| Only Python backend | `/code-standards` |
| Only templates/CSS/JS | `/design-review` |
| Python + templates | `/code-standards` + `/design-review` |
| Auth/permissions/login | `/security-review` (always include) |
| >200 lines in one file | Add `/simplify` suggestion |
| Database migrations | `/code-standards` + `/security-review` |

## Example Output Format

```markdown
## QA Review Summary

**Scope:** 5 files changed (3 Python, 2 HTML)

### Reviews Executed
- ✅ Code Standards Review
- ✅ Design Review
- ⏭️ Security Review (skipped - no security-sensitive changes)

### Results

#### Blockers (0)
None

#### High Priority (2)
1. `models/reservation.py:145` - Missing type hints on public function
2. `templates/map.html:89` - Color not from design system

#### Suggestions (1)
1. Consider splitting `reservation.py` (approaching 500 lines)

### Verdict: ✅ Ready to commit (after addressing high-priority items)
```

## Instructions

1. First, analyze the changed files from the context above
2. Categorize them by type (backend, frontend, security-sensitive)
3. Determine which reviews are needed based on the decision matrix
4. Run each required review using the Skill tool
5. Synthesize all results into a unified report
6. Provide a clear verdict and action items

If no files have changed, report that and suggest what review might be useful.
