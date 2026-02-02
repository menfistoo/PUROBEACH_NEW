/**
 * Reservation Unified View/Edit Page
 * Handles inline editing, state toggles, preferences, and furniture navigation
 */

class ReservationUnified {
    constructor() {
        this.reservationId = window.RESERVATION_DATA?.id;
        this.reservationDate = window.RESERVATION_DATA?.date;
        this.csrfToken = window.RESERVATION_DATA?.csrfToken;
        this.pendingChanges = {};
        this.hasUnsavedChanges = false;

        this.init();
    }

    init() {
        this.setupEditableFields();
        this.setupStateToggles();
        this.setupPreferences();
        this.setupFurnitureNavigation();
        this.setupSaveButton();
        this.setupBeforeUnload();
        this.checkForMessages();
    }

    checkForMessages() {
        const params = new URLSearchParams(window.location.search);

        // Check if returning from furniture selection
        if (params.get('furniture_updated') === '1') {
            this.showToast('Mobiliario actualizado exitosamente', 'success');

            // Clean up URL
            const url = new URL(window.location);
            url.searchParams.delete('furniture_updated');
            window.history.replaceState({}, '', url.toString());
        }
    }

    // =============================================================================
    // EDITABLE FIELDS
    // =============================================================================

    setupEditableFields() {
        document.querySelectorAll('.editable-field').forEach(field => {
            const editBtn = field.querySelector('.edit-btn');
            const displayValue = field.querySelector('.display-value');
            const editInput = field.querySelector('.edit-input');
            const fieldName = field.dataset.field;

            if (!editBtn || !editInput) return;

            editBtn.addEventListener('click', () => {
                if (field.classList.contains('editing')) {
                    // Save the field
                    this.saveField(fieldName, field);
                } else {
                    // Enter edit mode
                    field.classList.add('editing');
                    if (editInput.tagName === 'INPUT' || editInput.tagName === 'TEXTAREA') {
                        editInput.style.display = 'block';
                        editInput.focus();
                    } else {
                        editInput.style.display = 'block';
                    }
                    if (displayValue) displayValue.style.display = 'none';
                }
            });

            // Handle Enter key for single-line inputs
            if (editInput.tagName === 'INPUT') {
                editInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.saveField(fieldName, field);
                    }
                    if (e.key === 'Escape') {
                        this.cancelEdit(field);
                    }
                });
            }

