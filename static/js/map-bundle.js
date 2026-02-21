// =============================================================================
// MAP BUNDLE - Concatenated non-module JS for /beach/map page
// Source files preserved individually for maintainability
// =============================================================================

// --- customer-search.js ---
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


// --- date-picker.js ---
/**
 * DatePicker - Shared multi-day date picker component
 *
 * Provides a calendar-based date picker with multi-day selection support.
 * Used by both the reservation form and the map quick reservation modal.
 *
 * Usage:
 *   const picker = new DatePicker({
 *       container: document.getElementById('my-container'),
 *       onDateChange: (dates) => { console.log(dates); },
 *       initialDates: ['2025-01-15']
 *   });
 */

class DatePicker {
    constructor(options = {}) {
        // Required elements
        this.container = options.container;

        // Callbacks
        this.onDateChange = options.onDateChange || (() => {});

        // Configuration
        this.initialDates = options.initialDates || [];
        this.minDate = options.minDate || null;

        // Occupancy configuration
        this.fetchOccupancy = options.fetchOccupancy !== false; // Default true
        this.occupancyApiUrl = options.occupancyApiUrl || '/beach/api/reservations/availability-map';

        // Spanish month and day names
        this.monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        this.dayNames = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];

        // State
        this.selectedDates = new Set(this.initialDates);
        this.calendarMonth = new Date().getMonth();
        this.calendarYear = new Date().getFullYear();
        this.calendarOpen = false;
        this.calendarInteracting = false;

        // Occupancy state
        this.occupancyData = {};       // {date: {total, available, occupied, occupancy_rate}}
        this.occupancyLoading = false;
        this.occupancyLoadedMonth = null; // Track which month is loaded

