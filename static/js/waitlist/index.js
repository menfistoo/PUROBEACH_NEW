/**
 * WaitlistManager - Main Entry Point
 * Coordinates all modules into the WaitlistManager class
 */

import { createInitialState, createCallbacks, createOptions } from './state.js';
import { cacheElements } from './dom.js';
import { formatDateDisplay, showToast, getTodayDate } from './utils.js';
import * as api from './api.js';
import * as renderers from './renderers.js';
import * as actions from './actions.js';
import * as modal from './modal.js';
import * as search from './search.js';
import * as formHandler from './form-handler.js';

/**
 * WaitlistManager class - manages the waitlist panel functionality
 */
class WaitlistManager {
    constructor(options = {}) {
        this.options = createOptions(options);
        this.state = createInitialState(options);
        this.callbacks = createCallbacks(options);

        // CSRF Token
        this.csrfToken = document.getElementById('waitlistCsrfToken')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';

        // Timers
        this.searchTimeout = null;

        // Cache DOM elements
        this.elements = cacheElements();

        // Initialize
        if (this.elements.panel) {
            this._attachListeners();
        }
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================

    _attachListeners() {
        const { elements } = this;

        // Panel close
        elements.closeBtn?.addEventListener('click', () => this.close());
        elements.backdrop?.addEventListener('click', () => this.close());

        // Add buttons
        elements.addBtn?.addEventListener('click', () => this.openAddModal());
        elements.footerAddBtn?.addEventListener('click', () => this.openAddModal());

        // Tab switching
        elements.tabPending?.addEventListener('click', () => this._switchTab('pending'));
        elements.tabHistory?.addEventListener('click', () => this._switchTab('history'));

        // Modal
        elements.modalBackdrop?.addEventListener('click', () => this.closeAddModal());
        elements.modalCloseBtn?.addEventListener('click', () => this.closeAddModal());
        elements.modalCancelBtn?.addEventListener('click', () => this.closeAddModal());
        elements.modalSaveBtn?.addEventListener('click', () => this._submitEntry());

        // Customer type toggle
        elements.typeInterno?.addEventListener('click', () => this.setCustomerType('interno'));
        elements.typeExterno?.addEventListener('click', () => this.setCustomerType('externo'));

        // Room search
        elements.roomSearchInput?.addEventListener('input', (e) => search.onRoomSearch(this, e));
        elements.clearGuestBtn?.addEventListener('click', () => modal.clearSelectedGuest(this));

        // Customer search
        elements.customerSearchInput?.addEventListener('input', (e) => search.onCustomerSearch(this, e));
        elements.clearCustomerBtn?.addEventListener('click', () => modal.clearSelectedCustomer(this));
        elements.createCustomerBtn?.addEventListener('click', () => modal.showCreateCustomer());

        // Reservation type change
        elements.reservationTypeRadios?.forEach(radio => {
            radio.addEventListener('change', () => this.onReservationTypeChange());
        });

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (elements.modal?.style.display !== 'none') {
                    this.closeAddModal();
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
        if (this.elements.dateDisplay) {
            this.elements.dateDisplay.textContent = formatDateDisplay(date);
        }
        if (this.state.isOpen) {
            this.refresh();
        }
    }

    /**
     * Open the panel and load data
     */
    async open() {
        if (!this.elements.panel) return;

        this.state.isOpen = true;

        // Update date display
        if (this.elements.dateDisplay) {
            this.elements.dateDisplay.textContent = formatDateDisplay(this.state.currentDate);
        }

        // Show panel
        this.elements.panel.classList.add('open');
        this.elements.backdrop?.classList.add('show');
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
        if (!this.elements.panel) return;

        this.state.isOpen = false;
        this.elements.panel.classList.remove('open');
        this.elements.backdrop?.classList.remove('show');
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

    /**
     * Mark an entry as converted after reservation created
     * @param {number} entryId - Waitlist entry ID
     * @param {number} reservationId - Created reservation ID
     */
    async markAsConverted(entryId, reservationId) {
        await actions.markAsConverted(this, entryId, reservationId);
    }

    // =========================================================================
    // TAB MANAGEMENT
    // =========================================================================

    _switchTab(tab) {
        if (tab === this.state.currentTab) return;

        this.state.currentTab = tab;
        const { elements } = this;

        // Update tab styles
        if (tab === 'pending') {
            elements.tabPending?.classList.add('active');
            elements.tabHistory?.classList.remove('active');
            elements.contentPending.style.display = 'block';
            elements.contentPending.classList.add('active');
            elements.contentHistory.style.display = 'none';
            elements.contentHistory.classList.remove('active');
            this._loadPendingEntries();
        } else {
            elements.tabPending?.classList.remove('active');
            elements.tabHistory?.classList.add('active');
            elements.contentPending.style.display = 'none';
            elements.contentPending.classList.remove('active');
            elements.contentHistory.style.display = 'block';
            elements.contentHistory.classList.add('active');
            this._loadHistoryEntries();
        }
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================

    async _loadPendingEntries() {
        this._showLoading(true);

        try {
            const result = await api.loadPendingEntries(this.options.apiBaseUrl, this.state.currentDate);

            if (result.success) {
                this.state.entries = result.entries || [];
                renderers.renderPendingEntries(
                    this.elements,
                    this.state.entries,
                    (entryId, action) => actions.handleEntryAction(this, entryId, action)
                );
                this._updateCount(result.count || 0);
            } else {
                showToast(result.error || 'Error al cargar lista', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading entries', error);
            showToast('Error de conexion', 'error');
        } finally {
            this._showLoading(false);
        }
    }

    async _loadHistoryEntries() {
        this._showLoading(true);

        try {
            const result = await api.loadHistoryEntries(this.options.apiBaseUrl, this.state.currentDate);

            if (result.success) {
                this.state.historyEntries = result.entries || [];
                renderers.renderHistoryEntries(this.elements, this.state.historyEntries);
            } else {
                showToast(result.error || 'Error al cargar historial', 'error');
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading history', error);
            showToast('Error de conexion', 'error');
        } finally {
            this._showLoading(false);
        }
    }

    async _loadDropdownOptions() {
        try {
            // Load zones
            const zonesResult = await api.loadZones(this.options.apiBaseUrl);
            if (zonesResult.success && zonesResult.zones) {
                this.state.zones = zonesResult.zones;
                renderers.populateZonesDropdown(this.elements.zonePreferenceSelect, this.state.zones);
            }

            // Load furniture types
            const typesResult = await api.loadFurnitureTypes(this.options.apiBaseUrl);
            if (typesResult.success && typesResult.furniture_types) {
                this.state.furnitureTypes = typesResult.furniture_types;
                renderers.populateFurnitureTypesDropdown(this.elements.furnitureTypeSelect, this.state.furnitureTypes);
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading options', error);
        }
    }

    // =========================================================================
    // MODAL METHODS (delegated)
    // =========================================================================

    openAddModal() {
        modal.openAddModal(this);
    }

    closeAddModal() {
        modal.closeAddModal(this);
    }

    resetForm() {
        modal.resetForm(this);
    }

    setCustomerType(type) {
        modal.setCustomerType(this, type);
    }

    onReservationTypeChange() {
        modal.onReservationTypeChange(this);
    }

    // =========================================================================
    // FORM SUBMISSION
    // =========================================================================

    async _submitEntry() {
        await formHandler.submitEntry(this);
    }

    // =========================================================================
    // UTILITIES
    // =========================================================================

    _showLoading(show) {
        if (this.elements.loadingEl) {
            this.elements.loadingEl.style.display = show ? 'flex' : 'none';
        }
    }

    _updateCount(count) {
        if (this.elements.pendingCount) {
            this.elements.pendingCount.textContent = count;
        }
    }
}

// Export for ES modules
export { WaitlistManager };

// Also expose on window for legacy compatibility
window.WaitlistManager = WaitlistManager;
