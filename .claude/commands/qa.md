---
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git show:*), Bash(python -m pytest:*), Read, Glob, Grep, Task, Skill
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
!`git diff --name-only origin/HEAD... 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null || git diff --name-only HEAD 2>/dev/null || git diff --name-only --cached 2>/dev/null || echo "No changes detected (new repo or no commits)"`
```

RECENT COMMITS:
```
!`git log --oneline -5 --no-decorate 2>/dev/null || echo "No commits yet"`
```

DIFF SUMMARY:
```
!`git diff --stat origin/HEAD... 2>/dev/null || git diff --stat HEAD~1 2>/dev/null || git diff --stat HEAD 2>/dev/null || git diff --stat --cached 2>/dev/null || echo "No diff available"`
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

### Phase 4: Run Tests

If Python files were modified, run the test suite:

```bash
python -m pytest tests/ -x -q --tb=short 2>/dev/null || echo "No tests found or pytest not available"
```

- Use `-x` to stop on first failure (fail fast)
- Use `-q` for quiet output
- Report: **PASS** (all tests pass), **FAIL** (tests failing), or **SKIP** (no tests)

**Important:** Failing tests are BLOCKERS - code should not be committed with failing tests.

### Phase 5: Synthesize Results

After all reviews and tests complete, provide:

1. **Quick Summary**
   - What was reviewed
   - Test results (pass/fail/skip)
   - Overall assessment (Pass/Needs Attention/Blockers)

2. **Action Items**
   - List any blockers that must be fixed (including failing tests)
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

### Test Results
- ✅ **PASS** - 42 tests passed in 3.2s

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
5. If Python files changed, run the test suite with pytest
6. Synthesize all results into a unified report
7. Provide a clear verdict and action items

**Verdict Rules:**
- ❌ **FAIL** if any tests fail (blocker)
- ❌ **FAIL** if any security blockers found
- ⚠️ **NEEDS ATTENTION** if high-priority issues exist
- ✅ **PASS** if all tests pass and no blockers

If no files have changed, report that and suggest what review might be useful.