        // Initialize if container is provided
        if (this.container) {
            this._init();
        }
    }

    _init() {
        // Build the date picker structure
        this._buildStructure();

        // Set initial month/year based on initial dates or today
        if (this.initialDates.length > 0) {
            const firstDate = new Date(this.initialDates[0] + 'T12:00:00');
            this.calendarMonth = firstDate.getMonth();
            this.calendarYear = firstDate.getFullYear();
        }

        // Update preview text
        this._updatePreviewText();

        // Close calendar on outside click
        document.addEventListener('click', (e) => {
            if (this.calendarOpen && !this.calendarInteracting &&
                !e.target.closest('.dp-container')) {
                this.toggleCalendar(false);
            }
        });
    }

    _buildStructure() {
        this.container.innerHTML = `
            <div class="dp-container">
                <div class="dp-collapsed">
                    <div class="dp-preview">
                        <i class="fas fa-calendar-alt text-primary me-2"></i>
                        <span class="dp-preview-text">Seleccionar fechas...</span>
                    </div>
                    <i class="fas fa-chevron-down text-muted dp-chevron"></i>
                </div>
                <div class="dp-expanded" style="display:none;">
                    <div class="dp-calendar"></div>
                    <div class="dp-footer">
                        <div class="dp-selected-tags"></div>
                        <small class="text-muted mt-2 d-block">
                            <span class="dp-count">0</span> dias seleccionados
                        </small>
                    </div>
                </div>
            </div>
        `;

        // Cache DOM references
        this.collapsedEl = this.container.querySelector('.dp-collapsed');
        this.expandedEl = this.container.querySelector('.dp-expanded');
        this.calendarEl = this.container.querySelector('.dp-calendar');
        this.previewTextEl = this.container.querySelector('.dp-preview-text');
        this.chevronEl = this.container.querySelector('.dp-chevron');
        this.tagsEl = this.container.querySelector('.dp-selected-tags');
        this.countEl = this.container.querySelector('.dp-count');

        // Bind click handler for collapsed view
        this.collapsedEl.addEventListener('click', () => this.toggleCalendar(true));
    }

    toggleCalendar(open) {
        this.calendarOpen = open;
        if (open) {
            this.expandedEl.style.display = 'block';
            this.chevronEl.classList.replace('fa-chevron-down', 'fa-chevron-up');
            this._renderCalendar();
            // Auto-fetch occupancy if enabled
            if (this.fetchOccupancy) {
                this._fetchMonthAvailability();
            }
        } else {
            this.expandedEl.style.display = 'none';
            this.chevronEl.classList.replace('fa-chevron-up', 'fa-chevron-down');
            this._updatePreviewText();
            // Notify of date change
            this.onDateChange(this.getSelectedDates());
        }
    }

    /**
     * Fetch occupancy data for the current month
     */
    async _fetchMonthAvailability() {
        const monthKey = `${this.calendarYear}-${this.calendarMonth}`;

        // Skip if already loaded for this month
        if (this.occupancyLoadedMonth === monthKey) {
            return;
        }

        const firstDay = new Date(this.calendarYear, this.calendarMonth, 1);
        const lastDay = new Date(this.calendarYear, this.calendarMonth + 1, 0);
        const dateFrom = this._formatDateISO(firstDay);
        const dateTo = this._formatDateISO(lastDay);

        this.occupancyLoading = true;
        this._showLoadingIndicator(true);

        try {
            const response = await fetch(
                `${this.occupancyApiUrl}?date_from=${dateFrom}&date_to=${dateTo}`
            );
            const data = await response.json();

            if (data.summary) {
                this.occupancyData = { ...this.occupancyData, ...data.summary };
                this.occupancyLoadedMonth = monthKey;
                // Re-render to show occupancy
                this._renderCalendar();
            }
        } catch (error) {
            console.warn('Failed to fetch occupancy data:', error);
        } finally {
            this.occupancyLoading = false;
            this._showLoadingIndicator(false);
        }
    }

    /**
     * Show/hide loading indicator on calendar
     */
    _showLoadingIndicator(show) {
        if (!this.calendarEl) return;

        let loader = this.calendarEl.querySelector('.dp-loading');
        if (show && !loader) {
            loader = document.createElement('div');
            loader.className = 'dp-loading';
            loader.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.calendarEl.appendChild(loader);
        } else if (!show && loader) {
            loader.remove();
        }
    }

    _renderCalendar() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const firstDay = new Date(this.calendarYear, this.calendarMonth, 1);
        const lastDay = new Date(this.calendarYear, this.calendarMonth + 1, 0);
        let startDay = firstDay.getDay();
        startDay = startDay === 0 ? 6 : startDay - 1;

        let html = `
            <div class="cal-header">
                <button type="button" class="dp-prev-month">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="cal-title">${this.monthNames[this.calendarMonth]} ${this.calendarYear}</span>
                <button type="button" class="dp-next-month">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            <div class="cal-weekdays">
                ${this.dayNames.map(d => `<div>${d}</div>`).join('')}
            </div>
            <div class="cal-days">
        `;

        // Previous month days (disabled)
        for (let i = 0; i < startDay; i++) {
            const prevMonth = new Date(this.calendarYear, this.calendarMonth, 0 - startDay + i + 1);
            html += `<div class="cal-day other-month disabled">${prevMonth.getDate()}</div>`;
        }

        // Current month days
        for (let d = 1; d <= lastDay.getDate(); d++) {
            const date = new Date(this.calendarYear, this.calendarMonth, d);
            const dateStr = this._formatDateISO(date);
            const isToday = date.getTime() === today.getTime();
            const isPast = date < today;
            const isSelected = this.selectedDates.has(dateStr);

            // Get occupancy data for this date
            const occupancy = this.occupancyData[dateStr];
            const occupancyRate = occupancy?.occupancy_rate || 0;
            const isFullyBooked = occupancyRate >= 100;

            let classes = ['cal-day'];
            if (isToday) classes.push('today');
            if (isPast || isFullyBooked) classes.push('disabled');
            if (isSelected) classes.push('selected');

            // Add occupancy level classes
            if (occupancy && !isPast) {
                if (occupancyRate >= 100) {
                    classes.push('occupancy-full');
                } else if (occupancyRate >= 80) {
                    classes.push('occupancy-high');
                } else if (occupancyRate >= 50) {
                    classes.push('occupancy-medium');
                }
            }

            // Build day HTML with optional tooltip for fully booked days
            const tooltip = isFullyBooked ? ' title="Sin disponibilidad"' : '';
            html += `<div class="${classes.join(' ')}" data-date="${dateStr}"${tooltip}>${d}</div>`;
        }

        html += `</div>`;
        this.calendarEl.innerHTML = html;

        // Bind event handlers
        this.calendarEl.querySelector('.dp-prev-month').addEventListener('click', (e) => {
            e.stopPropagation();
            this._changeMonth(-1);
        });
        this.calendarEl.querySelector('.dp-next-month').addEventListener('click', (e) => {
            e.stopPropagation();
            this._changeMonth(1);
        });
        this.calendarEl.querySelectorAll('.cal-day:not(.disabled):not(.other-month)').forEach(dayEl => {
            dayEl.addEventListener('click', (e) => {
                e.stopPropagation();
                this._toggleDate(dayEl.dataset.date);
            });
        });

        this._updateSelectedDisplay();
    }

    _changeMonth(delta) {
        this.calendarInteracting = true;
        this.calendarMonth += delta;
        if (this.calendarMonth > 11) {
            this.calendarMonth = 0;
            this.calendarYear++;
        }
        if (this.calendarMonth < 0) {
            this.calendarMonth = 11;
            this.calendarYear--;
        }
        this._renderCalendar();
        // Fetch occupancy for new month if enabled
        if (this.fetchOccupancy) {
            this._fetchMonthAvailability();
        }
        setTimeout(() => { this.calendarInteracting = false; }, 50);
    }

    _toggleDate(dateStr) {
        this.calendarInteracting = true;
        if (this.selectedDates.has(dateStr)) {
            this.selectedDates.delete(dateStr);
        } else {
            this.selectedDates.add(dateStr);
        }
        this._renderCalendar();
        setTimeout(() => { this.calendarInteracting = false; }, 50);
    }

    _removeDate(dateStr, e) {
        if (e) e.stopPropagation();
        this.selectedDates.delete(dateStr);
        this._renderCalendar();
        this._updatePreviewText();
    }

    _updateSelectedDisplay() {
        const count = this.selectedDates.size;
        this.countEl.textContent = count;

        const sorted = this.getSelectedDates();
        this.tagsEl.innerHTML = sorted.map(d =>
            `<span class="date-tag">
                ${this._formatDate(d)}
                <span class="remove" data-date="${d}">&times;</span>
            </span>`
        ).join('');

        // Bind remove handlers
        this.tagsEl.querySelectorAll('.remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this._removeDate(btn.dataset.date);
            });
        });
    }

    _updatePreviewText() {
        const sorted = this.getSelectedDates();
        const count = sorted.length;

        if (count === 0) {
            this.previewTextEl.textContent = 'Seleccionar fechas...';
        } else if (count === 1) {
            this.previewTextEl.textContent = this._formatDate(sorted[0]);
        } else {
            const preview = sorted.slice(0, 3).map(d => this._formatDate(d)).join(', ');
            this.previewTextEl.innerHTML = `<strong>${count} dias:</strong> ${preview}${count > 3 ? ' ...' : ''}`;
        }
    }

    _formatDate(dateStr) {
        if (!dateStr) return '';

        // If already in DD/MM/YYYY format, return as is
        if (typeof dateStr === 'string' && dateStr.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
            return dateStr;
        }

        // If ISO format (YYYY-MM-DD), convert to DD/MM/YYYY
        if (typeof dateStr === 'string' && dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
            const parts = dateStr.split('-');
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }

        // Handle Date object or other date formats
        try {
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                const day = String(date.getDate()).padStart(2, '0');
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const year = date.getFullYear();
                return `${day}/${month}/${year}`;
            }
        } catch (e) {
            // Fall through to return original
        }

        return String(dateStr);
    }

    _formatDateISO(date) {
        // Format date as YYYY-MM-DD in local timezone (avoids UTC conversion issues)
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    _normalizeToISO(dateStr) {
        // Normalize any date format to ISO (YYYY-MM-DD)
        if (!dateStr) return null;

        // Already ISO format
        if (typeof dateStr === 'string' && dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
            return dateStr;
        }

        // Try to parse and convert
        try {
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                return this._formatDateISO(date);
            }
        } catch (e) {
            // Fall through
        }

        return null;
    }

    // Public methods
    getSelectedDates() {
        return Array.from(this.selectedDates).sort();
    }

    setSelectedDates(dates) {
        // Normalize all dates to ISO format
        const normalizedDates = dates
            .map(d => this._normalizeToISO(d))
            .filter(d => d !== null);
        this.selectedDates = new Set(normalizedDates);
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
    }

    addDate(dateStr) {
        this.selectedDates.add(dateStr);
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
    }

    /**
     * Remove a specific date from selection
     * @param {string} dateStr - Date to remove (YYYY-MM-DD)
     */
    removeDate(dateStr) {
        this.selectedDates.delete(dateStr);
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
        // Notify of change
        this.onDateChange(this.getSelectedDates());
    }

    clearDates() {
        this.selectedDates.clear();
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
    }

    getFirstDate() {
        const sorted = this.getSelectedDates();
        return sorted.length > 0 ? sorted[0] : null;
    }

    isMultiday() {
        return this.selectedDates.size > 1;
    }

    destroy() {
        this.container.innerHTML = '';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatePicker;
}


