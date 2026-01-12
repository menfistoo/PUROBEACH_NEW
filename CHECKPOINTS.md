# Checkpoints & Recovery Guide

## Current Stable Checkpoint
**Date:** 2026-01-12 (Updated: 22:16)
**Tag:** `stable-checkpoint-audit-20260112`
**Commit:** `eee4ee3`
**Branch:** `backup/audit-stable-20260112`
**Database:** `backups/beach_club_stable_20260112_221641.db`

### What's Stable
✅ All permissions working correctly
✅ Analytics dashboard functional
✅ Waitlist system operational
✅ Hotel guests Excel import working (535 guests tested)
✅ All configuration pages accessible
✅ Packages and minimum consumption accessible
✅ Menu structure consolidated and clean
✅ **Comprehensive audit logging system operational**
✅ **Audit logs for reservations (create, update, state changes, cancel)**
✅ **Audit logs for customers (create, update preferences)**
✅ **Admin UI at /beach/admin/audit-logs**

---

## How to Revert to This Checkpoint

### Option 1: Revert Code Only (Keep Current Database)
Use this if the database is fine but code changes broke something.

```bash
# Revert to tagged version
git reset --hard stable-checkpoint-audit-20260112

# Or revert to backup branch
git reset --hard backup/audit-stable-20260112
```

### Option 2: Revert Everything (Code + Database)
Use this for complete rollback.

```bash
# 1. Revert code
git reset --hard stable-checkpoint-audit-20260112

# 2. Restore database backup
cp backups/beach_club_stable_20260112_221641.db instance/beach_club.db

# 3. Restart server
# Kill current server, then: python app.py
```

### Option 3: Just Restore Database
Use this if code is fine but database got corrupted.

```bash
# Find your backup
ls -lh backups/

# Restore it
cp backups/beach_club_stable_20260112_XXXXXX.db instance/beach_club.db
```

---

## Creating New Checkpoints (Before Risky Merges)

**Always run before merging worktrees or branches:**

```bash
# 1. Backup database
mkdir -p backups
cp instance/beach_club.db backups/beach_club_$(date +%Y%m%d_%H%M%S).db

# 2. Commit any uncommitted changes
git add .
git commit -m "chore: checkpoint before merge"

# 3. Create a tag
git tag -a stable-$(date +%Y%m%d-%H%M) -m "Stable checkpoint before merge"

# 4. Create backup branch (optional but recommended)
git branch backup/before-merge-$(date +%Y%m%d)

# 5. List your checkpoints
git tag | grep stable
```

---

## Viewing Available Checkpoints

```bash
# View all stable tags
git tag | grep stable

# View all backup branches
git branch | grep backup

# View database backups
ls -lh backups/

# View details of a specific tag
git show stable-checkpoint-20260112
```

---

## Best Practices

### Before ANY merge:
1. ✅ Create database backup
2. ✅ Commit current changes
3. ✅ Create git tag
4. ✅ Test merge in a separate branch first

### After merge:
1. ✅ Test critical functionality:
   - Login works
   - Map loads
   - Reservations work
   - Configuration pages accessible
2. ✅ Check for 403 permission errors
3. ✅ Verify database integrity

### If something breaks after merge:
1. **Don't panic!**
2. Check `git log` to see what changed
3. Use `git diff stable-checkpoint-20260112` to see differences
4. Revert using one of the options above

---

## Emergency Recovery Commands

```bash
# See what changed since last stable checkpoint
git diff stable-checkpoint-20260112

# View commit history since checkpoint
git log stable-checkpoint-20260112..HEAD --oneline

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes - DANGEROUS!)
git reset --hard HEAD~1

# Restore a single file from checkpoint
git checkout stable-checkpoint-20260112 -- path/to/file.py
```

---

## Database Backup Schedule

**Recommended:**
- Before every merge: ALWAYS
- After major features: RECOMMENDED
- Daily (automated): OPTIONAL

**Automated daily backup (optional):**
```bash
# Add to cron or Task Scheduler
cd /c/Users/catia/programas/PuroBeach/PuroBeach && cp instance/beach_club.db backups/daily_$(date +%Y%m%d).db
```

---

## Previous Checkpoints

### Checkpoint: 2026-01-12 (20:00)
**Tag:** `stable-checkpoint-20260112`
**Commit:** `1e37068`
**Branch:** `backup/stable-20260112`
**Database:** `backups/beach_club_stable_20260112_211948.db`

**Features:**
- All permissions working correctly
- Analytics dashboard functional
- Waitlist system operational
- Hotel guests Excel import (535 guests tested)
- All configuration pages accessible
- Packages and minimum consumption accessible
- Menu structure consolidated

---

## Notes
- Git tags are permanent markers in history
- Backup branches can be deleted after confirmed stability
- Database backups should be kept for at least 30 days
- Always test in a separate environment before deploying to production
