/**
 * Map Search Manager
 * Handles search functionality for the beach map
 *
 * Enhanced: Groups by reservation, includes all states, supports filters
 */

export class SearchManager {
    constructor(options = {}) {
        this.options = {
            minChars: 1,
            debounceMs: 150,
            maxResults: 30,
            apiUrl: '/beach/api/map/all-reservations',
            ...options
        };

        // State
        this.isActive = false;
        this.currentQuery = '';
        this.results = [];
        this.activeIndex = -1;
        this.searchTimeout = null;

        // All reservations data from API
        this.allReservations = [];
        this.availableStates = [];
        this.currentDate = null;
        this.currentZoneId = null;

        // Filter state
        this.filters = {
            state: null,      // null = all
            customerType: null, // null = all, 'interno', 'externo'
            paid: null        // null = all, true, false
        };

        // Callbacks
        this.callbacks = {
            onSelect: null,
            onClear: null,
            onNavigate: null  // For released reservations
        };

        // DOM elements
        this.wrapper = null;
        this.input = null;
        this.clearBtn = null;
        this.filterBtn = null;
        this.filterPopover = null;
        this.resultsContainer = null;

        // Initialize
        this._init();
    }

    _init() {
        this._cacheElements();
        if (this.input) {
            this._attachListeners();
        }
    }

    _cacheElements() {
        this.wrapper = document.querySelector('.map-search-wrapper');
        this.input = document.getElementById('map-search-input');
        this.clearBtn = document.getElementById('map-search-clear');
        this.filterBtn = document.getElementById('map-search-filter-btn');
        this.filterPopover = document.getElementById('map-search-filter-popover');
        this.resultsContainer = document.getElementById('map-search-results');
    }

