/**
 * ReservationPanel V2 - Bundled
 * Auto-generated bundle of all V2 panel modules
 * DO NOT EDIT - modify source files in reservation-panel-v2/ instead
 */


// =============================================================================
// SOURCE: reservation-panel-v2/utils.js
// =============================================================================

/**
 * ReservationPanel Utility Functions
 *
 * Standalone utility functions extracted from ReservationPanel for reuse
 * across panel modules and other components.
 */

// =============================================================================
// HTML UTILITIES
// =============================================================================

/**
 * Escape HTML entities to prevent XSS when inserting user data into innerHTML
 * @param {string} str - String to escape
 * @returns {string} Escaped string safe for HTML insertion
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// =============================================================================
// NAME UTILITIES
// =============================================================================

/**
 * Get initials from first and last name
 * @param {string} firstName - First name
 * @param {string} lastName - Last name
 * @returns {string} Initials (uppercase) or '?' if no name provided
 */
function getInitials(firstName, lastName) {
    const first = (firstName || '')[0] || '';
    const last = (lastName || '')[0] || '';
    return (first + last).toUpperCase() || '?';
}

// =============================================================================
// DATE FORMATTING
// =============================================================================

/**
 * Format date for display with weekday, day, and month
 * @param {string} dateStr - Date string in any parseable format
 * @returns {string} Formatted date (e.g., "lun., 15 ene.") or original string if parsing fails
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        // Handle various date formats
        let date;
        if (dateStr.includes('T')) {
            date = new Date(dateStr);
        } else {
            date = new Date(dateStr + 'T00:00:00');
        }

        if (isNaN(date.getTime())) {
            return dateStr; // Return original if parsing fails
        }

        return date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    } catch (e) {
        return dateStr;
    }
}

/**
 * Format date in short format (DD/MM)
 * @param {string} dateStr - Date string in any parseable format
 * @returns {string} Formatted date (e.g., "15/01") or '-' if no date
 */
function formatDateShort(dateStr) {
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

/**
 * Parse any date string to YYYY-MM-DD format for comparison
 * @param {string} dateStr - Date string in any format
 * @returns {string} Date in YYYY-MM-DD format or original string if parsing fails
 */
function parseDateToYMD(dateStr) {
    if (!dateStr) return '';
    try {
        // If already in YYYY-MM-DD format
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return dateStr;
        }
        // If ISO format (YYYY-MM-DDTHH:MM:SS)
        const isoMatch = dateStr.match(/^(\d{4}-\d{2}-\d{2})T/);
        if (isoMatch) {
            return isoMatch[1];
        }
        // Any other format - parse with Date and extract components
        const date = new Date(dateStr);
        if (!isNaN(date.getTime())) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return dateStr;
    } catch (e) {
        return dateStr;
    }
}

// =============================================================================
// FURNITURE UTILITIES
// =============================================================================

/**
 * Get emoji icon for furniture type based on name
 * @param {string} typeName - Furniture type name (e.g., "hamaca", "balinesa")
 * @returns {string} Emoji icon for the furniture type
 */
function getFurnitureIcon(typeName) {
    const icons = {
        'hamaca': '🛏️',
        'balinesa': '🛖',
        'sombrilla': '☂️',
        'mesa': '🪑'
    };
    const lowerType = (typeName || '').toLowerCase();
    for (const [key, icon] of Object.entries(icons)) {
        if (lowerType.includes(key)) return icon;
    }
    return '🪑';
}

// =============================================================================
// NOTIFICATIONS
// =============================================================================

/**
 * Show toast notification using global PuroBeach toast system
 * Falls back to console.log if toast system is not available
 * @param {string} message - Message to display
 * @param {string} type - Toast type: 'info', 'success', 'warning', 'error'
 * @param {number|boolean} duration - Duration in ms, 0 or false for persistent (default: 5000)
 * @param {string} toastId - Optional ID for programmatic dismissal
 */
function showToast(message, type = 'info', duration = 5000, toastId = null) {
    if (window.PuroBeach?.showToast) {
        window.PuroBeach.showToast(message, type, duration, toastId);
    } else {
        console.log(`[${type}] ${message}`);
    }
}

/**
 * Dismiss a toast by its ID
 * @param {string} toastId - The toast ID to dismiss
 */
function dismissToast(toastId) {
    if (window.PuroBeach?.dismissToast) {
        window.PuroBeach.dismissToast(toastId);
    }
}

// =============================================================================
// SOURCE: reservation-panel-v2/panel-base.js
// =============================================================================

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


// =============================================================================
// RESERVATION PANEL BASE CLASS
// =============================================================================

