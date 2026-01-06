# Issue Workflow - Claude Instructions

**IMPORTANT: Always read this file when working with issues.**

## Folder Structure

```
Issues/
├── PENDING/              # New issues waiting to be worked on
├── IN PROGRESS/          # Currently being worked on
├── PENDING USER REVIEW/  # Completed, awaiting user approval
└── DONE/                 # Approved and closed
```

## Workflow States

```
User creates issue → PENDING → IN PROGRESS → PENDING USER REVIEW → DONE
                                    ↑                    │
                                    └────────────────────┘
                                      (if rejected)
```

## Issue File Template

When creating a new issue file, use this structure:

```markdown
# [Short Title]

**Created:** YYYY-MM-DD
**Priority:** High | Medium | Low

## Description
[Clear description of the issue]

## Steps to Reproduce (if bug)
1. Step one
2. Step two
3. ...

## Expected Behavior
[What should happen]

## Current Behavior
[What actually happens]

## Technical Notes
- Relevant files: `path/to/file.py`
- Related features: [feature name]

---

## Work Log

### [DATE] - Status: [IN PROGRESS | PENDING USER REVIEW]
**Changes made:**
- File: `path/to/file` - Description of change

**Testing done:**
- [ ] Manual testing
- [ ] Verified fix works

**Notes:**
[Any additional context]
```

## My Actions by State

### When user reports an issue:
1. Read `_WORKFLOW.md` (this file)
2. Create structured issue file in `PENDING/`
3. Use naming: `YYYY-MM-DD_short-description.md`

### When starting work on an issue:
1. Move file from `PENDING/` to `IN PROGRESS/`
2. Update Work Log section with current date
3. Work on the fix

### When fix is complete:
1. Update Work Log with all changes made
2. Move file from `IN PROGRESS/` to `PENDING USER REVIEW/`
3. Inform user: "Issue ready for review in PENDING USER REVIEW"

### When user approves:
1. Add final note to Work Log
2. Move file to `DONE/`

### When user rejects:
1. Add rejection feedback to Work Log
2. Move file back to `IN PROGRESS/`
3. Continue working on the fix

## File Naming Convention

`YYYY-MM-DD_short-description.md`

Examples:
- `2026-01-06_zoom-interferes-with-inputs.md`
- `2026-01-06_furniture-numbers-not-showing.md`

## Quick Reference

| User Says | My Action |
|-----------|-----------|
| "I have an issue..." | Create file in `PENDING/` |
| "Work on issue X" | Move to `IN PROGRESS/`, start work |
| "Check pending issues" | List files in `PENDING/` |
| "OK" / "Approved" | Move from `PENDING USER REVIEW/` to `DONE/` |
| "Not fixed" / "Still broken" | Move back to `IN PROGRESS/` |
| "Delete issue X" | Remove the file |

## Important Notes

- Always update the Work Log when making changes
- Never skip `PENDING USER REVIEW` - user must approve
- Keep descriptions concise but complete
- Reference exact file paths and line numbers when possible
