/**
 * WaitlistManager - Manages the waitlist panel functionality
 * Controls panel open/close, tab switching, entry loading, and actions
 *
 * Usage:
 *   const manager = new WaitlistManager({
 *       currentDate: '2024-01-15',
 *       onConvert: (entry) => { ... }
 *   });
 *   manager.open();
 */

class WaitlistManager {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/beach/api',
            debounceMs: 300,
            ...options
        };

        // State
        this.state = {
            isOpen: false,
            currentDate: options.currentDate || this._getTodayDate(),
            currentTab: 'pending',
            entries: [],
            historyEntries: [],
            isLoading: false,
            selectedCustomerId: null,
            selectedHotelGuestId: null,
            customerType: 'interno',
            zones: [],
            furnitureTypes: [],
            packages: []
        };

        // Callbacks
        this.callbacks = {
            onConvert: options.onConvert || null,
            onCountUpdate: options.onCountUpdate || null
        };

        // CSRF Token
        this.csrfToken = document.getElementById('waitlistCsrfToken')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';

        // Timers
        this.searchTimeout = null;

        // Cache DOM elements
        this._cacheElements();

        // Initialize
        if (this.panel) {
            this._attachListeners();
        }
    }

    // =========================================================================
    // DOM CACHING
    // =========================================================================

    _cacheElements() {
        // Panel elements
        this.panel = document.getElementById('waitlistPanel');
        this.backdrop = document.getElementById('waitlistPanelBackdrop');

        if (!this.panel) {
            console.warn('WaitlistManager: Panel element not found');
            return;
        }

        // Header
        this.closeBtn = document.getElementById('waitlistPanelCloseBtn');
        this.addBtn = document.getElementById('waitlistAddBtn');
        this.dateDisplay = document.getElementById('waitlistPanelDate');

        // Tabs
        this.tabPending = document.getElementById('waitlistTabPending');
        this.tabHistory = document.getElementById('waitlistTabHistory');
        this.pendingCount = document.getElementById('waitlistPendingCount');

        // Content
        this.loadingEl = document.getElementById('waitlistPanelLoading');
        this.contentPending = document.getElementById('waitlistContentPending');
        this.contentHistory = document.getElementById('waitlistContentHistory');
        this.entriesPending = document.getElementById('waitlistEntriesPending');
        this.entriesHistory = document.getElementById('waitlistEntriesHistory');
        this.emptyPending = document.getElementById('waitlistEmptyPending');
        this.emptyHistory = document.getElementById('waitlistEmptyHistory');

        // Footer
        this.footerAddBtn = document.getElementById('waitlistFooterAddBtn');

        // Modal elements
        this.modal = document.getElementById('waitlistAddModal');
        this.modalBackdrop = document.getElementById('waitlistModalBackdrop');
        this.modalCloseBtn = document.getElementById('waitlistModalCloseBtn');
        this.modalCancelBtn = document.getElementById('waitlistModalCancelBtn');
        this.modalSaveBtn = document.getElementById('waitlistModalSaveBtn');
        this.addForm = document.getElementById('waitlistAddForm');

        // Customer type toggles
        this.typeInterno = document.getElementById('waitlistTypeInterno');
        this.typeExterno = document.getElementById('waitlistTypeExterno');

        // Room search (interno)
        this.roomSearchGroup = document.getElementById('waitlistRoomSearchGroup');
        this.roomSearchInput = document.getElementById('waitlistRoomSearch');
        this.roomResults = document.getElementById('waitlistRoomResults');
        this.selectedGuestEl = document.getElementById('waitlistSelectedGuest');
        this.guestNameEl = document.getElementById('waitlistGuestName');
        this.guestRoomEl = document.getElementById('waitlistGuestRoom');
        this.clearGuestBtn = document.getElementById('waitlistClearGuest');

        // Customer search (externo)
        this.customerSearchGroup = document.getElementById('waitlistCustomerSearchGroup');
        this.customerSearchInput = document.getElementById('waitlistCustomerSearch');
        this.customerResults = document.getElementById('waitlistCustomerResults');
        this.selectedCustomerEl = document.getElementById('waitlistSelectedCustomer');
        this.customerNameEl = document.getElementById('waitlistCustomerName');
        this.customerPhoneEl = document.getElementById('waitlistCustomerPhone');
        this.clearCustomerBtn = document.getElementById('waitlistClearCustomer');
        this.createCustomerBtn = document.getElementById('waitlistCreateCustomerBtn');

        // Form fields
        this.dateInput = document.getElementById('waitlistDate');
        this.numPeopleInput = document.getElementById('waitlistNumPeople');
        this.timePreferenceSelect = document.getElementById('waitlistTimePreference');
        this.zonePreferenceSelect = document.getElementById('waitlistZonePreference');
        this.furnitureTypeSelect = document.getElementById('waitlistFurnitureType');
        this.notesInput = document.getElementById('waitlistNotes');
        this.reservationTypeRadios = document.querySelectorAll('input[name="reservationType"]');
        this.packageGroup = document.getElementById('waitlistPackageGroup');
        this.packageSelect = document.getElementById('waitlistPackageSelect');

        // Hidden fields
        this.customerIdInput = document.getElementById('waitlistCustomerId');
        this.customerTypeInput = document.getElementById('waitlistCustomerType');
        this.hotelGuestIdInput = document.getElementById('waitlistHotelGuestId');
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================

    _attachListeners() {
        // Panel close
        this.closeBtn?.addEventListener('click', () => this.close());
        this.backdrop?.addEventListener('click', () => this.close());

        // Add buttons
        this.addBtn?.addEventListener('click', () => this._openAddModal());
        this.footerAddBtn?.addEventListener('click', () => this._openAddModal());

        // Tab switching
        this.tabPending?.addEventListener('click', () => this._switchTab('pending'));
        this.tabHistory?.addEventListener('click', () => this._switchTab('history'));

        // Modal
        this.modalBackdrop?.addEventListener('click', () => this._closeAddModal());
        this.modalCloseBtn?.addEventListener('click', () => this._closeAddModal());
        this.modalCancelBtn?.addEventListener('click', () => this._closeAddModal());
        this.modalSaveBtn?.addEventListener('click', () => this._submitEntry());

        // Customer type toggle
        this.typeInterno?.addEventListener('click', () => this._setCustomerType('interno'));
        this.typeExterno?.addEventListener('click', () => this._setCustomerType('externo'));

        // Room search
        this.roomSearchInput?.addEventListener('input', (e) => this._onRoomSearch(e));
        this.clearGuestBtn?.addEventListener('click', () => this._clearSelectedGuest());

        // Customer search
        this.customerSearchInput?.addEventListener('input', (e) => this._onCustomerSearch(e));
        this.clearCustomerBtn?.addEventListener('click', () => this._clearSelectedCustomer());
        this.createCustomerBtn?.addEventListener('click', () => this._showCreateCustomer());

        // Reservation type change
        this.reservationTypeRadios?.forEach(radio => {
            radio.addEventListener('change', () => this._onReservationTypeChange());
        });

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.modal?.style.display !== 'none') {
                    this._closeAddModal();
                } else if (this.state.isOpen) {
                    this.close();
                }
            }
        });
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    /**
     * Set the current date and refresh data
     * @param {string} date - Date string (YYYY-MM-DD)
     */
    setDate(date) {
        this.state.currentDate = date;
        if (this.dateDisplay) {
            this.dateDisplay.textContent = this._formatDateDisplay(date);
        }
        if (this.state.isOpen) {
            this.refresh();
        }
    }

    /**
     * Open the panel and load data
     */
    async open() {
        if (!this.panel) return;

        this.state.isOpen = true;

        // Update date display
        if (this.dateDisplay) {
            this.dateDisplay.textContent = this._formatDateDisplay(this.state.currentDate);
        }

        // Show panel
        this.panel.classList.add('open');
        this.backdrop?.classList.add('show');
        document.body.style.overflow = 'hidden';

        // Load data
        await this.refresh();

        // Load dropdown options
        await this._loadDropdownOptions();
    }

    /**
     * Close the panel
     */
    close() {
        if (!this.panel) return;

        this.state.isOpen = false;
        this.panel.classList.remove('open');
        this.backdrop?.classList.remove('show');
        document.body.style.overflow = '';
    }

    /**
     * Refresh entries data
     */
    async refresh() {
        if (this.state.currentTab === 'pending') {
            await this._loadPendingEntries();
        } else {
            await this._loadHistoryEntries();
        }
    }

    /**
     * Get current pending count for badge
     * @returns {number}
     */
    getCount() {
        return this.state.entries.filter(e => e.status === 'waiting').length;
    }

    /**
     * Check if panel is open
     * @returns {boolean}
     */
    isOpen() {
        return this.state.isOpen;
    }

    // =========================================================================
    // TAB MANAGEMENT
    // =========================================================================

    _switchTab(tab) {
        if (tab === this.state.currentTab) return;

        this.state.currentTab = tab;

        // Update tab styles
        if (tab === 'pending') {
            this.tabPending?.classList.add('active');
            this.tabHistory?.classList.remove('active');
            this.contentPending.style.display = 'block';
            this.contentPending.classList.add('active');
            this.contentHistory.style.display = 'none';
            this.contentHistory.classList.remove('active');
            this._loadPendingEntries();
        } else {
            this.tabPending?.classList.remove('active');
            this.tabHistory?.classList.add('active');
            this.contentPending.style.display = 'none';
            this.contentPending.classList.remove('active');
            this.contentHistory.style.display = 'block';
            this.contentHistory.classList.add('active');
            this._loadHistoryEntries();
        }
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================

    async _loadPendingEntries() {
        this._showLoading(true);

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/waitlist?date=${this.state.currentDate}`
            );
            const data = await response.json();

            if (data.success) {
                this.state.entries = data.entries || [];
                this._renderPendingEntries();
                this._updateCount(data.count || 0);
            } else {
                this._showToast(data.error || 'Error al cargar lista', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading entries', error);
            this._showToast('Error de conexion', 'error');
        } finally {
            this._showLoading(false);
        }
    }

    async _loadHistoryEntries() {
        this._showLoading(true);

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/waitlist/history?date=${this.state.currentDate}`
            );
            const data = await response.json();

            if (data.success) {
                this.state.historyEntries = data.entries || [];
                this._renderHistoryEntries();
            } else {
                this._showToast(data.error || 'Error al cargar historial', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading history', error);
            this._showToast('Error de conexion', 'error');
        } finally {
            this._showLoading(false);
        }
    }

    async _loadDropdownOptions() {
        try {
            // Load zones
            const zonesRes = await fetch(`${this.options.apiBaseUrl}/zones`);
            const zonesData = await zonesRes.json();
            if (zonesData.success && zonesData.zones) {
                this.state.zones = zonesData.zones;
                this._populateZonesDropdown();
            }

            // Load furniture types
            const typesRes = await fetch(`${this.options.apiBaseUrl}/furniture-types`);
            const typesData = await typesRes.json();
            if (typesData.success && typesData.furniture_types) {
                this.state.furnitureTypes = typesData.furniture_types;
                this._populateFurnitureTypesDropdown();
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading options', error);
        }
    }

    _populateZonesDropdown() {
        if (!this.zonePreferenceSelect) return;

        this.zonePreferenceSelect.innerHTML = '<option value="">Sin preferencia</option>';
        this.state.zones.forEach(zone => {
            const option = document.createElement('option');
            option.value = zone.id;
            option.textContent = zone.name;
            this.zonePreferenceSelect.appendChild(option);
        });
    }

    _populateFurnitureTypesDropdown() {
        if (!this.furnitureTypeSelect) return;

        this.furnitureTypeSelect.innerHTML = '<option value="">Sin preferencia</option>';
        this.state.furnitureTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.id;
            option.textContent = type.display_name || type.name;
            this.furnitureTypeSelect.appendChild(option);
        });
    }

    // =========================================================================
    // RENDERING
    // =========================================================================

    _renderPendingEntries() {
        if (!this.entriesPending) return;

        const entries = this.state.entries;

        if (entries.length === 0) {
            this.entriesPending.innerHTML = '';
            this.emptyPending.style.display = 'flex';
            return;
        }

        this.emptyPending.style.display = 'none';

        const html = entries.map((entry, index) => this._renderEntryCard(entry, index + 1, false)).join('');
        this.entriesPending.innerHTML = html;

        // Attach action listeners
        this._attachEntryListeners(this.entriesPending);
    }

    _renderHistoryEntries() {
        if (!this.entriesHistory) return;

        const entries = this.state.historyEntries;

        if (entries.length === 0) {
            this.entriesHistory.innerHTML = '';
            this.emptyHistory.style.display = 'flex';
            return;
        }

        this.emptyHistory.style.display = 'none';

        const html = entries.map((entry, index) => this._renderEntryCard(entry, null, true)).join('');
        this.entriesHistory.innerHTML = html;
    }

    _renderEntryCard(entry, position, isHistory) {
        const statusClass = `status-${entry.status}`;
        const statusLabel = this._getStatusLabel(entry.status);
        const timeAgo = this._formatTimeAgo(entry.created_at);
        const historyClass = isHistory ? 'history-entry' : '';
        const convertedClass = entry.status === 'converted' ? 'converted' : '';

        // Build preferences chips
        let prefsHtml = '';
        if (entry.zone_name) {
            prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-map-marker-alt"></i> ${this._escapeHtml(entry.zone_name)}</span>`;
        }
        if (entry.furniture_type_name) {
            prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-umbrella-beach"></i> ${this._escapeHtml(entry.furniture_type_name)}</span>`;
        }
        if (entry.time_preference) {
            const timeLabel = this._getTimePreferenceLabel(entry.time_preference);
            prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-clock"></i> ${timeLabel}</span>`;
        }

        // Build actions (only for pending entries)
        let actionsHtml = '';
        if (!isHistory && entry.status === 'waiting') {
            actionsHtml = `
                <div class="waitlist-entry-actions">
                    <button type="button" class="btn-action" data-action="contacted" data-id="${entry.id}">
                        <i class="fas fa-phone"></i> Contactado
                    </button>
                    <button type="button" class="btn-action btn-convert" data-action="convert" data-id="${entry.id}">
                        <i class="fas fa-check"></i> Convertir
                    </button>
                    <button type="button" class="btn-action btn-danger" data-action="declined" data-id="${entry.id}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        } else if (!isHistory && entry.status === 'contacted') {
            actionsHtml = `
                <div class="waitlist-entry-actions">
                    <button type="button" class="btn-action" data-action="no_answer" data-id="${entry.id}">
                        <i class="fas fa-phone-slash"></i> Sin respuesta
                    </button>
                    <button type="button" class="btn-action btn-convert" data-action="convert" data-id="${entry.id}">
                        <i class="fas fa-check"></i> Convertir
                    </button>
                    <button type="button" class="btn-action btn-danger" data-action="declined" data-id="${entry.id}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }

        return `
            <div class="waitlist-entry ${historyClass} ${convertedClass}" data-entry-id="${entry.id}">
                <div class="waitlist-entry-header">
                    ${position ? `<div class="waitlist-entry-priority">${position}</div>` : ''}
                    <div class="waitlist-entry-customer">
                        <div class="waitlist-entry-name">${this._escapeHtml(entry.customer_name || 'Sin nombre')}</div>
                        <div class="waitlist-entry-meta">
                            ${entry.room_number ? `<i class="fas fa-door-open"></i> Hab. ${this._escapeHtml(entry.room_number)}` : ''}
                            ${entry.phone ? `<i class="fas fa-phone"></i> ${this._escapeHtml(entry.phone)}` : ''}
                            <span title="${entry.created_at}">${timeAgo}</span>
                        </div>
                    </div>
                    <span class="waitlist-entry-status ${statusClass}">${statusLabel}</span>
                </div>
                <div class="waitlist-entry-body">
                    <div class="waitlist-entry-details">
                        <span class="waitlist-entry-detail">
                            <i class="fas fa-users"></i> ${entry.num_people} personas
                        </span>
                        <span class="waitlist-entry-detail">
                            <i class="fas fa-calendar"></i> ${this._formatDateShort(entry.requested_date)}
                        </span>
                        ${entry.package_name ? `
                            <span class="waitlist-entry-detail">
                                <i class="fas fa-gift"></i> ${this._escapeHtml(entry.package_name)}
                            </span>
                        ` : ''}
                    </div>
                    ${prefsHtml ? `<div class="waitlist-entry-preferences">${prefsHtml}</div>` : ''}
                    ${entry.notes ? `<div class="waitlist-entry-notes">${this._escapeHtml(entry.notes)}</div>` : ''}
                    ${actionsHtml}
                </div>
            </div>
        `;
    }

    _attachEntryListeners(container) {
        container.querySelectorAll('.btn-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = btn.dataset.action;
                const entryId = parseInt(btn.dataset.id);
                this._handleEntryAction(entryId, action);
            });
        });
    }

    // =========================================================================
    // ENTRY ACTIONS
    // =========================================================================

    async _handleEntryAction(entryId, action) {
        if (action === 'convert') {
            this._handleConvert(entryId);
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
            const response = await fetch(`${this.options.apiBaseUrl}/waitlist/${entryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ status: newStatus })
            });

            const data = await response.json();

            if (data.success) {
                this._showToast('Estado actualizado', 'success');
                await this.refresh();
                this._dispatchCountUpdate();
            } else {
                this._showToast(data.error || 'Error al actualizar', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error updating status', error);
            this._showToast('Error de conexion', 'error');
        }
    }

    _handleConvert(entryId) {
        // Find the entry
        const entry = this.state.entries.find(e => e.id === entryId);
        if (!entry) return;

        // Close waitlist panel
        this.close();

        // Call conversion callback
        if (this.callbacks.onConvert) {
            this.callbacks.onConvert(entry);
        } else {
            // Dispatch event for other components to handle
            document.dispatchEvent(new CustomEvent('waitlist:convert', {
                detail: { entry, entryId }
            }));
        }
    }

    /**
     * Mark an entry as converted after reservation created
     * @param {number} entryId - Waitlist entry ID
     * @param {number} reservationId - Created reservation ID
     */
    async markAsConverted(entryId, reservationId) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/waitlist/${entryId}/convert`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ reservation_id: reservationId })
            });

            const data = await response.json();

            if (data.success) {
                this._showToast('Entrada convertida a reserva', 'success');
                this._dispatchCountUpdate();
            } else {
                this._showToast(data.error || 'Error al convertir', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error marking as converted', error);
        }
    }

    // =========================================================================
    // ADD ENTRY MODAL
    // =========================================================================

    _openAddModal() {
        if (!this.modal) return;

        // Reset form
        this._resetForm();

        // Set default date to current date
        if (this.dateInput) {
            this.dateInput.value = this.state.currentDate;
            this.dateInput.min = this._getTodayDate();
        }

        // Show modal
        this.modal.style.display = 'flex';
    }

    _closeAddModal() {
        if (!this.modal) return;
        this.modal.style.display = 'none';
    }

    _resetForm() {
        // Reset customer type to interno
        this._setCustomerType('interno');

        // Clear searches
        this._clearSelectedGuest();
        this._clearSelectedCustomer();

        // Reset form fields
        if (this.roomSearchInput) this.roomSearchInput.value = '';
        if (this.customerSearchInput) this.customerSearchInput.value = '';
        if (this.numPeopleInput) this.numPeopleInput.value = '2';
        if (this.timePreferenceSelect) this.timePreferenceSelect.value = '';
        if (this.zonePreferenceSelect) this.zonePreferenceSelect.value = '';
        if (this.furnitureTypeSelect) this.furnitureTypeSelect.value = '';
        if (this.notesInput) this.notesInput.value = '';
        if (this.packageSelect) this.packageSelect.value = '';

        // Reset reservation type
        const defaultRadio = document.querySelector('input[name="reservationType"][value="consumo_minimo"]');
        if (defaultRadio) defaultRadio.checked = true;
        if (this.packageGroup) this.packageGroup.style.display = 'none';

        // Hide search results
        if (this.roomResults) this.roomResults.classList.remove('show');
        if (this.customerResults) this.customerResults.classList.remove('show');
    }

    _setCustomerType(type) {
        this.state.customerType = type;

        if (this.customerTypeInput) {
            this.customerTypeInput.value = type;
        }

        // Update toggle buttons
        if (type === 'interno') {
            this.typeInterno?.classList.add('active');
            this.typeExterno?.classList.remove('active');
            if (this.roomSearchGroup) this.roomSearchGroup.style.display = 'block';
            if (this.customerSearchGroup) this.customerSearchGroup.style.display = 'none';
        } else {
            this.typeInterno?.classList.remove('active');
            this.typeExterno?.classList.add('active');
            if (this.roomSearchGroup) this.roomSearchGroup.style.display = 'none';
            if (this.customerSearchGroup) this.customerSearchGroup.style.display = 'block';
        }

        // Clear selections when switching
        this._clearSelectedGuest();
        this._clearSelectedCustomer();
    }

    _onReservationTypeChange() {
        const selected = document.querySelector('input[name="reservationType"]:checked');
        if (!selected) return;

        if (selected.value === 'paquete') {
            if (this.packageGroup) this.packageGroup.style.display = 'block';
            this._loadPackages();
        } else {
            if (this.packageGroup) this.packageGroup.style.display = 'none';
        }
    }

    async _loadPackages() {
        if (!this.packageSelect) return;

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/packages`);
            const data = await response.json();

            if (data.success && data.packages) {
                this.state.packages = data.packages;
                this.packageSelect.innerHTML = '<option value="">Seleccionar paquete...</option>';
                data.packages.forEach(pkg => {
                    const option = document.createElement('option');
                    option.value = pkg.id;
                    option.textContent = `${pkg.package_name} - ${pkg.base_price}`;
                    this.packageSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading packages', error);
        }
    }

    // =========================================================================
    // ROOM SEARCH (INTERNO)
    // =========================================================================

    _onRoomSearch(e) {
        const query = e.target.value.trim();

        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < 1) {
            if (this.roomResults) this.roomResults.classList.remove('show');
            return;
        }

        this.searchTimeout = setTimeout(() => this._searchRooms(query), this.options.debounceMs);
    }

    async _searchRooms(query) {
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/hotel-guests/search?q=${encodeURIComponent(query)}`
            );
            const data = await response.json();

            if (data.success) {
                this._renderRoomResults(data.guests || []);
            }
        } catch (error) {
            console.error('WaitlistManager: Error searching rooms', error);
        }
    }

    _renderRoomResults(guests) {
        if (!this.roomResults) return;

        if (guests.length === 0) {
            this.roomResults.innerHTML = '<div class="p-3 text-muted">No se encontraron huespedes</div>';
            this.roomResults.classList.add('show');
            return;
        }

        const html = guests.map(guest => `
            <div class="cs-item" data-guest-id="${guest.id}" data-guest-name="${this._escapeHtml(guest.guest_name || guest.first_name + ' ' + (guest.last_name || ''))}" data-room="${guest.room_number}">
                <div class="cs-info">
                    <div class="cs-name">${this._escapeHtml(guest.guest_name || guest.first_name + ' ' + (guest.last_name || ''))}</div>
                    <div class="cs-details"><i class="fas fa-door-open"></i> Hab. ${guest.room_number}</div>
                </div>
            </div>
        `).join('');

        this.roomResults.innerHTML = html;
        this.roomResults.classList.add('show');

        // Attach click listeners
        this.roomResults.querySelectorAll('.cs-item').forEach(item => {
            item.addEventListener('click', () => this._selectGuest(item));
        });
    }

    _selectGuest(item) {
        const guestId = item.dataset.guestId;
        const guestName = item.dataset.guestName;
        const roomNumber = item.dataset.room;

        // Update state
        this.state.selectedHotelGuestId = guestId;

        // Update hidden fields
        if (this.hotelGuestIdInput) this.hotelGuestIdInput.value = guestId;

        // Show selected guest
        if (this.selectedGuestEl) {
            this.selectedGuestEl.style.display = 'flex';
            if (this.guestNameEl) this.guestNameEl.textContent = guestName;
            if (this.guestRoomEl) this.guestRoomEl.textContent = `Hab. ${roomNumber}`;
        }

        // Hide search
        if (this.roomSearchInput) this.roomSearchInput.style.display = 'none';
        if (this.roomResults) this.roomResults.classList.remove('show');
    }

    _clearSelectedGuest() {
        this.state.selectedHotelGuestId = null;
        if (this.hotelGuestIdInput) this.hotelGuestIdInput.value = '';
        if (this.selectedGuestEl) this.selectedGuestEl.style.display = 'none';
        if (this.roomSearchInput) {
            this.roomSearchInput.style.display = 'block';
            this.roomSearchInput.value = '';
        }
    }

    // =========================================================================
    // CUSTOMER SEARCH (EXTERNO)
    // =========================================================================

    _onCustomerSearch(e) {
        const query = e.target.value.trim();

        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        if (query.length < 2) {
            if (this.customerResults) this.customerResults.classList.remove('show');
            return;
        }

        this.searchTimeout = setTimeout(() => this._searchCustomers(query), this.options.debounceMs);
    }

    async _searchCustomers(query) {
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}&type=externo`
            );
            const data = await response.json();

            if (data.success || data.customers) {
                this._renderCustomerResults(data.customers || []);
            }
        } catch (error) {
            console.error('WaitlistManager: Error searching customers', error);
        }
    }

    _renderCustomerResults(customers) {
        if (!this.customerResults) return;

        if (customers.length === 0) {
            this.customerResults.innerHTML = '<div class="p-3 text-muted">No se encontraron clientes</div>';
            this.customerResults.classList.add('show');
            return;
        }

        const html = customers.map(customer => {
            const name = customer.display_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim();
            return `
                <div class="cs-item" data-customer-id="${customer.id}" data-customer-name="${this._escapeHtml(name)}" data-phone="${customer.phone || ''}">
                    <div class="cs-info">
                        <div class="cs-name">${this._escapeHtml(name)}</div>
                        <div class="cs-details">${customer.phone ? `<i class="fas fa-phone"></i> ${customer.phone}` : ''}</div>
                    </div>
                </div>
            `;
        }).join('');

        this.customerResults.innerHTML = html;
        this.customerResults.classList.add('show');

        // Attach click listeners
        this.customerResults.querySelectorAll('.cs-item').forEach(item => {
            item.addEventListener('click', () => this._selectCustomer(item));
        });
    }

    _selectCustomer(item) {
        const customerId = item.dataset.customerId;
        const customerName = item.dataset.customerName;
        const phone = item.dataset.phone;

        // Update state
        this.state.selectedCustomerId = customerId;

        // Update hidden fields
        if (this.customerIdInput) this.customerIdInput.value = customerId;

        // Show selected customer
        if (this.selectedCustomerEl) {
            this.selectedCustomerEl.style.display = 'flex';
            if (this.customerNameEl) this.customerNameEl.textContent = customerName;
            if (this.customerPhoneEl) this.customerPhoneEl.textContent = phone || '-';
        }

        // Hide search
        if (this.customerSearchInput) this.customerSearchInput.style.display = 'none';
        if (this.customerResults) this.customerResults.classList.remove('show');
    }

    _clearSelectedCustomer() {
        this.state.selectedCustomerId = null;
        if (this.customerIdInput) this.customerIdInput.value = '';
        if (this.selectedCustomerEl) this.selectedCustomerEl.style.display = 'none';
        if (this.customerSearchInput) {
            this.customerSearchInput.style.display = 'block';
            this.customerSearchInput.value = '';
        }
    }

    _showCreateCustomer() {
        // Navigate to customer creation page with return URL
        const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/beach/customers/create?type=externo&return_url=${returnUrl}`;
    }

    // =========================================================================
    // FORM SUBMISSION
    // =========================================================================

    async _submitEntry() {
        // Validate customer selection
        const customerId = this.customerIdInput?.value;
        const hotelGuestId = this.hotelGuestIdInput?.value;

        if (this.state.customerType === 'interno' && !hotelGuestId) {
            this._showToast('Selecciona un huesped', 'warning');
            return;
        }

        if (this.state.customerType === 'externo' && !customerId) {
            this._showToast('Selecciona un cliente', 'warning');
            return;
        }

        // Validate date
        const requestedDate = this.dateInput?.value;
        if (!requestedDate) {
            this._showToast('La fecha es requerida', 'warning');
            return;
        }

        // Validate reservation type
        const reservationType = document.querySelector('input[name="reservationType"]:checked')?.value || 'consumo_minimo';
        if (reservationType === 'paquete' && !this.packageSelect?.value) {
            this._showToast('Selecciona un paquete', 'warning');
            return;
        }

        // Show loading
        if (this.modalSaveBtn) {
            this.modalSaveBtn.disabled = true;
            const saveText = this.modalSaveBtn.querySelector('.save-text');
            const saveLoading = this.modalSaveBtn.querySelector('.save-loading');
            if (saveText) saveText.style.display = 'none';
            if (saveLoading) saveLoading.style.display = 'flex';
        }

        try {
            // If interno (hotel guest), we need to convert to customer first
            let finalCustomerId = customerId;

            if (this.state.customerType === 'interno' && hotelGuestId) {
                // Convert hotel guest to customer
                const convertResponse = await fetch(`${this.options.apiBaseUrl}/customers/from-hotel-guest`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ hotel_guest_id: parseInt(hotelGuestId) })
                });

                const convertData = await convertResponse.json();
                if (!convertData.success) {
                    throw new Error(convertData.error || 'Error al convertir huesped');
                }
                finalCustomerId = convertData.customer.id;
            }

            // Build payload
            const payload = {
                customer_id: parseInt(finalCustomerId),
                requested_date: requestedDate,
                num_people: parseInt(this.numPeopleInput?.value) || 2,
                preferred_zone_id: this.zonePreferenceSelect?.value ? parseInt(this.zonePreferenceSelect.value) : null,
                preferred_furniture_type_id: this.furnitureTypeSelect?.value ? parseInt(this.furnitureTypeSelect.value) : null,
                time_preference: this.timePreferenceSelect?.value || null,
                reservation_type: reservationType,
                package_id: reservationType === 'paquete' ? parseInt(this.packageSelect?.value) : null,
                notes: this.notesInput?.value?.trim() || null
            };

            const response = await fetch(`${this.options.apiBaseUrl}/waitlist`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                this._showToast(data.message || 'Agregado a lista de espera', 'success');
                this._closeAddModal();
                await this.refresh();
                this._dispatchCountUpdate();
            } else {
                this._showToast(data.error || 'Error al crear entrada', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error submitting entry', error);
            this._showToast(error.message || 'Error de conexion', 'error');
        } finally {
            // Reset button
            if (this.modalSaveBtn) {
                this.modalSaveBtn.disabled = false;
                const saveText = this.modalSaveBtn.querySelector('.save-text');
                const saveLoading = this.modalSaveBtn.querySelector('.save-loading');
                if (saveText) saveText.style.display = 'inline-flex';
                if (saveLoading) saveLoading.style.display = 'none';
            }
        }
    }

    // =========================================================================
    // UTILITIES
    // =========================================================================

    _showLoading(show) {
        if (this.loadingEl) {
            this.loadingEl.style.display = show ? 'flex' : 'none';
        }
    }

    _updateCount(count) {
        if (this.pendingCount) {
            this.pendingCount.textContent = count;
        }
    }

    _dispatchCountUpdate() {
        // Dispatch event for badge updates
        document.dispatchEvent(new CustomEvent('waitlist:countUpdate', {
            detail: { count: this.getCount() }
        }));

        // Call callback if provided
        if (this.callbacks.onCountUpdate) {
            this.callbacks.onCountUpdate(this.getCount());
        }
    }

    _showToast(message, type = 'info') {
        if (window.PuroBeach?.showToast) {
            window.PuroBeach.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    _getTodayDate() {
        const today = new Date();
        return today.toISOString().split('T')[0];
    }

    _formatDateDisplay(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr + 'T12:00:00');
            return date.toLocaleDateString('es-ES', {
                weekday: 'short',
                day: 'numeric',
                month: 'short'
            });
        } catch (e) {
            return dateStr;
        }
    }

    _formatDateShort(dateStr) {
        if (!dateStr) return '-';
        try {
            const date = new Date(dateStr);
            const day = date.getDate().toString().padStart(2, '0');
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            return `${day}/${month}`;
        } catch (e) {
            return dateStr;
        }
    }

    _formatTimeAgo(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return 'Ahora';
            if (diffMins < 60) return `hace ${diffMins} min`;
            if (diffHours < 24) return `hace ${diffHours}h`;
            if (diffDays === 1) return 'Ayer';
            return `hace ${diffDays} dias`;
        } catch (e) {
            return '';
        }
    }

    _getStatusLabel(status) {
        const labels = {
            'waiting': 'En espera',
            'contacted': 'Contactado',
            'converted': 'Convertido',
            'declined': 'Rechazado',
            'no_answer': 'Sin respuesta',
            'expired': 'Expirado'
        };
        return labels[status] || status;
    }

    _getTimePreferenceLabel(pref) {
        const labels = {
            'morning': 'Manana',
            'manana': 'Manana',
            'afternoon': 'Tarde',
            'tarde': 'Tarde',
            'mediodia': 'Mediodia',
            'all_day': 'Todo el dia',
            'todo_el_dia': 'Todo el dia'
        };
        return labels[pref] || pref;
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WaitlistManager;
}

// Make available globally
window.WaitlistManager = WaitlistManager;