    _attachListeners() {
        // Input events
        this.input.addEventListener('input', (e) => this._onInput(e));
        this.input.addEventListener('focus', () => this._onFocus());
        this.input.addEventListener('blur', (e) => this._onBlur(e));
        this.input.addEventListener('keydown', (e) => this._handleKeyDown(e));

        // Clear button
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clear();
                this.input.focus();
            });
        }

        // Filter button
        if (this.filterBtn) {
            this.filterBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this._toggleFilterPopover();
            });
        }

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (this.wrapper && !this.wrapper.contains(e.target)) {
                this._hideResults();
                this._hideFilterPopover();
            }
        });
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    /**
     * Load all reservations for the date from API
     * @param {string} date - Date string YYYY-MM-DD
     * @param {number|null} zoneId - Optional zone filter
     */
    async loadReservations(date, zoneId = null) {
        this.currentDate = date;
        this.currentZoneId = zoneId;

        try {
            let url = `${this.options.apiUrl}?date=${date}`;
            if (zoneId) url += `&zone_id=${zoneId}`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load reservations');

            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'API error');

            this.allReservations = data.reservations || [];
            this.availableStates = data.states || [];

            // Update filter dropdowns if they exist
            this._updateFilterDropdowns();

        } catch (error) {
            console.error('SearchManager: Failed to load reservations', error);
            this.allReservations = [];
        }
    }

    /**
     * Focus the search input
     */
    focus() {
        if (this.input) {
            this.input.focus();
            this.input.select();
        }
    }

    /**
     * Clear search and hide results
     */
    clear() {
        if (this.input) {
            this.input.value = '';
        }
        this.currentQuery = '';
        this.results = [];
        this.activeIndex = -1;
        this._hideResults();
        this._updateClearButton();

        if (this.callbacks.onClear) {
            this.callbacks.onClear();
        }
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        this.filters = {
            state: null,
            customerType: null,
            paid: null
        };
        this._updateFilterDropdowns();
        this._updateFilterBadge();

        // Show results based on current query (or hide if no query)
        this._showFilteredResults();
    }

    /**
     * Set a filter value
     * @param {string} filterName - 'state', 'customerType', or 'paid'
     * @param {*} value - Filter value or null for all
     */
    setFilter(filterName, value) {
        if (this.filters.hasOwnProperty(filterName)) {
            this.filters[filterName] = value;
            this._updateFilterBadge();

            // Show filtered results - either with query or all matching
            this._showFilteredResults();
        }
    }

    /**
     * Show all reservations matching current filters (can be used without typing)
     * Called when filters change or when user wants to browse
     */
    showFilteredResults() {
        this._showFilteredResults();
    }

    _showFilteredResults() {
        if (this.allReservations.length === 0) {
            this._displayNoResults('No hay datos cargados');
            return;
        }

        // Start with query filter if exists, otherwise all reservations
        let matches;
        if (this.currentQuery) {
            const normalizedQuery = this.currentQuery.toLowerCase().trim();
            matches = this._filterReservations(normalizedQuery);
        } else {
            // No query - start with all reservations
            matches = [...this.allReservations];
        }

        // Apply filters
        matches = this._applyFilters(matches);

        // If no filters and no query, hide results
        if (!this.currentQuery && !this.hasActiveFilters()) {
            this._hideResults();
            return;
        }

        // Limit results
        matches = matches.slice(0, this.options.maxResults);

        this.results = matches;
        this.activeIndex = -1;

        if (matches.length === 0) {
            this._displayNoResults('No se encontraron resultados');
        } else {
            this._displayResults(matches);
        }
    }

    /**
     * Register callback
     * @param {string} eventName - 'onSelect', 'onClear', or 'onNavigate'
     * @param {Function} callback - Callback function
     */
    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
    }

    /**
     * Check if any filters are active
     * @returns {boolean}
     */
    hasActiveFilters() {
        return this.filters.state !== null ||
               this.filters.customerType !== null ||
               this.filters.paid !== null;
    }

    // =========================================================================
    // INPUT HANDLING
    // =========================================================================

    _onInput(e) {
        const query = e.target.value.trim();
        this._updateClearButton();

        // Debounce search
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < this.options.minChars) {
            this._hideResults();
            return;
        }

        this.searchTimeout = setTimeout(() => {
            this._search(query);
        }, this.options.debounceMs);
    }

    _onFocus() {
        this.isActive = true;
        if (this.currentQuery && this.results.length > 0) {
            this._showResults();
        }
    }

    _onBlur(e) {
        // Delay to allow click on result
        setTimeout(() => {
            if (!this.wrapper?.contains(document.activeElement)) {
                this.isActive = false;
                this._hideResults();
            }
        }, 200);
    }

    _updateClearButton() {
        if (this.clearBtn) {
            this.clearBtn.style.display = this.input?.value ? 'flex' : 'none';
        }
    }

    // =========================================================================
    // SEARCH LOGIC
    // =========================================================================

    _search(query) {
        if (this.allReservations.length === 0) {
            this._displayNoResults('No hay datos cargados');
            return;
        }

        this.currentQuery = query;
        const normalizedQuery = query.toLowerCase().trim();

        // Filter reservations by query
        let matches = this._filterReservations(normalizedQuery);

        // Apply filters
        matches = this._applyFilters(matches);

        // Limit results
        matches = matches.slice(0, this.options.maxResults);

        this.results = matches;
        this.activeIndex = -1;

        if (matches.length === 0) {
            this._displayNoResults('No se encontraron resultados');
        } else {
            this._displayResults(matches);
        }
    }

    _filterReservations(query) {
        return this.allReservations.filter(res => {
            // Match customer name
            const customerName = (res.customer_name || '').toLowerCase();
            if (customerName.includes(query)) return true;

            // Match room number
            const roomNumber = (res.room_number || '').toLowerCase();
            if (roomNumber.includes(query)) return true;

            // Match ticket number
            const ticketNumber = (res.ticket_number || '').toLowerCase();
            if (ticketNumber.includes(query)) return true;

            // Match furniture codes
            const furnitureCodes = (res.furniture_codes || []).join(' ').toLowerCase();
            // Match with or without dash (H-01 or H01)
            const normalizedQuery = query.replace(/-/g, '');
            const normalizedCodes = furnitureCodes.replace(/-/g, '');
            if (furnitureCodes.includes(query) || normalizedCodes.includes(normalizedQuery)) {
                return true;
            }

            // Match state name
            const stateName = (res.state || '').toLowerCase();
            if (stateName.includes(query)) return true;

            return false;
        });
    }

    _applyFilters(reservations) {
        return reservations.filter(res => {
            // State filter
            if (this.filters.state !== null) {
                if (res.state !== this.filters.state) return false;
            }

            // Customer type filter
            if (this.filters.customerType !== null) {
                if (res.customer_type !== this.filters.customerType) return false;
            }

            // Payment status filter
            if (this.filters.paid !== null) {
                if (res.paid !== this.filters.paid) return false;
            }

            return true;
        });
    }

    // =========================================================================
    // RESULTS DISPLAY
    // =========================================================================

    _displayResults(results) {
        if (!this.resultsContainer) return;

        let html = '<div class="search-results-list">';

        for (const res of results) {
            const isReleased = res.is_released;
            const itemClass = isReleased ? 'search-result-item released' : 'search-result-item';

            // Customer type badge
            const typeLabel = res.customer_type === 'interno' ? 'Interno' : 'Externo';
            const typeClass = res.customer_type === 'interno' ? 'type-interno' : 'type-externo';

            // Room display for interno
            const roomDisplay = res.room_number ? ` · Hab. ${this._escapeHtml(res.room_number)}` : '';

            // Payment status
            const paidLabel = res.paid ? 'Pagado' : 'Sin pagar';
            const paidClass = res.paid ? 'paid' : 'unpaid';

            // Furniture list
            const furnitureList = (res.furniture_codes || []).join(', ');

            // State badge style
            const stateStyle = `background: ${res.state_color}; color: ${res.state_text_color};`;

            html += `
                <div class="${itemClass}"
                     data-reservation-id="${res.reservation_id}"
                     data-furniture-ids="${(res.furniture_ids || []).join(',')}"
                     data-is-released="${isReleased}"
                     role="option">
                    <div class="result-header">
                        <span class="result-customer-name">${this._escapeHtml(res.customer_name)}</span>
                        <span class="result-state" style="${stateStyle}">${this._escapeHtml(res.state)}</span>
                    </div>
                    <div class="result-meta">
                        <span class="result-type ${typeClass}">${typeLabel}</span>${roomDisplay}
                        <span class="result-paid ${paidClass}">${paidLabel}</span>
                    </div>
                    <div class="result-furniture">
                        <i class="fas fa-umbrella-beach"></i>
                        ${this._escapeHtml(furnitureList)}
                        ${isReleased ? '<span class="released-hint">(reserva liberada)</span>' : ''}
                    </div>
                </div>
            `;
        }

        html += '</div>';

        // Keyboard hint
        html += `
            <div class="search-keyboard-hint">
                <kbd>↑</kbd><kbd>↓</kbd> navegar · <kbd>Enter</kbd> seleccionar · <kbd>Esc</kbd> cerrar
            </div>
        `;

        this.resultsContainer.innerHTML = html;
        this._attachResultListeners();
        this._showResults();
    }

    _displayNoResults(message) {
        if (!this.resultsContainer) return;

        const hasFilters = this.hasActiveFilters();
        const filterHint = hasFilters
            ? '<button class="clear-filters-btn" type="button">Limpiar filtros</button>'
            : '';

        this.resultsContainer.innerHTML = `
            <div class="search-no-results">
                <i class="fas fa-search"></i>
                <span>${this._escapeHtml(message)}</span>
                ${filterHint}
            </div>
        `;

        // Attach clear filters handler
        const clearBtn = this.resultsContainer.querySelector('.clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFilters());
        }

        this._showResults();
    }

    _attachResultListeners() {
        const items = this.resultsContainer.querySelectorAll('.search-result-item');
        items.forEach((item, index) => {
            item.addEventListener('click', () => this._selectResult(index));
            item.addEventListener('mouseenter', () => this._setActiveIndex(index));
        });
    }

    _showResults() {
        if (this.resultsContainer) {
            this.resultsContainer.classList.add('show');
        }
    }

    _hideResults() {
        if (this.resultsContainer) {
            this.resultsContainer.classList.remove('show');
        }
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // =========================================================================
    // FILTER POPOVER
    // =========================================================================

    _toggleFilterPopover() {
        if (!this.filterPopover) return;

        if (this.filterPopover.classList.contains('show')) {
            this._hideFilterPopover();
        } else {
            this._showFilterPopover();
        }
    }

    _showFilterPopover() {
        if (this.filterPopover) {
            this.filterPopover.classList.add('show');
        }
    }

    _hideFilterPopover() {
        if (this.filterPopover) {
            this.filterPopover.classList.remove('show');
        }
    }

    _updateFilterDropdowns() {
        // State dropdown
        const stateSelect = document.getElementById('search-filter-state');
        if (stateSelect && this.availableStates.length > 0) {
            let options = '<option value="">Estado</option>';
            for (const state of this.availableStates) {
                const selected = this.filters.state === state.name ? 'selected' : '';
                options += `<option value="${this._escapeHtml(state.name)}" ${selected}>${this._escapeHtml(state.name)}</option>`;
            }
            stateSelect.innerHTML = options;
        }

        // Customer type dropdown
        const typeSelect = document.getElementById('search-filter-type');
        if (typeSelect) {
            typeSelect.value = this.filters.customerType || '';
        }

        // Payment status dropdown
        const paidSelect = document.getElementById('search-filter-paid');
        if (paidSelect) {
            paidSelect.value = this.filters.paid === null ? '' : (this.filters.paid ? '1' : '0');
        }
    }

    _updateFilterBadge() {
        if (!this.filterBtn) return;

        const activeCount = (this.filters.state !== null ? 1 : 0) +
                           (this.filters.customerType !== null ? 1 : 0) +
                           (this.filters.paid !== null ? 1 : 0);

        // Update badge
        let badge = this.filterBtn.querySelector('.filter-badge');
        if (activeCount > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'filter-badge';
                this.filterBtn.appendChild(badge);
            }
            badge.textContent = activeCount;
            this.filterBtn.classList.add('has-filters');
        } else {
            if (badge) badge.remove();
            this.filterBtn.classList.remove('has-filters');
        }
    }

    // =========================================================================
    // KEYBOARD NAVIGATION
    // =========================================================================

    _handleKeyDown(e) {
        if (!this.resultsContainer?.classList.contains('show')) {
            // If results not showing and Enter pressed, trigger search
            if (e.key === 'Enter' && this.input?.value) {
                this._search(this.input.value.trim());
            }
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this._navigateResults(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this._navigateResults(-1);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.activeIndex >= 0) {
                    this._selectResult(this.activeIndex);
                }
                break;
            case 'Escape':
                e.preventDefault();
                this.clear();
                this.input?.blur();
                break;
        }
    }

    _navigateResults(direction) {
        const items = this.resultsContainer.querySelectorAll('.search-result-item');
        if (items.length === 0) return;

        let newIndex = this.activeIndex + direction;

        if (newIndex < 0) {
            newIndex = items.length - 1;
        } else if (newIndex >= items.length) {
            newIndex = 0;
        }

        this._setActiveIndex(newIndex);
    }

    _setActiveIndex(index) {
        const items = this.resultsContainer.querySelectorAll('.search-result-item');

        // Remove active from previous
        items.forEach(item => item.classList.remove('active'));

        // Set new active
        this.activeIndex = index;
        if (index >= 0 && index < items.length) {
            items[index].classList.add('active');
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    _selectResult(index) {
        const items = this.resultsContainer.querySelectorAll('.search-result-item');
        if (index < 0 || index >= items.length) return;

        const item = items[index];
        const reservationId = parseInt(item.dataset.reservationId, 10);
        const furnitureIds = item.dataset.furnitureIds
            ? item.dataset.furnitureIds.split(',').map(id => parseInt(id, 10))
            : [];
        const isReleased = item.dataset.isReleased === 'true';

        // Hide results
        this._hideResults();

        // Handle based on release status
        if (isReleased) {
            // Navigate to reservation page for released reservations
            if (this.callbacks.onNavigate) {
                this.callbacks.onNavigate(reservationId);
            } else {
                // Default: navigate to reservations page
                window.location.href = `/beach/reservations/${reservationId}`;
            }
        } else {
            // Trigger callback for active reservations
            if (this.callbacks.onSelect) {
                this.callbacks.onSelect({
                    reservationId,
                    furnitureIds,
                    customerName: item.querySelector('.result-customer-name')?.textContent || ''
                });
            }
        }
    }
}
