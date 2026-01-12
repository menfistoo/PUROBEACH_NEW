# Audit Log Merge Plan

## What the Audit Log System Adds

**Commit:** `2214ac9` (auto-claude merge of 001-audit-log-system)
**Total changes:** 3,879 lines across 14 files

### New Files
1. `models/audit_log.py` (358 lines) - Audit log data model
2. `utils/audit.py` (405 lines) - Audit utilities and decorators
3. `blueprints/beach/routes/admin/__init__.py` (15 lines) - Admin blueprint init
4. `blueprints/beach/routes/admin/audit_logs.py` (311 lines) - Admin UI routes
5. `templates/beach/admin/audit_logs.html` (614 lines) - Admin UI template
6. `tests/test_audit_log.py` (520 lines) - Unit tests
7. `tests/test_audit_admin.py` (715 lines) - E2E tests
8. `tests/test_customer.py` (364 lines) - Customer tests
9. `tests/test_reservation.py` (390 lines) - Reservation tests

### Modified Files
1. `app.py` (+7 lines) - Register admin blueprint
2. `blueprints/beach/__init__.py` (+4 lines) - Import admin routes
3. `blueprints/beach/routes/api/customers.py` (+62 lines) - Add audit logging
4. `blueprints/beach/routes/api/reservations.py` (+97 lines) - Add audit logging
5. `database/schema.py` (+22 lines) - Add audit_log table
6. `database/seed.py` (1 line changed) - Add audit menu entry

---

## Potential Issues from Last Merge

From the conversation history, the last merge caused:
1. ❌ Empty database (0 bytes)
2. ❌ Missing tables error ("no such table: permissions")
3. ❌ System completely broken

**Root Cause:** The merge likely conflicted with database state or schema changes.

---

## Safe Merge Strategy

### Phase 1: Preparation ✅
**Status:** COMPLETE
- [x] Create checkpoint: `stable-checkpoint-20260112`
- [x] Backup database
- [x] Document current stable state

### Phase 2: Code Analysis (Before Merge)
**Goal:** Understand what conflicts might occur

```bash
# 1. Check if audit log table exists
sqlite3 instance/beach_club.db "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log';"

# 2. Compare database schema
git show 2214ac9:database/schema.py > /tmp/audit_schema.py
diff database/schema.py /tmp/audit_schema.py

# 3. Check for conflicts in modified files
git diff HEAD 2214ac9 -- app.py
git diff HEAD 2214ac9 -- blueprints/beach/__init__.py
git diff HEAD 2214ac9 -- blueprints/beach/routes/api/customers.py
git diff HEAD 2214ac9 -- blueprints/beach/routes/api/reservations.py
```

### Phase 3: Isolated Testing Branch
**Goal:** Test merge without affecting main

```bash
# 1. Create test branch from current stable state
git checkout -b test-audit-merge

# 2. Attempt merge
git merge 2214ac9

# 3. If conflicts occur:
#    - Resolve carefully
#    - Prioritize current code over audit branch
#    - Keep database schema additions only

# 4. After merge, check schema
python -c "from database.schema import init_db; init_db()"

# 5. Test server starts
python app.py

# 6. Test critical functionality:
#    - Login works
#    - Map loads
#    - Reservations work
#    - No permission errors
```

### Phase 4: Incremental File Merge (If Full Merge Fails)
**Goal:** Add audit log files one at a time

```bash
# 1. Start fresh from main
git checkout main

# 2. Create clean branch
git checkout -b audit-log-manual

# 3. Add files incrementally:

# Step 1: Database schema
git checkout 2214ac9 -- database/schema.py
# Test: python -c "from database.schema import init_db; init_db()"

# Step 2: Models
git checkout 2214ac9 -- models/audit_log.py
# Test: python -c "from models.audit_log import create_audit_log"

# Step 3: Utilities
git checkout 2214ac9 -- utils/audit.py
# Test: python -c "from utils.audit import audit_action"

# Step 4: Admin routes
git checkout 2214ac9 -- blueprints/beach/routes/admin/

# Step 5: Template
git checkout 2214ac9 -- templates/beach/admin/audit_logs.html

# Step 6: Integrate into app
# Manually add admin blueprint registration to app.py
# Manually add admin routes import to blueprints/beach/__init__.py

# Step 7: Add audit logging to API endpoints (OPTIONAL - can skip initially)
# git checkout 2214ac9 -- blueprints/beach/routes/api/customers.py
# git checkout 2214ac9 -- blueprints/beach/routes/api/reservations.py

# Test after each step!
```

### Phase 5: Permission Setup
**Goal:** Add audit log permission to database

```python
# After successful merge, run this:
from app import create_app
from database import get_db

app = create_app()
with app.app_context():
    with get_db() as conn:
        cursor = conn.cursor()

        # Get admin parent permission
        admin_parent = cursor.execute('SELECT id FROM permissions WHERE code = ?', ('admin.view',)).fetchone()
        parent_id = admin_parent[0] if admin_parent else None

        # Create audit permission
        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin.audit.view', 'Registro de Auditoría', 'admin', 1, '/beach/admin/audit-logs', parent_id))

        perm_id = cursor.lastrowid

        # Assign to admin role only
        admin_role = cursor.execute('SELECT id FROM roles WHERE name = ?', ('admin',)).fetchone()
        cursor.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (admin_role[0], perm_id))

        conn.commit()
```

### Phase 6: Verification Checklist
After merge, verify:

- [ ] Server starts without errors
- [ ] Database has `audit_log` table
- [ ] Can login
- [ ] Map loads
- [ ] Can create reservation
- [ ] Can view customers
- [ ] Configuration pages accessible
- [ ] New audit log page accessible at `/beach/admin/audit-logs`
- [ ] Audit logs are being created for actions
- [ ] No 403 permission errors

---

## Rollback Plan

If merge fails at any point:

```bash
# 1. Abort merge if in progress
git merge --abort

# 2. Return to stable checkpoint
git checkout main
git reset --hard stable-checkpoint-20260112

# 3. Restore database
cp backups/beach_club_stable_20260112*.db instance/beach_club.db

# 4. Restart server
python app.py
```

---

## Recommended Approach

**Option A: Full Merge in Test Branch** (Fastest if it works)
- Low risk: Uses test branch
- If successful, can merge to main
- If fails, easy to abort

**Option B: Incremental File Merge** (Safest)
- Higher confidence: Test each component
- More time consuming
- Better understanding of what each part does

**Recommendation:** Start with Option A, fall back to Option B if conflicts arise.

---

## Next Steps

1. Run Phase 2 (Code Analysis) to understand potential conflicts
2. Decide between Option A or Option B
3. Execute merge in test branch
4. Verify functionality
5. If successful, merge to main with new checkpoint
