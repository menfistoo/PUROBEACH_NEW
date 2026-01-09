/**
 * ReservationPanelBase - Base class for the reservation panel
 *
 * Handles:
 * - Configuration and state initialization
 * - DOM element caching (120+ references)
 * - Basic event listener setup
 * - Swipe gesture support for mobile
 * - Map data integration
 *
 * This class is extended by mixins to add specific functionality.
 */

import { showToast } from './utils.js';

// =============================================================================
// RESERVATION PANEL BASE CLASS
// =============================================================================

export class ReservationPanelBase {
    /**
     * Create a new ReservationPanelBase instance
     * @param {Object} options - Configuration options
     * @param {string} options.apiBaseUrl - Base URL for API calls (default: '/beach/api')
     * @param {number} options.animationDuration - Animation duration in ms (default: 300)
     * @param {number} options.swipeThreshold - Swipe threshold in px (default: 100)
     * @param {string} options.context - Context mode: 'map' or 'standalone' (default: 'map')
     * @param {Function} options.onClose - Callback when panel is closed
     * @param {Function} options.onSave - Callback when changes are saved
     * @param {Function} options.onStateChange - Callback when reservation state changes
     * @param {Function} options.onFurnitureReassign - Callback for furniture reassignment
     * @param {Function} options.onCustomerChange - Callback when customer is changed
     */
    constructor(options = {}) {
        // Merge options with defaults
        this.options = {
            apiBaseUrl: '/beach/api',
            animationDuration: 300,
            swipeThreshold: 100,
            context: 'map', // 'map' or 'standalone'
            onClose: null,
            onSave: null,
            onStateChange: null,
            onFurnitureReassign: null,
            onCustomerChange: null,
            ...options
        };

        // Context mode (map = inside map page, standalone = reservations list page)
        this.context = this.options.context;

        // Main panel state
        this.state = {
            isOpen: false,
            isCollapsed: false,
            mode: 'view', // 'view', 'edit', or 'reassignment'
            reservationId: null,
            currentDate: null,
            data: null,           // Current reservation data
            originalData: null,   // Original data for dirty checking
            isDirty: false,
            isLoading: false,
            isSubmitting: false,
            numPeopleManuallyEdited: false  // Track if user manually edited num_people
        };

        // Reassignment state (separate for clarity)
        this.reassignmentState = {
            originalFurniture: [],    // Original furniture IDs for reference
            selectedFurniture: [],    // New selection (furniture IDs)
            maxAllowed: 2             // Max furniture = num_people
        };

        // Preferences editing state
        this.preferencesEditState = {
            isEditing: false,
            allPreferences: [],       // All available preferences from server
            selectedCodes: [],        // Currently selected preference codes
            originalCodes: []         // Original codes for dirty checking
        };

        // Pricing editing state
        this.pricingEditState = {
            originalPrice: 0,         // Original price from reservation
            calculatedPrice: 0,       // System-calculated price
            availablePackages: [],    // Available packages from API
            selectedPackageId: null,  // Currently selected package
            isModified: false         // Whether user manually modified price
        };

        // Touch gesture tracking
        this.swipe = {
            startX: 0,
            currentX: 0,
            isDragging: false
        };

        // Customer search debounce timer
        this.customerSearchTimer = null;

        // Map data reference (set by BeachMap)
        this.mapData = null;

        // States data (can be set independently for standalone mode)
        this.states = [];

        // Initialize DOM and event listeners
        this.cacheElements();
        this.attachListeners();
    }

    // =========================================================================
    // DOM ELEMENT CACHING
    // =========================================================================