class ReservationPanelBase {
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
            onCustomerChange: null,
            ...options
        };

        // Context mode (map = inside map page, standalone = reservations list page)
        this.context = this.options.context;

        // Main panel state
        this.state = {
            isOpen: false,
            isCollapsed: false,
            mode: 'view', // 'view' or 'edit'
            reservationId: null,
            currentDate: null,
            data: null,           // Current reservation data
            originalData: null,   // Original data for dirty checking
            isDirty: false,
            isLoading: false,
            isSubmitting: false,
            numPeopleManuallyEdited: false  // Track if user manually edited num_people
        };

        // Preferences editing state
        this.preferencesEditState = {
            isEditing: false,
            allPreferences: [],       // All available preferences from server
            selectedCodes: [],        // Currently selected preference codes
            originalCodes: []         // Original codes for dirty checking
        };

        // Tags editing state
        this.tagsEditState = {
            isEditing: false,
            allTags: [],              // All available tags from server
            selectedIds: [],          // Currently selected tag IDs
            originalIds: []           // Original IDs for dirty checking
        };

        // Pricing editing state
        this.pricingEditState = {
            originalPrice: 0,         // Original price from reservation
            calculatedPrice: 0,       // System-calculated price
            availablePackages: [],    // Available packages from API
            availablePolicies: [],    // Available min consumption policies
            selectedPackageId: null,  // Currently selected package
            selectedPolicyId: null,   // Currently selected min consumption policy ('auto' or ID)
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
        this.collapseBtn = document.getElementById('reservationCollapseBtn');
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

        // Tags section
        this.tagsSection = document.getElementById('tagsSection');
        this.tagChipsContainer = document.getElementById('panelTagChips');
        this.tagsViewMode = document.getElementById('tagsViewMode');
        this.tagsEditModeEl = document.getElementById('tagsEditMode');
        this.tagsAllChips = document.getElementById('panelAllTagChips');

        // State section
        this.stateChipsContainer = document.getElementById('panelStateChips');

        // State history section (collapsible)
        this.stateHistorySection = document.getElementById('stateHistorySection');
        this.stateHistoryToggle = document.getElementById('stateHistoryToggle');
        this.stateHistoryContent = document.getElementById('stateHistoryContent');
        this.stateHistoryList = document.getElementById('stateHistoryList');

        // Furniture section
        this.furnitureViewMode = document.getElementById('furnitureViewMode');
        this.furnitureChipsContainer = document.getElementById('panelFurnitureChips');
        this.moveModeBtn = document.getElementById('panelMoveModeBtn');
        this.furnitureSummary = document.getElementById('furnitureSummary');

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
        this.panelMinConsumptionSelector = document.getElementById('panelMinConsumptionSelector');
        this.panelMinConsumptionSelect = document.getElementById('panelMinConsumptionSelect');
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

        // Toggle buttons (collapse/expand)
        this.toggleBtn?.addEventListener('click', () => this.toggleCollapse());
        this.collapseBtn?.addEventListener('click', () => this.toggleCollapse());

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

        // Move mode button - enters global move mode from this reservation
        this.moveModeBtn?.addEventListener('click', () => this.enterMoveMode());

        // Furniture lock toggle
        this.initFurnitureLock();

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isOpen) {
                if (this.state.mode === 'edit') {
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

        // Minimum consumption policy selector change
        this.panelMinConsumptionSelect?.addEventListener('change', () => {
            const selectedValue = this.panelMinConsumptionSelect.value;
            this.pricingEditState.selectedPolicyId = selectedValue === 'auto' ? null : parseInt(selectedValue);
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

default ReservationPanelBase;

// =============================================================================
// SOURCE: reservation-panel-v2/panel-lifecycle.js
// =============================================================================

/**
 * Panel Lifecycle Mixin
 *
 * Handles the panel's lifecycle operations:
 * - Opening and closing the panel
 * - Loading reservation data from API
 * - Rendering content orchestration
 * - Collapse/expand functionality
 * - Error display
 */


// =============================================================================
// PANEL LIFECYCLE MIXIN
// =============================================================================

/**
 * Mixin that adds lifecycle management methods to a panel class.
 * Handles opening, closing, loading data, and rendering orchestration.
 *
 * @param {class} Base - The base class to extend
 * @returns {class} Extended class with lifecycle methods
 */
const PanelLifecycleMixin = (Base) => class extends Base {

    // =========================================================================
    // OPEN / CLOSE
    // =========================================================================

    /**
     * Open the panel with reservation data
     * @param {number} reservationId - The reservation ID to load
     * @param {string} date - The current date (YYYY-MM-DD)
     * @param {string} mode - 'view' or 'edit'
     */
    async open(reservationId, date, mode = 'view') {
        if (!this.panel) {
            console.error('ReservationPanel: Panel element not found');
            return;
        }

        // Set state
        this.state.reservationId = reservationId;
        this.state.currentDate = date;
        this.state.mode = mode;
        this.state.isOpen = true;

        // Notify modal state manager (closes other modals, bottom bar, controls map)
        if (window.modalStateManager) {
            window.modalStateManager.openModal('reservation', this);
        }
        this.state.isDirty = false;
        this.state.numPeopleManuallyEdited = false;  // Reset flag when opening new reservation

        // Show loading state
        this.showLoading(true);

        // Show panel and backdrop
        this.backdrop.classList.add('show');
        this.panel.classList.add('open');

        // Handle standalone vs map context
        if (this.isStandalone()) {
            this.panel.classList.add('standalone');
            this.backdrop.classList.add('standalone');
            // Don't lock body scroll in standalone mode - page should scroll normally
        } else {
            // Only lock body scroll in map context (overlay mode)
            document.body.style.overflow = 'hidden';
        }

        // Adjust map canvas if on tablet/desktop (only in map context)
        if (!this.isStandalone()) {
            const mapWrapper = document.querySelector('.map-canvas-wrapper');
            if (mapWrapper && window.innerWidth >= 768) {
                mapWrapper.classList.add('panel-open');
            }
        }

        // In standalone mode, fetch states if not already loaded
        if (this.isStandalone() && this.states.length === 0) {
            await this.fetchStates();
        }

        // Load reservation data
        await this.loadReservation(reservationId, date);

        // Apply mode
        if (mode === 'edit') {
            this.enterEditMode();
        } else {
            this.exitEditMode(false);
        }

        // Highlight reservation furniture on the map (after mode is applied)
        this.highlightReservationFurniture();
    }

    /**
     * Close the panel
     */
    async close() {
        if (!this.state.isOpen) return;

        // Remove furniture highlights from map
        this.unhighlightReservationFurniture();

        // Check for unsaved changes
        if (this.state.mode === 'edit' && this.state.isDirty) {
            const confirmed = await (window.PuroBeach
                ? window.PuroBeach.confirmAction({
                    title: 'Cambios sin guardar',
                    message: 'Tienes cambios sin guardar. ¿Seguro que quieres cerrar?',
                    confirmText: 'Cerrar',
                    confirmClass: 'btn-warning',
                    iconClass: 'fa-exclamation-triangle'
                })
                : Promise.resolve(confirm('Tienes cambios sin guardar. ¿Seguro que quieres cerrar?')));
            if (!confirmed) return;
        }

        // Reset state
        this.state.isOpen = false;
        this.state.isCollapsed = false;
        this.state.mode = 'view';
        this.state.isDirty = false;

        // Notify modal state manager
        if (window.modalStateManager) {
            window.modalStateManager.closeModal('reservation');
        }

        // Hide panel and backdrop
        this.backdrop.classList.remove('show');
        this.panel.classList.remove('open');
        this.panel.classList.remove('collapsed');
        this.panel.classList.remove('edit-mode');
        this.panel.classList.remove('standalone');
        this.backdrop.classList.remove('standalone');
        this.panel.style.transform = '';
        document.body.style.overflow = '';

        // Remove map canvas adjustment (only in map context)
        if (!this.isStandalone()) {
            const mapWrapper = document.querySelector('.map-canvas-wrapper');
            if (mapWrapper) {
                mapWrapper.classList.remove('panel-open');
            }
        }

        // Hide customer search
        this.hideCustomerSearch();

        // Callback
        if (this.options.onClose) {
            this.options.onClose();
        }
    }

    // =========================================================================
    // COLLAPSE / EXPAND
    // =========================================================================

    /**
     * Toggle collapsed state
     */
    toggleCollapse() {
        if (!this.state.isOpen) return;

        const wasCollapsed = this.state.isCollapsed;
        this.state.isCollapsed = !this.state.isCollapsed;

        // Notify modal state manager
        if (window.modalStateManager) {
            if (this.state.isCollapsed) {
                window.modalStateManager.collapseModal('reservation');
            } else {
                window.modalStateManager.expandModal('reservation');
            }
        }

        // Get map canvas wrapper
        const mapWrapper = document.querySelector('.map-canvas-wrapper');

        if (this.state.isCollapsed) {
            this.panel.classList.add('collapsed');

            // Hide backdrop - allow map interaction
            if (this.backdrop) {
                this.backdrop.classList.remove('show');
            }

            // Remove map adjustment - let map fill full width
            if (mapWrapper) {
                mapWrapper.classList.remove('panel-open');
            }

            // Update button label
            if (this.toggleBtn) {
                this.toggleBtn.setAttribute('aria-label', 'Expandir panel');
                this.toggleBtn.setAttribute('title', 'Expandir');
            }
        } else {
            this.panel.classList.remove('collapsed');

            // Show backdrop again
            if (this.backdrop) {
                this.backdrop.classList.add('show');
            }

            // Add map adjustment - make room for panel
            if (mapWrapper) {
                mapWrapper.classList.add('panel-open');
            }

            // Update button label
            if (this.toggleBtn) {
                this.toggleBtn.setAttribute('aria-label', 'Colapsar panel');
                this.toggleBtn.setAttribute('title', 'Colapsar');
            }
        }
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================

    /**
     * Load reservation data from API
     * @param {number} reservationId - The reservation ID to load
     * @param {string} date - The date for the reservation details
     */
    async loadReservation(reservationId, date) {
        try {
            // Use the dedicated panel endpoint for full reservation + customer data
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${reservationId}/details?date=${date}`
            );

            if (!response.ok) {
                throw new Error('Error al cargar la reserva');
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Reserva no encontrada');
            }

            this.state.data = result;
            this.renderContent(result);
            this.showLoading(false);

        } catch (error) {
            console.error('Error loading reservation:', error);
            this.showError(error.message);
        }
    }

    // =========================================================================
    // CONTENT RENDERING
    // =========================================================================

    /**
     * Render all panel content
     * @param {Object} data - The reservation data from API
     */
    renderContent(data) {
        const res = data.reservation;
        const customer = data.customer;

        // Header - ticket number and date
        this.ticketEl.textContent = `Reserva #${res.ticket_number || res.id}`;
        this.dateEl.textContent = formatDate(res.reservation_date || res.start_date);

        // Render sections
        this.renderCustomerSection(customer);
        this.renderPreferencesSection(customer);
        this.renderTagsSection(res);
        this.renderStateSection(res);
        this.renderFurnitureSection(res);
        this.renderDetailsSection(res);
        this.renderPricingSection(res);
        this.renderPaymentSection(res);

        // Load state history (async, non-blocking)
        this.loadStateHistory(res.id);
    }

    // =========================================================================
    // ERROR HANDLING
    // =========================================================================

    /**
     * Show error state in panel
     * @param {string} message - Error message to display
     */
    showError(message) {
        this.showLoading(false);

        if (this.contentEl) {
            this.contentEl.innerHTML = `
                <div class="text-center text-danger py-4">
                    <i class="fas fa-exclamation-circle fa-3x mb-3"></i>
                    <p>${message}</p>
                    <button class="btn btn-outline-primary mt-2" onclick="document.getElementById('reservationPanel').__panel?.close()">
                        Cerrar
                    </button>
                </div>
            `;
            this.contentEl.style.display = 'block';
        }
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/edit-mode-mixin.js
// =============================================================================

/**
 * Edit Mode Mixin for ReservationPanel
 *
 * Handles switching between view and edit modes, including:
 * - toggleEditMode() - Switch between modes
 * - enterEditMode() - Activate edit mode with UI changes
 * - exitEditMode() - Return to view mode with optional discard confirmation
 *
 * Dependencies (provided by other mixins):
 * - highlightReservationFurniture() - From furniture mixin
 * - unhighlightReservationFurniture() - From furniture mixin
 * - enterPreferencesEditMode() - From preferences mixin
 * - exitPreferencesEditMode() - From preferences mixin
 * - enterPricingEditMode() - From pricing mixin
 * - exitPricingEditMode() - From pricing mixin
 * - hideCustomerSearch() - From customer mixin
 */

/**
 * Mixin that adds edit mode functionality to ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with edit mode methods
 */
const EditModeMixin = (Base) => class extends Base {

    /**
     * Toggle between view and edit modes
     */
    toggleEditMode() {
        if (this.state.mode === 'view') {
            this.enterEditMode();
        } else {
            this.exitEditMode(false);
        }
    }

    /**
     * Enter edit mode
     * - Sets mode to 'edit'
     * - Adds 'edit-mode' class to panel
     * - Updates edit button icon to eye (view mode indicator)
     * - Highlights reservation furniture on map
     * - Shows edit fields, hides view fields
     * - Pre-fills edit fields with current values
     * - Stores original data for dirty checking
     */
    async enterEditMode() {
        this.state.mode = 'edit';
        this.panel.classList.add('edit-mode');

        // Update edit button icon to indicate we're in edit mode
        if (this.editIcon) {
            this.editIcon.className = 'fas fa-eye';
        }

        // Highlight furniture on map
        this.highlightReservationFurniture();

        // Show edit fields, hide view fields for details section
        if (this.detailsViewMode) this.detailsViewMode.style.display = 'none';
        if (this.detailsEditMode) this.detailsEditMode.style.display = 'grid';

        // Show pricing edit mode, hide view mode
        if (this.pricingViewMode) this.pricingViewMode.style.display = 'none';
        if (this.pricingEditMode) this.pricingEditMode.style.display = 'block';

        // Show payment edit mode, hide view mode
        if (this.paymentViewMode) this.paymentViewMode.style.display = 'none';
        if (this.paymentEditMode) this.paymentEditMode.style.display = 'grid';

        // Pre-fill edit fields with current values (only if not manually edited)
        if (this.state.data) {
            const data = this.state.data;
            // Pre-fill date
            if (this.editReservationDate) {
                this.editReservationDate.value = data.reservation?.reservation_date ||
                    data.reservation?.start_date ||
                    this.state.currentDate || '';
                // Set minimum date to today to prevent past dates
                const today = new Date().toISOString().split('T')[0];
                this.editReservationDate.min = today;
            }
            if (this.editNumPeople && !this.state.numPeopleManuallyEdited) {
                this.editNumPeople.value = data.reservation?.num_people || 1;
            }
            if (this.editNotes) {
                this.editNotes.value = data.reservation?.notes || '';
            }
            // Pre-fill payment fields
            if (this.editPaymentTicket) {
                this.editPaymentTicket.value = data.reservation?.payment_ticket_number || '';
            }
            if (this.editPaymentMethod) {
                this.editPaymentMethod.value = data.reservation?.payment_method || '';
            }
        }

        // Store original data for dirty checking
        this.state.originalData = {
            reservation_date: this.editReservationDate?.value,
            num_people: this.editNumPeople?.value,
            notes: this.editNotes?.value,
            price: this.panelFinalPriceInput?.value,
            payment_ticket_number: this.editPaymentTicket?.value,
            payment_method: this.editPaymentMethod?.value,
            minimum_consumption_policy_id: this.state.data?.reservation?.minimum_consumption_policy_id || null,
            package_id: this.state.data?.reservation?.package_id || null
        };

        // Enter customer edit mode (shows guest dropdown for interno, search for externo)
        this.enterCustomerEditMode();

        // Also enter preferences edit mode
        await this.enterPreferencesEditMode();

        // Enter tags edit mode
        await this.enterTagsEditMode();

        // Enter pricing edit mode - fetch packages and calculate pricing
        await this.enterPricingEditMode();
    }

    /**
     * Exit edit mode
     * - Optionally confirms discard if there are unsaved changes
     * - Sets mode back to 'view'
     * - Resets dirty and numPeopleManuallyEdited flags
     * - Removes 'edit-mode' class from panel
     * - Updates edit button icon to pen (edit mode indicator)
     * - Unhighlights reservation furniture on map
     * - Shows view fields, hides edit fields
     * - Exits preferences and pricing edit modes
     * - Hides customer search
     *
     * @param {boolean} discard - Whether to discard changes (prompts confirmation if dirty)
     */
    async exitEditMode(discard = false) {
        // Check for unsaved changes if discarding
        if (discard && this.state.isDirty) {
            const confirmed = await (window.PuroBeach
                ? window.PuroBeach.confirmAction({
                    title: 'Cambios sin guardar',
                    message: 'Tienes cambios sin guardar. ¿Descartar cambios?',
                    confirmText: 'Descartar',
                    confirmClass: 'btn-warning',
                    iconClass: 'fa-exclamation-triangle'
                })
                : Promise.resolve(confirm('Tienes cambios sin guardar. ¿Descartar cambios?')));
            if (!confirmed) return;
        }

        this.state.mode = 'view';
        this.state.isDirty = false;
        this.state.numPeopleManuallyEdited = false;  // Reset flag when exiting edit mode
        this.panel.classList.remove('edit-mode');

        // Update edit button icon to indicate we're in view mode
        if (this.editIcon) {
            this.editIcon.className = 'fas fa-pen';
        }

        // Re-highlight furniture on the map (stays visible in view mode)
        this.highlightReservationFurniture();

        // Show view fields, hide edit fields for details section
        if (this.detailsViewMode) this.detailsViewMode.style.display = 'grid';
        if (this.detailsEditMode) this.detailsEditMode.style.display = 'none';

        // Show pricing view mode, hide edit mode
        if (this.pricingViewMode) this.pricingViewMode.style.display = 'block';
        if (this.pricingEditMode) this.pricingEditMode.style.display = 'none';

        // Show payment view mode, hide edit mode
        if (this.paymentViewMode) this.paymentViewMode.style.display = 'grid';
        if (this.paymentEditMode) this.paymentEditMode.style.display = 'none';

        // Exit preferences edit mode
        this.exitPreferencesEditMode(discard);

        // Exit tags edit mode
        this.exitTagsEditMode(discard);

        // Exit pricing edit mode
        this.exitPricingEditMode(discard);

        // Exit customer edit mode
        this.exitCustomerEditMode();
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/save-mixin.js
// =============================================================================

/**
 * ReservationPanel Save Mixin
 *
 * Handles saving all changes made in edit mode - reservation updates and
 * customer preferences. Orchestrates multiple API calls and updates local state.
 *
 * Extracted from reservation-panel.js as part of the modular refactoring.
 */


// =============================================================================
// SAVE MIXIN
// =============================================================================

/**
 * Mixin that adds save functionality to the ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with save methods
 */
const SaveMixin = (Base) => class extends Base {

    /**
     * Handle reservation date change
     * Checks availability and either changes the date directly or shows conflict modal
     *
     * @param {Event} event - Change event from date input
     * @returns {Promise<void>}
     */
    async handleDateChange(event) {
        const newDate = event.target.value;
        const originalDate = this.state.originalData?.reservation_date;

        // Skip if same date
        if (newDate === originalDate) return;

        // Validate not a past date
        const today = new Date().toISOString().split('T')[0];
        if (newDate < today) {
            showToast('No se puede cambiar a una fecha pasada', 'error');
            this.editReservationDate.value = originalDate;
            return;
        }

        try {
            // Check availability on new date
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/check-date-availability`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ new_date: newDate })
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al verificar disponibilidad');
            }

            if (result.all_available) {
                // All furniture available - change date directly
                await this._changeDateDirectly(newDate);
            } else {
                // Furniture unavailable - show conflict modal
                await this._showDateConflictModal(newDate, originalDate, result);
            }

        } catch (error) {
            console.error('Date change error:', error);
            showToast(error.message, 'error');
            this.editReservationDate.value = originalDate;
        }
    }

    /**
     * Show modal when furniture is unavailable on new date
     * @private
     * @param {string} newDate - The new date
     * @param {string} originalDate - The original date to revert to
     * @param {object} availabilityResult - Result from check-date-availability
     */
    async _showDateConflictModal(newDate, originalDate, availabilityResult) {
        // Get SafeguardModal instance
        const SafeguardModal = window.SafeguardModal;
        if (!SafeguardModal) {
            // Fallback if modal not available
            showToast('El mobiliario no está disponible. Usa Modo Mover para cambiar.', 'warning');
            this.editReservationDate.value = originalDate;
            return;
        }

        const modal = SafeguardModal.getInstance();

        // Format date for display
        const formattedDate = new Date(newDate + 'T12:00:00').toLocaleDateString('es-ES', {
            weekday: 'long',
            day: 'numeric',
            month: 'long'
        });

        // Build conflict list HTML
        const conflicts = availabilityResult.conflicts || [];
        let conflictHtml = '';
        if (conflicts.length > 0) {
            const conflictItems = conflicts.map(c => {
                const furnitureName = c.furniture_number || `#${c.furniture_id}`;
                const customerName = c.customer_name || 'Otra reserva';
                return `<span class="blocking-item">${furnitureName}</span>`;
            }).join(' ');
            conflictHtml = `
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Mobiliario ocupado:</span>
                    </div>
                    <div class="blocking-list" style="margin-top: 8px;">
                        ${conflictItems}
                    </div>
                </div>
            `;
        }

        // Show modal
        const action = await modal.show({
            title: 'Mobiliario no disponible',
            type: 'warning',
            message: `
                <p>El mobiliario actual no está disponible para el <strong>${formattedDate}</strong>.</p>
                ${conflictHtml}
                <div class="safeguard-note" style="margin-top: 12px;">
                    <i class="fas fa-info-circle"></i>
                    <span>Puedes continuar sin mobiliario y asignarlo con el <strong>Modo Mover</strong>.</span>
                </div>
            `,
            buttons: [
                { label: 'Cancelar', action: 'cancel', style: 'secondary' },
                { label: 'Continuar', action: 'continue', style: 'primary', icon: 'fas fa-arrow-right' }
            ]
        });

        if (action === 'continue') {
            // User wants to continue without furniture
            await this._changeDateWithoutFurniture(newDate);
        } else {
            // User cancelled - revert date input
            this.editReservationDate.value = originalDate;
        }
    }

    /**
     * Change date and clear furniture, then activate move mode
     * @private
     * @param {string} newDate - The new date
     */
    async _changeDateWithoutFurniture(newDate) {
        try {
            // Call API with clear_furniture flag
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-date`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        new_date: newDate,
                        clear_furniture: true
                    })
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al cambiar fecha');
            }

            // Store reservation ID for move mode
            const reservationId = this.state.reservationId;

            // Close the panel
            this.close();

            // Navigate map to new date and activate move mode
            if (window.moveMode) {
                // Navigate map to new date first
                if (window.beachMap && typeof window.beachMap.goToDate === 'function') {
                    await window.beachMap.goToDate(newDate);
                }

                // Activate move mode (this also loads unassigned reservations)
                await window.moveMode.activate(newDate);

                // Update toolbar button state
                const moveModeBtn = document.getElementById('btn-move-mode');
                if (moveModeBtn) {
                    moveModeBtn.classList.add('active');
                }
                document.querySelector('.beach-map-container')?.classList.add('move-mode-active');

                // Show success toast
                const formattedDate = new Date(newDate + 'T12:00:00').toLocaleDateString('es-ES', {
                    day: 'numeric',
                    month: 'short'
                });
                showToast(`Reserva movida al ${formattedDate} - selecciona mobiliario`, 'info');
            } else {
                // Fallback if move mode not available
                showToast('Reserva movida. Usa Modo Mover para asignar mobiliario.', 'warning');
            }

            // Notify parent to refresh map
            if (this.options.onSave) {
                this.options.onSave(reservationId, { date_changed: true, furniture_cleared: true });
            }

        } catch (error) {
            console.error('Date change without furniture error:', error);
            showToast(error.message || 'Error al cambiar fecha', 'error');
        }
    }

    /**
     * Change reservation date directly (when all furniture is available)
     * @private
     * @param {string} newDate - The new date in YYYY-MM-DD format
     */
    async _changeDateDirectly(newDate) {
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/change-date`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ new_date: newDate })
                }
            );

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al cambiar fecha');
            }

            // Update local state
            if (this.state.data?.reservation) {
                this.state.data.reservation.reservation_date = newDate;
                this.state.data.reservation.start_date = newDate;
            }
            this.state.currentDate = newDate;
            this.state.originalData.reservation_date = newDate;

            // Update header date display
            if (this.dateEl) {
                this.dateEl.textContent = this._formatDate(newDate);
            }

            // Notify parent to refresh map for old and new dates
            if (this.options.onDateChange) {
                this.options.onDateChange(this.state.reservationId, newDate);
            }

            showToast('Fecha actualizada', 'success');
            this.markDirty();

        } catch (error) {
            console.error('Date change error:', error);
            showToast(error.message, 'error');
            // Revert date input
            this.editReservationDate.value = this.state.originalData?.reservation_date;
        }
    }

    /**
     * Format date for display
     * @private
     * @param {string} dateStr - Date string in YYYY-MM-DD format
     * @returns {string} Formatted date string
     */
    _formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr + 'T12:00:00');
        return date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    }

    /**
     * Save changes made in edit mode
     *
     * Collects all changed values from edit fields, validates them,
     * and sends updates to the server. Also handles preference changes
     * for the customer separately.
     *
     * @returns {Promise<void>}
     */
    async saveChanges() {
        // Guard against double-submit
        if (this.state.isSubmitting) return;

        const updates = {};
        let hasChanges = false;
        let preferencesChanged = false;
        let priceChanged = false;

        // ---------------------------------------------------------------------
        // Collect changed values
        // ---------------------------------------------------------------------

        // Number of people
        if (this.editNumPeople && this.editNumPeople.value !== this.state.originalData?.num_people) {
            updates.num_people = parseInt(this.editNumPeople.value) || 1;
            hasChanges = true;
        }

        // Observations/notes
        if (this.editNotes && this.editNotes.value !== this.state.originalData?.notes) {
            updates.observations = this.editNotes.value;
            hasChanges = true;
        }

        // Price and package
        if (this.panelFinalPriceInput) {
            const currentPrice = this.panelFinalPriceInput.value;
            const originalPrice = this.state.originalData?.price;
            if (currentPrice !== originalPrice) {
                updates.total_price = parseFloat(currentPrice) || 0;
                priceChanged = true;
                hasChanges = true;
            }

            // Also include package_id if changed
            const selectedPackageId = this.pricingEditState?.selectedPackageId;
            const originalPackageId = this.state.originalData?.package_id;
            if (selectedPackageId !== originalPackageId) {
                updates.package_id = selectedPackageId || null;
                hasChanges = true;
            }
        }

        // Minimum consumption policy
        const selectedPolicyId = this.pricingEditState?.selectedPolicyId;
        const originalPolicyId = this.state.originalData?.minimum_consumption_policy_id;
        if (selectedPolicyId !== originalPolicyId) {
            updates.minimum_consumption_policy_id = selectedPolicyId || null;
            hasChanges = true;
        }

        // Payment ticket number
        if (this.editPaymentTicket) {
            const currentTicket = this.editPaymentTicket.value.trim();
            const originalTicket = this.state.originalData?.payment_ticket_number || '';
            if (currentTicket !== originalTicket) {
                updates.payment_ticket_number = currentTicket || null;
                hasChanges = true;
            }
        }

        // Payment method
        if (this.editPaymentMethod) {
            const currentMethod = this.editPaymentMethod.value;
            const originalMethod = this.state.originalData?.payment_method || '';
            if (currentMethod !== originalMethod) {
                updates.payment_method = currentMethod || null;
                hasChanges = true;
            }
        }

        // ---------------------------------------------------------------------
        // Auto-toggle paid when payment details are filled
        // ---------------------------------------------------------------------
        const hasPaymentTicket = this.editPaymentTicket?.value.trim();
        const hasPaymentMethod = this.editPaymentMethod?.value;
        if (hasPaymentTicket || hasPaymentMethod) {
            const currentPaid = this.state.data?.reservation?.paid;
            if (!currentPaid) {
                updates.paid = 1;
                hasChanges = true;
            }
        }

        // ---------------------------------------------------------------------
        // Check if preferences have changed
        // ---------------------------------------------------------------------
        const originalCodes = this.preferencesEditState.originalCodes || [];
        const selectedCodes = this.preferencesEditState.selectedCodes || [];
        preferencesChanged = JSON.stringify(originalCodes.sort()) !== JSON.stringify(selectedCodes.sort());

        // ---------------------------------------------------------------------
        // Check if tags have changed
        // ---------------------------------------------------------------------
        const originalTagIds = [...(this.tagsEditState.originalIds || [])].sort();
        const selectedTagIds = [...(this.tagsEditState.selectedIds || [])].sort();
        const tagsChanged = JSON.stringify(originalTagIds) !== JSON.stringify(selectedTagIds);

        // Include tag_ids in the main updates payload to avoid a separate API call
        if (tagsChanged) {
            updates.tag_ids = this.tagsEditState.selectedIds;
            hasChanges = true;
        }

        // Exit early if no changes
        if (!hasChanges && !preferencesChanged) {
            this.exitEditMode(false);
            return;
        }

        // ---------------------------------------------------------------------
        // Show loading state on save button
        // ---------------------------------------------------------------------
        this.state.isSubmitting = true;
        this.saveBtn.querySelector('.save-text').style.display = 'none';
        this.saveBtn.querySelector('.save-loading').style.display = 'inline-flex';
        this.saveBtn.disabled = true;

        try {
            // -----------------------------------------------------------------
            // Save reservation updates if any
            // -----------------------------------------------------------------
            if (hasChanges) {
                const response = await fetch(
                    `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/update`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        },
                        body: JSON.stringify(updates)
                    }
                );

                const result = await response.json();

                if (!result.success) {
                    throw new Error(result.error || 'Error al guardar reserva');
                }

                // Update local data
                if (this.state.data?.reservation) {
                    Object.assign(this.state.data.reservation, updates);
                }

                // Re-render sections with new data
                this.renderDetailsSection(this.state.data.reservation);
                this.renderPricingSection(this.state.data.reservation);
                this.renderPaymentSection(this.state.data.reservation);
            }

            // -----------------------------------------------------------------
            // Save preferences if changed
            // -----------------------------------------------------------------
            if (preferencesChanged) {
                const customerId = this.state.data?.customer?.id;
                if (customerId) {
                    const prefResponse = await fetch(
                        `${this.options.apiBaseUrl}/customers/${customerId}/preferences`,
                        {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': this.csrfToken
                            },
                            body: JSON.stringify({ preference_codes: selectedCodes })
                        }
                    );

                    const prefResult = await prefResponse.json();

                    if (!prefResult.success) {
                        throw new Error(prefResult.error || 'Error al guardar preferencias');
                    }

                    // Update local customer data with new preferences
                    const allPrefs = this.preferencesEditState.allPreferences;
                    const newPrefs = selectedCodes.map(code => {
                        return allPrefs.find(p => p.code === code);
                    }).filter(Boolean);

                    if (this.state.data?.customer) {
                        this.state.data.customer.preferences = newPrefs;
                    }
                }
            }

            // Also save characteristics to the reservation itself
            if (preferencesChanged) {
                await fetch(
                    `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/update`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        },
                        body: JSON.stringify({
                            preferences: selectedCodes.join(',')
                        })
                    }
                );
            }

            // -----------------------------------------------------------------
            // Update local tag data if tags changed
            // -----------------------------------------------------------------
            if (tagsChanged) {
                const allTags = this.tagsEditState.allTags;
                const newTags = this.tagsEditState.selectedIds.map(id => {
                    return allTags.find(t => t.id === id);
                }).filter(Boolean);

                if (this.state.data?.reservation) {
                    this.state.data.reservation.tags = newTags;
                }

                this.renderTagsSection(this.state.data?.reservation);
            }

            // -----------------------------------------------------------------
            // Exit edit mode and notify
            // -----------------------------------------------------------------
            this.state.isDirty = false;
            this.state.numPeopleManuallyEdited = false;  // Reset flag after successful save
            this.exitEditMode(false);

            // Call onSave callback if provided
            if (this.options.onSave) {
                this.options.onSave(this.state.reservationId, {
                    ...updates,
                    preferences_changed: preferencesChanged,
                    tags_changed: tagsChanged
                });
            }

            showToast('Reserva actualizada', 'success');

        } catch (error) {
            console.error('Save error:', error);
            showToast(error.message, 'error');
        } finally {
            // Reset button state
            this.state.isSubmitting = false;
            this.saveBtn.querySelector('.save-text').style.display = 'inline-flex';
            this.saveBtn.querySelector('.save-loading').style.display = 'none';
            this.saveBtn.disabled = false;
        }
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/customer-mixin.js
// =============================================================================

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
const CustomerMixin = (Base) => class extends Base {

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
            this.customerName.href = '#';
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
     * Render customer name as clickable link to customer details
     * @private
     * @param {Object} customer - Customer data
     */
    _renderCustomerName(customer) {
        if (!this.customerName) return;

        this.customerName.textContent = customer.full_name ||
            `${customer.first_name || ''} ${customer.last_name || ''}`.trim() ||
            'Sin nombre';

        // Set link to customer details page
        if (customer.id) {
            this.customerName.href = `/beach/customers/${customer.id}`;
            this.customerName.title = 'Ver detalles del cliente';
        } else {
            this.customerName.href = '#';
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
                        'X-CSRFToken': this.csrfToken
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
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}`
            );

            if (!response.ok) {
                throw new Error('Error en la busqueda');
            }

            const result = await response.json();
            this.renderCustomerSearchResults(result);

        } catch (error) {
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
        const hotelGuests = result.hotel_guests || [];

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
                        'X-CSRFToken': this.csrfToken
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

// =============================================================================
// SOURCE: reservation-panel-v2/state-mixin.js
// =============================================================================

/**
 * ReservationPanel State Mixin
 *
 * Handles all reservation state management functionality:
 * - Rendering state section with clickable chip buttons
 * - Handling state change clicks with API calls
 * - Loading and displaying state history timeline
 * - Toggling state history visibility
 *
 * @module reservation-panel-v2/state-mixin
 */


// =============================================================================
// STATE MIXIN
// =============================================================================

/**
 * State mixin factory function
 * Adds reservation state display, change, and history functionality to the panel
 *
 * @param {class} Base - Base class to extend
 * @returns {class} Extended class with state functionality
 *
 * @example
 * class ReservationPanel extends StateMixin(PreferencesMixin(BasePanel)) {
 *     // Panel implementation
 * }
 */
const StateMixin = (Base) => class extends Base {

    // =========================================================================
    // STATE SECTION RENDERING
    // =========================================================================

    /**
     * Render state section with clickable chip buttons
     * Displays all active states as chips with the current state highlighted
     *
     * @param {Object} reservation - Reservation data object
     * @param {string} reservation.current_state - Current state name
     * @param {string} reservation.display_color - Color to use if no states available
     */
    renderStateSection(reservation) {
        if (!this.stateChipsContainer) return;

        const currentState = reservation.current_state;
        // Use this.states (populated from mapData or setStates/fetchStates)
        const states = this.states || [];
        const activeStates = states.filter(s => s.active !== false);

        // If no states available, show current state as static chip
        if (activeStates.length === 0) {
            this.stateChipsContainer.innerHTML = `
                <span class="state-chip active" style="background: ${reservation.display_color || '#6C757D'}; border-color: ${reservation.display_color || '#6C757D'};">
                    ${escapeHtml(currentState || 'Sin estado')}
                </span>
            `;
            return;
        }

        // Render all active states as clickable chips
        const chipsHtml = activeStates.map(state => {
            const isActive = state.name === currentState;
            const bgColor = isActive ? state.color : 'transparent';
            const textColor = isActive ? '#FFFFFF' : 'var(--color-secondary)';

            return `
                <button type="button"
                        class="state-chip ${isActive ? 'active' : ''}"
                        data-state="${state.name}"
                        data-color="${state.color}"
                        style="background: ${bgColor}; border-color: ${state.color}; color: ${textColor};">
                    ${escapeHtml(state.name)}
                </button>
            `;
        }).join('');

        this.stateChipsContainer.innerHTML = chipsHtml;

        // Attach click handlers
        this.stateChipsContainer.querySelectorAll('.state-chip').forEach(chip => {
            chip.addEventListener('click', (e) => this.handleStateChange(e));
        });
    }

    // =========================================================================
    // STATE CHANGE HANDLING
    // =========================================================================

    /**
     * Handle state change click
     * Updates the reservation state via API and provides visual feedback
     *
     * @param {Event} event - Click event from state chip
     * @returns {Promise<void>}
     */
    async handleStateChange(event) {
        const chip = event.currentTarget;
        const newState = chip.dataset.state;
        const chipColor = chip.dataset.color;

        // Skip if already active
        if (chip.classList.contains('active')) return;

        // Store previous active chip for potential revert
        const prevActive = this.stateChipsContainer.querySelector('.state-chip.active');

        // Visual feedback - deactivate previous chip
        if (prevActive) {
            prevActive.classList.remove('active');
            prevActive.style.background = 'transparent';
            prevActive.style.color = 'var(--color-secondary)';
        }

        // Visual feedback - activate new chip with loading state
        chip.classList.add('active', 'loading');
        chip.style.background = chipColor;
        chip.style.color = '#FFFFFF';

        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/reservations/${this.state.reservationId}/toggle-state`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ state: newState, action: 'set' })
                }
            );

            const result = await response.json();

            if (result.success) {
                // Update local data
                if (this.state.data?.reservation) {
                    this.state.data.reservation.current_state = newState;
                }

                // Trigger callback for external listeners
                if (this.options.onStateChange) {
                    this.options.onStateChange(this.state.reservationId, newState);
                }

                showToast(`Estado cambiado a ${newState}`, 'success');
            } else {
                throw new Error(result.error || 'Error al cambiar estado');
            }

        } catch (error) {
            console.error('State change error:', error);

            // Revert visual state on error
            chip.classList.remove('active');
            chip.style.background = 'transparent';
            chip.style.color = 'var(--color-secondary)';

            // Restore previous active chip
            if (prevActive) {
                prevActive.classList.add('active');
                prevActive.style.background = prevActive.dataset.color;
                prevActive.style.color = '#FFFFFF';
            }

            showToast(error.message, 'error');
        } finally {
            chip.classList.remove('loading');
        }
    }

    // =========================================================================
    // STATE HISTORY
    // =========================================================================

    /**
     * Load and render state history for a reservation
     * Fetches history from API and shows/hides the history section
     *
     * @param {number} reservationId - ID of the reservation
     * @returns {Promise<void>}
     */
    async loadStateHistory(reservationId) {
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/reservations/${reservationId}/history`
            );

            if (!response.ok) return;

            const result = await response.json();

            if (result.success && result.history && result.history.length > 0) {
                this.renderStateHistory(result.history);
                if (this.stateHistorySection) {
                    this.stateHistorySection.style.display = 'block';
                }
            } else {
                // Hide section if no history
                if (this.stateHistorySection) {
                    this.stateHistorySection.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Failed to load state history:', error);
        }
    }

    /**
     * Render state history items as a timeline
     * Displays each history item with date, action icon, state color, and notes
     *
     * @param {Array} history - Array of history items
     * @param {string} history[].created_at - ISO date string when action occurred
     * @param {string} history[].action - Action type: 'add', 'remove', 'change', 'set'
     * @param {string} history[].status_type - State name
     * @param {string} history[].changed_by - Username who made the change
     * @param {string} history[].notes - Optional notes for the change
     */
    renderStateHistory(history) {
        if (!this.stateHistoryList) return;

        const historyHtml = history.map(item => {
            // Format date in Spanish locale
            const date = new Date(item.created_at);
            const dateStr = date.toLocaleDateString('es-ES', {
                day: '2-digit',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
            });

            // Get action icon and CSS class based on action type
            let actionIcon = 'fa-circle';
            let actionClass = '';

            if (item.action === 'add' || item.action === 'added') {
                actionIcon = 'fa-plus-circle';
                actionClass = 'action-add';
            } else if (item.action === 'remove' || item.action === 'removed') {
                actionIcon = 'fa-minus-circle';
                actionClass = 'action-remove';
            } else if (item.action === 'change' || item.action === 'changed' || item.action === 'set') {
                actionIcon = 'fa-exchange-alt';
                actionClass = 'action-change';
            }

            // Get state color from our states array
            const state = this.states.find(s => s.name === item.status_type);
            const stateColor = state?.color || '#6C757D';

            return `
                <div class="history-item ${actionClass}">
                    <div class="history-icon">
                        <i class="fas ${actionIcon}"></i>
                    </div>
                    <div class="history-content">
                        <span class="history-state" style="color: ${stateColor};">
                            ${escapeHtml(item.status_type)}
                        </span>
                        <span class="history-meta">
                            ${dateStr}
                            ${item.changed_by ? `• ${escapeHtml(item.changed_by)}` : ''}
                        </span>
                        ${item.notes ? `<span class="history-notes">${escapeHtml(item.notes)}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        this.stateHistoryList.innerHTML = historyHtml;
    }

    /**
     * Toggle state history section visibility
     * Expands or collapses the history content and updates toggle button state
     */
    toggleStateHistory() {
        if (!this.stateHistoryContent || !this.stateHistoryToggle) return;

        const isExpanded = this.stateHistoryContent.style.display !== 'none';

        if (isExpanded) {
            this.stateHistoryContent.style.display = 'none';
            this.stateHistoryToggle.classList.remove('expanded');
        } else {
            this.stateHistoryContent.style.display = 'block';
            this.stateHistoryToggle.classList.add('expanded');
        }
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/tags-mixin.js
// =============================================================================

/**
 * ReservationPanel Tags Mixin
 *
 * Handles reservation tag functionality:
 * - Rendering tags section with chips
 * - Entering/exiting tags edit mode
 * - Loading all available tags
 * - Toggling tag selections
 *
 * @module reservation-panel-v2/tags-mixin
 */


// =============================================================================
// TAGS MIXIN
// =============================================================================

const TagsMixin = (Base) => class extends Base {

    // =========================================================================
    // TAGS SECTION RENDERING
    // =========================================================================

    /**
     * Render tags section with chips (view mode)
     * @param {Object} reservation - Reservation data
     */
    renderTagsSection(reservation) {
        if (!this.tagChipsContainer) return;

        const tags = reservation?.tags || [];

        if (this.tagsSection) {
            this.tagsSection.style.display = 'block';
        }

        if (tags.length === 0) {
            this.tagChipsContainer.innerHTML =
                '<span class="text-muted small">Sin etiquetas</span>';
            return;
        }

        const chipsHtml = tags.map(tag => {
            const color = this._sanitizeColor(tag.color) || '#6C757D';
            const name = escapeHtml(tag.name);
            const title = escapeHtml(tag.description || tag.name);
            return `
                <span class="tag-chip" style="--tag-color: ${color};" title="${title}">
                    <i class="fas fa-tag"></i>
                    <span>${name}</span>
                </span>
            `;
        }).join('');

        this.tagChipsContainer.innerHTML = chipsHtml;
    }

    // =========================================================================
    // TAGS EDIT MODE
    // =========================================================================

    /**
     * Enter tags edit mode
     * Loads all available tags and renders them as toggleable chips
     */
    async enterTagsEditMode() {
        if (this.tagsEditState.allTags.length === 0) {
            await this.loadAllTags();
        }

        const currentTags = this.state.data?.reservation?.tags || [];
        this.tagsEditState.selectedIds = currentTags.map(t => t.id);
        this.tagsEditState.originalIds = [...this.tagsEditState.selectedIds];
        this.tagsEditState.isEditing = true;

        this.renderAllTagChips();

        if (this.tagsViewMode) {
            this.tagsViewMode.style.display = 'none';
        }
        if (this.tagsEditModeEl) {
            this.tagsEditModeEl.style.display = 'block';
        }
        if (this.tagsSection) {
            this.tagsSection.style.display = 'block';
        }
    }

    /**
     * Exit tags edit mode
     * @param {boolean} discard - Whether to discard changes
     */
    exitTagsEditMode(discard = false) {
        this.tagsEditState.isEditing = false;

        if (this.tagsViewMode) {
            this.tagsViewMode.style.display = 'block';
        }
        if (this.tagsEditModeEl) {
            this.tagsEditModeEl.style.display = 'none';
        }

        const reservation = this.state.data?.reservation;
        if (reservation) {
            this.renderTagsSection(reservation);
        }
    }

    // =========================================================================
    // TAGS DATA LOADING
    // =========================================================================

    /**
     * Load all available tags from server
     */
    async loadAllTags() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/tags`);
            if (response.ok) {
                const result = await response.json();
                this.tagsEditState.allTags = result.tags || [];
            }
        } catch (error) {
            console.error('Failed to load tags:', error);
        }
    }

    // =========================================================================
    // TAGS CHIPS RENDERING
    // =========================================================================

    /**
     * Render all tags as toggleable chips (edit mode)
     */
    renderAllTagChips() {
        if (!this.tagsAllChips) return;

        const allTags = this.tagsEditState.allTags;
        const selectedIds = this.tagsEditState.selectedIds;

        if (allTags.length === 0) {
            this.tagsAllChips.innerHTML =
                '<span class="text-muted small">No hay etiquetas disponibles</span>';
            return;
        }

        const chipsHtml = allTags.map(tag => {
            const isSelected = selectedIds.includes(tag.id);
            const color = this._sanitizeColor(tag.color) || '#6C757D';
            const name = escapeHtml(tag.name);
            const title = escapeHtml(tag.description || tag.name);
            return `
                <button type="button" class="tag-chip toggleable ${isSelected ? 'active' : ''}"
                        data-tag-id="${tag.id}"
                        style="--tag-color: ${color};"
                        title="${title}">
                    <i class="fas fa-tag"></i>
                    <span>${name}</span>
                </button>
            `;
        }).join('');

        this.tagsAllChips.innerHTML = chipsHtml;

        this._attachTagChipHandlers();
    }

    /**
     * Attach click handlers to toggleable tag chips
     * @private
     */
    _attachTagChipHandlers() {
        if (!this.tagsAllChips) return;

        this.tagsAllChips
            .querySelectorAll('.tag-chip.toggleable')
            .forEach(chip => {
                chip.addEventListener('click', () => {
                    this.toggleTag(parseInt(chip.dataset.tagId));
                });
            });
    }

    // =========================================================================
    // TAGS SELECTION
    // =========================================================================

    /**
     * Toggle a tag selection
     * @param {number} tagId - The tag ID to toggle
     */
    toggleTag(tagId) {
        const index = this.tagsEditState.selectedIds.indexOf(tagId);
        if (index >= 0) {
            this.tagsEditState.selectedIds.splice(index, 1);
        } else {
            this.tagsEditState.selectedIds.push(tagId);
        }
        this.renderAllTagChips();
        this.markDirty();
    }

    // =========================================================================
    // PRIVATE HELPERS
    // =========================================================================

    /**
     * Sanitize a CSS color value to prevent injection via style attributes
     * @param {string} color - Color value (hex, rgb, named)
     * @returns {string|null} Sanitized color or null if invalid
     * @private
     */
    _sanitizeColor(color) {
        if (!color) return null;
        // Allow hex colors, rgb/rgba, hsl/hsla, and named colors (letters only)
        if (/^#[0-9A-Fa-f]{3,8}$/.test(color)) return color;
        if (/^(rgb|hsl)a?\([^)]+\)$/.test(color)) return color;
        if (/^[a-zA-Z]+$/.test(color)) return color;
        return null;
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/preferences-mixin.js
// =============================================================================

/**
 * ReservationPanel Preferences Mixin
 *
 * Handles all customer preferences functionality:
 * - Rendering preferences section with chips
 * - Entering/exiting preferences edit mode
 * - Loading all available preferences
 * - Toggling preference selections
 *
 * @module reservation-panel-v2/preferences-mixin
 */


// =============================================================================
// PREFERENCES MIXIN
// =============================================================================

/**
 * Preferences mixin factory function
 * Adds customer preferences display and edit functionality to the panel
 *
 * @param {class} Base - Base class to extend
 * @returns {class} Extended class with preferences functionality
 *
 * @example
 * class ReservationPanel extends PreferencesMixin(CustomerMixin(BasePanel)) {
 *     // Panel implementation
 * }
 */
const PreferencesMixin = (Base) => class extends Base {

    // =========================================================================
    // PREFERENCES SECTION RENDERING
    // =========================================================================

    /**
     * Render preferences section with chips
     * Displays customer preferences as styled chip elements
     *
     * @param {Object|null} customer - Customer data object
     * @param {Array} customer.preferences - Array of preference objects
     * @param {string} customer.preferences[].code - Preference code
     * @param {string} customer.preferences[].name - Preference display name
     * @param {string} customer.preferences[].icon - FontAwesome icon class
     */
    renderPreferencesSection(customer) {
        if (!this.preferencesChipsContainer) return;

        // Prefer reservation-specific characteristics over customer defaults
        const reservationChars = this.state.data?.reservation_characteristics || [];
        const preferences = reservationChars.length > 0 ? reservationChars : (customer?.preferences || []);

        // Hide section if no preferences
        if (this.preferencesSection) {
            this.preferencesSection.style.display = 'block';
        }

        if (preferences.length === 0) {
            this.preferencesChipsContainer.innerHTML =
                '<span class="text-muted small">Sin preferencias registradas</span>';
            return;
        }

        const chipsHtml = preferences.map(pref => {
            const icon = this._normalizeIconClass(pref.icon);
            const name = escapeHtml(pref.name);
            return `
                <span class="preference-chip" title="${name}">
                    <i class="${icon}"></i>
                    <span>${name}</span>
                </span>
            `;
        }).join('');

        this.preferencesChipsContainer.innerHTML = chipsHtml;
    }

    // =========================================================================
    // PREFERENCES EDIT MODE
    // =========================================================================

    /**
     * Enter preferences edit mode
     * Loads all available preferences and renders them as toggleable chips
     *
     * @returns {Promise<void>}
     */
    async enterPreferencesEditMode() {
        // Load all available preferences if not already loaded
        if (this.preferencesEditState.allPreferences.length === 0) {
            await this.loadAllPreferences();
        }

        // Get current preferences - prefer reservation-specific over customer defaults
        const reservationChars = this.state.data?.reservation_characteristics || [];
        const customerPrefs = this.state.data?.customer?.preferences || [];
        const activePrefs = reservationChars.length > 0 ? reservationChars : customerPrefs;
        this.preferencesEditState.selectedCodes = activePrefs.map(p => p.code);
        this.preferencesEditState.originalCodes = [...this.preferencesEditState.selectedCodes];
        this.preferencesEditState.isEditing = true;

        // Render all preferences as toggleable chips
        this.renderAllPreferencesChips();

        // Show edit mode, hide view mode
        if (this.preferencesViewMode) {
            this.preferencesViewMode.style.display = 'none';
        }
        if (this.preferencesEditMode) {
            this.preferencesEditMode.style.display = 'block';
        }

        // Always show the section in edit mode
        if (this.preferencesSection) {
            this.preferencesSection.style.display = 'block';
        }
    }

    /**
     * Exit preferences edit mode
     * Optionally discards changes and returns to view mode
     *
     * @param {boolean} discard - Whether to discard changes (default: false)
     */
    exitPreferencesEditMode(discard = false) {
        this.preferencesEditState.isEditing = false;

        // Show view mode, hide edit mode
        if (this.preferencesViewMode) {
            this.preferencesViewMode.style.display = 'block';
        }
        if (this.preferencesEditMode) {
            this.preferencesEditMode.style.display = 'none';
        }

        // Re-render view mode with current preferences
        const customer = this.state.data?.customer;
        if (customer) {
            this.renderPreferencesSection(customer);
        }
    }

    // =========================================================================
    // PREFERENCES DATA LOADING
    // =========================================================================

    /**
     * Load all available preferences from server
     * Fetches the complete list of preferences that can be assigned to customers
     *
     * @returns {Promise<void>}
     */
    async loadAllPreferences() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/preferences`);
            if (response.ok) {
                const result = await response.json();
                this.preferencesEditState.allPreferences = result.preferences || [];
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
        }
    }

    // =========================================================================
    // PREFERENCES CHIPS RENDERING
    // =========================================================================

    /**
     * Render all preferences as toggleable chips
     * Used in edit mode to show all available preferences with selection state
     */
    renderAllPreferencesChips() {
        if (!this.preferencesAllChips) return;

        const allPrefs = this.preferencesEditState.allPreferences;
        const selectedCodes = this.preferencesEditState.selectedCodes;

        if (allPrefs.length === 0) {
            this.preferencesAllChips.innerHTML =
                '<span class="text-muted small">No hay preferencias disponibles</span>';
            return;
        }

        const chipsHtml = allPrefs.map(pref => {
            const isSelected = selectedCodes.includes(pref.code);
            const icon = this._normalizeIconClass(pref.icon);
            const name = escapeHtml(pref.name);
            return `
                <span class="preference-chip toggleable ${isSelected ? 'selected' : ''}"
                      data-code="${pref.code}"
                      title="${name}">
                    <i class="${icon}"></i>
                    <span>${name}</span>
                </span>
            `;
        }).join('');

        this.preferencesAllChips.innerHTML = chipsHtml;

        // Attach click handlers
        this._attachPreferenceChipHandlers();
    }

    /**
     * Attach click handlers to toggleable preference chips
     * @private
     */
    _attachPreferenceChipHandlers() {
        if (!this.preferencesAllChips) return;

        this.preferencesAllChips
            .querySelectorAll('.preference-chip.toggleable')
            .forEach(chip => {
                chip.addEventListener('click', () => {
                    this.togglePreference(chip.dataset.code);
                });
            });
    }

    // =========================================================================
    // PREFERENCES SELECTION
    // =========================================================================

    /**
     * Toggle a preference selection
     * Adds or removes the preference code from selected list
     *
     * @param {string} code - The preference code to toggle
     */
    togglePreference(code) {
        const index = this.preferencesEditState.selectedCodes.indexOf(code);
        if (index >= 0) {
            // Remove from selection
            this.preferencesEditState.selectedCodes.splice(index, 1);
        } else {
            // Add to selection
            this.preferencesEditState.selectedCodes.push(code);
        }
        // Re-render chips to update selection state
        this.renderAllPreferencesChips();
        this.markDirty();
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    /**
     * Normalize icon class to ensure proper FontAwesome prefix
     * Icons are stored as 'fa-umbrella', need to add 'fas ' prefix if missing
     *
     * @private
     * @param {string} icon - Icon class string
     * @returns {string} Normalized icon class with proper prefix
     */
    _normalizeIconClass(icon) {
        let normalizedIcon = icon || 'fa-heart';
        if (normalizedIcon &&
            !normalizedIcon.startsWith('fas ') &&
            !normalizedIcon.startsWith('far ') &&
            !normalizedIcon.startsWith('fab ')) {
            normalizedIcon = 'fas ' + normalizedIcon;
        }
        return normalizedIcon;
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/furniture-mixin.js
// =============================================================================

/**
 * ReservationPanel Furniture Mixin
 *
 * Handles furniture display functionality:
 * - Rendering furniture section with chips and summary
 * - Entering move mode from this reservation
 * - Highlighting furniture on the map
 * - Furniture lock toggle
 */


// =============================================================================
// FURNITURE MIXIN
// =============================================================================

/**
 * Mixin that adds furniture display functionality
 * @param {class} Base - The base class to extend
 * @returns {class} Extended class with furniture methods
 */
const FurnitureMixin = (Base) => class extends Base {

    // =========================================================================
    // FURNITURE RENDERING
    // =========================================================================

    /**
     * Render the furniture section with chips showing assigned furniture
     * @param {object} reservation - Reservation data containing furniture array
     */
    renderFurnitureSection(reservation) {
        const furniture = reservation.furniture || [];
        const currentDate = this.state.currentDate;

        // Filter furniture for current date (if assignment_date exists) or show all
        let displayFurniture = furniture;
        if (furniture.length > 0 && furniture[0].assignment_date) {
            displayFurniture = furniture.filter(f => {
                // Parse any date format to YYYY-MM-DD for comparison
                const assignDate = parseDateToYMD(f.assignment_date);
                return assignDate === currentDate;
            });
        }

        if (displayFurniture.length === 0) {
            this.furnitureChipsContainer.innerHTML =
                '<span class="text-muted">Sin mobiliario asignado</span>';
            this.furnitureSummary.textContent = '';
            return;
        }

        const chipsHtml = displayFurniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${getFurnitureIcon(f.type_name || f.furniture_type)}</span>
                ${escapeHtml(f.number || f.furniture_number || `#${f.furniture_id || f.id}`)}
            </span>
        `).join('');

        this.furnitureChipsContainer.innerHTML = chipsHtml;

        // Summary
        const totalCapacity = displayFurniture.reduce((sum, f) => sum + (f.capacity || 2), 0);
        this.furnitureSummary.textContent =
            `${displayFurniture.length} ${displayFurniture.length === 1 ? 'item' : 'items'} • Capacidad: ${totalCapacity} personas`;

        // Render lock state
        this.renderLockState(reservation.is_furniture_locked || false);
    }

    // =========================================================================
    // MOVE MODE
    // =========================================================================

    /**
     * Enter move mode from this reservation
     * Closes the panel and activates global move mode with this reservation
     */
    async enterMoveMode() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        // Check if window.moveMode is available
        if (!window.moveMode) {
            showToast('Modo mover no disponible', 'error');
            return;
        }

        // Get current furniture IDs for this date
        const currentFurniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });

        const furnitureIds = currentFurniture.map(f => f.furniture_id || f.id);

        // Close the panel first
        this.close();

        // Activate move mode
        window.moveMode.activate(this.state.currentDate);

        // Unassign furniture from this reservation to add it to the pool
        // Pass the original furniture array so we can track what needs to be restored
        if (furnitureIds.length > 0) {
            await window.moveMode.unassignFurniture(reservation.id, furnitureIds, false, currentFurniture);
        } else {
            // No furniture assigned, just load the reservation to pool
            await window.moveMode.loadReservationToPool(reservation.id);
        }

        // Update toolbar button state
        const moveModeBtn = document.getElementById('btn-move-mode');
        if (moveModeBtn) {
            moveModeBtn.classList.add('active');
        }
        document.querySelector('.beach-map-container')?.classList.add('move-mode-active');

        showToast('Modo mover activado - selecciona nuevo mobiliario', 'info');
    }

    // =========================================================================
    // MAP HIGHLIGHTING
    // =========================================================================

    /**
     * Highlight reservation's furniture on the map with gold pulsing glow
     * Adds 'highlighted' class to furniture elements for the current date
     */
    highlightReservationFurniture() {
        const furniture = this.state.data?.reservation?.furniture;
        if (!furniture || furniture.length === 0) return;

        const currentDate = this.state.currentDate;

        // Filter furniture for current date
        const todayFurniture = furniture.filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === currentDate;
        });

        // Dispatch event so the map can highlight during its render cycle
        const furnitureIds = todayFurniture.map(f => f.furniture_id || f.id);
        document.dispatchEvent(new CustomEvent('reservation:highlightFurniture', {
            detail: { furnitureIds }
        }));
    }

    /**
     * Remove highlight from reservation's furniture
     */
    unhighlightReservationFurniture() {
        document.dispatchEvent(new CustomEvent('reservation:clearHighlight'));
    }

    // =========================================================================
    // FURNITURE LOCK
    // =========================================================================

    /**
     * Initialize furniture lock toggle
     */
    initFurnitureLock() {
        this.lockBtn = document.getElementById('toggleFurnitureLock');
        if (this.lockBtn) {
            this.lockBtn.addEventListener('click', () => this.toggleFurnitureLock());
        }
    }

    /**
     * Render the lock button state
     * @param {boolean} isLocked - Whether furniture is locked
     */
    renderLockState(isLocked) {
        if (!this.lockBtn) return;

        const icon = this.lockBtn.querySelector('i');
        if (isLocked) {
            this.lockBtn.classList.add('locked');
            this.lockBtn.dataset.locked = 'true';
            this.lockBtn.title = 'Desbloquear mobiliario';
            this.lockBtn.setAttribute('aria-label', 'Desbloquear mobiliario');
            icon.classList.remove('fa-lock-open');
            icon.classList.add('fa-lock');
        } else {
            this.lockBtn.classList.remove('locked');
            this.lockBtn.dataset.locked = 'false';
            this.lockBtn.title = 'Bloquear mobiliario';
            this.lockBtn.setAttribute('aria-label', 'Bloquear mobiliario');
            icon.classList.remove('fa-lock');
            icon.classList.add('fa-lock-open');
        }

        // Disable move mode button when locked
        const moveModeBtn = document.getElementById('panelMoveModeBtn');
        if (moveModeBtn) {
            moveModeBtn.disabled = isLocked;
            moveModeBtn.title = isLocked ? 'Mobiliario bloqueado' : 'Modo Mover';
        }
    }

    /**
     * Toggle furniture lock via API
     */
    async toggleFurnitureLock() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        const currentLocked = this.lockBtn.dataset.locked === 'true';
        const newLocked = !currentLocked;

        // Disable button during request
        this.lockBtn.disabled = true;

        try {
            const response = await fetch(
                `/beach/api/map/reservations/${reservation.id}/toggle-lock`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ locked: newLocked })
                }
            );

            const result = await response.json();

            if (result.success) {
                this.renderLockState(result.is_furniture_locked);
                // Update local state
                if (this.state.data.reservation) {
                    this.state.data.reservation.is_furniture_locked = result.is_furniture_locked;
                }
                showToast(
                    result.is_furniture_locked
                        ? 'Mobiliario bloqueado'
                        : 'Mobiliario desbloqueado',
                    'success'
                );
            } else {
                showToast(result.error || 'Error al cambiar bloqueo', 'error');
            }
        } catch (error) {
            console.error('Error toggling lock:', error);
            showToast('Error al cambiar bloqueo', 'error');
        } finally {
            this.lockBtn.disabled = false;
        }
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/pricing-mixin.js
// =============================================================================

/**
 * Pricing Mixin for ReservationPanel
 *
 * Handles pricing display and editing functionality, including:
 * - renderPricingSection() - Display pricing in view mode
 * - enterPricingEditMode() - Initialize pricing edit mode
 * - exitPricingEditMode() - Return to view mode
 * - fetchAvailablePackages() - Load available pricing packages
 * - updatePackageSelector() - Update package dropdown UI
 * - calculateAndUpdatePricing() - Calculate pricing based on selections
 *
 * Dependencies:
 * - parseDateToYMD from utils.js
 *
 * Expected instance properties:
 * - pricingSection, detailTotalPrice, detailPricingBreakdown
 * - pricingEditState: { originalPrice, isModified, selectedPackageId, availablePackages, calculatedPrice }
 * - panelFinalPriceInput, panelPriceOverride, panelCalculatedPrice, panelPriceResetBtn
 * - panelPricingTypeSelector, panelPricingTypeSelect, panelPricingDisplay
 * - panelSelectedPackageId, panelPricingBreakdown
 * - editNumPeople
 * - state: { data, currentDate }
 * - options: { apiBaseUrl }
 * - csrfToken
 */


// =============================================================================
// PRICING MIXIN
// =============================================================================

/**
 * Mixin that adds pricing functionality to ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with pricing methods
 */
const PricingMixin = (Base) => class extends Base {

    // =========================================================================
    // VIEW MODE RENDERING
    // =========================================================================

    /**
     * Render pricing section (view mode)
     *
     * Displays the current price, package name, and/or breakdown.
     * Updates both view mode display and pre-fills edit mode input.
     *
     * @param {Object} reservation - Reservation data with pricing info
     * @param {number} [reservation.final_price] - Final calculated price
     * @param {number} [reservation.total_price] - Total price (legacy)
     * @param {number} [reservation.price] - Base price (legacy fallback)
     * @param {string} [reservation.package_name] - Name of applied package
     * @param {string} [reservation.price_breakdown] - Price breakdown text
     */
    renderPricingSection(reservation) {
        if (!this.pricingSection) return;

        // Get price from reservation (API returns final_price, fallback to total_price/price for backward compat)
        const totalPrice = reservation.final_price || reservation.total_price || reservation.price || 0;
        const packageName = reservation.package_name || null;
        const priceBreakdown = reservation.price_breakdown || null;

        // Store original price for comparison
        this.pricingEditState.originalPrice = totalPrice;

        // Update view mode display
        if (this.detailTotalPrice) {
            this.detailTotalPrice.textContent = `€${parseFloat(totalPrice).toFixed(2)}`;
        }

        // Show package name if available, otherwise show breakdown
        if (this.detailPricingBreakdown) {
            if (packageName) {
                this.detailPricingBreakdown.innerHTML = `<span class="package-name">${escapeHtml(packageName)}</span>`;
                this.detailPricingBreakdown.style.display = 'block';
            } else if (priceBreakdown) {
                this.detailPricingBreakdown.textContent = priceBreakdown;
                this.detailPricingBreakdown.style.display = 'block';
            } else {
                this.detailPricingBreakdown.style.display = 'none';
            }
        }

        // Pre-fill edit mode with current price
        if (this.panelFinalPriceInput) {
            this.panelFinalPriceInput.value = parseFloat(totalPrice).toFixed(2);
        }
    }

    // =========================================================================
    // EDIT MODE MANAGEMENT
    // =========================================================================

    /**
     * Enter pricing edit mode - fetch packages and set up pricing
     *
     * Initializes pricing edit state:
     * - Resets modification flags
     * - Sets current price in input
     * - Clears override and calculated displays
     * - Fetches available packages for the reservation
     * - Fetches minimum consumption policies
     * - Stores calculated price for reference
     */
    async enterPricingEditMode() {
        if (!this.state.data?.reservation) return;

        const reservation = this.state.data.reservation;
        const customer = this.state.data.customer;

        // Reset pricing state
        this.pricingEditState.isModified = false;
        this.pricingEditState.selectedPackageId = reservation.package_id || null;
        this.pricingEditState.selectedPolicyId = reservation.minimum_consumption_policy_id || null;

        // Set current price in input (API returns final_price)
        const currentPrice = reservation.final_price || reservation.total_price || reservation.price || 0;
        if (this.panelFinalPriceInput) {
            this.panelFinalPriceInput.value = parseFloat(currentPrice).toFixed(2);
            this.panelFinalPriceInput.classList.remove('modified');
        }

        // Clear override input
        if (this.panelPriceOverride) {
            this.panelPriceOverride.value = '';
        }

        // Hide calculated price display initially
        if (this.panelCalculatedPrice) {
            this.panelCalculatedPrice.style.display = 'none';
        }

        // Hide reset button initially
        if (this.panelPriceResetBtn) {
            this.panelPriceResetBtn.style.display = 'none';
        }

        // Fetch available packages and policies
        await Promise.all([
            this.fetchAvailablePackages(),
            this.fetchMinConsumptionPolicies()
        ]);

        // Store calculated price for reference
        this.pricingEditState.calculatedPrice = currentPrice;
    }

    /**
     * Exit pricing edit mode
     *
     * Resets edit state and re-renders view mode with current reservation data.
     *
     * @param {boolean} [discard=false] - Whether changes are being discarded (unused but kept for API consistency)
     */
    exitPricingEditMode(discard = false) {
        // Reset state
        this.pricingEditState.isModified = false;

        // Re-render view mode with current reservation data
        const reservation = this.state.data?.reservation;
        if (reservation) {
            this.renderPricingSection(reservation);
        }
    }

    // =========================================================================
    // MINIMUM CONSUMPTION POLICY MANAGEMENT
    // =========================================================================

    /**
     * Fetch minimum consumption policies for dropdown (filtered by customer type)
     */
    async fetchMinConsumptionPolicies() {
        try {
            // Get customer type to filter policies
            const customer = this.state.data?.customer;
            const customerType = customer?.customer_type || 'externo';

            const url = new URL(`${window.location.origin}${this.options.apiBaseUrl}/pricing/minimum-consumption-policies`);
            url.searchParams.set('customer_type', customerType);

            const response = await fetch(url, {
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            const result = await response.json();

            if (result.success) {
                this.pricingEditState.availablePolicies = result.policies || [];
                this.updateMinConsumptionPolicySelector();
            }
        } catch (error) {
            console.error('[Pricing] Error fetching min consumption policies:', error);
        }
    }

    /**
     * Update minimum consumption policy selector UI
     */
    updateMinConsumptionPolicySelector() {
        if (!this.panelMinConsumptionSelect) return;

        const policies = this.pricingEditState.availablePolicies;
        const currentPolicyId = this.pricingEditState.selectedPolicyId;

        // Clear and rebuild options
        this.panelMinConsumptionSelect.innerHTML = '<option value="auto">Automático</option>';

        policies.forEach(policy => {
            const option = document.createElement('option');
            option.value = policy.id;

            // Build display text
            let displayText = policy.policy_name;
            if (policy.minimum_amount > 0) {
                const amountStr = policy.calculation_type === 'per_person'
                    ? `${policy.minimum_amount.toFixed(2)}€/pers`
                    : `${policy.minimum_amount.toFixed(2)}€`;
                displayText += ` - ${amountStr}`;
            } else {
                displayText += ' - Sin minimo';
            }

            option.textContent = displayText;
            this.panelMinConsumptionSelect.appendChild(option);
        });

        // Select current policy if any
        if (currentPolicyId) {
            this.panelMinConsumptionSelect.value = currentPolicyId.toString();
        } else {
            this.panelMinConsumptionSelect.value = 'auto';
        }
    }

    // =========================================================================
    // PACKAGE MANAGEMENT
    // =========================================================================

    /**
     * Fetch available packages for the current reservation
     *
     * Makes API call to get packages based on:
     * - Customer type (interno/externo)
     * - Furniture IDs for current date
     * - Reservation date
     * - Number of people
     *
     * Updates availablePackages in state and calls updatePackageSelector()
     */
    async fetchAvailablePackages() {
        if (!this.state.data?.reservation || !this.state.data?.customer) return;

        const reservation = this.state.data.reservation;
        const customer = this.state.data.customer;

        // Determine customer type
        const customerType = customer.customer_type || 'externo';

        // Get furniture IDs for this date
        const furniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });
        const furnitureIds = furniture.map(f => f.furniture_id || f.id);

        try {
            const response = await fetch(`${this.options.apiBaseUrl}/pricing/packages/available`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    customer_type: customerType,
                    furniture_ids: furnitureIds,
                    reservation_date: this.state.currentDate,
                    num_people: reservation.num_people || 1
                })
            });

            const result = await response.json();

            if (result.success) {
                this.pricingEditState.availablePackages = result.packages || [];
                this.updatePackageSelector();
            }
        } catch (error) {
            console.error('[Pricing] Error fetching packages:', error);
        }
    }

    /**
     * Update package selector UI with available options
     *
     * Rebuilds the package dropdown:
     * - Hides selector if no packages available
     * - Clears and rebuilds options with package name and price
     * - Selects current package if one is assigned
     * - Shows the selector
     */
    updatePackageSelector() {
        if (!this.panelPricingTypeSelector || !this.panelPricingTypeSelect) return;

        const packages = this.pricingEditState.availablePackages;
        const currentPackageId = this.pricingEditState.selectedPackageId;

        // Hide selector if no packages
        if (!packages || packages.length === 0) {
            this.panelPricingTypeSelector.style.display = 'none';
            return;
        }

        // Clear and rebuild options
        this.panelPricingTypeSelect.innerHTML = '<option value="">Consumo minimo</option>';

        packages.forEach(pkg => {
            const option = document.createElement('option');
            option.value = pkg.id;
            option.textContent = `${pkg.package_name} - €${pkg.calculated_price.toFixed(2)}`;
            this.panelPricingTypeSelect.appendChild(option);
        });

        // Select current package if any
        if (currentPackageId) {
            this.panelPricingTypeSelect.value = currentPackageId.toString();
        } else {
            this.panelPricingTypeSelect.value = '';
        }

        // Show selector
        this.panelPricingTypeSelector.style.display = 'block';
    }

    // =========================================================================
    // PRICE CALCULATION
    // =========================================================================

    /**
     * Calculate and update pricing based on current selections
     *
     * Makes API call to calculate pricing based on:
     * - Customer ID
     * - Furniture IDs for current date
     * - Reservation date
     * - Number of people
     * - Selected package (if any)
     *
     * Updates:
     * - Final price input (if not manually modified)
     * - Calculated price display
     * - Price breakdown text
     */
    async calculateAndUpdatePricing() {
        if (!this.state.data?.reservation || !this.state.data?.customer) return;

        const reservation = this.state.data.reservation;
        const customer = this.state.data.customer;

        // Get furniture IDs for current date
        const furniture = (reservation.furniture || []).filter(f => {
            const assignDate = parseDateToYMD(f.assignment_date);
            return assignDate === this.state.currentDate;
        });
        const furnitureIds = furniture.map(f => f.furniture_id || f.id);

        // Show loading state
        const loadingEl = this.panelPricingDisplay?.querySelector('.pricing-loading');
        const contentEl = this.panelPricingDisplay?.querySelector('.pricing-content');

        if (loadingEl && contentEl) {
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
        }

        try {
            const requestBody = {
                customer_id: customer.id,
                customer_source: 'customer',
                furniture_ids: furnitureIds,
                reservation_date: this.state.currentDate,
                num_people: parseInt(this.editNumPeople?.value) || reservation.num_people || 1
            };

            // Add package_id if selected
            const packageId = this.panelSelectedPackageId?.value;
            if (packageId) {
                requestBody.package_id = parseInt(packageId);
            }

            // Add minimum consumption policy if manually selected
            const policyId = this.pricingEditState.selectedPolicyId;
            if (policyId) {
                requestBody.minimum_consumption_policy_id = policyId;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/pricing/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(requestBody)
            });

            const result = await response.json();

            if (result.success && result.pricing) {
                const calculatedPrice = result.pricing.calculated_price;
                this.pricingEditState.calculatedPrice = calculatedPrice;

                // Update display if not manually modified
                if (!this.pricingEditState.isModified) {
                    if (this.panelFinalPriceInput) {
                        this.panelFinalPriceInput.value = calculatedPrice.toFixed(2);
                    }
                }

                // Update calculated price display
                const calculatedAmountEl = this.panelCalculatedPrice?.querySelector('.calculated-amount');
                if (calculatedAmountEl) {
                    calculatedAmountEl.textContent = `€${calculatedPrice.toFixed(2)}`;
                }

                // Show breakdown if available
                if (this.panelPricingBreakdown && result.pricing.breakdown) {
                    this.panelPricingBreakdown.textContent = result.pricing.breakdown;
                    this.panelPricingBreakdown.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('[Pricing] Calculation error:', error);
        } finally {
            // Hide loading state
            if (loadingEl && contentEl) {
                loadingEl.style.display = 'none';
                contentEl.style.display = 'flex';
            }
        }
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/details-mixin.js
// =============================================================================

/**
 * Details Mixin for ReservationPanel
 *
 * Handles the details and payment sections display, including:
 * - renderDetailsSection() - Display num_people and notes in view mode
 * - renderPaymentSection() - Display payment ticket and method in view mode
 *
 * Dependencies: None
 *
 * Expected instance properties:
 * - detailNumPeople, detailNotes - View mode elements for details
 * - editNumPeople, editNotes - Edit mode elements for details
 * - paymentSection - Payment section container
 * - detailPaymentTicket, detailPaymentMethod - View mode payment elements
 * - editPaymentTicket, editPaymentMethod - Edit mode payment elements
 * - state: { numPeopleManuallyEdited }
 */

// =============================================================================
// DETAILS MIXIN
// =============================================================================

/**
 * Mixin that adds details and payment functionality to ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with details methods
 */
const DetailsMixin = (Base) => class extends Base {

    // =========================================================================
    // DETAILS SECTION
    // =========================================================================

    /**
     * Render details section (view mode)
     *
     * Displays number of people and notes in the reservation panel.
     * Also pre-fills edit mode fields for seamless transition.
     *
     * @param {Object} reservation - Reservation data with details
     * @param {number} [reservation.num_people=1] - Number of people in reservation
     * @param {string} [reservation.notes] - Reservation notes
     * @param {string} [reservation.observations] - Alternative field for notes
     */
    renderDetailsSection(reservation) {
        // Number of people
        if (this.detailNumPeople) {
            this.detailNumPeople.textContent = reservation.num_people || 1;
        }

        // Notes - check both possible field names
        const notes = reservation.notes || reservation.observations;

        if (this.detailNotes) {
            if (notes) {
                this.detailNotes.textContent = notes;
                this.detailNotes.classList.remove('empty');
            } else {
                this.detailNotes.textContent = 'Sin notas';
                this.detailNotes.classList.add('empty');
            }
        }

        // Pre-fill edit fields (only if not manually edited for num_people)
        if (this.editNumPeople && !this.state.numPeopleManuallyEdited) {
            this.editNumPeople.value = reservation.num_people || 1;
        }
        if (this.editNotes) {
            this.editNotes.value = notes || '';
        }
    }

    // =========================================================================
    // PAYMENT SECTION
    // =========================================================================

    /**
     * Payment method labels for Spanish display
     * @type {Object.<string, string>}
     */
    static PAYMENT_METHOD_LABELS = {
        'efectivo': 'Efectivo',
        'tarjeta': 'Tarjeta',
        'cargo_habitacion': 'Cargo a habitación'
    };

    /**
     * Render payment section (view mode)
     *
     * Displays payment ticket number and method in the reservation panel.
     * Translates internal payment method values to Spanish labels.
     * Also pre-fills edit mode fields.
     *
     * @param {Object} reservation - Reservation data with payment info
     * @param {string} [reservation.payment_ticket_number] - Payment ticket number
     * @param {string} [reservation.payment_method] - Payment method code (efectivo, tarjeta, cargo_habitacion)
     */
    renderPaymentSection(reservation) {
        if (!this.paymentSection) return;

        // Payment ticket number
        const ticketNumber = reservation.payment_ticket_number || '-';

        if (this.detailPaymentTicket) {
            this.detailPaymentTicket.textContent = ticketNumber;
        }
        if (this.editPaymentTicket) {
            this.editPaymentTicket.value = reservation.payment_ticket_number || '';
        }

        // Payment method - translate to Spanish for display
        const methodValue = reservation.payment_method || '';
        const methodLabels = this.constructor.PAYMENT_METHOD_LABELS;
        const methodDisplay = methodLabels[methodValue] || '-';

        if (this.detailPaymentMethod) {
            this.detailPaymentMethod.textContent = methodDisplay;
        }
        if (this.editPaymentMethod) {
            this.editPaymentMethod.value = methodValue;
        }
    }
};

// =============================================================================
// SOURCE: reservation-panel-v2/index.js
// =============================================================================

/**
 * ReservationPanel - Main Entry Point
 * Composes all mixins into the final ReservationPanel class
 */


/**
 * Compose all mixins into the final ReservationPanel class
 * Order matters: each mixin may depend on methods from previous mixins
 */
const ReservationPanel = SaveMixin(
    DetailsMixin(
        PricingMixin(
            FurnitureMixin(
                StateMixin(
                    TagsMixin(
                        PreferencesMixin(
                            CustomerMixin(
                                EditModeMixin(
                                    PanelLifecycleMixin(
                                        ReservationPanelBase
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
);

// Export for ES modules

// Also expose on window for legacy compatibility
window.ReservationPanel = ReservationPanel;
