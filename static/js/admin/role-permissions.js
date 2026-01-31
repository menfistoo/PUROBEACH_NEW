/**
 * Role permission matrix interactions.
 * Handles checkbox selection, bulk save via AJAX, and audit log loading.
 */

let roleId = null;
let canEdit = false;

function initRolePermissions(id, editable) {
    roleId = id;
    canEdit = editable;

    if (canEdit) {
        initSelectAll();
        initColumnSelect();
        initSaveButton();
    }

    initAuditLog();
}

// ============================================================
// Select All / Column Selection
// ============================================================

function initSelectAll() {
    document.querySelectorAll('.btn-select-all').forEach(btn => {
        btn.addEventListener('click', function () {
            const group = this.dataset.group;
            const checkboxes = document.querySelectorAll(
                `.perm-checkbox[data-group="${group}"]:not(:disabled)`
            );

            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !allChecked);

            this.textContent = allChecked ? 'Seleccionar todos' : 'Deseleccionar todos';
        });
    });
}

function initColumnSelect() {
    document.querySelectorAll('.btn-select-column').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const group = this.dataset.group;
            const action = this.dataset.action;
            const checkboxes = document.querySelectorAll(
                `.perm-checkbox[data-group="${group}"][data-action="${action}"]:not(:disabled)`
            );

            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !allChecked);
        });
    });
}

// ============================================================
// Save Permissions (AJAX)
// ============================================================

function initSaveButton() {
    const btn = document.getElementById('savePermissions');
    if (!btn) return;

    btn.addEventListener('click', async function () {
        const checkboxes = document.querySelectorAll('.perm-checkbox:checked');
        const permissionIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
            const response = await fetch(`/admin/api/roles/${roleId}/permissions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ permission_ids: permissionIds })
            });

            const data = await response.json();

            if (data.success) {
                const msg = `Permisos actualizados: ${data.added} añadidos, ${data.removed} eliminados`;
                showToast(msg, 'success');
            } else {
                showToast(data.error || 'Error al guardar permisos', 'error');
            }
        } catch (err) {
            showToast('Error de conexión al guardar permisos', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Guardar Permisos';
        }
    });
}

function showToast(message, type) {
    const container = document.querySelector('.main-content');
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';

    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible fade show mx-3 mt-2`;
    alert.innerHTML = `
        <i class="fas ${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const content = container.querySelector('.container-fluid') || container;
    content.insertBefore(alert, content.firstChild);

    setTimeout(() => alert.remove(), 5000);
}

// ============================================================
// Audit Log
// ============================================================

function initAuditLog() {
    const historyTab = document.getElementById('history-tab');
    if (!historyTab) return;

    let loaded = false;
    historyTab.addEventListener('shown.bs.tab', function () {
        if (!loaded) {
            loadAuditLog(1);
            loaded = true;
        }
    });
}

async function loadAuditLog(page) {
    const container = document.getElementById('auditLogContainer');
    const pagination = document.getElementById('auditLogPagination');

    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Cargando...</div>';

    try {
        const response = await fetch(`/admin/api/roles/${roleId}/audit-log?page=${page}`);
        const data = await response.json();

        if (!data.entries || data.entries.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-4"><i class="fas fa-info-circle"></i> Sin registros de cambios</div>';
            pagination.innerHTML = '';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-sm table-hover">';
        html += '<thead><tr><th>Fecha</th><th>Usuario</th><th>Cambio</th><th></th></tr></thead><tbody>';

        data.entries.forEach((entry, idx) => {
            const date = new Date(entry.created_at).toLocaleString('es-ES', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
            });
            const user = entry.full_name || entry.username || 'Sistema';
            const summary = formatAuditSummary(entry);

            html += `<tr>`;
            html += `<td><small>${date}</small></td>`;
            html += `<td>${user}</td>`;
            html += `<td>${summary}</td>`;
            html += `<td>`;
            if (entry.action === 'permissions_updated' && entry.changes) {
                html += `<button class="btn btn-sm btn-outline-secondary" onclick="toggleDetail(${idx})"><i class="fas fa-eye"></i> Ver</button>`;
            }
            html += `</td></tr>`;

            // Detail row (hidden by default)
            if (entry.action === 'permissions_updated' && entry.changes) {
                html += `<tr id="detail-${idx}" style="display:none;"><td colspan="4" class="bg-light">`;
                const changes = entry.changes;
                if (changes.added && changes.added.length > 0) {
                    changes.added.forEach(p => {
                        html += `<div class="text-success"><i class="fas fa-check"></i> Añadido: ${p.name} <small class="text-muted">(${p.code})</small></div>`;
                    });
                }
                if (changes.removed && changes.removed.length > 0) {
                    changes.removed.forEach(p => {
                        html += `<div class="text-danger"><i class="fas fa-times"></i> Quitado: ${p.name} <small class="text-muted">(${p.code})</small></div>`;
                    });
                }
                html += `</td></tr>`;
            }
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;

        // Pagination
        if (data.pages > 1) {
            let pagHtml = '<nav><ul class="pagination pagination-sm">';
            for (let i = 1; i <= data.pages; i++) {
                const active = i === data.page ? 'active' : '';
                pagHtml += `<li class="page-item ${active}"><a class="page-link" href="#" onclick="loadAuditLog(${i}); return false;">${i}</a></li>`;
            }
            pagHtml += '</ul></nav>';
            pagination.innerHTML = pagHtml;
        } else {
            pagination.innerHTML = '';
        }

    } catch (err) {
        container.innerHTML = '<div class="alert alert-danger">Error al cargar historial</div>';
    }
}

function toggleDetail(idx) {
    const row = document.getElementById(`detail-${idx}`);
    if (row) {
        row.style.display = row.style.display === 'none' ? '' : 'none';
    }
}

function formatAuditSummary(entry) {
    switch (entry.action) {
        case 'role_created': {
            const clone = entry.changes?.cloned_from;
            return 'Rol creado' + (clone ? ` (basado en ${clone})` : '');
        }
        case 'role_updated': {
            const changes = entry.changes?.changes || {};
            const fields = Object.keys(changes).map(f => {
                const labels = { display_name: 'nombre', description: 'descripción' };
                return labels[f] || f;
            });
            return `Rol editado: ${fields.join(', ')}`;
        }
        case 'role_deleted':
            return 'Rol eliminado';
        case 'permissions_updated': {
            const added = entry.changes?.added?.length || 0;
            const removed = entry.changes?.removed?.length || 0;
            const parts = [];
            if (added) parts.push(`+${added} permiso${added > 1 ? 's' : ''}`);
            if (removed) parts.push(`-${removed} permiso${removed > 1 ? 's' : ''}`);
            return parts.join(', ') || 'Sin cambios';
        }
        default:
            return entry.action;
    }
}
