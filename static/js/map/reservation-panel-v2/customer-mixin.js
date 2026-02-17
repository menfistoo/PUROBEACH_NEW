/**
 * ReservationPanel Customer Mixin
 *
 * Handles all customer-related functionality:
 * - Rendering customer information section
 * - Customer search functionality
 * - Changing customer on a reservation
 *
 * @module reservation-panel-v2/customer-mixin
 */

import { escapeHtml, formatDateShort } from './utils.js';

// =============================================================================
// CUSTOMER MIXIN
// =============================================================================

/**
 * Customer mixin factory function
 * Adds customer display and search functionality to the panel
 *
 * @param {class} Base - Base class to extend
 * @returns {class} Extended class with customer functionality
 *
 * @example
 * class ReservationPanel extends CustomerMixin(StateMixin(BasePanel)) {
 *     // Panel implementation
 * }
 */
export const CustomerMixin = (Base) => class extends Base {

    // =========================================================================
    // CUSTOMER SECTION RENDERING
    // =========================================================================

    /**
     * Render customer section with compact layout
     * Displays customer name, badges, hotel info, and contact details
     *
     * @param {Object|null} customer - Customer data object
     * @param {string} customer.full_name - Full name (optional)
     * @param {string} customer.first_name - First name
     * @param {string} customer.last_name - Last name
     * @param {string} customer.room_number - Hotel room number
     * @param {boolean} customer.vip_status - VIP status flag
     * @param {string} customer.customer_type - 'interno' or 'externo'
     * @param {string} customer.arrival_date - Hotel check-in date
     * @param {string} customer.departure_date - Hotel check-out date
     * @param {string} customer.booking_reference - Hotel booking reference
     * @param {string} customer.phone - Contact phone number
     */
    renderCustomerSection(customer) {
        if (!customer) {
            this._renderNoCustomer();
            return;
        }

        this._renderCustomerName(customer);
        this._renderRoomBadge(customer);
        this._renderVipBadge(customer);
        this._renderHotelInfo(customer);
        this._renderContactInfo(customer);
    }

    /**
     * Render empty customer state
     * @private
     */
    _renderNoCustomer() {
        if (this.customerName) {
            this.customerName.textContent = 'Cliente no encontrado';
            this.customerName.onclick = null;
            this.customerName.removeAttribute('title');
        }
        if (this.customerRoomBadge) {
            this.customerRoomBadge.style.display = 'none';
        }
        if (this.customerVipBadge) {
            this.customerVipBadge.style.display = 'none';
        }
        if (this.customerHotelInfo) {
            this.customerHotelInfo.style.display = 'none';
        }
        if (this.customerContact) {
            this.customerContact.style.display = 'none';
        }
    }

    /**
     * Render customer name as clickable button to open customer details
     * Uses window.open for reliable new-tab navigation from a button element
     * @private
     * @param {Object} customer - Customer data
     */
    _renderCustomerName(customer) {
        if (!this.customerName) return;

        const displayName = escapeHtml(
            customer.full_name ||
            `${customer.first_name || ''} ${customer.last_name || ''}`.trim() ||
            'Sin nombre'
        );

        if (customer.id) {
            const customerUrl = `/beach/customers/${customer.id}`;
            this.customerName.innerHTML = `${displayName} <i class="fas fa-external-link-alt"></i>`;
            this.customerName.title = 'Ver detalles del cliente';
            this.customerName.onclick = () => {
                window.open(customerUrl, '_blank', 'noopener,noreferrer');
            };
        } else {
            this.customerName.textContent = displayName;
            this.customerName.onclick = null;
            this.customerName.removeAttribute('title');
        }
    }

    /**
     * Render room badge for hotel guests
     * @private
     * @param {Object} customer - Customer data
     */
    _renderRoomBadge(customer) {
        if (!this.customerRoomBadge || !this.customerRoom) return;

        if (customer.room_number) {
            this.customerRoom.textContent = customer.room_number;
            this.customerRoomBadge.style.display = 'inline-flex';

            // Show room change indicator if room changed
            if (this.roomChangeIndicator) {
                const reservation = this.state.data?.reservation;
                if (reservation?.room_changed && reservation?.original_room) {
                    this.roomChangeIndicator.style.display = 'inline';
                    this.roomChangeIndicator.title = `Cambio de hab. ${reservation.original_room}`;
                    // Reinitialize tooltip (dispose existing first to prevent memory leaks)
                    if (typeof bootstrap !== 'undefined') {
                        const existingTooltip = bootstrap.Tooltip.getInstance(this.roomChangeIndicator);
                        if (existingTooltip) existingTooltip.dispose();
                        new bootstrap.Tooltip(this.roomChangeIndicator);
                    }
                } else {
                    this.roomChangeIndicator.style.display = 'none';
                    // Dispose tooltip when hiding
                    if (typeof bootstrap !== 'undefined') {
                        const existingTooltip = bootstrap.Tooltip.getInstance(this.roomChangeIndicator);
                        if (existingTooltip) existingTooltip.dispose();
                    }
                }
            }
        } else {
            this.customerRoomBadge.style.display = 'none';
            if (this.roomChangeIndicator) {
                this.roomChangeIndicator.style.display = 'none';
                // Dispose tooltip when hiding
                if (typeof bootstrap !== 'undefined') {
                    const existingTooltip = bootstrap.Tooltip.getInstance(this.roomChangeIndicator);
                    if (existingTooltip) existingTooltip.dispose();
                }
            }
        }
    }

    /**
     * Render VIP status badge
     * @private
     * @param {Object} customer - Customer data
     */
    _renderVipBadge(customer) {
        if (!this.customerVipBadge) return;

        this.customerVipBadge.style.display = customer.vip_status
            ? 'inline-flex'
            : 'none';
    }

    /**
     * Render hotel information (check-in, check-out, booking reference)
     * Only displayed for internal customers with hotel dates
     * @private
     * @param {Object} customer - Customer data
     */
    _renderHotelInfo(customer) {
        if (!this.customerHotelInfo) return;

        const isHotelGuest = customer.customer_type === 'interno' &&
            (customer.arrival_date || customer.departure_date);

        if (!isHotelGuest) {
            this.customerHotelInfo.style.display = 'none';
            return;
        }

        this.customerHotelInfo.style.display = 'flex';

        // Check-in date
        if (this.customerCheckin) {
            this.customerCheckin.textContent = customer.arrival_date
                ? formatDateShort(customer.arrival_date)
                : '-';
        }

        // Check-out date
        if (this.customerCheckout) {
            this.customerCheckout.textContent = customer.departure_date
                ? formatDateShort(customer.departure_date)
                : '-';
        }

        // Booking reference
        if (this.customerBookingRef && this.customerBookingItem) {
            if (customer.booking_reference) {
                this.customerBookingRef.textContent = customer.booking_reference;
                this.customerBookingItem.style.display = 'inline-flex';
            } else {
                this.customerBookingItem.style.display = 'none';
            }
        }
    }

    /**
     * Render contact information (phone) for external customers
     * @private
     * @param {Object} customer - Customer data
     */
    _renderContactInfo(customer) {
        if (!this.customerContact || !this.customerPhone) return;

        const isHotelGuest = customer.customer_type === 'interno' &&
            (customer.arrival_date || customer.departure_date);

        if (!isHotelGuest && customer.phone) {
            this.customerPhone.innerHTML = `<i class="fas fa-phone"></i> ${escapeHtml(customer.phone)}`;
            this.customerContact.style.display = 'block';
        } else {
            this.customerContact.style.display = 'none';
        }
    }

    // =========================================================================
    // CUSTOMER EDIT MODE UI
    // =========================================================================

    /**
     * Enter customer edit mode based on customer type
     * - Interno: Show room guest dropdown
     * - Externo: Show customer search
     */
    enterCustomerEditMode() {
        const customer = this.state.data?.customer;
        if (!customer) return;

        // Hide the change button in edit mode
        if (this.customerChangeBtn) {
            this.customerChangeBtn.style.display = 'none';
        }

        if (customer.customer_type === 'interno' && customer.room_number) {
            // Show room guest dropdown for interno
            this.showRoomGuestSelector(customer.room_number);
        } else if (customer.customer_type === 'externo') {
            // Show search for externo
            this.showCustomerSearch();
        }
    }

    /**
     * Exit customer edit mode - hide all edit UIs
     */
    exitCustomerEditMode() {
        this.hideCustomerSearch();
        this.hideRoomGuestSelector();

        // Show the change button again (but only if needed)
        if (this.customerChangeBtn) {
            this.customerChangeBtn.style.display = 'none'; // Keep hidden, we don't use it anymore
        }
    }

    /**
     * Show room guest selector for interno customers
     * Fetches and populates guests from the same room
     *
     * @param {string} roomNumber - The room number to fetch guests for
     */
    async showRoomGuestSelector(roomNumber) {
        if (!this.roomGuestSelector || !this.roomGuestSelect) return;

        try {
            // Fetch room guests
            const response = await fetch(
                `${this.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(roomNumber)}`
            );
            const data = await response.json();

            const guests = data.guests || [];

            // Only show if there are multiple guests
            if (guests.length <= 1) {
                this.roomGuestSelector.style.display = 'none';
                return;
            }

            // Populate dropdown - match by name since hotel guests don't have customer_id
            const currentCustomerName = this.state.data?.customer?.full_name?.toUpperCase() || '';
            let options = '';

            guests.forEach(guest => {
                // API returns guest_name as a single field
                const fullName = guest.guest_name || `${guest.first_name || ''} ${guest.last_name || ''}`.trim();
                // Match by uppercase name comparison
                const isSelected = fullName.toUpperCase() === currentCustomerName;
                options += `<option value="${guest.id}" ${isSelected ? 'selected' : ''}>${escapeHtml(fullName)}</option>`;
            });

            this.roomGuestSelect.innerHTML = options;
            this.roomGuestSelector.style.display = 'block';

        } catch (error) {
            console.error('Error fetching room guests:', error);
            this.roomGuestSelector.style.display = 'none';
        }
    }

    /**
     * Hide room guest selector
     */
    hideRoomGuestSelector() {
        if (this.roomGuestSelector) {
            this.roomGuestSelector.style.display = 'none';
        }
    }

    /**
     * Handle room guest selection from dropdown
     * @param {Event} event - Change event from select element
     */
    async handleRoomGuestChange(event) {
        const hotelGuestId = event.target.value;
        if (!hotelGuestId) return;

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-customer`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({
                        customer_id: null,
                        hotel_guest_id: parseInt(hotelGuestId)
                    })
                }
            );

            const result = await response.json();

            if (result.success) {
                this._handleCustomerChangeSuccess(result);
            } else {
                throw new Error(result.error || 'Error al cambiar huésped');
            }

        } catch (error) {
            console.error('Guest change error:', error);
            this.showToast(error.message, 'error');
        }
    }

    /**
     * Show customer search input and focus it
     * Called for externo customers in edit mode
     */
    showCustomerSearch() {
        if (this.customerSearchWrapper) {
            this.customerSearchWrapper.style.display = 'block';
            this.customerSearchInput?.focus();
        }
    }

    /**
     * Hide customer search input and clear results
     * Called after selecting a customer or canceling search
     */
    hideCustomerSearch() {
        if (this.customerSearchWrapper) {
            this.customerSearchWrapper.style.display = 'none';
            if (this.customerSearchInput) {
                this.customerSearchInput.value = '';
            }
            if (this.customerSearchResults) {
                this.customerSearchResults.style.display = 'none';
            }
        }
    }

    // =========================================================================
    // CUSTOMER SEARCH LOGIC
    // =========================================================================

    /**
     * Handle customer search input with debouncing
     * Triggers search after 300ms of no typing
     *
     * @param {Event} event - Input event from search field
     */
    handleCustomerSearch(event) {
        const query = event.target.value.trim();

        // Clear previous debounce timer
        if (this.customerSearchTimer) {
            clearTimeout(this.customerSearchTimer);
        }

        // Require minimum 2 characters
        if (query.length < 2) {
            if (this.customerSearchResults) {
                this.customerSearchResults.style.display = 'none';
            }
            return;
        }

        // Debounce search to avoid excessive API calls
        this.customerSearchTimer = setTimeout(() => {
            this.searchCustomers(query);
        }, 300);
    }

    /**
     * Search customers via API
     * Searches both beach club customers and hotel guests
     *
     * @param {string} query - Search query (name, room number, etc.)
     * @returns {Promise<void>}
     */
    async searchCustomers(query) {
        // Cancel previous in-flight request
        if (this._searchAbortController) {
            this._searchAbortController.abort();
        }
        this._searchAbortController = new AbortController();

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}`,
                { signal: this._searchAbortController.signal }
            );

            if (!response.ok) {
                throw new Error('Error en la busqueda');
            }

            const result = await response.json();
            this.renderCustomerSearchResults(result);

        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Customer search error:', error);
        }
    }

    /**
     * Render customer search results dropdown
     * Shows both beach club customers and hotel guests
     *
     * @param {Object} result - API response with search results
     * @param {Array} result.customers - Beach club customers
     * @param {Array} result.hotel_guests - Hotel guests (not yet customers)
     */
    renderCustomerSearchResults(result) {
        const customers = result.customers || [];
        let hotelGuests = result.hotel_guests || [];

        // Filter out hotel guests that are already beach customers (by room + name)
        if (customers.length > 0 && hotelGuests.length > 0) {
            const existingKeys = new Set();
            customers.forEach(c => {
                if (c.customer_type === 'interno' && c.room_number) {
                    existingKeys.add(`${c.room_number}|${(c.first_name || '').toLowerCase()}`);
                }
            });
            hotelGuests = hotelGuests.filter(g => {
                const key = `${g.room_number}|${(g.first_name || '').toLowerCase()}`;
                return !existingKeys.has(key);
            });
        }

        // Show "no results" message if empty
        if (customers.length === 0 && hotelGuests.length === 0) {
            this.customerSearchResults.innerHTML = `
                <div class="customer-search-item text-muted">
                    No se encontraron resultados
                </div>
            `;
            this.customerSearchResults.style.display = 'block';
            return;
        }

        let html = '';

        // Render beach club customers
        customers.forEach(c => {
            html += this._renderCustomerSearchItem(c);
        });

        // Render hotel guests (that aren't already beach customers)
        hotelGuests.forEach(g => {
            html += this._renderHotelGuestSearchItem(g);
        });

        this.customerSearchResults.innerHTML = html;
        this.customerSearchResults.style.display = 'block';

        // Attach click handlers to results
        this._attachSearchResultHandlers();
    }

    /**
     * Render a beach club customer search result item
     * @private
     * @param {Object} customer - Customer data
     * @returns {string} HTML string for the result item
     */
    _renderCustomerSearchItem(customer) {
        const typeLabel = customer.customer_type === 'interno'
            ? `Hab. ${escapeHtml(customer.room_number || '?')}`
            : 'Externo';
        const vipIcon = customer.vip_status
            ? '<i class="fas fa-star text-warning ms-1"></i>'
            : '';

        return `
            <div class="customer-search-item" data-customer-id="${customer.id}">
                <div class="fw-semibold">${escapeHtml(customer.first_name)} ${escapeHtml(customer.last_name)}</div>
                <div class="small text-muted">
                    ${typeLabel}
                    ${vipIcon}
                </div>
            </div>
        `;
    }

    /**
     * Render a hotel guest search result item
     * @private
     * @param {Object} guest - Hotel guest data
     * @returns {string} HTML string for the result item
     */
    _renderHotelGuestSearchItem(guest) {
        return `
            <div class="customer-search-item" data-hotel-guest-id="${guest.id}">
                <div class="fw-semibold">${escapeHtml(guest.first_name)} ${escapeHtml(guest.last_name)}</div>
                <div class="small text-muted">
                    Huesped - Hab. ${escapeHtml(guest.room_number)}
                </div>
            </div>
        `;
    }

    /**
     * Attach click handlers to search result items
     * @private
     */
    _attachSearchResultHandlers() {
        this.customerSearchResults
            .querySelectorAll('.customer-search-item')
            .forEach(item => {
                item.addEventListener('click', () => this.selectCustomer(item));
            });
    }

    // =========================================================================
    // CUSTOMER SELECTION
    // =========================================================================

    /**
     * Select a customer from search results and update the reservation
     *
     * @param {HTMLElement} item - Clicked search result item
     * @returns {Promise<void>}
     */
    async selectCustomer(item) {
        const customerId = item.dataset.customerId;
        const hotelGuestId = item.dataset.hotelGuestId;

        if (!customerId && !hotelGuestId) return;

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-customer`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({
                        customer_id: customerId ? parseInt(customerId) : null,
                        hotel_guest_id: hotelGuestId ? parseInt(hotelGuestId) : null
                    })
                }
            );

            const result = await response.json();

            if (result.success) {
                this._handleCustomerChangeSuccess(result);
            } else {
                throw new Error(result.error || 'Error al cambiar cliente');
            }

        } catch (error) {
            console.error('Customer change error:', error);
            this.showToast(error.message, 'error');
        }
    }

    /**
     * Handle successful customer change
     * @private
     * @param {Object} result - API response with new customer data
     */
    _handleCustomerChangeSuccess(result) {
        // Update local data
        if (this.state.data) {
            this.state.data.customer = result.customer;
        }

        // Re-render customer section with new data
        this.renderCustomerSection(result.customer);

        // Recalculate pricing (customer type affects pricing)
        if (typeof this.calculateAndUpdatePricing === 'function') {
            this.calculateAndUpdatePricing();
        }

        // Hide search UI
        this.hideCustomerSearch();

        // Notify parent/external components via callback
        if (this.options.onCustomerChange) {
            this.options.onCustomerChange(this.state.reservationId, result.customer);
        }

        // Show success message
        this.showToast('Cliente actualizado', 'success');
    }
};