// --- touch-handler.js ---
/**
 * Touch Handler Module
 * Handles touch gestures for the beach map including long-press detection.
 *
 * Events:
 * - longpress: Fired when user long-presses (500ms) on an element
 * - tap: Fired for regular taps (< 300ms, < 10px movement)
 */
class TouchHandler {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            longPressDelay: options.longPressDelay || 500,
            tapMaxDuration: options.tapMaxDuration || 300,
            moveThreshold: options.moveThreshold || 10,
            vibrate: options.vibrate !== false,  // Default true
            ...options
        };

        // State
        this.touchStartTime = 0;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.longPressTimer = null;
        this.currentTarget = null;
        this.isTouchActive = false;
        this._longPressFired = false;

        // Callbacks
        this.callbacks = {
            onLongPress: null,
            onTap: null
        };

        // Bind methods
        this.handleTouchStart = this.handleTouchStart.bind(this);
        this.handleTouchMove = this.handleTouchMove.bind(this);
        this.handleTouchEnd = this.handleTouchEnd.bind(this);
        this.handleTouchCancel = this.handleTouchCancel.bind(this);
        this.handleContextMenu = this.handleContextMenu.bind(this);

        // Attach listeners
        this.attachListeners();
    }

    attachListeners() {
        this.container.addEventListener('touchstart', this.handleTouchStart, { passive: false });
        this.container.addEventListener('touchmove', this.handleTouchMove, { passive: false });
        this.container.addEventListener('touchend', this.handleTouchEnd, { passive: false });
        this.container.addEventListener('touchcancel', this.handleTouchCancel, { passive: false });
        // Prevent native context menu on touch devices during long-press
        this.container.addEventListener('contextmenu', this.handleContextMenu);
    }

    /**
     * Prevent native context menu when touch is active (long-press handling)
     */
    handleContextMenu(event) {
        // If we're in the middle of a touch interaction, prevent native menu
        if (this.isTouchActive || this.longPressTimer) {
            event.preventDefault();
            event.stopPropagation();
        }
    }

    handleTouchStart(event) {
        // Only handle single touch
        if (event.touches.length !== 1) {
            this.cancelLongPress();
            return;
        }

        const touch = event.touches[0];
        this.touchStartTime = Date.now();
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
        this.isTouchActive = true;

        // Find the furniture element (traverse up to find data-furniture-id)
        this.currentTarget = this.findFurnitureElement(touch.target);

        if (this.currentTarget) {
            // Start long-press timer
            this.longPressTimer = setTimeout(() => {
                if (this.isTouchActive && this.currentTarget) {
                    this.triggerLongPress(event, this.currentTarget);
                }
            }, this.options.longPressDelay);

            // Visual feedback: scale up slightly
            this.currentTarget.style.transition = 'transform 0.15s ease';
            this.currentTarget.style.transformOrigin = 'center center';
        }
    }

    handleTouchMove(event) {
        if (!this.isTouchActive) return;

        const touch = event.touches[0];
        const deltaX = Math.abs(touch.clientX - this.touchStartX);
        const deltaY = Math.abs(touch.clientY - this.touchStartY);

        // Cancel long-press if moved too much
        if (deltaX > this.options.moveThreshold || deltaY > this.options.moveThreshold) {
            this.cancelLongPress();
        }
    }

    handleTouchEnd(event) {
        // After a long-press, prevent the synthetic click event
        if (this._longPressFired) {
            event.preventDefault();
            this.cancelLongPress();
            this.resetState();
            return;
        }

        if (!this.isTouchActive) return;

        const touchDuration = Date.now() - this.touchStartTime;

        // Cancel long-press timer
        this.cancelLongPress();

        // Check if it was a tap (short touch without much movement)
        if (touchDuration < this.options.tapMaxDuration && this.currentTarget) {
            this.triggerTap(event, this.currentTarget);
        }

        this.resetState();
    }

    handleTouchCancel() {
        this.cancelLongPress();
        this.resetState();
    }

    triggerLongPress(event, target) {
        // Mark long-press as fired so handleTouchEnd can prevent synthetic click
        this._longPressFired = true;
        this.isTouchActive = false;

        // Clean up visual feedback
        if (target) {
            target.style.transition = '';
            target.style.transformOrigin = '';
        }

        // Vibration feedback
        if (this.options.vibrate && navigator.vibrate) {
            navigator.vibrate(50);
        }

        // Prevent context menu
        event.preventDefault();

        // Get furniture data
        const furnitureId = parseInt(target.getAttribute('data-furniture-id'));

        if (this.callbacks.onLongPress) {
            this.callbacks.onLongPress({
                furnitureId: furnitureId,
                target: target,
                clientX: this.touchStartX,
                clientY: this.touchStartY,
                originalEvent: event
            });
        }
    }

    triggerTap(event, target) {
        const furnitureId = parseInt(target.getAttribute('data-furniture-id'));

        if (this.callbacks.onTap) {
            this.callbacks.onTap({
                furnitureId: furnitureId,
                target: target,
                clientX: this.touchStartX,
                clientY: this.touchStartY,
                originalEvent: event
            });
        }
    }

    cancelLongPress() {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }

        // Remove visual feedback
        if (this.currentTarget) {
            this.currentTarget.style.transition = '';
        }
    }

    resetState() {
        this.isTouchActive = false;
        this._longPressFired = false;
        this.currentTarget = null;
        this.touchStartTime = 0;
        this.touchStartX = 0;
        this.touchStartY = 0;
    }

    findFurnitureElement(element) {
        // Walk up the DOM tree to find furniture group
        let current = element;
        while (current && current !== this.container) {
            if (current.hasAttribute && current.hasAttribute('data-furniture-id')) {
                return current;
            }
            current = current.parentElement;
        }
        return null;
    }

    // Public API
    onLongPress(callback) {
        this.callbacks.onLongPress = callback;
        return this;
    }

    onTap(callback) {
        this.callbacks.onTap = callback;
        return this;
    }

    destroy() {
        this.cancelLongPress();
        this.container.removeEventListener('touchstart', this.handleTouchStart);
        this.container.removeEventListener('touchmove', this.handleTouchMove);
        this.container.removeEventListener('touchend', this.handleTouchEnd);
        this.container.removeEventListener('touchcancel', this.handleTouchCancel);
        this.container.removeEventListener('contextmenu', this.handleContextMenu);
    }
}