    /**
     * Cache DOM element references for performance
     * Called once during construction to avoid repeated DOM queries
     */
    cacheElements() {
        // Main panel and backdrop
        this.panel = document.getElementById('reservationPanel');
        this.backdrop = document.getElementById('reservationPanelBackdrop');

        if (!this.panel || !this.backdrop) {
            console.warn('ReservationPanelBase: Required elements not found in DOM');
            return;
        }

        // Header elements
        this.toggleBtn = document.getElementById('panelToggleBtn');
        this.toggleIcon = document.getElementById('panelToggleIcon');
        this.closeBtn = document.getElementById('panelCloseBtn');
        this.editBtn = document.getElementById('panelEditBtn');
        this.editIcon = document.getElementById('panelEditIcon');
        this.ticketEl = document.getElementById('panelTicket');
        this.dateEl = document.getElementById('panelDate');

        // Loading/content containers
        this.loadingEl = document.getElementById('panelLoading');
        this.contentEl = document.getElementById('panelContent');

        // Customer section - Compact display
        this.customerSection = document.getElementById('customerSection');
        this.customerDisplay = document.getElementById('customerDisplay');
        this.customerName = document.getElementById('customerName');
        this.customerRoomBadge = document.getElementById('customerRoomBadge');
        this.customerRoom = document.getElementById('customerRoom');
        this.roomChangeIndicator = document.getElementById('roomChangeIndicator');
        this.customerVipBadge = document.getElementById('customerVipBadge');
        this.customerHotelInfo = document.getElementById('customerHotelInfo');
        this.customerCheckin = document.getElementById('customerCheckin');
        this.customerCheckout = document.getElementById('customerCheckout');
        this.customerBookingRef = document.getElementById('customerBookingRef');
        this.customerBookingItem = document.getElementById('customerBookingItem');
        this.customerContact = document.getElementById('customerContact');
        this.customerPhone = document.getElementById('customerPhone');
        this.customerChangeBtn = document.getElementById('customerChangeBtn');
        this.customerSearchWrapper = document.getElementById('customerSearchWrapper');
        this.customerSearchInput = document.getElementById('panelCustomerSearch');
        this.customerSearchResults = document.getElementById('panelCustomerResults');
        this.roomGuestSelector = document.getElementById('roomGuestSelector');
        this.roomGuestSelect = document.getElementById('roomGuestSelect');

        // Preferences section
        this.preferencesSection = document.getElementById('preferencesSection');
        this.preferencesChipsContainer = document.getElementById('panelPreferencesChips');
        this.preferencesViewMode = document.getElementById('preferencesViewMode');
        this.preferencesEditMode = document.getElementById('preferencesEditMode');
        this.preferencesAllChips = document.getElementById('panelAllPreferencesChips');

        // State section
        this.stateChipsContainer = document.getElementById('panelStateChips');

        // State history section (collapsible)
        this.stateHistorySection = document.getElementById('stateHistorySection');
        this.stateHistoryToggle = document.getElementById('stateHistoryToggle');
        this.stateHistoryContent = document.getElementById('stateHistoryContent');
        this.stateHistoryList = document.getElementById('stateHistoryList');

        // Furniture section - View mode
        this.furnitureViewMode = document.getElementById('furnitureViewMode');
        this.furnitureChipsContainer = document.getElementById('panelFurnitureChips');
        this.furnitureChangeBtn = document.getElementById('panelChangeFurnitureBtn');
        this.furnitureSummary = document.getElementById('furnitureSummary');

        // Furniture section - Reassignment mode
        this.furnitureReassignmentMode = document.getElementById('furnitureReassignmentMode');
        this.reassignmentOriginalChips = document.getElementById('reassignmentOriginalChips');
        this.reassignmentNewChips = document.getElementById('reassignmentNewChips');
        this.reassignmentCounter = document.getElementById('reassignmentCounter');
        this.reassignmentCancelBtn = document.getElementById('reassignmentCancelBtn');
        this.reassignmentSaveBtn = document.getElementById('reassignmentSaveBtn');

        // Details section - View mode
        this.detailsViewMode = document.getElementById('detailsViewMode');
        this.detailNumPeople = document.getElementById('detailNumPeople');
        this.detailNotes = document.getElementById('detailNotes');

        // Details section - Edit mode
        this.detailsEditMode = document.getElementById('detailsEditMode');
        this.editReservationDate = document.getElementById('editReservationDate');
        this.editNumPeople = document.getElementById('editNumPeople');
        this.editNotes = document.getElementById('editNotes');

        // Pricing section - View mode
        this.pricingSection = document.getElementById('pricingSection');
        this.pricingViewMode = document.getElementById('pricingViewMode');
        this.detailTotalPrice = document.getElementById('detailTotalPrice');
        this.detailPricingBreakdown = document.getElementById('detailPricingBreakdown');

        // Pricing section - Edit mode
        this.pricingEditMode = document.getElementById('pricingEditMode');
        this.panelPricingDisplay = document.getElementById('panelPricingDisplay');
        this.panelPricingTypeSelector = document.getElementById('panelPricingTypeSelector');
        this.panelPricingTypeSelect = document.getElementById('panelPricingTypeSelect');
        this.panelFinalPriceInput = document.getElementById('panelFinalPriceInput');
        this.panelPriceResetBtn = document.getElementById('panelPriceResetBtn');
        this.panelCalculatedPrice = document.getElementById('panelCalculatedPrice');
        this.panelPricingBreakdown = document.getElementById('panelPricingBreakdown');
        this.panelPriceOverride = document.getElementById('panelPriceOverride');
        this.panelSelectedPackageId = document.getElementById('panelSelectedPackageId');

        // Payment section
        this.paymentSection = document.getElementById('paymentSection');
        this.paymentViewMode = document.getElementById('paymentViewMode');
        this.paymentEditMode = document.getElementById('paymentEditMode');
        this.detailPaymentTicket = document.getElementById('detailPaymentTicket');
        this.detailPaymentMethod = document.getElementById('detailPaymentMethod');
        this.editPaymentTicket = document.getElementById('editPaymentTicket');
        this.editPaymentMethod = document.getElementById('editPaymentMethod');

        // Footer
        this.footer = document.getElementById('panelFooter');
        this.cancelBtn = document.getElementById('panelCancelBtn');
        this.saveBtn = document.getElementById('panelSaveBtn');

        // CSRF token
        this.csrfToken = document.getElementById('panelCsrfToken')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================

    /**
     * Attach event listeners to DOM elements
     * Sets up all basic interactions - specific functionality is added by mixins
     */
    attachListeners() {
        if (!this.panel) return;

        // Toggle button (collapse/expand)
        this.toggleBtn?.addEventListener('click', () => this.toggleCollapse());

        // Close button
        this.closeBtn?.addEventListener('click', () => this.close());

        // Backdrop click
        this.backdrop?.addEventListener('click', () => this.close());

        // Edit button toggle
        this.editBtn?.addEventListener('click', () => this.toggleEditMode());

        // Cancel button
        this.cancelBtn?.addEventListener('click', () => this.exitEditMode(true));

        // Save button
        this.saveBtn?.addEventListener('click', () => this.saveChanges());

        // Room guest selector (for interno customers in edit mode)
        this.roomGuestSelect?.addEventListener('change', (e) => this.handleRoomGuestChange(e));

        // State history toggle
        this.stateHistoryToggle?.addEventListener('click', () => this.toggleStateHistory());

        // Customer search input
        this.customerSearchInput?.addEventListener('input', (e) => this.handleCustomerSearch(e));

        // Furniture change button
        this.furnitureChangeBtn?.addEventListener('click', () => this.enterReassignmentMode());

        // Reassignment mode buttons
        this.reassignmentCancelBtn?.addEventListener('click', () => this.exitReassignmentMode(true));
        this.reassignmentSaveBtn?.addEventListener('click', () => this.saveReassignment());

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isOpen) {
                if (this.state.mode === 'reassignment') {
                    this.exitReassignmentMode(true);
                } else if (this.state.mode === 'edit') {
                    this.exitEditMode(true);
                } else {
                    this.close();
                }
            }
        });

        // Swipe to close (mobile)
        this.setupSwipeGestures();

        // Track dirty state on edit inputs
        this.editReservationDate?.addEventListener('change', (e) => this.handleDateChange(e));
        this.editNumPeople?.addEventListener('input', () => {
            this.state.numPeopleManuallyEdited = true;
            this.markDirty();
        });
        this.editNotes?.addEventListener('input', () => this.markDirty());

        // Pricing event listeners
        this.setupPricingEventListeners();
    }

    /**
     * Setup pricing-related event listeners
     * Handles price input, reset button, and package selector
     */
    setupPricingEventListeners() {
        // Price input manual change
        this.panelFinalPriceInput?.addEventListener('input', () => {
            const manualPrice = parseFloat(this.panelFinalPriceInput.value) || 0;
            const calculatedPrice = this.pricingEditState.calculatedPrice || 0;

            if (Math.abs(manualPrice - calculatedPrice) > 0.01) {
                // Price has been manually modified
                this.panelFinalPriceInput.classList.add('modified');
                this.panelPriceOverride.value = manualPrice.toFixed(2);
                if (this.panelCalculatedPrice) this.panelCalculatedPrice.style.display = 'block';
                if (this.panelPriceResetBtn) this.panelPriceResetBtn.style.display = 'block';
                this.pricingEditState.isModified = true;
            } else {
                // Price matches calculated, remove override
                this.panelFinalPriceInput.classList.remove('modified');
                this.panelPriceOverride.value = '';
                if (this.panelCalculatedPrice) this.panelCalculatedPrice.style.display = 'none';
                if (this.panelPriceResetBtn) this.panelPriceResetBtn.style.display = 'none';
                this.pricingEditState.isModified = false;
            }
            this.markDirty();
        });

        // Reset button
        this.panelPriceResetBtn?.addEventListener('click', () => {
            const calculatedPrice = this.pricingEditState.calculatedPrice || 0;
            this.panelFinalPriceInput.value = calculatedPrice.toFixed(2);
            this.panelFinalPriceInput.classList.remove('modified');
            this.panelPriceOverride.value = '';
            if (this.panelCalculatedPrice) this.panelCalculatedPrice.style.display = 'none';
            if (this.panelPriceResetBtn) this.panelPriceResetBtn.style.display = 'none';
            this.pricingEditState.isModified = false;
        });

        // Package selector change
        this.panelPricingTypeSelect?.addEventListener('change', () => {
            const selectedValue = this.panelPricingTypeSelect.value;
            this.panelSelectedPackageId.value = selectedValue;
            this.pricingEditState.selectedPackageId = selectedValue ? parseInt(selectedValue) : null;
            this.calculateAndUpdatePricing();
            this.markDirty();
        });
    }

    /**
     * Setup swipe-to-close gesture for mobile devices
     * Allows swiping the panel to the right to close it
     */
    setupSwipeGestures() {
        if (!this.panel) return;

        this.panel.addEventListener('touchstart', (e) => {
            // Only start swipe if touching the header or panel edge
            const touch = e.touches[0];
            const panelRect = this.panel.getBoundingClientRect();

            // Allow swipe from right edge (within 40px) or header
            const isRightEdge = touch.clientX > panelRect.right - 40;
            const isHeader = e.target.closest('.panel-header');

            if (isRightEdge || isHeader) {
                this.swipe.isDragging = true;
                this.swipe.startX = touch.clientX;
                this.panel.classList.add('dragging');
            }
        });

        this.panel.addEventListener('touchmove', (e) => {
            if (!this.swipe.isDragging) return;

            this.swipe.currentX = e.touches[0].clientX;
            const deltaX = this.swipe.currentX - this.swipe.startX;

            // Only allow dragging right (positive delta)
            if (deltaX > 0) {
                this.panel.style.transform = `translateX(${deltaX}px)`;
            }
        });

        this.panel.addEventListener('touchend', () => {
            if (!this.swipe.isDragging) return;

            this.swipe.isDragging = false;
            this.panel.classList.remove('dragging');

            const deltaX = this.swipe.currentX - this.swipe.startX;

            if (deltaX > this.options.swipeThreshold) {
                this.close();
            } else {
                // Snap back
                this.panel.style.transform = '';
            }
        });
    }

    // =========================================================================
    // MAP DATA INTEGRATION
    // =========================================================================

    /**
     * Set map data reference for states, colors, etc.
     * Called by BeachMap when the panel is integrated with the map
     * @param {Object} data - Map data object containing states and other info
     */
    setMapData(data) {
        this.mapData = data;
        // Also extract states from mapData
        if (data?.states) {
            this.states = data.states;
        }
    }

    /**
     * Set states independently (for standalone mode without full map data)
     * @param {Array} states - Array of state objects [{id, name, code, color, icon, ...}]
     */
    setStates(states) {
        this.states = states || [];
    }

    /**
     * Fetch states from API (for standalone mode)
     * @returns {Promise<Array>} Array of state objects
     */
    async fetchStates() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/states`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.states) {
                    this.states = result.states;
                    return result.states;
                }
            }
        } catch (error) {
            console.error('Failed to fetch states:', error);
        }
        return [];
    }

    /**
     * Check if running in standalone mode (outside of map context)
     * @returns {boolean} True if in standalone mode
     */
    isStandalone() {
        return this.context === 'standalone';
    }

    // =========================================================================
    // STATE MANAGEMENT HELPERS
    // =========================================================================

    /**
     * Show/hide loading state in the panel
     * @param {boolean} show - Whether to show loading state
     */
    showLoading(show) {
        this.state.isLoading = show;
        if (this.loadingEl) this.loadingEl.style.display = show ? 'flex' : 'none';
        if (this.contentEl) this.contentEl.style.display = show ? 'none' : 'block';
    }

    /**
     * Mark the form as dirty (has unsaved changes)
     * Used to prompt user before closing if changes are pending
     */
    markDirty() {
        this.state.isDirty = true;
    }

    /**
     * Show toast notification
     * Delegates to the imported showToast utility function
     * @param {string} message - Message to display
     * @param {string} type - Toast type: 'info', 'success', 'warning', 'error'
     */
    showToast(message, type = 'info') {
        showToast(message, type);
    }

    // =========================================================================
    // ABSTRACT METHODS (to be implemented by mixins/subclasses)
    // =========================================================================

    /**
     * Toggle collapsed state
     * @abstract Should be implemented by panel-core mixin
     */
    toggleCollapse() {
        console.warn('ReservationPanelBase: toggleCollapse() not implemented');
    }

    /**
     * Close the panel
     * @abstract Should be implemented by panel-core mixin
     */
    close() {
        console.warn('ReservationPanelBase: close() not implemented');
    }

    /**
     * Toggle between view and edit modes
     * @abstract Should be implemented by edit mixin
     */
    toggleEditMode() {
        console.warn('ReservationPanelBase: toggleEditMode() not implemented');
    }

    /**
     * Exit edit mode
     * @param {boolean} discard - Whether to discard changes
     * @abstract Should be implemented by edit mixin
     */
    exitEditMode(discard = false) {
        console.warn('ReservationPanelBase: exitEditMode() not implemented');
    }

    /**
     * Save changes
     * @abstract Should be implemented by edit mixin
     */
    saveChanges() {
        console.warn('ReservationPanelBase: saveChanges() not implemented');
    }

    /**
     * Show customer search input
     * @abstract Should be implemented by customer mixin
     */
    showCustomerSearch() {
        console.warn('ReservationPanelBase: showCustomerSearch() not implemented');
    }

    /**
     * Toggle state history section
     * @abstract Should be implemented by state mixin
     */
    toggleStateHistory() {
        console.warn('ReservationPanelBase: toggleStateHistory() not implemented');
    }

    /**
     * Handle customer search input
     * @param {Event} event - Input event
     * @abstract Should be implemented by customer mixin
     */
    handleCustomerSearch(event) {
        console.warn('ReservationPanelBase: handleCustomerSearch() not implemented');
    }

    /**
     * Handle room guest selection change
     * @param {Event} event - Change event
     * @abstract Should be implemented by customer mixin
     */
    handleRoomGuestChange(event) {
        console.warn('ReservationPanelBase: handleRoomGuestChange() not implemented');
    }

    /**
     * Enter customer edit mode
     * @abstract Should be implemented by customer mixin
     */
    enterCustomerEditMode() {
        console.warn('ReservationPanelBase: enterCustomerEditMode() not implemented');
    }

    /**
     * Exit customer edit mode
     * @abstract Should be implemented by customer mixin
     */
    exitCustomerEditMode() {
        console.warn('ReservationPanelBase: exitCustomerEditMode() not implemented');
    }

    /**
     * Handle reservation date change
     * @param {Event} event - Change event from date input
     * @abstract Should be implemented by save mixin or details mixin
     */
    handleDateChange(event) {
        console.warn('ReservationPanelBase: handleDateChange() not implemented');
    }

    /**
     * Enter reassignment mode
     * @abstract Should be implemented by furniture mixin
     */
    enterReassignmentMode() {
        console.warn('ReservationPanelBase: enterReassignmentMode() not implemented');
    }

    /**
     * Enter reassignment mode for a specific date (used when changing reservation date)
     * @param {string} targetDate - The date to reassign furniture for
     * @abstract Should be implemented by furniture mixin
     */
    enterReassignmentModeForDate(targetDate) {
        // For now, fall back to regular reassignment mode
        // The furniture mixin can override this to handle date-specific behavior
        console.warn('ReservationPanelBase: enterReassignmentModeForDate() using fallback');
        this.enterReassignmentMode();
    }

    /**
     * Exit reassignment mode
     * @param {boolean} cancel - Whether to cancel without saving
     * @abstract Should be implemented by furniture mixin
     */
    exitReassignmentMode(cancel = false) {
        console.warn('ReservationPanelBase: exitReassignmentMode() not implemented');
    }

    /**
     * Save furniture reassignment
     * @abstract Should be implemented by furniture mixin
     */
    saveReassignment() {
        console.warn('ReservationPanelBase: saveReassignment() not implemented');
    }

    /**
     * Calculate and update pricing
     * @abstract Should be implemented by pricing mixin
     */
    calculateAndUpdatePricing() {
        console.warn('ReservationPanelBase: calculateAndUpdatePricing() not implemented');
    }

    /**
     * Destroy the panel instance and clean up
     */
    destroy() {
        // Subclasses should override to add cleanup logic
    }
}

// =============================================================================
// EXPORTS
// =============================================================================

export default ReservationPanelBase;
