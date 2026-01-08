/**
 * Waitlist Form Handler
 * Form submission and validation logic
 */

import { convertHotelGuestToCustomer, createEntry, updateEntry } from './api.js';
import { showToast } from './utils.js';
import { dispatchCountUpdate } from './actions.js';

/**
 * Submit the waitlist entry form (create or update)
 * @param {Object} context - Manager context
 */
export async function submitEntry(context) {
    const { elements, state, options, csrfToken, callbacks } = context;

    // Validate customer selection
    const customerId = elements.customerIdInput?.value;
    const hotelGuestId = elements.hotelGuestIdInput?.value;

    // For external guests, get name and phone from the simple entry fields
    const externoName = document.getElementById('waitlistExternoName')?.value?.trim();
    const externoPhone = document.getElementById('waitlistExternoPhone')?.value?.trim();

    if (state.customerType === 'interno' && !hotelGuestId && !customerId) {
        showToast('Selecciona un huesped', 'warning');
        return;
    }

    if (state.customerType === 'externo' && !externoName) {
        showToast('Ingresa el nombre del cliente', 'warning');
        return;
    }

    if (state.customerType === 'externo' && !externoPhone) {
        showToast('Ingresa el telefono del cliente', 'warning');
        return;
    }

    // Validate date
    const requestedDate = elements.dateInput?.value;
    if (!requestedDate) {
        showToast('La fecha es requerida', 'warning');
        return;
    }

    // Validate reservation type
    const reservationType = document.querySelector('input[name="reservationType"]:checked')?.value || 'consumo_minimo';
    if (reservationType === 'paquete' && !elements.packageSelect?.value) {
        showToast('Selecciona un paquete', 'warning');
        return;
    }

    // Show loading
    setSubmitButtonLoading(elements, true);

    try {
        // If interno (hotel guest), we need to convert to customer first
        let finalCustomerId = customerId;

        if (state.customerType === 'interno' && hotelGuestId) {
            // Convert hotel guest to customer
            const convertResult = await convertHotelGuestToCustomer(
                options.apiBaseUrl,
                csrfToken,
                parseInt(hotelGuestId)
            );

            if (!convertResult.success) {
                throw new Error(convertResult.error || 'Error al convertir huesped');
            }
            finalCustomerId = convertResult.customer.id;
        }

        // Build payload
        const payload = buildPayload(elements, state, finalCustomerId, externoName, externoPhone, requestedDate, reservationType);

        // Determine if this is an edit or create
        const isEdit = !!state.editingEntryId;
        let result;

        if (isEdit) {
            result = await updateEntry(options.apiBaseUrl, csrfToken, state.editingEntryId, payload);
        } else {
            result = await createEntry(options.apiBaseUrl, csrfToken, payload);
        }

        if (result.success) {
            const message = isEdit
                ? 'Entrada actualizada'
                : (result.message || 'Agregado a lista de espera');
            showToast(message, 'success');
            context.closeAddModal();
            await context.refresh();
            dispatchCountUpdate(context);
        } else {
            const errorMsg = isEdit
                ? (result.error || 'Error al actualizar entrada')
                : (result.error || 'Error al crear entrada');
            showToast(errorMsg, 'error');
        }
    } catch (error) {
        console.error('WaitlistManager: Error submitting entry', error);
        showToast(error.message || 'Error de conexion', 'error');
    } finally {
        setSubmitButtonLoading(elements, false);
    }
}

/**
 * Build the payload object for creating/updating an entry
 * @param {Object} elements - DOM elements
 * @param {Object} state - Manager state
 * @param {number|string} finalCustomerId - Customer ID (if interno)
 * @param {string} externoName - External customer name
 * @param {string} externoPhone - External customer phone
 * @param {string} requestedDate - Requested date
 * @param {string} reservationType - Reservation type
 * @returns {Object} Payload object
 */
function buildPayload(elements, state, finalCustomerId, externoName, externoPhone, requestedDate, reservationType) {
    const payload = {
        requested_date: requestedDate,
        num_people: parseInt(elements.numPeopleInput?.value) || 2,
        preferred_zone_id: elements.zonePreferenceSelect?.value ? parseInt(elements.zonePreferenceSelect.value) : null,
        preferred_furniture_type_id: elements.furnitureTypeSelect?.value ? parseInt(elements.furnitureTypeSelect.value) : null,
        time_preference: elements.timePreferenceSelect?.value || null,
        reservation_type: reservationType,
        package_id: reservationType === 'paquete' ? parseInt(elements.packageSelect?.value) : null,
        notes: elements.notesInput?.value?.trim() || null
    };

    // Add customer info based on type
    if (state.customerType === 'interno' && finalCustomerId) {
        payload.customer_id = parseInt(finalCustomerId);
    } else if (state.customerType === 'externo') {
        // External guests use name+phone, customer created on convert
        payload.external_name = externoName;
        payload.external_phone = externoPhone;
    }

    return payload;
}

/**
 * Set submit button loading state
 * @param {Object} elements - DOM elements
 * @param {boolean} loading - Whether button should show loading
 */
function setSubmitButtonLoading(elements, loading) {
    if (!elements.modalSaveBtn) return;

    elements.modalSaveBtn.disabled = loading;
    const saveText = elements.modalSaveBtn.querySelector('.save-text');
    const saveLoading = elements.modalSaveBtn.querySelector('.save-loading');

    if (loading) {
        if (saveText) saveText.style.display = 'none';
        if (saveLoading) saveLoading.style.display = 'flex';
    } else {
        if (saveText) saveText.style.display = 'inline-flex';
        if (saveLoading) saveLoading.style.display = 'none';
    }
}

/**
 * Validate form fields
 * @param {Object} elements - DOM elements
 * @param {Object} state - Manager state
 * @returns {Object} Validation result { valid: boolean, error: string }
 */
export function validateForm(elements, state) {
    const customerId = elements.customerIdInput?.value;
    const hotelGuestId = elements.hotelGuestIdInput?.value;
    const externoName = document.getElementById('waitlistExternoName')?.value?.trim();
    const externoPhone = document.getElementById('waitlistExternoPhone')?.value?.trim();
    const requestedDate = elements.dateInput?.value;
    const reservationType = document.querySelector('input[name="reservationType"]:checked')?.value || 'consumo_minimo';

    if (state.customerType === 'interno' && !hotelGuestId && !customerId) {
        return { valid: false, error: 'Selecciona un huesped' };
    }

    if (state.customerType === 'externo' && !externoName) {
        return { valid: false, error: 'Ingresa el nombre del cliente' };
    }

    if (state.customerType === 'externo' && !externoPhone) {
        return { valid: false, error: 'Ingresa el telefono del cliente' };
    }

    if (!requestedDate) {
        return { valid: false, error: 'La fecha es requerida' };
    }

    if (reservationType === 'paquete' && !elements.packageSelect?.value) {
        return { valid: false, error: 'Selecciona un paquete' };
    }

    return { valid: true, error: null };
}
