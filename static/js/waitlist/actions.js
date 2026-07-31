/**
 * Waitlist Actions
 * Entry actions: convert, edit, status changes
 */

import { updateEntryStatus, markEntryAsConverted } from './api.js';
import { showToast } from './utils.js';

/**
 * Handle entry action button click
 * @param {Object} context - Manager context (state, callbacks, elements, etc.)
 * @param {number} entryId - Entry ID
 * @param {string} action - Action type (convert, edit, contacted, declined, no_answer)
 */
export async function handleEntryAction(context, entryId, action) {
    if (action === 'convert') {
        handleConvert(context, entryId);
        return;
    }

    if (action === 'edit') {
        handleEdit(context, entryId);
        return;
    }

    // Status change actions
    const statusMap = {
        'contacted': 'contacted',
        'declined': 'declined',
        'no_answer': 'no_answer'
    };

    const newStatus = statusMap[action];
    if (!newStatus) return;

    try {
        const result = await updateEntryStatus(context.options.apiBaseUrl, context.csrfToken, entryId, newStatus);

        if (result.success) {
            showToast('Estado actualizado', 'success');
            await context.refresh();
            dispatchCountUpdate(context);
        } else {
            showToast(result.error || 'Error al actualizar', 'error');
        }
    } catch (error) {
        console.error('WaitlistManager: Error updating status', error);
        showToast('Error de conexion', 'error');
    }
}

/**
 * Handle convert action - close panel and trigger conversion
 * @param {Object} context - Manager context
 * @param {number} entryId - Entry ID
 */
export function handleConvert(context, entryId) {
    // Find the entry
    const entry = context.state.entries.find(e => e.id === entryId);
    if (!entry) return;

    // Close waitlist panel
    context.close();

    // Call conversion callback
    if (context.callbacks.onConvert) {
        context.callbacks.onConvert(entry);
    } else {
        // Dispatch event for other components to handle
        document.dispatchEvent(new CustomEvent('waitlist:convert', {
            detail: { entry, entryId }
        }));
    }
}

/**
 * Handle edit action - open modal in edit mode
 * @param {Object} context - Manager context
 * @param {number} entryId - Entry ID
 */