// Export for use
window.TouchHandler = TouchHandler;


// --- safeguard-modal.js ---
/**
 * SafeguardModal - Reusable warning modal for reservation safeguards
 * Shows warnings before potentially problematic actions
 */
function _sgEscape(str) {
    if (!str) return '';
    const s = String(str);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class SafeguardModal {
    constructor() {
        this.modal = null;
        this.backdrop = null;
        this.resolvePromise = null;
        this.init();
    }

    /**
     * Initialize the modal DOM elements
     */
    init() {
        // Create backdrop
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'safeguard-backdrop';
        this.backdrop.addEventListener('click', () => this.dismiss());

        // Create modal
        this.modal = document.createElement('div');
        this.modal.className = 'safeguard-modal';
        this.modal.setAttribute('role', 'dialog');
        this.modal.setAttribute('aria-modal', 'true');

        // Append to body
        document.body.appendChild(this.backdrop);
        document.body.appendChild(this.modal);

        // Escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.dismiss();
            }
        });
    }

    /**
     * Check if modal is currently open
     */
    isOpen() {
        return this.modal.classList.contains('open');
    }

    /**
     * Show a safeguard warning
     * @param {Object} options - Modal options
     * @param {string} options.code - Safeguard code (e.g., 'SG-01')
     * @param {string} options.title - Modal title
     * @param {string} options.message - Warning message (supports HTML)
     * @param {string} options.type - 'warning', 'error', or 'info'
     * @param {Array} options.buttons - Button configurations
     * @returns {Promise<string|null>} - Returns button action or null if dismissed
     */
    show(options) {
        const {
            code = '',
            title = 'Advertencia',
            message = '',
            type = 'warning',
            buttons = [{ label: 'Entendido', action: 'ok', style: 'primary' }]
        } = options;

        // Build modal content
        this.modal.innerHTML = `
            <div class="safeguard-modal-header ${type}">
                <div class="safeguard-icon">
                    ${this.getIcon(type)}
                </div>
                <div class="safeguard-title-group">
                    <h3 class="safeguard-title">${title}</h3>
                    ${code ? `<span class="safeguard-code">${code}</span>` : ''}
                </div>
                <button type="button" class="safeguard-close" aria-label="Cerrar">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="safeguard-modal-body">
                <div class="safeguard-message">${message}</div>
            </div>
            <div class="safeguard-modal-footer">
                ${buttons.map(btn => `
                    <button type="button"
                            class="safeguard-btn ${btn.style || 'secondary'}"
                            data-action="${btn.action}">
                        ${btn.icon ? `<i class="${btn.icon}"></i>` : ''}
                        ${btn.label}
                    </button>
                `).join('')}
            </div>
        `;

        // Attach button handlers
        this.modal.querySelectorAll('.safeguard-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.close(btn.dataset.action);
            });
        });

        // Close button handler
        this.modal.querySelector('.safeguard-close').addEventListener('click', () => {
            this.dismiss();
        });

        // Show modal
        this.backdrop.classList.add('show');
        this.modal.classList.add('open');
        document.body.style.overflow = 'hidden';

        // Focus first button
        const firstBtn = this.modal.querySelector('.safeguard-btn');
        if (firstBtn) firstBtn.focus();

        // Return promise
        return new Promise(resolve => {
            this.resolvePromise = resolve;
        });
    }

    /**
     * Get icon for modal type
     */
    getIcon(type) {
        switch (type) {
            case 'error':
                return '<i class="fas fa-exclamation-circle"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle"></i>';
            case 'info':
                return '<i class="fas fa-info-circle"></i>';
            case 'success':
                return '<i class="fas fa-check-circle"></i>';
            default:
                return '<i class="fas fa-exclamation-triangle"></i>';
        }
    }

    /**
     * Close the modal with an action
     */
    close(action) {
        this.backdrop.classList.remove('show');
        this.modal.classList.remove('open');
        document.body.style.overflow = '';

        if (this.resolvePromise) {
            this.resolvePromise(action);
            this.resolvePromise = null;
        }
    }

    /**
     * Dismiss the modal (no action)
     */
    dismiss() {
        this.close(null);
    }

    // =========================================================================
    // STATIC HELPER METHODS FOR COMMON SAFEGUARDS
    // =========================================================================

    /**
     * Show duplicate reservation warning
     * @param {Object} existingReservation - The existing reservation data
     * @returns {Promise<string|null>}
     */
    static async showDuplicateWarning(existingReservation) {
        const instance = SafeguardModal.getInstance();
        const res = existingReservation;

        const furnitureList = (res.furniture || [])
            .map(f => _sgEscape(f.number || f.furniture_number || `#${f.id}`))
            .join(', ') || 'Sin mobiliario';

        return instance.show({
            code: 'SG-01',
            title: 'Reserva duplicada',
            type: 'warning',
            message: `
                <p>Este cliente ya tiene una reserva para esta fecha:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Ticket:</span>
                        <span class="detail-value">#${_sgEscape(res.ticket_number || res.id)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Mobiliario:</span>
                        <span class="detail-value">${furnitureList}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Estado:</span>
                        <span class="detail-value">${_sgEscape(res.current_state || res.state || 'Pendiente')}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Deseas crear otra reserva de todas formas?</p>
            `,
            buttons: [
                { label: 'Cancelar', action: 'cancel', style: 'secondary' },
                { label: 'Ver existente', action: 'view', style: 'outline', icon: 'fas fa-eye' },
                { label: 'Crear de todas formas', action: 'proceed', style: 'warning' }
            ]
        });
    }

    /**
     * Show hotel stay date warning
     * @param {Object} guest - Hotel guest data with arrival/departure
     * @param {Array} outOfRangeDates - Dates outside stay
     * @returns {Promise<string|null>}
     */
    static async showHotelStayWarning(guest, outOfRangeDates) {
        const instance = SafeguardModal.getInstance();

        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        };

        return instance.show({
            code: 'SG-03',
            title: 'Fechas fuera de estadia',
            type: 'warning',
            message: `
                <p>Las siguientes fechas estan fuera de la estadia del huesped:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Check-in:</span>
                        <span class="detail-value">${formatDate(guest.arrival_date)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Check-out:</span>
                        <span class="detail-value">${formatDate(guest.departure_date)}</span>
                    </div>
                    <div class="detail-row highlight">
                        <span class="detail-label">Fuera de rango:</span>
                        <span class="detail-value">${outOfRangeDates.map(formatDate).join(', ')}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Continuar de todas formas?</p>
            `,
            buttons: [
                { label: 'Ajustar fechas', action: 'adjust', style: 'secondary' },
                { label: 'Continuar', action: 'proceed', style: 'warning' }
            ]
        });
    }

    /**
     * Show past date error
     * @param {Array} pastDates - Past dates selected
     * @returns {Promise<string|null>}
     */
    static async showPastDateError(pastDates) {
        const instance = SafeguardModal.getInstance();

        const formatDate = (dateStr) => {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
        };

        return instance.show({
            code: 'SG-05',
            title: 'Fechas no validas',
            type: 'error',
            message: `
                <p>No se pueden crear reservas para fechas pasadas:</p>
                <div class="safeguard-detail-box error">
                    <div class="past-dates-list">
                        ${pastDates.map(d => `<span class="past-date">${formatDate(d)}</span>`).join('')}
                    </div>
                </div>
                <p>Por favor selecciona fechas validas (hoy o futuro).</p>
            `,
            buttons: [
                { label: 'Entendido', action: 'ok', style: 'primary' }
            ]
        });
    }

    /**
     * Show capacity mismatch warning
     * @param {number} requestedPeople - Number of people requested
     * @param {number} maxCapacity - Maximum furniture capacity
     * @returns {Promise<string|null>}
     */
    static async showCapacityWarning(requestedPeople, maxCapacity) {
        const instance = SafeguardModal.getInstance();

        return instance.show({
            code: 'SG-04',
            title: 'Capacidad excedida',
            type: 'warning',
            message: `
                <p>El numero de personas excede la capacidad del mobiliario:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Personas indicadas:</span>
                        <span class="detail-value highlight">${requestedPeople}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Capacidad maxima:</span>
                        <span class="detail-value">${maxCapacity}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Ajustar a ${maxCapacity} personas?</p>
            `,
            buttons: [
                { label: 'Mantener ' + requestedPeople, action: 'keep', style: 'secondary' },
                { label: 'Ajustar a ' + maxCapacity, action: 'adjust', style: 'primary' }
            ]
        });
    }

    /**
     * Show excess capacity warning (more sunbeds than guests)
     * @param {number} numPeople - Number of people
     * @param {number} capacity - Furniture capacity
     * @returns {Promise<string|null>}
     */
    static async showExcessCapacityWarning(numPeople, capacity) {
        const instance = SafeguardModal.getInstance();
        const excess = capacity - numPeople;

        return instance.show({
            code: 'SG-04b',
            title: 'Mobiliario excedente',
            type: 'warning',
            message: `
                <p>El mobiliario seleccionado tiene mas capacidad de la necesaria:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Huespedes:</span>
                        <span class="detail-value">${numPeople}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Capacidad mobiliario:</span>
                        <span class="detail-value highlight">${capacity}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Plazas sobrantes:</span>
                        <span class="detail-value highlight">${excess}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Desea continuar con esta seleccion?</p>
            `,
            buttons: [
                { label: 'Cancelar', action: 'cancel', style: 'secondary' },
                { label: 'Continuar', action: 'proceed', style: 'primary' }
            ]
        });
    }

    /**
     * Show furniture availability error
     * @param {Array} conflicts - List of furniture conflicts
     * @returns {Promise<string|null>}
     */
    static async showFurnitureConflictError(conflicts) {
        const instance = SafeguardModal.getInstance();

        const formatDate = (dateStr) => {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        };

        const conflictList = conflicts.map(c => `
            <div class="conflict-item">
                <span class="conflict-furniture">${_sgEscape(c.furniture_number || 'Mobiliario #' + c.furniture_id)}</span>
                <span class="conflict-date">${formatDate(c.date)}</span>
                <span class="conflict-reservation">
                    Reserva #${_sgEscape(c.ticket_number || c.reservation_id)}
                    ${c.customer_name ? ` - ${_sgEscape(c.customer_name)}` : ''}
                </span>
            </div>
        `).join('');

        return instance.show({
            code: 'SG-02',
            title: 'Mobiliario no disponible',
            type: 'error',
            message: `
                <p>El mobiliario seleccionado no esta disponible:</p>
                <div class="safeguard-detail-box error">
                    ${conflictList}
                </div>
                <p>Selecciona otro mobiliario o cambia las fechas.</p>
            `,
            buttons: [
                { label: 'Entendido', action: 'ok', style: 'primary' }
            ]
        });
    }

    /**
     * Show non-contiguous furniture warning
     * @param {Object} contiguityResult - Result from validate-contiguity endpoint
     * @returns {Promise<string|null>}
     */
    static async showContiguityWarning(contiguityResult) {
        const instance = SafeguardModal.getInstance();

        const gapCount = contiguityResult.gap_count || 0;
        const blockingFurniture = contiguityResult.blocking_furniture || [];

        // Build blocking furniture list
        const blockingList = blockingFurniture.length > 0
            ? blockingFurniture.map(f => `
                <span class="blocking-item">${_sgEscape(f.number || '#' + f.id)}</span>
            `).join('')
            : '<span class="no-blocking">Mobiliario disperso en diferentes filas</span>';

        return instance.show({
            code: 'SG-07',
            title: 'Mobiliario no agrupado',
            type: 'warning',
            message: `
                <p>El mobiliario seleccionado no esta agrupado.</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Separaciones:</span>
                        <span class="detail-value highlight">${gapCount}</span>
                    </div>
                    ${blockingFurniture.length > 0 ? `
                    <div class="detail-row">
                        <span class="detail-label">Mobiliario entre seleccion:</span>
                        <div class="blocking-list">${blockingList}</div>
                    </div>
                    ` : ''}
                </div>
                <p class="safeguard-note">
                    <i class="fas fa-info-circle"></i>
                    Esto puede resultar en una experiencia fragmentada para el cliente.
                </p>
                <p class="safeguard-question">¿Continuar con esta seleccion?</p>
            `,
            buttons: [
                { label: 'Seleccionar otro', action: 'cancel', style: 'secondary' },
                { label: 'Continuar', action: 'proceed', style: 'warning' }
            ]
        });
    }

    /**
     * Get singleton instance
     */
    static getInstance() {
        if (!SafeguardModal._instance) {
            SafeguardModal._instance = new SafeguardModal();
        }
        return SafeguardModal._instance;
    }
}