            // Special handling for paid checkbox
            if (fieldName === 'paid') {
                const paidSwitch = field.querySelector('#paidSwitch');
                const ticketInput = field.querySelector('.ticket-input');
                if (paidSwitch && ticketInput) {
                    paidSwitch.addEventListener('change', () => {
                        ticketInput.style.display = paidSwitch.checked ? 'block' : 'none';
                    });
                }
            }
        });
    }

    async saveField(fieldName, fieldElement) {
        const editInput = fieldElement.querySelector('.edit-input');
        const displayValue = fieldElement.querySelector('.display-value');
        let value;

        if (fieldName === 'paid') {
            const paidSwitch = fieldElement.querySelector('#paidSwitch');
            const ticketInput = fieldElement.querySelector('.ticket-input input');
            value = {
                paid: paidSwitch?.checked ? 1 : 0,
                payment_ticket_number: ticketInput?.value || null
            };
        } else if (editInput.tagName === 'INPUT' || editInput.tagName === 'TEXTAREA') {
            value = editInput.value;
        }

        // Store pending change
        if (fieldName === 'paid') {
            this.pendingChanges.paid = value.paid;
            this.pendingChanges.payment_ticket_number = value.payment_ticket_number;
        } else {
            this.pendingChanges[fieldName] = value;
        }

        // Update display immediately
        this.updateFieldDisplay(fieldName, fieldElement, value);

        // Exit edit mode
        fieldElement.classList.remove('editing');
        if (displayValue) displayValue.style.display = '';
        if (editInput.tagName === 'INPUT' || editInput.tagName === 'TEXTAREA') {
            editInput.style.display = 'none';
        } else {
            editInput.style.display = 'none';
        }

        // Mark as having changes
        this.markAsChanged(fieldElement);
        this.showSaveButton();
    }

    updateFieldDisplay(fieldName, fieldElement, value) {
        const displayValue = fieldElement.querySelector('.display-value');
        if (!displayValue) return;

        if (fieldName === 'num_people') {
            displayValue.innerHTML = `<span class="badge bg-secondary fs-6">${value}</span>`;
        } else if (fieldName === 'observations') {
            displayValue.innerHTML = value
                ? `<p class="mb-0">${this.escapeHtml(value)}</p>`
                : `<p class="text-muted mb-0">Sin observaciones</p>`;
        } else if (fieldName === 'paid') {
            if (value.paid) {
                let html = `<span class="badge bg-success fs-6"><i class="fas fa-check-circle"></i> PAGADO</span>`;
                if (value.payment_ticket_number) {
                    html += `<div class="mt-1"><small class="text-muted"><i class="fas fa-receipt"></i> ${this.escapeHtml(value.payment_ticket_number)}</small></div>`;
                }
                displayValue.innerHTML = html;
            } else {
                displayValue.innerHTML = `<span class="badge bg-warning text-dark fs-6"><i class="fas fa-clock"></i> PENDIENTE</span>`;
            }
        }
    }

    cancelEdit(fieldElement) {
        const displayValue = fieldElement.querySelector('.display-value');
        const editInput = fieldElement.querySelector('.edit-input');

        fieldElement.classList.remove('editing');
        if (displayValue) displayValue.style.display = '';
        if (editInput) editInput.style.display = 'none';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // =============================================================================
    // STATE TOGGLES
    // =============================================================================

    setupStateToggles() {
        document.querySelectorAll('.state-toggle').forEach(btn => {
            btn.addEventListener('click', () => this.toggleState(btn));
        });
    }

    async toggleState(button) {
        const stateName = button.dataset.state;
        const stateColor = button.dataset.color;
        const isActive = button.classList.contains('active');
        const action = isActive ? 'remove' : 'add';

        button.disabled = true;

        try {
            const response = await fetch(`/beach/api/reservations/${this.reservationId}/toggle-state`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ state: stateName, action })
            });

            const data = await response.json();

            if (data.success) {
                // Toggle visual state
                if (action === 'add') {
                    button.classList.add('active');
                    button.style.backgroundColor = stateColor;
                    button.style.borderColor = stateColor;
                    button.style.color = 'white';
                } else {
                    button.classList.remove('active');
                    button.style.backgroundColor = '';
                    button.style.borderColor = stateColor;
                    button.style.color = stateColor;
                }

                // Update header badges
                this.updateHeaderStates();

                this.showToast('Estado actualizado', 'success');
            } else {
                this.showToast(data.error || 'Error al actualizar estado', 'error');
            }
        } catch (err) {
            console.error('Error toggling state:', err);
            this.showToast('Error de conexión', 'error');
        } finally {
            button.disabled = false;
        }
    }

    updateHeaderStates() {
        // Collect active states
        const activeStates = [];
        document.querySelectorAll('.state-toggle.active').forEach(btn => {
            activeStates.push({
                name: btn.dataset.state,
                color: btn.dataset.color
            });
        });

        // Update header badges
        const headerBadges = document.querySelector('.unified-header .d-flex.flex-wrap.gap-2');
        if (headerBadges) {
            if (activeStates.length > 0) {
                headerBadges.innerHTML = activeStates.map(s =>
                    `<span class="badge fs-6" style="background-color: ${s.color}">${s.name}</span>`
                ).join('');
            } else {
                headerBadges.innerHTML = '<span class="badge bg-secondary fs-6">Sin estado</span>';
            }
        }
    }

    // =============================================================================
    // PREFERENCES
    // =============================================================================

    setupPreferences() {
        // Listen to checkbox changes directly
        document.querySelectorAll('.preference-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const item = checkbox.closest('.preference-item');
                if (item) {
                    item.classList.toggle('selected', checkbox.checked);
                }
                this.updatePreferences();
            });
        });
    }

    updatePreferences() {
        const selectedPrefs = [];
        document.querySelectorAll('.preference-item input:checked').forEach(input => {
            selectedPrefs.push(input.value);
        });
        this.pendingChanges.preferences = selectedPrefs.join(',');
        this.showSaveButton();

        // Mark the preferences card as changed
        const prefsCard = document.querySelector('.preference-item')?.closest('.unified-card');
        if (prefsCard) this.markAsChanged(prefsCard);
    }

    // =============================================================================
    // FURNITURE NAVIGATION
    // =============================================================================

    setupFurnitureNavigation() {
        const changeFurnitureBtn = document.getElementById('changeFurnitureBtn');
        const assignFurnitureBtn = document.getElementById('assignFurnitureBtn');

        [changeFurnitureBtn, assignFurnitureBtn].forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => this.navigateToMapForFurniture());
            }
        });
    }

    navigateToMapForFurniture() {
        // Check for unsaved changes first
        if (Object.keys(this.pendingChanges).length > 0) {
            if (!confirm('Hay cambios sin guardar. ¿Desea continuar sin guardarlos?')) {
                return;
            }
        }

        // Build return URL
        const returnUrl = encodeURIComponent(window.location.pathname);

        // Navigate to map in furniture selection mode
        const mapUrl = `/beach/map?mode=furniture_select&reservation_id=${this.reservationId}&date=${this.reservationDate}&return_url=${returnUrl}`;
        window.location.href = mapUrl;
    }

    // =============================================================================
    // SAVE FUNCTIONALITY
    // =============================================================================

    setupSaveButton() {
        const saveBtn = document.getElementById('saveAllBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveAllChanges());
        }
    }

    showSaveButton() {
        const saveBtn = document.getElementById('saveAllBtn');
        if (saveBtn && Object.keys(this.pendingChanges).length > 0) {
            saveBtn.style.display = 'inline-block';
            this.hasUnsavedChanges = true;
        }
    }

    hideSaveButton() {
        const saveBtn = document.getElementById('saveAllBtn');
        if (saveBtn) {
            saveBtn.style.display = 'none';
        }
        this.hasUnsavedChanges = false;
    }

    markAsChanged(element) {
        const card = element.closest('.unified-card');
        if (card) {
            card.classList.add('has-changes');
        }
    }

    clearChangedMarkers() {
        document.querySelectorAll('.unified-card.has-changes').forEach(card => {
            card.classList.remove('has-changes');
        });
    }

    async saveAllChanges() {
        if (Object.keys(this.pendingChanges).length === 0) {
            this.showToast('No hay cambios pendientes', 'info');
            return;
        }

        const saveBtn = document.getElementById('saveAllBtn');
        if (window.PuroBeach) {
            window.PuroBeach.setButtonLoading(saveBtn, true, 'Guardando...');
        }

        try {
            const response = await fetch(`/beach/api/map/reservations/${this.reservationId}/update`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(this.pendingChanges)
            });

            const data = await response.json();

            if (data.success) {
                this.pendingChanges = {};
                this.clearChangedMarkers();
                this.hideSaveButton();
                this.showToast('Cambios guardados exitosamente', 'success');
            } else {
                this.showToast(data.error || 'Error al guardar cambios', 'error');
            }
        } catch (err) {
            console.error('Error saving changes:', err);
            this.showToast('Error de conexión', 'error');
        } finally {
            if (window.PuroBeach) {
                window.PuroBeach.setButtonLoading(saveBtn, false);
            }
        }
    }

    // =============================================================================
    // UTILITIES
    // =============================================================================

    setupBeforeUnload() {
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges && Object.keys(this.pendingChanges).length > 0) {
                e.preventDefault();
                e.returnValue = 'Hay cambios sin guardar. ¿Está seguro de salir?';
            }
        });
    }

    showToast(message, type = 'info') {
        // Create toast container if not exists
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast show align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        container.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);

        // Close button handler
        toast.querySelector('.btn-close').addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.reservationUnified = new ReservationUnified();
});