export function handleEdit(context, entryId) {
    const entry = context.state.entries.find(e => e.id === entryId);
    if (!entry) return;

    const { elements, state } = context;

    // Reset form first (clears editingEntryId and resets title/button)
    context.resetForm();

    // Then store entry being edited (after reset)
    state.editingEntryId = entryId;

    // Set customer type (this also updates the UI)
    context.setCustomerType(entry.customer_type || 'interno');

    // Pre-fill customer info
    if (entry.customer_id) {
        // Customer already exists (converted hotel guest or existing external)
        state.selectedCustomerId = entry.customer_id;
        if (elements.customerIdInput) elements.customerIdInput.value = entry.customer_id;

        // Display customer name in appropriate section
        if (entry.customer_type === 'interno') {
            // For internal, show in selected guest display
            const guestDisplay = document.getElementById('waitlistSelectedGuest');
            const guestName = document.getElementById('waitlistGuestName');
            const guestRoom = document.getElementById('waitlistGuestRoom');
            const searchWrapper = document.querySelector('#waitlistRoomSearchGroup .room-search-wrapper');

            if (guestDisplay && guestName) {
                guestName.textContent = entry.customer_name || 'Huésped';
                if (guestRoom && entry.room_number) {
                    guestRoom.textContent = `Hab. ${entry.room_number}`;
                }
                guestDisplay.style.display = 'flex';
                if (searchWrapper) searchWrapper.style.display = 'none';
            }
        } else {
            // For external with customer_id, show name in externo fields
            const externoNameInput = document.getElementById('waitlistExternoName');
            const externoPhoneInput = document.getElementById('waitlistExternoPhone');
            if (externoNameInput) externoNameInput.value = entry.customer_name || '';
            if (externoPhoneInput) externoPhoneInput.value = entry.phone || '';
        }
    } else if (entry.external_name) {
        // External customer (not yet converted to customer record)
        const externoNameInput = document.getElementById('waitlistExternoName');
        const externoPhoneInput = document.getElementById('waitlistExternoPhone');
        if (externoNameInput) externoNameInput.value = entry.external_name;
        if (externoPhoneInput) externoPhoneInput.value = entry.external_phone || '';
    }

    // Pre-fill date
    if (elements.dateInput && entry.requested_date) {
        // Normalize to ISO format
        let isoDate = entry.requested_date;
        if (!/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) {
            try {
                const d = new Date(isoDate);
                if (!isNaN(d.getTime())) {
                    isoDate = d.toISOString().split('T')[0];
                }
            } catch (e) { /* ignore */ }
        }
        elements.dateInput.value = isoDate;
    }

    // Pre-fill num_people
    if (elements.numPeopleInput && entry.num_people) {
        elements.numPeopleInput.value = entry.num_people;
    }

    // Pre-fill preferences
    if (elements.zonePreferenceSelect && entry.preferred_zone_id) {
        elements.zonePreferenceSelect.value = entry.preferred_zone_id;
    }
    if (elements.furnitureTypeSelect && entry.preferred_furniture_type_id) {
        elements.furnitureTypeSelect.value = entry.preferred_furniture_type_id;
    }
    if (elements.timePreferenceSelect && entry.time_preference) {
        elements.timePreferenceSelect.value = entry.time_preference;
    }

    // Pre-fill reservation type
    if (entry.reservation_type) {
        const typeRadio = document.querySelector(`input[name="reservationType"][value="${entry.reservation_type}"]`);
        if (typeRadio) {
            typeRadio.checked = true;
            context.onReservationTypeChange(); // Show/hide package group based on selection
        }
    }

    // Pre-fill package
    if (elements.packageSelect && entry.package_id) {
        elements.packageSelect.value = entry.package_id;
    }

    // Pre-fill notes
    if (elements.notesInput && entry.notes) {
        elements.notesInput.value = entry.notes;
    }

    // Update modal title for edit mode
    const modalTitle = document.getElementById('waitlistModalTitle');
    if (modalTitle) {
        modalTitle.innerHTML = '<i class="fas fa-edit me-2"></i> Editar en Lista de Espera';
    }

    // Update submit button text (keep save-text/save-loading structure)
    const saveText = elements.modalSaveBtn?.querySelector('.save-text');
    if (saveText) {
        saveText.innerHTML = '<i class="fas fa-save me-1"></i> Guardar Cambios';
    }

    // Open modal
    context.openAddModal();
}

/**
 * Mark an entry as converted after reservation created
 * @param {Object} context - Manager context
 * @param {number} entryId - Waitlist entry ID
 * @param {number} reservationId - Created reservation ID
 */
export async function markAsConverted(context, entryId, reservationId) {
    try {
        const result = await markEntryAsConverted(
            context.options.apiBaseUrl,
            context.csrfToken,
            entryId,
            reservationId
        );

        if (result.success) {
            showToast('Entrada convertida a reserva', 'success');
            dispatchCountUpdate(context);
        } else {
            showToast(result.error || 'Error al convertir', 'error');
        }
    } catch (error) {
        console.error('WaitlistManager: Error marking as converted', error);
    }
}

/**
 * Dispatch count update event and callback
 * @param {Object} context - Manager context
 */
export function dispatchCountUpdate(context) {
    const count = context.state.entries.filter(e => e.status === 'waiting').length;

    // Dispatch event for badge updates
    document.dispatchEvent(new CustomEvent('waitlist:countUpdate', {
        detail: { count }
    }));

    // Call callback if provided
    if (context.callbacks.onCountUpdate) {
        context.callbacks.onCountUpdate(count);
    }
}
