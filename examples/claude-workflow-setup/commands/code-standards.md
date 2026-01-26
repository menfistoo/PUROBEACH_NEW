---
allowed-tools: Grep, Read, Edit, Write, Bash, Glob, Task
description: Review code for CLAUDE.md standards compliance and propose refactoring
---

You are an expert code standards reviewer. Analyze code against the project's CLAUDE.md guidelines and propose specific refactoring recommendations.

## Context

GIT STATUS:
```
!`git status`
```

FILES MODIFIED:
```
!`git diff --name-only origin/HEAD... 2>/dev/null || echo "No changes from origin"`
```

## Review Scope

1. **Review pending changes** - Files modified in current branch
2. **Review specific files** - If user specifies files/directories
3. **Review entire codebase** - Scan all code files for compliance

## Standards Checklist

### 1. File Size Limits
- **Target:** 300-500 lines per module
- **Warning:** >600 lines
- **Critical:** >800 lines - must refactor

### 2. Code Conventions
- Type hints on function signatures
- Docstrings on public functions
- Consistent naming (verb_noun for functions)
- No hardcoded values (use constants/config)

### 3. Security Checklist
- Authentication decorators on protected routes
- Parameterized SQL (no f-strings in queries)
- No sensitive data in logs
- Input validation on user data

### 4. Module Organization
- Clear section headers
- Single responsibility per module
- Logical grouping of functions

## Review Process

### Phase 1: File Size Analysis
Identify files exceeding limits and propose splitting strategies.

### Phase 2: Code Quality Scan
- Functions missing type hints
- Public functions missing docstrings
- SQL with f-strings
- Routes missing decorators

### Phase 3: Naming Convention Check
- Functions not following conventions
- Inconsistent naming patterns

## Report Format

```markdown
# Code Standards Review

## Summary
[Overall compliance and key findings]

## File Size Issues

### Critical (>800 lines)
| File | Lines | Recommended Action |
|------|-------|-------------------|

### Warning (600-800 lines)
| File | Lines | Recommendation |
|------|-------|----------------|

## Code Quality Issues
[List with file:line references]

## Security Issues
[List with file:line references]

## Refactoring Proposals
[Specific recommendations]

## Compliance Score
| Category | Score | Notes |
|----------|-------|-------|
| Overall | X/10 | |
```

## Instructions

1. Analyze file sizes across codebase
2. Scan for convention violations
3. Check for missing type hints and docstrings
4. Review security decorators on routes
5. Identify naming issues
6. Produce structured report with line references
7. Propose concrete refactoring strategies
