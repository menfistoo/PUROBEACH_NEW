# Advanced Permission Management - Design Document

**Date:** 2026-01-31
**Status:** Approved
**Scope:** Intermediate — CRUD roles, permission matrix, cloning, audit history

---

## Overview

Complete Phase 2 of the permission management system: replace the read-only role detail view with a full permission management UI featuring checkbox matrix, custom role CRUD, role cloning, and permission change auditing.

## Decisions Made

- **Permission UI:** Checkbox matrix grouped by module with columns per action type (View/Create/Edit/Delete/Manage)
- **Cloning:** Dropdown "Basado en..." in role creation modal pre-loads permissions from selected template
- **Audit:** Visible in UI as "Historial" tab in role detail, stored in existing `audit_log` table
- **System roles:** Editable permissions (except admin which is always read-only with all permissions)
- **Admin role:** Matrix shown in read-only mode, all checkboxes marked, with info banner

## Architecture

### Files Modified

| File | Change |
|------|--------|
| `templates/admin/roles.html` | Add "Crear Rol" button, update action column, remove Phase 2 banner |
| `templates/admin/role_detail.html` | Full rewrite: tabbed layout (Permisos/Historial), permission matrix, audit log |
| `blueprints/admin/routes.py` | New routes: role create, edit, delete |
| `models/role.py` | Add bulk_assign_permissions, clone_role_permissions |

### Files Created

| File | Purpose |
|------|---------|
| `static/js/admin/role-permissions.js` | Matrix interaction logic (select row/column, AJAX save) |
| `blueprints/admin/services/role_service.py` | Business logic: validation, cloning, audit logging |

### New Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/admin/roles/create` | Show create role modal/page | `admin.roles.manage` |
| POST | `/admin/roles/create` | Create role (with optional template) | `admin.roles.manage` |
| POST | `/admin/roles/<id>/edit` | Update role name/description | `admin.roles.manage` |
| POST | `/admin/roles/<id>/delete` | Delete custom role | `admin.roles.manage` |
| POST | `/api/roles/<id>/permissions` | AJAX: bulk save permissions | `admin.roles.manage` |
| GET | `/api/roles/<id>/audit-log` | AJAX: paginated audit history | `admin.roles.manage` |

## UI Design

### 1. Roles List (roles.html)

- Add `[+ Crear Rol]` button in header
- Action column rules:
  - **Admin role:** only "Ver" button
  - **System roles (manager, staff, readonly):** "Editar" + "Ver"
  - **Custom roles:** "Editar" + "Ver" + "Eliminar" (disabled if has users)
- Remove "Fase 2" info banner
- Delete action shows confirmation modal

### 2. Role Detail — Permission Matrix (role_detail.html)

Tabbed layout with "Permisos" and "Historial" tabs.

**Permission Matrix structure:**
- Collapsible cards per module group (Beach Operations, Beach Config, Admin)
- Each card has "Seleccionar todos" button
- Table with rows per feature, columns per action type
- Empty cells = permission doesn't exist (not unchecked)
- Column headers clickable to select/deselect all in that column within the module

**Action type mapping from permission codes:**
- `*.view` → Ver
- `*.create` → Crear
- `*.edit` → Editar
- `*.delete` → Eliminar
- `*.manage` → Gestionar
- `*.import` → Importar
- `*.export` → Exportar
- `*.interact` → Interactuar
- `*.change_state` → Cambiar Estado
- `*.merge` → Fusionar

**Module grouping:**
- **Beach - Operaciones:** map, reservations, customers
- **Beach - Configuración:** zones, furniture_types, furniture, pricing, states, characteristics, config
- **Beach - Reportes:** reports, analytics
- **Administración:** users, roles, hotel_guests
- **API:** api access, api admin

**Admin role behavior:** Matrix rendered in read-only mode (disabled checkboxes, all checked) with banner: "El rol Administrador tiene todos los permisos automáticamente"

**Save behavior:** AJAX POST with array of selected permission IDs. Backend computes diff (added/removed) for audit.

### 3. Create Role Modal

Fields:
- **Nombre interno** (slug): auto-generated from display name, editable, `[a-z0-9_-]`, 3-30 chars, unique
- **Nombre visible**: required, 2-50 chars
- **Descripción**: optional text
- **Basado en**: dropdown with "Ninguno" + all active roles (except admin)

Flow:
1. Fill form, optionally select template role
2. Submit creates role in DB
3. If template selected, copies all permissions from template role
4. Redirects to role_detail with pre-loaded permission matrix
5. User adjusts checkboxes and saves

### 4. Edit Role

Same fields as create except:
- No "Basado en" dropdown
- "Nombre interno" is immutable (shown as read-only)
- Only display_name and description are editable

### 5. Audit History Tab

Table columns: Fecha | Usuario | Cambio | Detalle

**Expandable rows** — clicking "Ver" shows:
- Added permissions (green checkmark + permission name and code)
- Removed permissions (red X + permission name and code)

**Audit log storage** — uses existing `audit_log` table:
```sql
INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, created_at)
```

Actions logged:
- `role_created` — details: `{name, display_name, cloned_from?}`
- `role_updated` — details: `{changes: {field: [old, new]}}`
- `role_deleted` — details: `{name, display_name}`
- `permissions_updated` — details: `{added: [{id, code, name}], removed: [{id, code, name}]}`

Loaded via AJAX with pagination (10 per page).

## Protections

1. **Admin role**: read-only permission matrix, cannot be deleted or renamed
2. **System roles**: cannot be deleted, cannot change `name` field
3. **Delete role**: only custom roles with zero active users
4. **All permission changes**: recorded in audit_log with user_id and timestamp
5. **CSRF**: all POST endpoints protected with Flask-WTF tokens
6. **Permission**: all endpoints require `admin.roles.manage`

## No Changes Required

- Database schema (all tables exist)
- Permission decorator system (`@permission_required`)
- Dynamic menu generation (`get_menu_items`)
- Login flow and permission caching
- Existing seeded permissions
