/**
 * CustomerSearch - Shared customer search component
 *
 * Provides unified customer search functionality for reservation forms and map.
 * Supports both beach club customers and hotel guests with VIP indicators.
 *
 * Usage:
 *   const search = new CustomerSearch({
 *     inputElement: document.getElementById('search-input'),
 *     resultsContainer: document.getElementById('results'),
 *     onSelect: (customer) => { ... },
 *     apiUrl: '/beach/api/customers/search',
 *     csrfToken: '...'
 *   });
 */

function _escapeHtml(str) {
    if (!str) return '';
    const s = String(str);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class CustomerSearch {
    constructor(options = {}) {
        // Required elements
        this.inputElement = options.inputElement;
        this.resultsContainer = options.resultsContainer;

        // Callbacks
        this.onSelect = options.onSelect || (() => {});
        this.onHotelGuestSelect = options.onHotelGuestSelect || null;
        this.onCustomerCreated = options.onCustomerCreated || null;
        this.onShowCreateForm = options.onShowCreateForm || null;

        // Configuration
        this.apiUrl = options.apiUrl || '/beach/api/customers/search';
        this.createApiUrl = options.createApiUrl || '/beach/api/customers/create';
        this.csrfToken = options.csrfToken || '';
        this.minChars = options.minChars || 2;
        this.debounceMs = options.debounceMs || 300;
        this.showCreateLink = options.showCreateLink !== false;
        this.showInlineCreate = options.showInlineCreate !== false; // New: inline creation form
        this.createCustomerUrl = options.createCustomerUrl || '/beach/customers/create';
        this.compact = options.compact || false; // Compact mode for map

        // State
        this.searchTimeout = null;
        this.searchCache = [];
        this.selectedCustomer = null;
        this.selectedSource = 'customer';
        this.isCreatingCustomer = false;
        this.lastSearchQuery = '';

        // Initialize
        this._init();
    }

    _init() {
        if (!this.inputElement || !this.resultsContainer) {
            console.error('CustomerSearch: inputElement and resultsContainer are required');
            return;
        }

        // Build results HTML structure
        this._buildResultsStructure();

        // Bind events
        this.inputElement.addEventListener('input', (e) => this._onInput(e));
        this.resultsContainer.addEventListener('click', (e) => this._onResultClick(e));

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.customer-search-wrapper') &&
                !this.resultsContainer.contains(e.target)) {
                this.hideResults();
            }
        });
    }

    _buildResultsStructure() {
        this.resultsContainer.innerHTML = `
            <div class="cs-beach-club-section cs-section" style="display: none;">
                <div class="cs-section-header">
                    <i class="fas fa-umbrella-beach"></i> Clientes Beach Club
                </div>
                <div class="cs-beach-club-list cs-list"></div>
            </div>
            <div class="cs-hotel-guests-section cs-section" style="display: none;">
                <div class="cs-section-header">
                    <i class="fas fa-hotel"></i> Huespedes Hotel
                </div>
                <div class="cs-hotel-guests-list cs-list"></div>
            </div>
            <div class="cs-no-results" style="display: none;">
                <i class="fas fa-search"></i>
                <span>No se encontraron resultados</span>
            </div>
            ${this.showInlineCreate ? `
            <div class="cs-create-option" style="display: none;">
                <div class="cs-divider"><span>o</span></div>
                <button type="button" class="cs-btn-show-create" id="csShowCreateBtn">
                    <i class="fas fa-plus-circle"></i> Crear nuevo cliente externo
                </button>
            </div>
            ` : ''}
            ${this.showCreateLink && !this.showInlineCreate ? `
            <a href="${this.createCustomerUrl}" class="cs-create-link">
                <i class="fas fa-plus"></i> Crear nuevo cliente
            </a>
            ` : ''}
        `;

        // Cache DOM references
        this.beachSection = this.resultsContainer.querySelector('.cs-beach-club-section');
        this.beachList = this.resultsContainer.querySelector('.cs-beach-club-list');
        this.hotelSection = this.resultsContainer.querySelector('.cs-hotel-guests-section');
        this.hotelList = this.resultsContainer.querySelector('.cs-hotel-guests-list');
        this.noResults = this.resultsContainer.querySelector('.cs-no-results');
        this.createOption = this.resultsContainer.querySelector('.cs-create-option');
        this.showCreateBtn = this.resultsContainer.querySelector('.cs-btn-show-create');

        // Bind create button click
        if (this.showInlineCreate && this.showCreateBtn) {
            this.showCreateBtn.addEventListener('click', () => this._onShowCreateClick());
        }
    }

    _onInput(e) {
        const query = e.target.value.trim();

        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < this.minChars) {
            this.hideResults();
            return;
        }

        this.searchTimeout = setTimeout(() => this._search(query), this.debounceMs);
    }

    async _search(query) {
        try {
            this.lastSearchQuery = query;
            const response = await fetch(`${this.apiUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            this.searchCache = data.customers || [];
            this._displayResults(this.searchCache);

        } catch (error) {
            console.error('CustomerSearch: Error searching', error);
            this.hideResults();
        }
    }

    _displayResults(customers) {
        const beachCustomers = customers.filter(c => c.source === 'customer');
        const hotelGuests = customers.filter(c => c.source === 'hotel_guest');

        // Clear lists
        this.beachList.innerHTML = '';
        this.hotelList.innerHTML = '';

        // Beach club customers
        if (beachCustomers.length > 0) {
            this.beachSection.style.display = 'block';
            beachCustomers.forEach(c => {
                this.beachList.innerHTML += this._renderCustomerItem(c);
            });
        } else {
            this.beachSection.style.display = 'none';
        }

        // Hotel guests
        if (hotelGuests.length > 0) {
            this.hotelSection.style.display = 'block';
            hotelGuests.forEach(g => {
                this.hotelList.innerHTML += this._renderHotelGuestItem(g);
            });
        } else {
            this.hotelSection.style.display = 'none';
        }

        // No results - show create button if enabled
        if (beachCustomers.length === 0 && hotelGuests.length === 0) {
            this.noResults.style.display = 'flex';
            if (this.showInlineCreate && this.createOption) {
                this.createOption.style.display = 'block';
            }
        } else {
            this.noResults.style.display = 'none';
            if (this.createOption) {
                this.createOption.style.display = 'none';
            }
        }

        this.showResults();
    }

    /**
     * Handle click on "Create new customer" button
     */
    _onShowCreateClick() {
        // Hide search results
        this.hideResults();

        // Pre-fill name from search query
        let prefillData = {};
        const query = this.lastSearchQuery;
        if (query && !/^\d+$/.test(query) && !query.includes('@')) {
            const nameParts = query.split(' ');
            prefillData.first_name = nameParts[0] || '';
            prefillData.last_name = nameParts.slice(1).join(' ') || '';
        }

        // Dispatch event for parent component to handle
        if (this.onShowCreateForm) {
            this.onShowCreateForm(prefillData);
        } else {
            // Fallback: dispatch custom event
            document.dispatchEvent(new CustomEvent('customerSearch:showCreateForm', {
                detail: prefillData
            }));
        }
    }

    _renderCustomerItem(c) {
        const displayName = _escapeHtml(c.display_name ||
            `${c.first_name || ''} ${c.last_name || ''}`.trim());
        const isVip = c.vip_status || c.vip_code;
        const roomInfo = c.room_number ? `Hab. ${_escapeHtml(c.room_number)}` : '';
        const typeInfo = c.customer_type === 'interno' ?
            `<i class="fas fa-door-open"></i> ${roomInfo}` :
            '<i class="fas fa-user"></i> Externo';
        const phone = c.phone ? ` - ${_escapeHtml(c.phone)}` : '';

        if (this.compact) {
            return `
                <div class="cs-item" data-id="${c.id}" data-source="customer">
                    <div class="cs-item-name">
                        ${displayName}
                        ${isVip ? '<span class="cs-badge cs-vip">VIP</span>' : ''}
                    </div>
                    <div class="cs-item-details">${roomInfo || _escapeHtml(c.phone) || _escapeHtml(c.email) || ''}</div>
                </div>
            `;
        }

        return `
            <div class="cs-item" data-id="${c.id}" data-source="customer">
                <div class="cs-avatar ${isVip ? 'vip' : ''}">
                    <i class="fas ${isVip ? 'fa-star' : 'fa-user'}"></i>
                </div>
                <div class="cs-info">
                    <div class="cs-name">
                        ${displayName}
                        ${isVip ? '<span class="cs-badge cs-vip">VIP</span>' : ''}
                    </div>
                    <div class="cs-details">${typeInfo}${phone}</div>
                </div>
                <div class="cs-action"><i class="fas fa-chevron-right"></i></div>
            </div>
        `;
    }

    _renderHotelGuestItem(g) {
        const isVip = g.vip_code;
        const guestName = _escapeHtml(g.guest_name);
        const roomNumber = _escapeHtml(g.room_number);
        const checkinBadge = g.is_checkin_today ?
            '<span class="cs-badge cs-checkin">Check-in</span>' : '';
        const checkoutBadge = g.is_checkout_today ?
            '<span class="cs-badge cs-checkout">Check-out</span>' : '';
        const mainGuestBadge = g.is_main_guest ?
            '<span class="cs-badge cs-main">Principal</span>' : '';

        if (this.compact) {
            return `
                <div class="cs-item" data-id="${g.id}" data-source="hotel_guest">
                    <div class="cs-item-name">
                        ${guestName}
                        ${isVip ? '<span class="cs-badge cs-vip">VIP</span>' : ''}
                        ${checkinBadge}${checkoutBadge}
                    </div>
                    <div class="cs-item-details">
                        <i class="fas fa-hotel"></i> Hab. ${roomNumber}
                    </div>
                </div>
            `;
        }

        return `
            <div class="cs-item" data-id="${g.id}" data-source="hotel_guest">
                <div class="cs-avatar hotel">
                    <i class="fas fa-hotel"></i>
                </div>
                <div class="cs-info">
                    <div class="cs-name">
                        ${guestName}
                        ${mainGuestBadge}
                        ${isVip ? '<span class="cs-badge cs-vip">VIP</span>' : ''}
                        ${checkinBadge}${checkoutBadge}
                    </div>
                    <div class="cs-details">
                        <i class="fas fa-door-open"></i> Hab. ${roomNumber}
                        ${g.arrival_date && g.departure_date ?
                            ` - <i class="fas fa-calendar"></i> ${this._formatDate(g.arrival_date)} - ${this._formatDate(g.departure_date)}` : ''}
                        ${g.booking_reference ? ` - #${_escapeHtml(g.booking_reference)}` : ''}
                    </div>
                </div>
                <div class="cs-action"><i class="fas fa-chevron-right"></i></div>
            </div>
        `;
    }

    _formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
    }

    _onResultClick(e) {
        const item = e.target.closest('.cs-item');
        if (!item) return;

        const id = parseInt(item.dataset.id);
        const source = item.dataset.source;

        const customer = this.searchCache.find(c => c.id === id && c.source === source);
        if (!customer) return;

        this.selectedCustomer = customer;
        this.selectedSource = source;

        // Get display name
        const displayName = customer.display_name || customer.guest_name ||
            `${customer.first_name || ''} ${customer.last_name || ''}`.trim();

        // Update input
        this.inputElement.value = displayName;
        this.hideResults();

        // Call appropriate callback
        if (source === 'hotel_guest' && this.onHotelGuestSelect) {
            this.onHotelGuestSelect(customer);
        } else {
            this.onSelect(customer);
        }
    }

    showResults() {
        this.resultsContainer.classList.add('show');
    }

    hideResults() {
        this.resultsContainer.classList.remove('show');
    }

    clear() {
        this.inputElement.value = '';
        this.selectedCustomer = null;
        this.selectedSource = 'customer';
        this.searchCache = [];
        this.hideResults();
    }

    getSelectedCustomer() {
        return this.selectedCustomer;
    }

    getSelectedSource() {
        return this.selectedSource;
    }

    getSelectedId() {
        return this.selectedCustomer?.id || null;
    }

    isHotelGuest() {
        return this.selectedSource === 'hotel_guest';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CustomerSearch;
}
