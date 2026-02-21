/**
 * Waitlist Modal
 * Modal open/close/reset functionality
 */

import { getTodayDate } from './utils.js';
import { loadPackages } from './api.js';

/**
 * Open the add entry modal
 * @param {Object} context - Manager context
 */
export function openAddModal(context) {
    const { elements, state } = context;
    if (!elements.modal) return;

    // Only reset form if not in edit mode (edit mode pre-fills before calling this)
    if (!state.editingEntryId) {
        resetForm(context);

        // Set default date to current date
        if (elements.dateInput) {
            elements.dateInput.value = state.currentDate;
            elements.dateInput.min = getTodayDate();
        }
    } else {
        // In edit mode, just set min date
        if (elements.dateInput) {
            elements.dateInput.min = getTodayDate();
        }
    }

    // Show modal
    elements.modal.style.display = 'flex';
}

/**
 * Close the add entry modal
 * @param {Object} context - Manager context
 */
export function closeAddModal(context) {
    const { elements } = context;
    if (!elements.modal) return;
    elements.modal.style.display = 'none';
}

/**
 * Reset the form to default state
 * @param {Object} context - Manager context
 */
export function resetForm(context) {
    const { elements, state } = context;

    // Clear editing state
    state.editingEntryId = null;

    // Reset customer type to interno
    setCustomerType(context, 'interno');

    // Clear selections
    clearSelectedGuest(context);
    clearSelectedCustomer(context);

    // Reset form fields
    if (elements.roomSearchInput) elements.roomSearchInput.value = '';
    if (elements.customerSearchInput) elements.customerSearchInput.value = '';
    if (elements.numPeopleInput) elements.numPeopleInput.value = '2';
    if (elements.timePreferenceSelect) elements.timePreferenceSelect.value = '';
    if (elements.zonePreferenceSelect) elements.zonePreferenceSelect.value = '';
    if (elements.furnitureTypeSelect) elements.furnitureTypeSelect.value = '';
    if (elements.notesInput) elements.notesInput.value = '';
    if (elements.packageSelect) elements.packageSelect.value = '';

    // Reset reservation type - 'incluido' for interno by default
    const defaultRadio = document.querySelector('input[name="reservationType"][value="incluido"]');
    if (defaultRadio) defaultRadio.checked = true;
    if (elements.packageGroup) elements.packageGroup.style.display = 'none';

    // Reset external guest name/phone fields
    const externoNameInput = document.getElementById('waitlistExternoName');
    const externoPhoneInput = document.getElementById('waitlistExternoPhone');
    if (externoNameInput) externoNameInput.value = '';
    if (externoPhoneInput) externoPhoneInput.value = '';

    // Hide search results
    if (elements.roomResults) elements.roomResults.classList.remove('show');
    if (elements.customerResults) elements.customerResults.classList.remove('show');

    // Reset modal title and button text to defaults
    const modalTitle = document.getElementById('waitlistModalTitle');
    if (modalTitle) {
        modalTitle.innerHTML = '<i class="fas fa-user-plus me-2"></i> Anadir a Lista de Espera';
    }
    const saveText = elements.modalSaveBtn?.querySelector('.save-text');
    if (saveText) {
        saveText.innerHTML = '<i class="fas fa-check me-1"></i> Anadir';
    }
}

/**
 * Set customer type (interno/externo)
 * @param {Object} context - Manager context
 * @param {string} type - Customer type ('interno' or 'externo')
 */
export function setCustomerType(context, type) {
    const { elements, state } = context;
    state.customerType = type;

    if (elements.customerTypeInput) {
        elements.customerTypeInput.value = type;
    }

    // Update toggle buttons
    if (type === 'interno') {
        elements.typeInterno?.classList.add('active');
        elements.typeExterno?.classList.remove('active');
        if (elements.roomSearchGroup) elements.roomSearchGroup.style.display = 'block';
        if (elements.customerSearchGroup) elements.customerSearchGroup.style.display = 'none';
        // Set default reservation type to 'incluido' for internal guests
        const incluidoRadio = document.querySelector('input[name="reservationType"][value="incluido"]');
        if (incluidoRadio) incluidoRadio.checked = true;
    } else {
        elements.typeInterno?.classList.remove('active');
        elements.typeExterno?.classList.add('active');
        if (elements.roomSearchGroup) elements.roomSearchGroup.style.display = 'none';
        if (elements.customerSearchGroup) elements.customerSearchGroup.style.display = 'block';
        // Set default reservation type to 'consumo_minimo' for external guests
        const consumoRadio = document.querySelector('input[name="reservationType"][value="consumo_minimo"]');
        if (consumoRadio) consumoRadio.checked = true;
    }

    // Clear selections when switching
    clearSelectedGuest(context);
    clearSelectedCustomer(context);
}

/**
 * Handle reservation type change (show/hide package group)
 * @param {Object} context - Manager context
 */