// Initialize singleton
SafeguardModal._instance = null;

// Export for use
window.SafeguardModal = SafeguardModal;


// --- conflict-resolution-modal.js ---
/**
 * ConflictResolutionModal - Modal for handling multi-day reservation conflicts
 *
 * Displays conflicts when furniture is not available for some dates in a
 * multi-day reservation. Allows users to either:
 * - Navigate to the map to select alternative furniture for each day
 * - Remove problematic days from the reservation
 *
 * Usage:
 *   const modal = new ConflictResolutionModal({
 *       onNavigateToDay: (date, conflicts) => { ... },
 *       onRetry: (furnitureByDate) => { ... },
 *       onCancel: () => { ... }
 *   });
 *   modal.show(conflicts, selectedDates, originalFurniture);
 */
class ConflictResolutionModal {
    constructor(options = {}) {
        this.options = {
            onNavigateToDay: null,  // (date, conflicts) => void
            onRetry: null,          // (furnitureByDate) => void
            onCancel: null,         // () => void
            onRemoveDate: null,     // (date) => void - notify parent when date is removed
            ...options
        };

        // State
        this.state = {
            isOpen: false,
            conflicts: [],           // [{furniture_id, date, ticket_number, customer_name}]
            selectedDates: [],       // All dates in the reservation
            furnitureByDate: {},     // {date: [furniture_ids]} - per-day selections
            originalFurniture: [],   // Initial furniture selection
            resolvedDates: new Set() // Dates that have alternative furniture selected
        };

        this.buildModal();
        this.bindEvents();
    }