export async function onReservationTypeChange(context) {
    const { elements, state, options, csrfToken } = context;
    const selected = document.querySelector('input[name="reservationType"]:checked');
    if (!selected) return;

    if (selected.value === 'paquete') {
        if (elements.packageGroup) elements.packageGroup.style.display = 'block';
        // Load packages
        try {
            const packages = await loadPackages(options.apiBaseUrl);
            if (packages && packages.length > 0) {
                state.packages = packages;
                // Populate dropdown
                if (elements.packageSelect) {
                    elements.packageSelect.innerHTML = '<option value="">Seleccionar paquete...</option>';
                    packages.forEach(pkg => {
                        const option = document.createElement('option');
                        option.value = pkg.id;
                        option.textContent = `${pkg.package_name} - ${pkg.base_price}`;
                        elements.packageSelect.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading packages', error);
        }
    } else {
        if (elements.packageGroup) elements.packageGroup.style.display = 'none';
    }
}

/**
 * Clear selected hotel guest
 * @param {Object} context - Manager context
 */
export function clearSelectedGuest(context) {
    const { elements, state } = context;
    state.selectedHotelGuestId = null;
    if (elements.hotelGuestIdInput) elements.hotelGuestIdInput.value = '';
    if (elements.customerIdInput) elements.customerIdInput.value = '';
    if (elements.selectedGuestEl) elements.selectedGuestEl.style.display = 'none';

    // Show the search wrapper and input
    const searchWrapper = document.querySelector('#waitlistRoomSearchGroup .room-search-wrapper');
    if (searchWrapper) searchWrapper.style.display = 'block';
    if (elements.roomSearchInput) {
        elements.roomSearchInput.style.display = 'block';
        elements.roomSearchInput.value = '';
    }
}

/**
 * Clear selected customer
 * @param {Object} context - Manager context
 */
export function clearSelectedCustomer(context) {
    const { elements, state } = context;
    state.selectedCustomerId = null;
    if (elements.customerIdInput) elements.customerIdInput.value = '';
    if (elements.selectedCustomerEl) elements.selectedCustomerEl.style.display = 'none';
    if (elements.customerSearchInput) {
        elements.customerSearchInput.style.display = 'block';
        elements.customerSearchInput.value = '';
    }
}

/**
 * Select a hotel guest from search results
 * @param {Object} context - Manager context
 * @param {HTMLElement} item - Selected item element
 */
export function selectGuest(context, item) {
    const { elements, state } = context;
    const guestId = item.dataset.guestId;
    const guestName = item.dataset.guestName;
    const roomNumber = item.dataset.room;
    const phone = item.dataset.phone || '';

    // Update state
    state.selectedHotelGuestId = guestId;
    state.selectedGuestPhone = phone;

    // Update hidden fields
    if (elements.hotelGuestIdInput) elements.hotelGuestIdInput.value = guestId;

    // Show selected guest with phone
    if (elements.selectedGuestEl) {
        elements.selectedGuestEl.style.display = 'flex';
        if (elements.guestNameEl) elements.guestNameEl.textContent = guestName;
        if (elements.guestRoomEl) {
            const escapeHtml = (str) => {
                if (!str) return '';
                const div = document.createElement('div');
                div.textContent = str;
                return div.innerHTML;
            };
            elements.guestRoomEl.innerHTML = `Hab. ${roomNumber}${phone ? ` <span class="guest-phone"><i class="fas fa-phone"></i> ${escapeHtml(phone)}</span>` : ''}`;
        }
    }

    // Hide search
    if (elements.roomSearchInput) elements.roomSearchInput.style.display = 'none';
    if (elements.roomResults) elements.roomResults.classList.remove('show');
}

/**
 * Select a customer from search results
 * @param {Object} context - Manager context
 * @param {HTMLElement} item - Selected item element
 */
export function selectCustomer(context, item) {
    const { elements, state } = context;
    const customerId = item.dataset.customerId;
    const customerName = item.dataset.customerName;
    const phone = item.dataset.phone;

    // Update state
    state.selectedCustomerId = customerId;

    // Update hidden fields
    if (elements.customerIdInput) elements.customerIdInput.value = customerId;

    // Show selected customer
    if (elements.selectedCustomerEl) {
        elements.selectedCustomerEl.style.display = 'flex';
        if (elements.customerNameEl) elements.customerNameEl.textContent = customerName;
        if (elements.customerPhoneEl) elements.customerPhoneEl.textContent = phone || '-';
    }

    // Hide search
    if (elements.customerSearchInput) elements.customerSearchInput.style.display = 'none';
    if (elements.customerResults) elements.customerResults.classList.remove('show');
}

/**
 * Navigate to create customer page
 */
export function showCreateCustomer() {
    // Navigate to customer creation page with return URL
    const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/beach/customers/create?type=externo&return_url=${returnUrl}`;
}