    /**
     * Build the modal DOM structure
     */
    buildModal() {
        this.modal = document.createElement('div');
        this.modal.className = 'conflict-modal';
        this.modal.innerHTML = `
            <div class="conflict-modal-backdrop"></div>
            <div class="conflict-modal-content">
                <div class="conflict-modal-header">
                    <h3>
                        <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                        Conflictos de Disponibilidad
                    </h3>
                    <button type="button" class="conflict-modal-close" aria-label="Cerrar">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="conflict-modal-body">
                    <p class="conflict-intro">
                        El mobiliario seleccionado no esta disponible para algunas fechas.
                        Puedes seleccionar mobiliario alternativo o quitar los dias problematicos.
                    </p>
                    <div class="conflict-list"></div>
                    <div class="conflict-summary"></div>
                </div>
                <div class="conflict-modal-footer">
                    <button type="button" class="btn btn-outline-secondary conflict-cancel-btn">
                        Cancelar
                    </button>
                    <button type="button" class="btn btn-primary conflict-retry-btn" disabled>
                        <i class="fas fa-check me-1"></i>
                        Reintentar con Cambios
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(this.modal);

        // Cache DOM references
        this.backdrop = this.modal.querySelector('.conflict-modal-backdrop');
        this.closeBtn = this.modal.querySelector('.conflict-modal-close');
        this.cancelBtn = this.modal.querySelector('.conflict-cancel-btn');
        this.retryBtn = this.modal.querySelector('.conflict-retry-btn');
        this.listEl = this.modal.querySelector('.conflict-list');
        this.summaryEl = this.modal.querySelector('.conflict-summary');
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        this.backdrop.addEventListener('click', () => this.close());
        this.closeBtn.addEventListener('click', () => this.close());
        this.cancelBtn.addEventListener('click', () => this.close());

        this.retryBtn.addEventListener('click', () => {
            if (this.options.onRetry) {
                this.options.onRetry(this.state.furnitureByDate);
            }
            this.close();
        });

        // Event delegation for dynamic buttons
        this.listEl.addEventListener('click', (e) => {
            const navBtn = e.target.closest('.navigate-to-day-btn');
            const removeBtn = e.target.closest('.remove-day-btn');

            if (navBtn) {
                const date = navBtn.dataset.date;
                const dateConflicts = this.getConflictsForDate(date);
                if (this.options.onNavigateToDay) {
                    this.options.onNavigateToDay(date, dateConflicts);
                }
                this.minimize();
            }

            if (removeBtn) {
                const date = removeBtn.dataset.date;
                this.removeDate(date);
            }
        });

        // Listen for alternative selection from map
        document.addEventListener('conflictResolution:alternativeSelected', (e) => {
            const { date, furnitureIds } = e.detail;
            this.updateDateSelection(date, furnitureIds);
        });

        // Listen for cancellation from map (when user clicks "Cancelar" in selection bar)
        document.addEventListener('conflictResolution:cancelled', () => {
            console.log('[ConflictModal] User cancelled from map, restoring modal');
            // Show the modal again
            this.modal.classList.remove('minimized');
            this.modal.classList.add('open');
            this.modal.style.removeProperty('display');
            this.modal.style.setProperty('display', 'flex', 'important');
            this.state.isOpen = true;
        });
    }

    /**
     * Show the modal with conflict data
     * @param {Array} conflicts - Array of conflict objects from API
     * @param {Array} selectedDates - All dates in the reservation
     * @param {Array} originalFurniture - Initial furniture selection (IDs)
     */
    show(conflicts, selectedDates, originalFurniture) {
        this.state.conflicts = conflicts;
        this.state.selectedDates = [...selectedDates];
        this.state.originalFurniture = [...originalFurniture];
        this.state.resolvedDates = new Set();

        // Initialize furniture by date with original selection
        this.state.furnitureByDate = {};
        selectedDates.forEach(date => {
            this.state.furnitureByDate[date] = [...originalFurniture];
        });

        this.renderConflicts();
        this.updateSummary();
        this.updateRetryButton();

        this.modal.classList.remove('minimized');
        this.modal.classList.add('open');
        this.modal.style.display = 'flex';  // Force display
        this.state.isOpen = true;
    }

    /**
     * Close the modal
     */
    close() {
        this.modal.classList.remove('open');
        this.modal.classList.remove('minimized');
        this.modal.style.display = 'none';  // Reset inline style
        this.state.isOpen = false;

        if (this.options.onCancel) {
            this.options.onCancel();
        }
    }

    /**
     * Minimize the modal (when navigating to map)
     */
    minimize() {
        this.modal.classList.add('minimized');
        this.modal.style.display = 'none';  // Hide when minimized
    }

    /**
     * Restore the modal from minimized state
     */
    restore() {
        this.modal.classList.remove('minimized');
    }

    /**
     * Render the conflict list grouped by date
     */
    renderConflicts() {
        // Group conflicts by date
        const conflictsByDate = {};
        this.state.conflicts.forEach(c => {
            if (!conflictsByDate[c.date]) conflictsByDate[c.date] = [];
            conflictsByDate[c.date].push(c);
        });

        // Only show dates that are still selected
        const activeDates = Object.keys(conflictsByDate).filter(
            date => this.state.selectedDates.includes(date)
        );

        if (activeDates.length === 0) {
            this.listEl.innerHTML = `
                <div class="conflict-empty">
                    <i class="fas fa-check-circle text-success"></i>
                    <p>Todos los conflictos han sido resueltos.</p>
                </div>
            `;
            return;
        }

        this.listEl.innerHTML = activeDates.map(date => {
            const dateConflicts = conflictsByDate[date];
            const formattedDate = this.formatDate(date);
            const isResolved = this.state.resolvedDates.has(date);
            const canRemove = this.state.selectedDates.length > 1;

            return `
                <div class="conflict-date-group ${isResolved ? 'resolved' : ''}" data-date="${date}">
                    <div class="conflict-date-header">
                        <span class="conflict-date">${formattedDate}</span>
                        ${isResolved
                    ? '<span class="badge bg-success"><i class="fas fa-check me-1"></i>Alternativa seleccionada</span>'
                    : '<span class="badge bg-warning text-dark"><i class="fas fa-exclamation me-1"></i>Requiere accion</span>'
                }
                    </div>
                    <div class="conflict-items">
                        ${dateConflicts.map(c => `
                            <div class="conflict-item">
                                <span class="conflict-furniture">
                                    <i class="fas fa-chair me-1"></i>
                                    ${c.furniture_number || 'Mobiliario #' + c.furniture_id}
                                </span>
                                <span class="conflict-blocker">
                                    Ocupado por: ${c.customer_name} (${c.ticket_number})
                                </span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="conflict-actions">
                        <button type="button" class="btn btn-sm btn-outline-primary navigate-to-day-btn"
                                data-date="${date}">
                            <i class="fas fa-map-marker-alt me-1"></i>
                            Ir al Mapa
                        </button>
                        ${canRemove ? `
                            <button type="button" class="btn btn-sm btn-outline-danger remove-day-btn"
                                    data-date="${date}">
                                <i class="fas fa-trash me-1"></i>
                                Quitar Dia
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Update the summary section
     */
    updateSummary() {
        const totalDates = this.state.selectedDates.length;
        const conflictDates = this.getUnresolvedConflictDates().length;
        const resolvedDates = this.state.resolvedDates.size;

        if (conflictDates === 0) {
            this.summaryEl.innerHTML = `
                <div class="conflict-summary-success">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <span>Listo para reintentar con ${totalDates} dia${totalDates !== 1 ? 's' : ''}</span>
                </div>
            `;
        } else {
            this.summaryEl.innerHTML = `
                <div class="conflict-summary-pending">
                    <i class="fas fa-info-circle text-warning me-2"></i>
                    <span>${conflictDates} dia${conflictDates !== 1 ? 's' : ''} pendiente${conflictDates !== 1 ? 's' : ''} de resolver</span>
                </div>
            `;
        }
    }

    /**
     * Update retry button state
     */
    updateRetryButton() {
        const unresolvedDates = this.getUnresolvedConflictDates();
        const canRetry = unresolvedDates.length === 0 && this.state.selectedDates.length > 0;

        this.retryBtn.disabled = !canRetry;
    }

    /**
     * Get dates with unresolved conflicts
     */
    getUnresolvedConflictDates() {
        const conflictDates = new Set(this.state.conflicts.map(c => c.date));
        return this.state.selectedDates.filter(
            date => conflictDates.has(date) && !this.state.resolvedDates.has(date)
        );
    }

    /**
     * Get conflicts for a specific date
     */
    getConflictsForDate(date) {
        return this.state.conflicts.filter(c => c.date === date);
    }

    /**
     * Check if a date has alternative furniture selected
     */
    hasAlternativeSelection(date) {
        return this.state.resolvedDates.has(date);
    }

    /**
     * Update furniture selection for a specific date
     * Called when user selects alternative furniture from the map
     */
    updateDateSelection(date, furnitureIds) {
        console.log('[ConflictModal] updateDateSelection called:', date, furnitureIds);

        // Update state
        this.state.furnitureByDate[date] = [...furnitureIds]; // Copy array
        this.state.resolvedDates.add(date);

        // Re-render UI
        this.renderConflicts();
        this.updateSummary();
        this.updateRetryButton();

        // Force modal to be visible - remove ALL hiding states and force display
        this.modal.classList.remove('minimized');
        this.modal.classList.add('open');

        // Clear any inline display:none and force flex with !important
        this.modal.style.removeProperty('display');
        this.modal.style.setProperty('display', 'flex', 'important');

        this.state.isOpen = true;

        console.log('[ConflictModal] Modal restored. Classes:', this.modal.className,
                    'Style:', this.modal.style.cssText,
                    'ComputedDisplay:', window.getComputedStyle(this.modal).display);
    }

    /**
     * Remove a date from the reservation
     */
    removeDate(date) {
        // Remove from selected dates
        this.state.selectedDates = this.state.selectedDates.filter(d => d !== date);

        // Remove from furniture map
        delete this.state.furnitureByDate[date];

        // Remove from resolved set
        this.state.resolvedDates.delete(date);

        // Notify parent (to update DatePicker)
        if (this.options.onRemoveDate) {
            this.options.onRemoveDate(date);
        }

        // Check if we still have dates
        if (this.state.selectedDates.length === 0) {
            this.close();
            return;
        }

        this.renderConflicts();
        this.updateSummary();
        this.updateRetryButton();
    }

    /**
     * Format date for display
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr + 'T12:00:00');
        const options = { weekday: 'short', day: 'numeric', month: 'short' };
        return date.toLocaleDateString('es-ES', options);
    }

    /**
     * Check if modal is open
     */
    isOpen() {
        return this.state.isOpen;
    }

    /**
     * Get the current furniture by date map
     */
    getFurnitureByDate() {
        return { ...this.state.furnitureByDate };
    }

    /**
     * Get remaining selected dates
     */
    getSelectedDates() {
        return [...this.state.selectedDates];
    }

    /**
     * Destroy the modal
     */
    destroy() {
        this.modal.remove();
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConflictResolutionModal;
}

