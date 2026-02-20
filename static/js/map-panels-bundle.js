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

/**
 * Sanitize a CSS color value to prevent injection via style attributes
 * @param {string} color - Color value (hex, rgb, named)
 * @returns {string|null} Sanitized color or null if invalid
 */
function sanitizeColor(color) {
    if (!color) return null;
    if (/^#[0-9A-Fa-f]{3,8}$/.test(color)) return color;
    if (/^(rgb|hsl)a?\([^)]+\)$/.test(color)) return color;
    if (/^[a-zA-Z]+$/.test(color)) return color;
    return null;
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

        // Back-reference for error state close button
        if (this.panel) {
            this.panel.__panel = this;
        }
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================

    getCsrfToken() {
        return document.getElementById('panelCsrfToken')?.value ||
               document.querySelector('meta[name="csrf-token"]')?.content ||
               this.csrfToken;
    }

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

// ReservationPanelBase is used by mixins below (was: export default)

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
            const confirmed = await confirmAction({
                title: 'Cambios sin guardar',
                message: 'Tienes cambios sin guardar. ¿Seguro que quieres cerrar?',
                confirmText: 'Cerrar',
                confirmClass: 'btn-warning',
                iconClass: 'fa-exclamation-triangle'
            });
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
                    <p>${escapeHtml(message)}</p>
                    <button class="btn btn-outline-primary mt-2" onclick="document.getElementById('reservationPanel').__panel?.close()">
                        Cerrar
                    </button>
                </div>
            `;
            this.contentEl.style.display = 'block';

            // Restore body scroll so user isn't trapped if close button fails
            if (!this.isStandalone()) {
                document.body.style.overflow = '';
            }
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
            const confirmed = await confirmAction({
                title: 'Cambios sin guardar',
                message: 'Tienes cambios sin guardar. ¿Descartar cambios?',
                confirmText: 'Descartar',
                confirmClass: 'btn-warning',
                iconClass: 'fa-exclamation-triangle'
            });
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
                        'X-CSRFToken': this.getCsrfToken()
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
                        'X-CSRFToken': this.getCsrfToken()
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
                        'X-CSRFToken': this.getCsrfToken()
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
                            'X-CSRFToken': this.getCsrfToken()
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
                                'X-CSRFToken': this.getCsrfToken()
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
                            'X-CSRFToken': this.getCsrfToken()
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

        // Skip if already active or if a state change is in progress
        if (chip.classList.contains('active')) return;
        if (this._stateChangeInProgress) return;
        this._stateChangeInProgress = true;

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
                        'X-CSRFToken': this.getCsrfToken()
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

                // Reload state history to show the new entry
                await this.loadStateHistory(this.state.reservationId);

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
            this._stateChangeInProgress = false;
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
        await this.close();

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
                    'X-CSRFToken': this.getCsrfToken()
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
                    'X-CSRFToken': this.getCsrfToken()
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
                    'X-CSRFToken': this.getCsrfToken()
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

// =============================================================================
// NEW RESERVATION PANEL (V1) - For creating new reservations
// =============================================================================

// --- customer-handler.js ---
function _chEscapeHtml(str) {
    if (!str) return '';
    const s = String(str);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * CustomerHandler - Manages customer selection, creation, and display
 * Handles customer search, inline creation form, hotel guest integration
 */
class CustomerHandler {
    constructor(panel) {
        this.panel = panel;
        this.state = {
            selectedCustomer: null,
            selectedGuest: null,
            roomGuests: []
        };

        // Initialize create customer form handlers
        this.initCreateCustomerForm();
    }

    /**
     * Initialize create customer form event handlers
     */
    initCreateCustomerForm() {
        const cancelBtn = document.getElementById('newPanelCancelCreateBtn');
        const saveBtn = document.getElementById('newPanelSaveCustomerBtn');

        cancelBtn?.addEventListener('click', () => this.hideCreateCustomerForm());
        saveBtn?.addEventListener('click', () => this.saveNewCustomer());
    }

    /**
     * Show the inline create customer form
     * @param {Object} prefillData - Data to pre-fill the form with
     * @param {string} prefillData.first_name - First name
     * @param {string} prefillData.last_name - Last name
     * @param {string} prefillData.phone - Phone number
     * @param {string} prefillData.email - Email address
     * @param {string} prefillData.language - Language code
     */
    showCreateCustomerForm(prefillData = {}) {
        const createForm = document.getElementById('newPanelCreateCustomerForm');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const firstNameInput = document.getElementById('newCustFirstName');
        const lastNameInput = document.getElementById('newCustLastName');
        const phoneInput = document.getElementById('newCustPhone');
        const emailInput = document.getElementById('newCustEmail');
        const languageSelect = document.getElementById('newCustLanguage');

        if (!createForm) return;

        // Hide search wrapper
        searchWrapper.style.display = 'none';

        // Pre-fill fields if provided
        if (prefillData.first_name) {
            firstNameInput.value = prefillData.first_name;
        }
        if (prefillData.last_name) {
            lastNameInput.value = prefillData.last_name;
        }
        if (prefillData.phone && phoneInput) {
            phoneInput.value = prefillData.phone;
        }
        if (prefillData.email && emailInput) {
            emailInput.value = prefillData.email;
        }
        if (prefillData.language && languageSelect) {
            languageSelect.value = prefillData.language;
        }

        // Show create form
        createForm.style.display = 'block';
        firstNameInput?.focus();
    }

    /**
     * Hide the inline create customer form
     */
    hideCreateCustomerForm() {
        const createForm = document.getElementById('newPanelCreateCustomerForm');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const errorEl = document.getElementById('newCustError');

        if (!createForm) return;

        // Clear form
        document.getElementById('newCustFirstName').value = '';
        document.getElementById('newCustLastName').value = '';
        document.getElementById('newCustPhone').value = '';
        document.getElementById('newCustEmail').value = '';
        document.getElementById('newCustLanguage').value = '';
        if (errorEl) errorEl.style.display = 'none';

        // Hide form, show search
        createForm.style.display = 'none';
        searchWrapper.style.display = 'block';
        document.getElementById('newPanelCustomerSearch').value = '';
    }

    /**
     * Save the new customer from the inline form
     */
    async saveNewCustomer() {
        const firstName = document.getElementById('newCustFirstName')?.value.trim() || '';
        const lastName = document.getElementById('newCustLastName')?.value.trim() || '';
        const phone = document.getElementById('newCustPhone')?.value.trim() || '';
        const email = document.getElementById('newCustEmail')?.value.trim() || '';
        const language = document.getElementById('newCustLanguage')?.value || '';
        const saveBtn = document.getElementById('newPanelSaveCustomerBtn');

        // Validation
        if (!firstName) {
            this.showCreateError('El nombre es requerido');
            return;
        }
        if (!phone && !email) {
            this.showCreateError('Se requiere telefono o email');
            return;
        }

        // Disable button
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando...';

        try {
            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/customers/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    customer_type: 'externo',
                    first_name: firstName,
                    last_name: lastName,
                    phone: phone,
                    email: email,
                    language: language,
                    country_code: '+34'
                })
            });

            const result = await response.json();

            if (result.success && result.customer) {
                this.hideCreateCustomerForm();
                this.handleNewCustomerCreated(result.customer);
            } else {
                this.showCreateError(result.error || 'Error al crear cliente');
            }
        } catch (error) {
            console.error('Error creating customer:', error);
            this.showCreateError('Error de conexion');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-check"></i> Crear Cliente';
        }
    }

    /**
     * Show error in create form
     */
    showCreateError(message) {
        const errorEl = document.getElementById('newCustError');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
            setTimeout(() => {
                errorEl.style.display = 'none';
            }, 3000);
        }
    }

    /**
     * Handle newly created customer from inline form
     */
    handleNewCustomerCreated(customer) {
        document.getElementById('newPanelCustomerId').value = customer.id;
        document.getElementById('newPanelCustomerSource').value = 'customer';
        this.state.selectedCustomer = customer;
        this.state.selectedGuest = null;

        // Show customer display
        this.showCustomerDisplay(customer);

        // Hide guest selector (external customers don't have room guests)
        this.hideGuestSelector();

        // Set num_people from the form if provided (only if not manually edited)
        const numPeopleInput = document.getElementById('newPanelNumPeople');
        if (customer.num_people && numPeopleInput && !this.panel.numPeopleManuallyEdited) {
            numPeopleInput.value = customer.num_people;
        }

        // Clear preferences (new customer has no preferences yet)
        this.panel.clearPreferences();

        // Calculate pricing after customer creation
        this.panel.pricingCalculator.calculateAndDisplayPricing();
    }

    /**
     * Auto-fill preferences and notes from customer record
     */
    async autoFillCustomerData(customer) {
        this.state.selectedCustomer = customer;
        const isInterno = customer.customer_type === 'interno';

        // Show customer display with details
        this.showCustomerDisplay(customer);

        // Clear current preferences first
        this.panel.clearPreferences();

        // If customer has preferences, activate matching chips
        if (customer.preferences && customer.preferences.length > 0) {
            customer.preferences.forEach(prefCode => {
                const chip = document.querySelector(`#newPanelPreferenceChips .pref-chip[data-pref="${prefCode}"]`);
                if (chip) {
                    chip.classList.add('active');
                    if (!this.panel.state.preferences.includes(prefCode)) {
                        this.panel.state.preferences.push(prefCode);
                    }
                }
            });
            // Update hidden input
            const prefsInput = document.getElementById('newPanelPreferences');
            if (prefsInput) {
                prefsInput.value = this.panel.state.preferences.join(',');
            }
        }

        // Auto-fill notes from customer record
        const notesInput = document.getElementById('newPanelNotes');
        if (customer.notes && notesInput) {
            let notes = customer.notes;
            // If showing dates in UI, remove date patterns from notes (legacy data cleanup)
            if (isInterno && customer.room_number) {
                notes = notes
                    .replace(/huesped\s+hotel\s*\([^)]*llegada[^)]*salida[^)]*\)/gi, '')
                    .replace(/check[- ]?in:?\s*[\d\-\/]+/gi, '')
                    .replace(/check[- ]?out:?\s*[\d\-\/]+/gi, '')
                    .replace(/entrada:?\s*[\d\-\/]+/gi, '')
                    .replace(/salida:?\s*[\d\-\/]+/gi, '')
                    .replace(/llegada:?\s*[\d\-\/]+/gi, '')
                    .replace(/\d{1,4}[\/\-]\d{1,2}[\/\-]\d{1,4}\s*[-–]\s*\d{1,4}[\/\-]\d{1,2}[\/\-]\d{1,4}/g, '')
                    .replace(/\s*[,;]\s*[,;]\s*/g, ', ')
                    .replace(/^\s*[,;]\s*/g, '')
                    .replace(/\s*[,;]\s*$/g, '')
                    .trim();
            }
            notesInput.value = notes;
        }

        // Calculate pricing after customer selection
        this.panel.pricingCalculator.calculateAndDisplayPricing();

        // For internal customers with a room number, fetch room guests
        if (isInterno && customer.room_number) {
            await this.fetchRoomGuests(customer);
        } else {
            // External customer - no guest selector
            this.hideGuestSelector();
            this.state.selectedGuest = null;
        }
    }

    /**
     * Fetch room guests for internal customer or hotel guest
     */
    async fetchRoomGuests(customer) {
        try {
            const response = await fetch(
                `${this.panel.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(customer.room_number)}`
            );
            const data = await response.json();

            this.state.roomGuests = data.guests || [];
            const guestCount = data.guest_count || 1;

            // If multiple guests in room, show the selector
            if (guestCount > 1 && this.state.roomGuests.length > 1) {
                // Find the matching guest based on customer name
                const customerName = `${customer.first_name || ''} ${customer.last_name || ''}`.trim().toUpperCase();
                let matchingGuest = this.state.roomGuests.find(g =>
                    g.guest_name.toUpperCase() === customerName
                );

                // If no exact match, use main guest or first guest
                if (!matchingGuest) {
                    matchingGuest = this.state.roomGuests.find(g => g.is_main_guest) || this.state.roomGuests[0];
                }

                this.state.selectedGuest = matchingGuest;
                this.showGuestSelector(matchingGuest, guestCount);

                // Update display with hotel guest data (arrival/departure)
                if (matchingGuest) {
                    this.showCustomerDisplay({
                        ...customer,
                        arrival_date: matchingGuest.arrival_date,
                        departure_date: matchingGuest.departure_date,
                        booking_reference: matchingGuest.booking_reference,
                        vip_code: matchingGuest.vip_code
                    });
                }
            } else if (this.state.roomGuests.length === 1) {
                // Single guest - update display with hotel data
                const guest = this.state.roomGuests[0];
                this.state.selectedGuest = guest;
                this.hideGuestSelector();
                this.showCustomerDisplay({
                    ...customer,
                    arrival_date: guest.arrival_date,
                    departure_date: guest.departure_date,
                    booking_reference: guest.booking_reference,
                    vip_code: guest.vip_code
                });
            } else {
                this.hideGuestSelector();
                this.state.selectedGuest = null;
            }

            // Auto-set num_people based on guest count (only if not manually edited)
            const capacity = this.panel.calculateCapacity();
            const numPeopleInput = document.getElementById('newPanelNumPeople');
            if (numPeopleInput && guestCount > 0 && !this.panel.numPeopleManuallyEdited) {
                numPeopleInput.value = guestCount;
            }

            // Check capacity warning
            if (guestCount > capacity) {
                this.panel.showCapacityWarning(guestCount, capacity);
            } else {
                this.panel.hideCapacityWarning();
            }

        } catch (error) {
            console.error('Error fetching room guests for customer:', error);
            this.hideGuestSelector();
            this.state.selectedGuest = null;
        }
    }

    /**
     * Show customer display with expanded details
     */
    showCustomerDisplay(customer) {
        // Hide search wrapper, show customer display
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const customerDisplay = document.getElementById('newPanelCustomerDisplay');
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');

        if (searchWrapper) searchWrapper.style.display = 'none';
        if (customerDisplay) customerDisplay.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'flex';

        // Initials
        const firstName = customer.first_name || customer.guest_name?.split(' ')[0] || '';
        const lastName = customer.last_name || customer.guest_name?.split(' ').slice(1).join(' ') || '';
        const initials = (firstName.charAt(0) + lastName.charAt(0)).toUpperCase() || '--';
        const initialsEl = document.getElementById('newPanelCustomerInitials');
        if (initialsEl) initialsEl.textContent = initials;

        // Avatar class
        const avatarEl = document.getElementById('newPanelCustomerAvatar');
        if (avatarEl) {
            avatarEl.className = 'customer-avatar';
            if (customer.vip_status || customer.vip_code) {
                avatarEl.classList.add('vip');
            } else if (customer.customer_type === 'interno' || customer.source === 'hotel_guest') {
                avatarEl.classList.add('interno');
            }
        }

        // Name
        const fullName = customer.display_name || customer.full_name ||
            `${customer.first_name || ''} ${customer.last_name || ''}`.trim() ||
            customer.guest_name || 'Sin nombre';
        const nameEl = document.getElementById('newPanelCustomerName');
        if (nameEl) nameEl.textContent = fullName;

        // Meta (type badge, VIP, phone)
        let meta = [];
        if (customer.customer_type === 'interno' || customer.source === 'hotel_guest') {
            meta.push('<span class="badge bg-info">Interno</span>');
        } else {
            meta.push('<span class="badge bg-secondary">Externo</span>');
        }
        if (customer.vip_status || customer.vip_code) {
            meta.push('<i class="fas fa-star vip-badge"></i> VIP');
        }
        if (customer.phone) {
            meta.push(`<i class="fas fa-phone"></i> ${_chEscapeHtml(customer.phone)}`);
        }
        const metaEl = document.getElementById('newPanelCustomerMeta');
        if (metaEl) {
            metaEl.innerHTML = meta.join(' <span class="mx-1">•</span> ');
        }

        // Details grid
        this.renderCustomerDetailsGrid(customer);
    }

    /**
     * Render customer details inline (room, check-in, check-out, booking ref)
     */
    renderCustomerDetailsGrid(customer) {
        // Room
        const roomEl = document.getElementById('newPanelCustomerRoom');
        const roomItem = document.getElementById('newPanelRoomItem');
        if (roomEl) {
            const room = customer.room_number;
            if (room) {
                roomEl.textContent = `Hab. ${room}`;
                if (roomItem) roomItem.style.display = 'inline-flex';
            } else {
                if (roomItem) roomItem.style.display = 'none';
            }
        }

        // Check-in date
        const checkinEl = document.getElementById('newPanelCustomerCheckin');
        const checkinItem = document.getElementById('newPanelCheckinItem');
        if (checkinEl) {
            const arrivalDate = customer.arrival_date;
            if (arrivalDate) {
                checkinEl.textContent = this.formatDateShort(arrivalDate);
                if (checkinItem) checkinItem.style.display = 'inline-flex';
            } else {
                if (checkinItem) checkinItem.style.display = 'none';
            }
        }

        // Check-out date
        const checkoutEl = document.getElementById('newPanelCustomerCheckout');
        const checkoutItem = document.getElementById('newPanelCheckoutItem');
        if (checkoutEl) {
            const departureDate = customer.departure_date;
            if (departureDate) {
                checkoutEl.textContent = this.formatDateShort(departureDate);
                if (checkoutItem) checkoutItem.style.display = 'inline-flex';
            } else {
                if (checkoutItem) checkoutItem.style.display = 'none';
            }
        }

        // Booking reference
        const bookingEl = document.getElementById('newPanelCustomerBookingRef');
        const bookingItem = document.getElementById('newPanelBookingItem');
        if (bookingEl) {
            const bookingRef = customer.booking_reference;
            if (bookingRef) {
                bookingEl.textContent = bookingRef;
                if (bookingItem) bookingItem.style.display = 'inline-flex';
            } else {
                if (bookingItem) bookingItem.style.display = 'none';
            }
        }

        // Hide details row if no details (external customer without hotel info)
        const detailsGrid = document.getElementById('newPanelCustomerDetailsGrid');
        if (detailsGrid) {
            const hasDetails = customer.room_number || customer.arrival_date ||
                               customer.departure_date || customer.booking_reference;
            detailsGrid.style.display = hasDetails ? 'flex' : 'none';
        }
    }

    /**
     * Format date for display (short format: DD/MM)
     */
    formatDateShort(dateStr) {
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
     * Clear customer selection and show search again
     */
    clearCustomerSelection() {
        // Clear state
        document.getElementById('newPanelCustomerId').value = '';
        document.getElementById('newPanelCustomerSource').value = 'customer';
        this.state.selectedCustomer = null;
        this.state.selectedGuest = null;

        // Hide customer display, show search wrapper
        const customerDisplay = document.getElementById('newPanelCustomerDisplay');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');

        if (customerDisplay) customerDisplay.style.display = 'none';
        if (searchWrapper) searchWrapper.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'none';

        // Clear and reset search
        if (this.panel.customerSearch) {
            this.panel.customerSearch.clear();
        }

        // Hide guest selector
        this.hideGuestSelector();

        // Clear notes
        const notesInput = document.getElementById('newPanelNotes');
        if (notesInput) notesInput.value = '';

        // Clear preferences
        this.panel.clearPreferences();

        // Focus on search input
        document.getElementById('newPanelCustomerSearch')?.focus();
    }

    /**
     * Handle hotel guest selection - fetch room guests and populate selector
     */
    async handleHotelGuestSelect(guest) {
        document.getElementById('newPanelCustomerId').value = guest.id;
        document.getElementById('newPanelCustomerSource').value = 'hotel_guest';
        this.state.selectedGuest = guest;

        // Show customer display with guest details
        this.showCustomerDisplay(guest);

        // Hotel guests don't have preferences yet, clear them
        this.panel.clearPreferences();

        // But they may have notes from the PMS
        const notesInput = document.getElementById('newPanelNotes');
        if (guest.notes && notesInput) {
            notesInput.value = guest.notes;
        }

        // Calculate pricing after hotel guest selection
        this.panel.pricingCalculator.calculateAndDisplayPricing();

        // Fetch all guests in the room
        await this.fetchRoomGuestsForGuest(guest);
    }

    /**
     * Fetch all room guests (for hotel guest selection)
     */
    async fetchRoomGuestsForGuest(guest) {
        try {
            const response = await fetch(
                `${this.panel.options.apiBaseUrl}/hotel-guests/lookup?room=${encodeURIComponent(guest.room_number)}`
            );
            const data = await response.json();

            this.state.roomGuests = data.guests || [];
            const guestCount = data.guest_count || 1;

            // If multiple guests, show the selector
            if (guestCount > 1 && this.state.roomGuests.length > 1) {
                this.showGuestSelector(guest, guestCount);
            } else {
                this.hideGuestSelector();
            }

            // Auto-set num_people based on guest count (only if not manually edited)
            const capacity = this.panel.calculateCapacity();
            const numPeopleInput = document.getElementById('newPanelNumPeople');
            if (numPeopleInput && !this.panel.numPeopleManuallyEdited) {
                numPeopleInput.value = guestCount;
            }

            // Check if we need more furniture for all guests
            if (guestCount > capacity) {
                this.panel.showCapacityWarning(guestCount, capacity);
            } else {
                this.panel.hideCapacityWarning();
            }

        } catch (error) {
            console.error('Error fetching room guests:', error);
            this.hideGuestSelector();
            // Set default num_people to 1 if fetch fails (only if not manually edited)
            const numPeopleInput = document.getElementById('newPanelNumPeople');
            if (numPeopleInput && !this.panel.numPeopleManuallyEdited) {
                numPeopleInput.value = 1;
            }
        }
    }

    /**
     * Show the guest selector dropdown
     */
    showGuestSelector(selectedGuest, guestCount) {
        const selectorWrapper = document.getElementById('newPanelGuestSelectorWrapper');
        const guestSelector = document.getElementById('newPanelGuestSelector');
        const guestCountDisplay = document.getElementById('newPanelGuestCount');

        if (!selectorWrapper || !guestSelector) return;

        // Update guest count display
        if (guestCountDisplay) {
            guestCountDisplay.textContent = guestCount;
        }

        // Populate the selector with all room guests
        guestSelector.innerHTML = this.state.roomGuests.map(g => {
            const isSelected = g.id === selectedGuest.id;
            const mainBadge = g.is_main_guest ? ' (Principal)' : '';
            return `<option value="${g.id}" ${isSelected ? 'selected' : ''}>${g.guest_name}${mainBadge}</option>`;
        }).join('');

        // Show the wrapper
        selectorWrapper.style.display = 'block';
    }

    /**
     * Hide the guest selector
     */
    hideGuestSelector() {
        const selectorWrapper = document.getElementById('newPanelGuestSelectorWrapper');
        if (selectorWrapper) {
            selectorWrapper.style.display = 'none';
        }
        this.state.roomGuests = [];
    }

    /**
     * Handle guest selector change
     */
    onGuestSelectorChange() {
        const guestSelector = document.getElementById('newPanelGuestSelector');
        const selectedId = parseInt(guestSelector.value);
        const guest = this.state.roomGuests.find(g => g.id === selectedId);

        if (guest) {
            document.getElementById('newPanelCustomerId').value = guest.id;
            this.state.selectedGuest = guest;

            // Update customer display with new guest info
            this.showCustomerDisplay(guest);

            // Update notes if the guest has any
            const notesInput = document.getElementById('newPanelNotes');
            if (notesInput) {
                notesInput.value = guest.notes || '';
            }
        }
    }
}

// --- date-availability.js ---
/**
 * DateAvailabilityHandler - Manages date picker and real-time availability checking
 * SG-02: Real-time availability check when dates change
 */
class DateAvailabilityHandler {
    constructor(panel) {
        this.panel = panel;
        this._availabilityCheckTimeout = null;
    }

    /**
     * Initialize DatePicker for the panel
     */
    initDatePicker(date) {
        const container = document.getElementById('newPanelDatePicker');
        if (!container) return null;

        // Destroy existing picker if any
        if (this.panel.datePicker) {
            this.panel.datePicker.destroy();
        }

        // Create new DatePicker with current date
        const datePicker = new DatePicker({
            container: container,
            initialDates: [date],
            onDateChange: (dates) => {
                // SG-02: Real-time availability check when dates change
                this.checkAvailabilityRealtime(dates);
                // Calculate pricing when dates change
                this.panel.pricingCalculator.calculateAndDisplayPricing();
            }
        });

        return datePicker;
    }

    /**
     * SG-02: Real-time availability check (called when dates change)
     * Uses debouncing to avoid excessive API calls
     */
    checkAvailabilityRealtime(dates) {
        // Clear any pending check
        if (this._availabilityCheckTimeout) {
            clearTimeout(this._availabilityCheckTimeout);
        }

        // Debounce: wait 300ms before checking
        this._availabilityCheckTimeout = setTimeout(async () => {
            if (!dates || dates.length === 0) return;

            const furnitureIds = this.panel.state.selectedFurniture.map(f => f.id);
            if (furnitureIds.length === 0) return;

            try {
                const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
                const response = await fetch(`${this.panel.options.apiBaseUrl}/reservations/check-availability`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        furniture_ids: furnitureIds,
                        dates: dates
                    })
                });

                if (!response.ok) return;

                const result = await response.json();

                if (!result.all_available && result.unavailable && result.unavailable.length > 0) {
                    // Show inline warning in the furniture section
                    this.showAvailabilityWarning(result.unavailable, dates);
                } else {
                    // Clear any existing warning
                    this.clearAvailabilityWarning();
                }
            } catch (error) {
                console.error('Real-time availability check error:', error);
            }
        }, 300);
    }

    /**
     * Show inline availability warning in furniture section
     */
    showAvailabilityWarning(conflicts, selectedDates) {
        const furnitureChips = document.getElementById('newPanelFurnitureChips');
        if (!furnitureChips) return;

        // Find or create warning element
        let warningEl = furnitureChips.parentElement?.querySelector('.availability-warning');
        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.className = 'availability-warning';
            furnitureChips.parentElement?.appendChild(warningEl);
        }

        // Get furniture numbers for display
        const furnitureMap = {};
        this.panel.state.selectedFurniture.forEach(f => {
            furnitureMap[f.id] = f.number;
        });

        // Group conflicts by date
        const conflictsByDate = {};
        conflicts.forEach(c => {
            if (!conflictsByDate[c.date]) conflictsByDate[c.date] = [];
            conflictsByDate[c.date].push({
                ...c,
                furniture_number: furnitureMap[c.furniture_id] || `#${c.furniture_id}`
            });
        });

        // Build warning message
        const formatDate = (dateStr) => {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        };

        let warningHtml = '<i class="fas fa-exclamation-triangle"></i> ';
        const conflictDates = Object.keys(conflictsByDate);

        if (conflictDates.length === 1) {
            const date = conflictDates[0];
            const items = conflictsByDate[date];
            warningHtml += `<strong>${items.map(i => escapeHtml(i.furniture_number)).join(', ')}</strong> ocupado el ${formatDate(date)}`;
        } else {
            warningHtml += `Mobiliario no disponible para ${conflictDates.length} fechas`;
        }

        warningEl.innerHTML = warningHtml;
        warningEl.style.display = 'flex';
    }

    /**
     * Clear availability warning
     */
    clearAvailabilityWarning() {
        const furnitureChips = document.getElementById('newPanelFurnitureChips');
        const warningEl = furnitureChips?.parentElement?.querySelector('.availability-warning');
        if (warningEl) {
            warningEl.style.display = 'none';
        }
    }

    /**
     * Show capacity warning when guest count exceeds furniture capacity
     */
    showCapacityWarning(guestCount, capacity) {
        const furnitureSummary = document.getElementById('newPanelFurnitureSummary');
        if (!furnitureSummary) return;

        // Find or create warning element in furniture section
        let warningEl = document.getElementById('newPanelCapacityWarning');
        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.id = 'newPanelCapacityWarning';
            warningEl.className = 'capacity-warning';
            furnitureSummary.parentElement?.appendChild(warningEl);
        }

        const needed = guestCount - capacity;
        warningEl.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>
                <strong>${guestCount} huespedes</strong> en la habitacion pero el mobiliario seleccionado
                solo tiene capacidad para <strong>${capacity}</strong>.
            </span>
            <button type="button" class="btn-add-furniture" id="btnAddMoreFurniture">
                <i class="fas fa-plus"></i> Agregar mobiliario
            </button>
        `;
        warningEl.style.display = 'flex';

        // Bind click event for add furniture button
        const addBtn = document.getElementById('btnAddMoreFurniture');
        addBtn?.addEventListener('click', () => this.triggerAddMoreFurniture(needed));
    }

    /**
     * Hide capacity warning
     */
    hideCapacityWarning() {
        const warningEl = document.getElementById('newPanelCapacityWarning');
        if (warningEl) {
            warningEl.style.display = 'none';
        }
    }

    /**
     * Trigger the add more furniture flow
     */
    triggerAddMoreFurniture(neededCapacity) {
        const panel = document.getElementById('newReservationPanel');
        const backdrop = document.getElementById('newReservationPanelBackdrop');

        // Minimize the panel and hide backdrop to allow map interaction
        panel.classList.add('minimized');
        backdrop.classList.remove('show');

        // Dispatch event to tell the map to enter furniture addition mode
        document.dispatchEvent(new CustomEvent('reservation:addMoreFurniture', {
            detail: {
                currentFurniture: this.panel.state.selectedFurniture.map(f => f.id),
                neededCapacity: neededCapacity,
                currentDate: this.panel.state.currentDate
            }
        }));
    }

    /**
     * Add furniture to the current selection (called from map)
     */
    addFurniture(furniture) {
        // Add to selected furniture
        furniture.forEach(f => {
            if (!this.panel.state.selectedFurniture.find(sf => sf.id === f.id)) {
                this.panel.state.selectedFurniture.push(f);
            }
        });

        // Re-render furniture chips
        this.panel.renderFurnitureChips();

        // Check capacity again
        const capacity = this.panel.calculateCapacity();
        const numPeopleInput = document.getElementById('newPanelNumPeople');
        const guestCount = this.panel.customerHandler.state.roomGuests.length ||
                          parseInt(numPeopleInput?.value) || 2;

        if (guestCount > capacity) {
            this.showCapacityWarning(guestCount, capacity);
        } else {
            this.hideCapacityWarning();
        }

        // Restore panel and backdrop
        const panel = document.getElementById('newReservationPanel');
        const backdrop = document.getElementById('newReservationPanelBackdrop');
        panel.classList.remove('minimized');
        backdrop.classList.add('show');

        // Calculate pricing after furniture changes
        this.panel.pricingCalculator.calculateAndDisplayPricing();
    }
}

// --- pricing-calculator.js ---
/**
 * PricingCalculator - Manages pricing calculations and display
 * Handles package fetching, selection, price calculation, and manual editing
 */
class PricingCalculator {
    constructor(panel) {
        this.panel = panel;
        this._lastCalculatedPrice = 0;
        this._packageChangeHandler = null;

        // Initialize price editing handlers
        this.setupPriceEditing();
    }

    /**
     * Fetch available packages based on reservation details
     */
    async fetchAvailablePackages(customerType, furnitureIds, reservationDate, numPeople) {
        try {
            console.log('[Pricing] Fetching available packages:', {customerType, furnitureIds, reservationDate, numPeople});
            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/pricing/packages/available`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    customer_type: customerType,
                    furniture_ids: furnitureIds,
                    reservation_date: reservationDate,
                    num_people: numPeople
                })
            });

            const result = await response.json();
            console.log('[Pricing] Available packages:', result);

            if (result.success) {
                return result.packages || [];
            }
            return [];
        } catch (error) {
            console.error('[Pricing] Error fetching packages:', error);
            return [];
        }
    }

    /**
     * Update package selector UI with available options (compact dropdown)
     */
    updatePackageSelector(packages, customerType) {
        const pricingTypeSelector = document.getElementById('newPanelPricingTypeSelector');
        const pricingTypeSelect = document.getElementById('newPanelPricingTypeSelect');
        const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');

        if (!pricingTypeSelector || !pricingTypeSelect) return;

        // Hide selector if no packages available
        if (!packages || packages.length === 0) {
            pricingTypeSelector.style.display = 'none';
            selectedPackageIdInput.value = '';
            return;
        }

        // Check if we need to rebuild (packages changed)
        const currentPackageIds = Array.from(pricingTypeSelect.options)
            .map(opt => opt.value)
            .filter(v => v !== '') // Exclude minimum consumption option
            .sort()
            .join(',');

        const newPackageIds = packages.map(p => p.id.toString()).sort().join(',');

        // If packages haven't changed, don't rebuild (preserve selection)
        if (currentPackageIds === newPackageIds && pricingTypeSelect.options.length > 1) {
            pricingTypeSelector.style.display = 'block';
            return;
        }

        // Save current selection before rebuilding
        const currentSelection = selectedPackageIdInput.value;

        // Clear previous options (keep the default minimum consumption)
        pricingTypeSelect.innerHTML = '<option value="">Consumo mínimo</option>';

        // Add package options to dropdown
        packages.forEach(pkg => {
            const option = document.createElement('option');
            option.value = pkg.id;
            option.textContent = `${pkg.package_name} - €${pkg.calculated_price.toFixed(2)}`;
            pricingTypeSelect.appendChild(option);
        });

        // Show selector
        pricingTypeSelector.style.display = 'block';

        // Add event listener for dropdown change
        pricingTypeSelect.removeEventListener('change', this._packageChangeHandler); // Remove old listener
        this._packageChangeHandler = () => {
            const selectedValue = pricingTypeSelect.value;
            selectedPackageIdInput.value = selectedValue;

            console.log('[Pricing] Package changed to:', selectedValue || 'Consumo mínimo');
            this.calculatePricingOnly();
        };
        pricingTypeSelect.addEventListener('change', this._packageChangeHandler);

        // Restore previous selection or default to minimum consumption
        if (currentSelection && pricingTypeSelect.querySelector(`option[value="${currentSelection}"]`)) {
            pricingTypeSelect.value = currentSelection;
            selectedPackageIdInput.value = currentSelection;
        } else {
            pricingTypeSelect.value = '';
            selectedPackageIdInput.value = '';
        }
    }

    /**
     * Calculate pricing only (without refetching packages)
     * Use when only the package selection changes
     */
    async calculatePricingOnly() {
        const customerId = document.getElementById('newPanelCustomerId').value;
        const customerSource = document.getElementById('newPanelCustomerSource')?.value || 'customer';
        const furniture = this.panel.state.selectedFurniture.map(f => f.id);
        const dates = this.panel.datePicker ? this.panel.datePicker.getSelectedDates() : [];
        const numPeople = parseInt(document.getElementById('newPanelNumPeople')?.value) || 2;
        const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');

        if (!customerId || furniture.length === 0 || dates.length === 0) {
            return;
        }

        // Show loading
        const pricingDisplay = document.getElementById('newPanelPricingDisplay');
        const loadingEl = pricingDisplay?.querySelector('.pricing-loading');
        const contentEl = pricingDisplay?.querySelector('.pricing-content');

        if (loadingEl && contentEl) {
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
        }

        try {
            const packageId = selectedPackageIdInput?.value || '';

            const requestBody = {
                customer_id: parseInt(customerId),
                customer_source: customerSource,
                furniture_ids: furniture,
                reservation_date: dates[0],
                num_people: numPeople
            };

            if (packageId) {
                requestBody.package_id = parseInt(packageId);
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/pricing/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestBody)
            });

            const result = await response.json();

            if (result.success) {
                this.updatePricingDisplay(result.pricing);
            } else {
                console.error('[Pricing] Calculation error:', result.error);
            }
        } catch (error) {
            console.error('[Pricing] API error:', error);
        } finally {
            if (loadingEl && contentEl) {
                loadingEl.style.display = 'none';
                contentEl.style.display = 'flex';
            }
        }
    }

    /**
     * Calculate and display pricing for current reservation
     */
    async calculateAndDisplayPricing() {
        const customerId = document.getElementById('newPanelCustomerId').value;
        const customerSource = document.getElementById('newPanelCustomerSource')?.value || 'customer';
        const furniture = this.panel.state.selectedFurniture.map(f => f.id);
        const dates = this.panel.datePicker ? this.panel.datePicker.getSelectedDates() : [];
        const numPeople = parseInt(document.getElementById('newPanelNumPeople')?.value) || 2;
        const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');

        console.log('[Pricing] Calculating pricing:', {customerId, customerSource, furniture, dates, numPeople});

        // Clear if not enough data
        if (!customerId || furniture.length === 0 || dates.length === 0) {
            console.log('[Pricing] Not enough data, clearing display');
            this.updatePricingDisplay(null);
            this.updatePackageSelector([], customerSource);
            return;
        }

        // Show loading
        const pricingDisplay = document.getElementById('newPanelPricingDisplay');
        const loadingEl = pricingDisplay?.querySelector('.pricing-loading');
        const contentEl = pricingDisplay?.querySelector('.pricing-content');

        if (loadingEl && contentEl) {
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
        }

        try {
            // Determine customer type based on source and actual customer data
            // Hotel guests are always 'interno'
            // For beach_customers, use the actual customer_type from the customer record
            let customerType;
            if (customerSource === 'hotel_guest') {
                customerType = 'interno';
            } else {
                // Try to get customer_type from the selected customer object
                customerType = this.panel.customerHandler?.state?.selectedCustomer?.customer_type || 'externo';
            }

            console.log('[Pricing] Determined customer_type:', customerType);

            // First, fetch available packages to populate the selector
            const packages = await this.fetchAvailablePackages(
                customerType,
                furniture,
                dates[0],
                numPeople
            );

            // Update package selector UI (only if packages list changed)
            this.updatePackageSelector(packages, customerType);

            // Get selected package_id (empty string for minimum consumption)
            const packageId = selectedPackageIdInput?.value || '';

            console.log('[Pricing] Calling API:', `${this.panel.options.apiBaseUrl}/pricing/calculate`);
            const requestBody = {
                customer_id: parseInt(customerId),
                customer_source: customerSource,
                furniture_ids: furniture,
                reservation_date: dates[0], // Use first date for pricing
                num_people: numPeople
            };

            // Add package_id only if selected
            if (packageId) {
                requestBody.package_id = parseInt(packageId);
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/pricing/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestBody)
            });

            console.log('[Pricing] Response status:', response.status);
            const result = await response.json();
            console.log('[Pricing] Response data:', result);

            if (result.success) {
                this.updatePricingDisplay(result.pricing);
            } else {
                console.error('[Pricing] Calculation error:', result.error);
                this.updatePricingDisplay(null);
            }
        } catch (error) {
            console.error('[Pricing] API error:', error);
            this.updatePricingDisplay(null);
        } finally {
            if (loadingEl && contentEl) {
                loadingEl.style.display = 'none';
                contentEl.style.display = 'flex';
            }
        }
    }

    /**
     * Update pricing display UI (with editable price)
     */
    updatePricingDisplay(pricing) {
        const priceInput = document.getElementById('newPanelFinalPriceInput');
        const calculatedPriceEl = document.getElementById('newPanelCalculatedPrice');
        const calculatedAmountEl = calculatedPriceEl?.querySelector('.calculated-amount');
        const breakdownEl = document.getElementById('newPanelPricingBreakdown');
        const priceOverrideInput = document.getElementById('newPanelPriceOverride');
        const resetBtn = document.getElementById('newPanelPriceResetBtn');

        if (!pricing) {
            if (priceInput) priceInput.value = '0.00';
            if (calculatedPriceEl) calculatedPriceEl.style.display = 'none';
            if (breakdownEl) breakdownEl.style.display = 'none';
            if (resetBtn) resetBtn.style.display = 'none';
            if (priceOverrideInput) priceOverrideInput.value = '';
            return;
        }

        const calculatedPrice = pricing.calculated_price.toFixed(2);

        // Store calculated price for reference
        this._lastCalculatedPrice = parseFloat(calculatedPrice);

        // Update calculated price display
        if (calculatedAmountEl) {
            calculatedAmountEl.textContent = `€${calculatedPrice}`;
        }

        // Only update input if user hasn't manually overridden it
        if (!priceOverrideInput?.value) {
            if (priceInput) {
                priceInput.value = calculatedPrice;
                priceInput.classList.remove('modified');
            }
            if (calculatedPriceEl) calculatedPriceEl.style.display = 'none';
            if (resetBtn) resetBtn.style.display = 'none';
        } else {
            // Show that price is modified
            if (priceInput) priceInput.classList.add('modified');
            if (calculatedPriceEl) calculatedPriceEl.style.display = 'block';
            if (resetBtn) resetBtn.style.display = 'block';
        }

        // Show breakdown
        if (breakdownEl && pricing.breakdown) {
            breakdownEl.textContent = pricing.breakdown;
            breakdownEl.style.display = 'block';
        } else if (breakdownEl) {
            breakdownEl.style.display = 'none';
        }
    }

    /**
     * Setup price editing handlers
     */
    setupPriceEditing() {
        const priceInput = document.getElementById('newPanelFinalPriceInput');
        const priceOverrideInput = document.getElementById('newPanelPriceOverride');
        const resetBtn = document.getElementById('newPanelPriceResetBtn');
        const calculatedPriceEl = document.getElementById('newPanelCalculatedPrice');

        if (!priceInput) return;

        // Handle manual price changes
        priceInput.addEventListener('input', () => {
            const manualPrice = parseFloat(priceInput.value) || 0;
            const calculatedPrice = this._lastCalculatedPrice || 0;

            if (Math.abs(manualPrice - calculatedPrice) > 0.01) {
                // Price has been manually modified
                priceInput.classList.add('modified');
                priceOverrideInput.value = manualPrice.toFixed(2);
                if (calculatedPriceEl) calculatedPriceEl.style.display = 'block';
                if (resetBtn) resetBtn.style.display = 'block';
            } else {
                // Price matches calculated, remove override
                priceInput.classList.remove('modified');
                priceOverrideInput.value = '';
                if (calculatedPriceEl) calculatedPriceEl.style.display = 'none';
                if (resetBtn) resetBtn.style.display = 'none';
            }
        });

        // Handle reset button
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                const calculatedPrice = this._lastCalculatedPrice || 0;
                priceInput.value = calculatedPrice.toFixed(2);
                priceInput.classList.remove('modified');
                priceOverrideInput.value = '';
                calculatedPriceEl.style.display = 'none';
                resetBtn.style.display = 'none';
            });
        }
    }
}

// --- conflict-resolver.js ---
/**
 * ConflictResolver - Handles multi-day furniture conflicts
 * Shows conflict modal, navigates to conflict days, retries with per-day selections
 */
class ConflictResolver {
    constructor(panel) {
        this.panel = panel;
        this.conflictModal = null;
    }

    /**
     * Initialize the conflict resolution modal (lazy)
     */
    initConflictModal() {
        if (this.conflictModal) return;

        this.conflictModal = new ConflictResolutionModal({
            onNavigateToDay: (date, conflicts) => {
                this.handleNavigateToConflictDay(date, conflicts);
            },
            onRetry: (furnitureByDate) => {
                this.retryWithPerDayFurniture(furnitureByDate);
            },
            onCancel: () => {
                this.panel.state.conflictResolutionMode = false;
                const panelEl = document.getElementById('newReservationPanel');
                panelEl.classList.remove('minimized');
            },
            onRemoveDate: (date) => {
                // Update the DatePicker when a date is removed from conflict modal
                if (this.panel.datePicker) {
                    this.panel.datePicker.removeDate(date);
                }
            }
        });
    }

    /**
     * Handle conflict error from API - show the conflict modal
     */
    handleConflictError(result, selectedDates) {
        this.initConflictModal();

        const originalFurniture = this.panel.state.selectedFurniture.map(f => f.id);

        // Save customer data for retry - the DOM might get reset during conflict resolution
        this.panel.state.savedCustomerForRetry = {
            customerId: document.getElementById('newPanelCustomerId').value,
            customerSource: document.getElementById('newPanelCustomerSource').value,
            selectedGuest: this.panel.customerHandler.state.selectedGuest,
            selectedCustomer: this.panel.customerHandler.state.selectedCustomer,
            chargeToRoom: document.getElementById('newPanelChargeToRoom')?.checked || false,
            numPeople: parseInt(document.getElementById('newPanelNumPeople').value) || 2,
            notes: document.getElementById('newPanelNotes')?.value || '',
            preferences: [...this.panel.state.preferences],
            tagIds: [...(this.panel.state.selectedTags || [])],
            packageId: document.getElementById('newPanelSelectedPackageId')?.value || ''
        };

        this.conflictModal.show(
            result.unavailable,
            selectedDates,
            originalFurniture
        );

        this.panel.state.conflictResolutionMode = true;
    }

    /**
     * Handle navigation to a conflict day - minimize panel and navigate map
     */
    handleNavigateToConflictDay(date, conflicts) {
        const panelEl = document.getElementById('newReservationPanel');
        // Minimize the panel
        panelEl.classList.add('minimized');

        // Get original selection for this date (or all furniture if not set)
        const originalSelection = this.panel.state.furnitureByDate[date] ||
                                  this.panel.state.selectedFurniture.map(f => f.id);

        // Build furniture number map for display
        const furnitureMap = {};
        this.panel.state.selectedFurniture.forEach(f => {
            furnitureMap[f.id] = f.number;
        });

        // Enhance conflicts with furniture numbers
        const enhancedConflicts = conflicts.map(c => ({
            ...c,
            furniture_number: c.furniture_number || furnitureMap[c.furniture_id] || `#${c.furniture_id}`
        }));

        // Dispatch event to tell the map to navigate and enter selection mode
        document.dispatchEvent(new CustomEvent('conflictResolution:selectAlternative', {
            detail: {
                date: date,
                conflicts: enhancedConflicts,
                currentSelection: originalSelection,
                originalCount: originalSelection.length,  // Total furniture to select
                conflictingLabels: enhancedConflicts.map(c => escapeHtml(c.furniture_number)).join(', ')
            }
        }));
    }

    /**
     * Retry creating reservation with per-day furniture selections
     */
    async retryWithPerDayFurniture(furnitureByDate) {
        const selectedDates = Object.keys(furnitureByDate).sort();

        if (selectedDates.length === 0) {
            this.panel.showToast('No hay fechas seleccionadas', 'warning');
            return;
        }

        // Validate all dates have furniture selections
        const missingDates = selectedDates.filter(d => !furnitureByDate[d]?.length);
        if (missingDates.length > 0) {
            this.panel.showToast('Selecciona mobiliario para todas las fechas', 'warning');
            return;
        }

        // Show loading state
        const createBtn = document.getElementById('newPanelCreateBtn');
        createBtn.disabled = true;
        createBtn.querySelector('.save-text').style.display = 'none';
        createBtn.querySelector('.save-loading').style.display = 'flex';

        try {
            // Use saved customer data from conflict resolution - PRIORITIZE saved values
            // because DOM might have been reset during conflict resolution flow
            const saved = this.panel.state.savedCustomerForRetry || {};

            // In conflict resolution, always use saved data if available
            const customerId = saved.customerId || document.getElementById('newPanelCustomerId').value;
            const customerSource = saved.customerSource || document.getElementById('newPanelCustomerSource').value || 'customer';

            console.log('[RetryReservation] Customer data:', {
                savedCustomerId: saved.customerId,
                domCustomerId: document.getElementById('newPanelCustomerId').value,
                finalCustomerId: customerId,
                savedSource: saved.customerSource,
                domSource: document.getElementById('newPanelCustomerSource').value,
                finalSource: customerSource
            });

            if (!customerId) {
                throw new Error('Cliente requerido');
            }

            let finalCustomerId = parseInt(customerId);

            // If hotel guest, convert to beach customer first
            if (customerSource === 'hotel_guest') {
                const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
                const convertResponse = await fetch(`${this.panel.options.apiBaseUrl}/customers/from-hotel-guest`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        hotel_guest_id: finalCustomerId
                    })
                });

                const convertData = await convertResponse.json();

                if (!convertData.success) {
                    throw new Error(convertData.error || 'Error al convertir huesped a cliente');
                }

                finalCustomerId = convertData.customer.id;
            }

            // Build payload with furniture_by_date, using saved values as fallback
            const numPeople = parseInt(document.getElementById('newPanelNumPeople').value) || saved.numPeople || 2;
            const notes = document.getElementById('newPanelNotes')?.value?.trim() || saved.notes || '';
            const preferences = this.panel.state.preferences?.length > 0 ? this.panel.state.preferences : (saved.preferences || []);
            const chargeToRoom = document.getElementById('newPanelChargeToRoom')?.checked ?? saved.chargeToRoom ?? false;

            const tagIds = this.panel.state.selectedTags?.length > 0 ? this.panel.state.selectedTags : (saved.tagIds || []);
            const packageId = document.getElementById('newPanelSelectedPackageId')?.value || saved.packageId || '';

            // Read payment fields (same as panel-core.js createReservation)
            const paymentTicketEl = document.getElementById('newPanelPaymentTicket');
            const paymentMethodEl = document.getElementById('newPanelPaymentMethod');
            const paymentTicketValue = paymentTicketEl ? paymentTicketEl.value.trim() : '';
            const paymentMethodValue = paymentMethodEl ? paymentMethodEl.value.trim() : '';

            const payload = {
                customer_id: finalCustomerId,
                dates: selectedDates,
                furniture_by_date: furnitureByDate,  // Per-day furniture selections
                num_people: numPeople,
                time_slot: 'all_day',
                notes: notes,
                preferences: preferences,
                charge_to_room: chargeToRoom,
                tag_ids: tagIds,
                payment_ticket_number: paymentTicketValue,
                payment_method: paymentMethodValue,
                paid: (paymentTicketValue || paymentMethodValue) ? 1 : 0
            };

            if (packageId) {
                payload.package_id = parseInt(packageId);
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/map/quick-reservation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                this.panel.showToast(result.message || 'Reserva creada exitosamente', 'success');
                this.panel.state.conflictResolutionMode = false;
                this.panel.state.savedCustomerForRetry = null;  // Clear saved data after success
                const panelEl = document.getElementById('newReservationPanel');
                panelEl.classList.remove('minimized');
                this.panel.close();

                // Notify callback
                if (this.panel.options.onSave) {
                    this.panel.options.onSave(result.reservation);
                }
            } else {
                // Still conflicts? Show modal again
                if (result.unavailable && result.unavailable.length > 0) {
                    const originalFurniture = Object.values(furnitureByDate)[0] || [];
                    this.conflictModal.show(
                        result.unavailable,
                        selectedDates,
                        originalFurniture
                    );
                } else {
                    throw new Error(result.error || 'Error al crear reserva');
                }
            }

        } catch (error) {
            console.error('Retry reservation error:', error);
            this.panel.showToast(error.message, 'error');
        } finally {
            // Reset button state
            const createBtn = document.getElementById('newPanelCreateBtn');
            createBtn.disabled = false;
            createBtn.querySelector('.save-text').style.display = 'inline';
            createBtn.querySelector('.save-loading').style.display = 'none';
        }
    }
}

// --- safeguard-checks.js ---
/**
 * SafeguardChecks - Validation checks before creating reservations
 * SG-01: Duplicate reservation check
 * SG-02: Furniture availability check
 * SG-03: Hotel stay dates validation
 * SG-04: Capacity mismatch warnings
 * SG-05: Past dates error
 * SG-07: Furniture contiguity check
 */
class SafeguardChecks {
    constructor(panel) {
        this.panel = panel;
    }

    /**
     * Run all safeguard checks before creating reservation
     * @returns {Object} { proceed: boolean, viewExisting: number|null }
     */
    async runSafeguardChecks(customerId, customerSource, selectedDates) {
        // SG-05: Check for past dates
        const pastDateResult = await this.checkPastDates(selectedDates);
        if (!pastDateResult.proceed) {
            return { proceed: false };
        }

        // SG-03: Check hotel stay dates (only for hotel guests)
        if (customerSource === 'hotel_guest' && this.panel.customerHandler.state.selectedGuest) {
            const hotelStayResult = await this.checkHotelStayDates(selectedDates);
            if (!hotelStayResult.proceed) {
                return { proceed: false };
            }
        }

        // SG-04: Check capacity mismatch
        const capacityResult = await this.checkCapacityMismatch();
        if (!capacityResult.proceed) {
            return { proceed: false };
        }

        // SG-02: Check furniture availability
        const availabilityResult = await this.checkFurnitureAvailability(selectedDates);
        if (!availabilityResult.proceed) {
            return { proceed: false };
        }

        // SG-01: Check for duplicate reservation
        const duplicateResult = await this.checkDuplicateReservation(customerId, customerSource, selectedDates);
        if (!duplicateResult.proceed) {
            if (duplicateResult.viewExisting) {
                // User wants to view existing reservation
                return { proceed: false, viewExisting: duplicateResult.viewExisting };
            }
            return { proceed: false };
        }

        // SG-07: Check furniture contiguity (only for multiple furniture)
        if (this.panel.state.selectedFurniture.length > 1) {
            const contiguityResult = await this.checkFurnitureContiguity(selectedDates[0]);
            if (!contiguityResult.proceed) {
                return { proceed: false };
            }
        }

        return { proceed: true };
    }

    /**
     * SG-05: Check for past dates
     */
    async checkPastDates(selectedDates) {
        const today = new Date().toISOString().split('T')[0];
        const pastDates = selectedDates.filter(d => d < today);

        if (pastDates.length > 0) {
            await SafeguardModal.showPastDateError(pastDates);
            return { proceed: false };
        }

        return { proceed: true };
    }

    /**
     * SG-03: Check if selected dates are within hotel guest's stay
     */
    async checkHotelStayDates(selectedDates) {
        const guest = this.panel.customerHandler.state.selectedGuest;
        if (!guest || !guest.arrival_date || !guest.departure_date) {
            return { proceed: true }; // No hotel dates to check
        }

        // Normalize dates to YYYY-MM-DD for consistent comparison
        const normalizeDate = (dateStr) => {
            if (!dateStr) return null;
            // Handle ISO format (2025-12-21T00:00:00) or plain date
            return dateStr.split('T')[0];
        };

        const arrivalDate = normalizeDate(guest.arrival_date);
        const departureDate = normalizeDate(guest.departure_date);

        if (!arrivalDate || !departureDate) {
            return { proceed: true }; // Invalid dates, skip check
        }

        const outOfRangeDates = selectedDates.filter(date => {
            const normalizedDate = normalizeDate(date);
            return normalizedDate < arrivalDate || normalizedDate > departureDate;
        });

        if (outOfRangeDates.length > 0) {
            const action = await SafeguardModal.showHotelStayWarning(guest, outOfRangeDates);

            if (action === 'proceed') {
                return { proceed: true };
            }
            return { proceed: false };
        }

        return { proceed: true };
    }

    /**
     * SG-04: Check if num_people exceeds furniture capacity
     * SG-04b: Check if furniture capacity exceeds num_people
     */
    async checkCapacityMismatch() {
        const numPeople = parseInt(document.getElementById('newPanelNumPeople')?.value) || 2;
        const capacity = this.panel.calculateCapacity();

        // SG-04: More people than furniture capacity
        if (numPeople > capacity) {
            const action = await SafeguardModal.showCapacityWarning(numPeople, capacity);

            if (action === 'adjust') {
                document.getElementById('newPanelNumPeople').value = capacity;
                return { proceed: true };
            } else if (action === 'keep') {
                return { proceed: true };
            }
            return { proceed: false };
        }

        // SG-04b: More furniture capacity than people (excess sunbeds)
        if (capacity > numPeople) {
            const action = await SafeguardModal.showExcessCapacityWarning(numPeople, capacity);

            if (action === 'proceed') {
                return { proceed: true };
            }
            return { proceed: false };
        }

        return { proceed: true };
    }

    /**
     * SG-02: Check furniture availability for selected dates
     */
    async checkFurnitureAvailability(selectedDates) {
        try {
            const furnitureIds = this.panel.state.selectedFurniture.map(f => f.id);

            if (furnitureIds.length === 0 || selectedDates.length === 0) {
                return { proceed: true };
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/reservations/check-availability`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    furniture_ids: furnitureIds,
                    dates: selectedDates
                })
            });

            if (!response.ok) {
                console.error('Availability check failed:', response.status);
                this.panel.showToast('Error verificando disponibilidad. Intenta de nuevo.', 'error'); return { proceed: false };
            }

            const result = await response.json();

            if (!result.all_available && result.unavailable && result.unavailable.length > 0) {
                console.log('[Safeguard] Furniture conflicts found:', result.unavailable);

                // Get furniture numbers for display
                const furnitureMap = {};
                this.panel.state.selectedFurniture.forEach(f => {
                    furnitureMap[f.id] = f.number;
                });

                // Enhance conflict data with furniture numbers
                const conflicts = result.unavailable.map(c => ({
                    ...c,
                    furniture_number: furnitureMap[c.furniture_id] || `#${c.furniture_id}`
                }));

                // For multi-day reservations, use the Conflict Resolution Modal
                // which allows selecting alternative furniture per day
                if (selectedDates.length > 1) {
                    // Trigger the conflict resolution flow
                    this.panel.conflictResolver.handleConflictError({ unavailable: conflicts }, selectedDates);
                    return { proceed: false, conflictResolution: true };
                }

                // For single-day reservations, show simple error modal
                await SafeguardModal.showFurnitureConflictError(conflicts);
                return { proceed: false };
            }

            return { proceed: true };

        } catch (error) {
            console.error('Furniture availability check error:', error);
            this.panel.showToast('Error verificando disponibilidad. Intenta de nuevo.', 'error'); return { proceed: false };
        }
    }

    /**
     * SG-07: Check if selected furniture is contiguous (no gaps with occupied furniture)
     */
    async checkFurnitureContiguity(date) {
        try {
            const furnitureIds = this.panel.state.selectedFurniture.map(f => f.id);

            // Only check contiguity when multiple furniture selected
            if (furnitureIds.length <= 1) {
                return { proceed: true };
            }

            const csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';
            const response = await fetch(`${this.panel.options.apiBaseUrl}/reservations/validate-contiguity`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    furniture_ids: furnitureIds,
                    date: date
                })
            });

            if (!response.ok) {
                console.error('Contiguity check failed:', response.status);
                this.panel.showToast('Error verificando contigüidad. Intenta de nuevo.', 'error'); return { proceed: false };
            }

            const result = await response.json();

            // If not contiguous, show warning
            if (!result.is_contiguous && result.gap_count > 0) {
                console.log('[Safeguard] Non-contiguous furniture detected:', result);

                const action = await SafeguardModal.showContiguityWarning(result);

                if (action === 'proceed') {
                    return { proceed: true };
                }
                return { proceed: false };
            }

            return { proceed: true };

        } catch (error) {
            console.error('Contiguity check error:', error);
            this.panel.showToast('Error verificando contigüidad. Intenta de nuevo.', 'error'); return { proceed: false };
        }
    }

    /**
     * SG-01: Check for duplicate reservation (same customer, same date)
     */
    async checkDuplicateReservation(customerId, customerSource, selectedDates) {
        try {
            // Build query params
            const params = new URLSearchParams();

            if (customerSource === 'hotel_guest') {
                params.append('hotel_guest_id', customerId);
            } else {
                params.append('customer_id', customerId);
            }

            // Check each date
            for (const date of selectedDates) {
                params.set('date', date);

                const response = await fetch(
                    `${this.panel.options.apiBaseUrl}/reservations/check-duplicate?${params.toString()}`
                );

                if (!response.ok) continue;

                const result = await response.json();

                if (result.has_duplicate && result.existing_reservation) {
                    console.log('[Safeguard] Duplicate found:', result.existing_reservation);
                    const action = await SafeguardModal.showDuplicateWarning(result.existing_reservation);
                    console.log('[Safeguard] User action:', action);

                    if (action === 'proceed') {
                        console.log('[Safeguard] User chose to proceed with duplicate');
                        return { proceed: true };
                    } else if (action === 'view') {
                        console.log('[Safeguard] User chose to view existing');
                        this.panel.close();
                        return { proceed: false, viewExisting: result.existing_reservation.id };
                    }
                    console.log('[Safeguard] User cancelled duplicate creation');
                    return { proceed: false };
                }
            }

            return { proceed: true };

        } catch (error) {
            console.error('Duplicate check error:', error);
            this.panel.showToast('Error verificando duplicados. Intenta de nuevo.', 'error'); return { proceed: false };
        }
    }
}

// --- panel-core.js ---
/**
 * NewReservationPanel - Main panel coordinator
 * Integrates all specialized modules for creating reservations
 *
 * Module Architecture:
 * - CustomerHandler: Customer selection, creation, display
 * - DateAvailabilityHandler: Date picker, availability checks
 * - PricingCalculator: Pricing fetch, display, editing
 * - ConflictResolver: Conflict modal, per-day selections
 * - SafeguardChecks: All validation checks (SG-01 to SG-07)
 *
 * Dependencies (must be loaded before this file):
 * - customer-handler.js
 * - date-availability.js
 * - pricing-calculator.js
 * - conflict-resolver.js
 * - safeguard-checks.js
 */

class NewReservationPanel {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/beach/api',
            onSave: null,
            onCancel: null,
            ...options
        };

        // State
        this.state = {
            isOpen: false,
            selectedFurniture: [],
            currentDate: null,
            preferences: [],
            selectedTags: [],
            conflictResolutionMode: false,
            furnitureByDate: {},   // {date: [furniture_ids]} - per-day selections
            savedCustomerForRetry: null,  // Saved customer data during conflict resolution
            waitlistEntryId: null  // Track waitlist entry ID for conversion
        };

        // Available characteristics (loaded from API)
        this.availableCharacteristics = [];

        // Cache DOM elements
        this.cacheElements();

        // CSRF token
        this.csrfToken = document.getElementById('newPanelCsrfToken')?.value || '';

        // Initialize modules
        this.customerHandler = new CustomerHandler(this);
        this.dateAvailabilityHandler = new DateAvailabilityHandler(this);
        this.pricingCalculator = new PricingCalculator(this);
        this.conflictResolver = new ConflictResolver(this);
        this.safeguardChecks = new SafeguardChecks(this);

        // Shared components (initialized on first open)
        this.customerSearch = null;
        this.datePicker = null;

        // Setup event listeners
        this.setupEventListeners();
        this.initCustomerSearch();
    }

    /**
     * Cache DOM elements for quick access
     */
    cacheElements() {
        this.panel = document.getElementById('newReservationPanel');
        this.backdrop = document.getElementById('newReservationPanelBackdrop');

        if (!this.panel || !this.backdrop) {
            console.warn('NewReservationPanel: Required elements not found');
            return;
        }

        // Furniture elements
        this.dateDisplay = document.getElementById('newPanelDate');
        this.furnitureChips = document.getElementById('newPanelFurnitureChips');
        this.furnitureSummary = document.getElementById('newPanelFurnitureSummary');

        // Details elements
        this.numPeopleInput = document.getElementById('newPanelNumPeople');
        this.notesInput = document.getElementById('newPanelNotes');
        this.preferencesInput = document.getElementById('newPanelPreferences');
        this.preferenceChipsContainer = document.getElementById('newPanelPreferenceChips');
        this.tagChipsContainer = document.getElementById('newPanelTagChips');

        // Buttons
        this.closeBtn = document.getElementById('newPanelCloseBtn');
        this.collapseBtn = document.getElementById('newReservationCollapseBtn');
        this.collapseBtnHeader = document.getElementById('newReservationCollapseBtnHeader');
        this.cancelBtn = document.getElementById('newPanelCancelBtn');
        this.createBtn = document.getElementById('newPanelCreateBtn');
    }

    /**
     * Initialize CustomerSearch component
     */
    initCustomerSearch() {
        const searchInput = document.getElementById('newPanelCustomerSearch');
        const resultsContainer = document.getElementById('newPanelCustomerResults');

        if (searchInput && resultsContainer) {
            this.customerSearch = new CustomerSearch({
                inputElement: searchInput,
                resultsContainer: resultsContainer,
                apiUrl: `${this.options.apiBaseUrl}/customers/search`,
                compact: true,
                showCreateLink: false,
                showInlineCreate: true,
                onSelect: (customer) => {
                    document.getElementById('newPanelCustomerId').value = customer.id;
                    document.getElementById('newPanelCustomerSource').value = 'customer';
                    this.customerHandler.autoFillCustomerData(customer);
                },
                onHotelGuestSelect: (guest) => {
                    this.customerHandler.handleHotelGuestSelect(guest);
                },
                onShowCreateForm: (prefillData) => {
                    this.customerHandler.showCreateCustomerForm(prefillData);
                }
            });
        }
    }

    /**
     * Load available characteristics from API
     */
    async loadCharacteristics() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/preferences`);
            if (response.ok) {
                const result = await response.json();
                this.availableCharacteristics = result.preferences || [];
                this.renderPreferenceChips();
            }
        } catch (error) {
            console.warn('Could not load characteristics:', error);
            if (this.preferenceChipsContainer) {
                this.preferenceChipsContainer.innerHTML =
                    '<span class="text-muted small">Error al cargar preferencias</span>';
            }
        }
    }

    /**
     * Render preference chips dynamically
     */
    renderPreferenceChips() {
        if (!this.preferenceChipsContainer) return;

        if (this.availableCharacteristics.length === 0) {
            this.preferenceChipsContainer.innerHTML =
                '<span class="text-muted small">No hay preferencias disponibles</span>';
            return;
        }

        const chipsHtml = this.availableCharacteristics.map(char => {
            // Normalize icon class
            let icon = char.icon || 'fa-star';
            if (!icon.startsWith('fas ') && !icon.startsWith('far ') && !icon.startsWith('fab ')) {
                icon = 'fas ' + icon;
            }
            const isActive = this.state.preferences.includes(char.code);
            return `
                <button type="button" class="pref-chip ${isActive ? 'active' : ''}" data-pref="${char.code}">
                    <i class="${icon}"></i> ${char.name}
                </button>
            `;
        }).join('');

        this.preferenceChipsContainer.innerHTML = chipsHtml;
    }

    /**
     * Load available tags from API
     */
    async loadTags() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/tags`);
            if (response.ok) {
                const result = await response.json();
                this.availableTags = result.tags || [];
                this.renderTagChips();
            }
        } catch (error) {
            console.warn('Could not load tags:', error);
            if (this.tagChipsContainer) {
                this.tagChipsContainer.innerHTML =
                    '<span class="text-muted small">Error al cargar etiquetas</span>';
            }
        }
    }

    /**
     * Render tag chips dynamically
     */
    renderTagChips() {
        if (!this.tagChipsContainer) return;

        if (!this.availableTags || this.availableTags.length === 0) {
            this.tagChipsContainer.innerHTML =
                '<span class="text-muted small">No hay etiquetas disponibles</span>';
            return;
        }

        const chipsHtml = this.availableTags.map(tag => {
            const isActive = this.state.selectedTags.includes(tag.id);
            const color = sanitizeColor(tag.color) || '#6C757D';
            return `
                <button type="button" class="tag-chip ${isActive ? 'active' : ''}"
                        data-tag-id="${tag.id}" style="--tag-color: ${color};">
                    <i class="fas fa-tag"></i> ${escapeHtml(tag.name)}
                </button>
            `;
        }).join('');

        this.tagChipsContainer.innerHTML = chipsHtml;
    }

    /**
     * Toggle tag chip
     */
    toggleTag(chip) {
        const tagId = parseInt(chip.dataset.tagId);
        chip.classList.toggle('active');

        if (chip.classList.contains('active')) {
            if (!this.state.selectedTags.includes(tagId)) {
                this.state.selectedTags.push(tagId);
            }
        } else {
            this.state.selectedTags = this.state.selectedTags.filter(id => id !== tagId);
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Close buttons
        this.closeBtn?.addEventListener('click', () => this.close());
        this.cancelBtn?.addEventListener('click', () => this.close());
        this.backdrop?.addEventListener('click', () => this.close());

        // Collapse buttons
        this.collapseBtn?.addEventListener('click', () => this.toggleCollapse());
        this.collapseBtnHeader?.addEventListener('click', () => this.toggleCollapse());

        // Create button
        this.createBtn?.addEventListener('click', () => this.createReservation());

        // Customer clear button
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');
        clearBtn?.addEventListener('click', () => this.customerHandler.clearCustomerSelection());

        // Guest selector change
        const guestSelector = document.getElementById('newPanelGuestSelector');
        guestSelector?.addEventListener('change', () => this.customerHandler.onGuestSelectorChange());

        // Preference chips - use event delegation for dynamic chips
        this.preferenceChipsContainer?.addEventListener('click', (e) => {
            const chip = e.target.closest('.pref-chip');
            if (chip) {
                this.togglePreference(chip);
            }
        });

        // Tag chips - use event delegation for dynamic chips
        this.tagChipsContainer?.addEventListener('click', (e) => {
            const chip = e.target.closest('.tag-chip');
            if (chip) {
                this.toggleTag(chip);
            }
        });

        // Load available characteristics and tags
        this.loadCharacteristics();
        this.loadTags();

        // Keyboard: Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isOpen) {
                this.close();
            }
        });

        // Track manual edits to num_people
        this.numPeopleManuallyEdited = false;

        // Track changes to num_people for pricing calculation
        this.numPeopleInput?.addEventListener('change', () => {
            // Mark as manually edited when user changes the value
            this.numPeopleManuallyEdited = true;

            // Calculate pricing when num_people changes
            this.pricingCalculator.calculateAndDisplayPricing();

            // Show capacity warning if exceeded (but don't prevent it)
            const capacity = this.calculateCapacity();
            const numPeople = parseInt(this.numPeopleInput.value) || 0;
            if (numPeople > capacity) {
                this.showCapacityWarning(numPeople, capacity);
            } else {
                this.hideCapacityWarning();
            }
        });

        // Also track input events (typing) as manual edits
        this.numPeopleInput?.addEventListener('input', () => {
            this.numPeopleManuallyEdited = true;
        });
    }

    /**
     * Open the panel with selected furniture
     */
    open(furniture, date) {
        if (!furniture || furniture.length === 0) {
            this.showToast('Selecciona mobiliario primero', 'warning');
            return;
        }

        // Set state
        this.state.isOpen = true;
        this.state.selectedFurniture = furniture;
        this.state.currentDate = date;
        this.state.preferences = [];
        this.state.selectedTags = [];

        // Notify modal state manager (closes other modals, bottom bar, controls map)
        if (window.modalStateManager) {
            window.modalStateManager.openModal('new-reservation', this);
        }

        // Reset manual edit flag when opening new reservation
        this.numPeopleManuallyEdited = false;

        // Reset form
        this.resetForm();

        // Populate furniture chips
        this.renderFurnitureChips();

        // Set date display
        this.dateDisplay.textContent = this.formatDateDisplay(date);

        // Initialize DatePicker with current date
        this.datePicker = this.dateAvailabilityHandler.initDatePicker(date);

        // Set default num_people based on capacity
        const capacity = this.calculateCapacity();
        this.numPeopleInput.value = Math.min(2, capacity);

        // Show panel
        this.panel.classList.add('open');
        this.backdrop.classList.add('show');

        // Focus on customer search
        setTimeout(() => {
            document.getElementById('newPanelCustomerSearch')?.focus();
        }, 300);

        // Calculate initial pricing if customer already selected
        if (document.getElementById('newPanelCustomerId').value) {
            this.pricingCalculator.calculateAndDisplayPricing();
        }
    }

    /**
     * Close the panel
     */
    close() {
        this.state.isOpen = false;
        this.state.conflictResolutionMode = false;
        this.state.savedCustomerForRetry = null;
        this.state.waitlistEntryId = null;  // Clear waitlist entry on close

        // Notify modal state manager
        if (window.modalStateManager) {
            window.modalStateManager.closeModal('new-reservation');
        }

        this.panel.classList.remove('open');
        this.panel.classList.remove('minimized');
        this.panel.classList.remove('collapsed');
        this.backdrop.classList.remove('show');

        // Notify callback
        if (this.options.onCancel) {
            this.options.onCancel();
        }
    }

    /**
     * Toggle panel collapsed state
     */
    toggleCollapse() {
        if (!this.panel) return;

        const isCurrentlyCollapsed = this.panel.classList.contains('collapsed');
        this.panel.classList.toggle('collapsed');

        // Notify modal state manager
        if (window.modalStateManager) {
            if (isCurrentlyCollapsed) {
                window.modalStateManager.expandModal('new-reservation');
            } else {
                window.modalStateManager.collapseModal('new-reservation');
            }
        }
    }

    /**
     * Open the panel pre-filled from a waitlist entry
     * Called when user clicks "Convertir" on a waitlist entry
     * @param {Object} entry - Waitlist entry with customer and preference data
     */
    async openFromWaitlist(entry) {
        if (!entry) {
            console.warn('NewReservationPanel.openFromWaitlist: No entry provided');
            return;
        }

        // Store waitlist entry ID for conversion after reservation is created
        this.state.waitlistEntryId = entry.id;

        // We need furniture selected to open the panel
        // If preferred zone/type specified, we could suggest furniture
        // For now, just notify user they need to select furniture
        this.showToast('Selecciona mobiliario en el mapa para crear la reserva', 'info');

        // Store waitlist data for pre-filling when panel opens
        this._pendingWaitlistEntry = entry;

        // Dispatch event to notify map that we're in waitlist convert mode
        document.dispatchEvent(new CustomEvent('waitlist:selectFurnitureForConvert', {
            detail: { entry }
        }));
    }

    /**
     * Pre-fill the panel with waitlist entry data
     * Called after furniture is selected
     * @param {Object} entry - Waitlist entry data
     */
    async prefillFromWaitlist(entry) {
        if (!entry) return;

        // Store waitlist entry ID
        this.state.waitlistEntryId = entry.id;

        // Pre-fill customer if available
        if (entry.customer_id) {
            try {
                // Fetch full customer data
                const response = await fetch(`${this.options.apiBaseUrl}/customers/${entry.customer_id}`);
                const data = await response.json();

                if (data.success && data.customer) {
                    document.getElementById('newPanelCustomerId').value = data.customer.id;
                    document.getElementById('newPanelCustomerSource').value = 'customer';
                    this.customerHandler.autoFillCustomerData(data.customer);
                }
            } catch (error) {
                console.error('Error fetching customer for waitlist conversion:', error);
            }
        } else if (entry.customer_name || entry.external_name) {
            // No customer_id but have name info
            const isInterno = entry.customer_type === 'interno';
            const displayName = entry.customer_name || entry.external_name || '';
            const phone = entry.phone || entry.external_phone || '';

            if (!isInterno) {
                // External customer: Show create customer form pre-filled
                // so user can complete the customer profile
                const nameParts = displayName.split(' ');
                const firstName = nameParts[0] || '';
                const lastName = nameParts.slice(1).join(' ') || '';

                this.customerHandler.showCreateCustomerForm({
                    first_name: firstName,
                    last_name: lastName,
                    phone: phone,
                    email: entry.email || ''
                });
            } else {
                // Internal customer (hotel guest) without customer_id
                // Display as pending customer info
                const tempCustomer = {
                    display_name: displayName,
                    first_name: displayName.split(' ')[0] || '',
                    last_name: displayName.split(' ').slice(1).join(' ') || '',
                    customer_type: 'interno',
                    room_number: entry.room_number || null,
                    phone: phone,
                    source: 'hotel_guest'
                };

                // Show in display (but don't set customer_id since it doesn't exist yet)
                this.customerHandler.showCustomerDisplay(tempCustomer);
            }
        }

        // Pre-fill number of people
        if (entry.num_people && this.numPeopleInput) {
            this.numPeopleInput.value = entry.num_people;
            this.numPeopleManuallyEdited = true; // Mark as set so it's not overwritten
        }

        // Pre-fill notes with waitlist context
        if (entry.notes && this.notesInput) {
            this.notesInput.value = 'Desde lista de espera: ' + entry.notes;
        }

        // Pre-fill date if available (initialize DatePicker with the requested date)
        if (entry.requested_date && this.datePicker) {
            this.datePicker.setSelectedDates([entry.requested_date]);
        }

        // Calculate pricing after pre-filling
        this.pricingCalculator.calculateAndDisplayPricing();
    }

    /**
     * Reset the form to initial state
     */
    resetForm() {
        // Clear customer search
        if (this.customerSearch) {
            this.customerSearch.clear();
        }
        document.getElementById('newPanelCustomerId').value = '';
        document.getElementById('newPanelCustomerSource').value = 'customer';

        // Hide customer display, show search wrapper
        const customerDisplay = document.getElementById('newPanelCustomerDisplay');
        const searchWrapper = document.getElementById('newPanelCustomerWrapper');
        const clearBtn = document.getElementById('newPanelCustomerClearBtn');

        if (customerDisplay) customerDisplay.style.display = 'none';
        if (searchWrapper) searchWrapper.style.display = 'block';
        if (clearBtn) clearBtn.style.display = 'none';

        // Hide guest selector and clear room guests state
        this.customerHandler.hideGuestSelector();
        this.customerHandler.state.selectedGuest = null;
        this.customerHandler.state.selectedCustomer = null;

        // Reset inputs
        if (this.notesInput) this.notesInput.value = '';

        // Clear payment fields
        const paymentTicketInput = document.getElementById('newPanelPaymentTicket');
        const paymentMethodSelect = document.getElementById('newPanelPaymentMethod');
        if (paymentTicketInput) paymentTicketInput.value = '';
        if (paymentMethodSelect) paymentMethodSelect.value = '';

        // Clear preferences
        this.clearPreferences();
    }

    /**
     * Render furniture chips
     */
    renderFurnitureChips() {
        if (!this.furnitureChips) return;

        const chipsHtml = this.state.selectedFurniture.map(f => `
            <span class="furniture-chip">
                <span class="furniture-type-icon">${this.getFurnitureIcon(f.type_name)}</span>
                ${escapeHtml(String(f.number))}
            </span>
        `).join('');

        this.furnitureChips.innerHTML = chipsHtml;

        // Update summary
        const count = this.state.selectedFurniture.length;
        const capacity = this.calculateCapacity();
        this.furnitureSummary.textContent = `${count} item${count !== 1 ? 's' : ''} • Capacidad: ${capacity} personas`;
    }

    /**
     * Get furniture icon based on type
     */
    getFurnitureIcon(typeName) {
        if (!typeName) return '🪑';
        const name = typeName.toLowerCase();
        if (name.includes('hamaca')) return '🛏️';
        if (name.includes('balinesa')) return '🛖';
        if (name.includes('sombrilla')) return '☂️';
        return '🪑';
    }

    /**
     * Calculate total capacity
     */
    calculateCapacity() {
        return this.state.selectedFurniture.reduce((sum, f) => sum + (f.capacity || 2), 0);
    }

    /**
     * Format date for display
     */
    formatDateDisplay(dateStr) {
        const date = new Date(dateStr + 'T12:00:00');
        const options = { weekday: 'short', day: 'numeric', month: 'short' };
        return date.toLocaleDateString('es-ES', options);
    }

    /**
     * Toggle preference chip
     */
    togglePreference(chip) {
        const pref = chip.dataset.pref;
        chip.classList.toggle('active');

        if (chip.classList.contains('active')) {
            if (!this.state.preferences.includes(pref)) {
                this.state.preferences.push(pref);
            }
        } else {
            this.state.preferences = this.state.preferences.filter(p => p !== pref);
        }

        // Update hidden input
        this.preferencesInput.value = this.state.preferences.join(',');
    }

    /**
     * Clear all preferences
     */
    clearPreferences() {
        // Query all chips within the container (dynamic chips)
        const chips = this.preferenceChipsContainer?.querySelectorAll('.pref-chip');
        chips?.forEach(chip => chip.classList.remove('active'));
        this.state.preferences = [];
        if (this.preferencesInput) {
            this.preferencesInput.value = '';
        }

        // Clear tag chips
        const tagChips = this.tagChipsContainer?.querySelectorAll('.tag-chip');
        tagChips?.forEach(chip => chip.classList.remove('active'));
        this.state.selectedTags = [];
    }

    /**
     * Create the reservation
     */
    async createReservation() {
        // Validate customer
        const customerId = document.getElementById('newPanelCustomerId').value;
        const customerSource = document.getElementById('newPanelCustomerSource').value;

        if (!customerId) {
            this.showToast('Selecciona un cliente', 'warning');
            document.getElementById('newPanelCustomerSearch')?.focus();
            return;
        }

        // Get selected dates from DatePicker
        const selectedDates = this.datePicker ? this.datePicker.getSelectedDates() : [];
        if (selectedDates.length === 0) {
            this.showToast('Selecciona al menos una fecha', 'warning');
            return;
        }

        // Run safeguard checks before proceeding
        const safeguardResult = await this.safeguardChecks.runSafeguardChecks(customerId, customerSource, selectedDates);
        if (!safeguardResult.proceed) {
            // Check if user wants to view an existing reservation
            if (safeguardResult.viewExisting) {
                // Dispatch event to open the existing reservation panel
                document.dispatchEvent(new CustomEvent('reservation:openExisting', {
                    detail: { reservationId: safeguardResult.viewExisting }
                }));
            }
            return; // User cancelled or viewing existing
        }

        // Show loading state
        this.createBtn.disabled = true;
        this.createBtn.querySelector('.save-text').style.display = 'none';
        this.createBtn.querySelector('.save-loading').style.display = 'flex';

        try {
            let finalCustomerId = parseInt(customerId);

            // If hotel guest, convert to beach customer first
            if (customerSource === 'hotel_guest') {
                const convertResponse = await fetch(`${this.options.apiBaseUrl}/customers/from-hotel-guest`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({
                        hotel_guest_id: finalCustomerId
                    })
                });

                const convertData = await convertResponse.json();

                if (!convertData.success) {
                    throw new Error(convertData.error || 'Error al convertir huesped a cliente');
                }

                finalCustomerId = convertData.customer.id;
            }

            // Get selected package_id if any
            const selectedPackageIdInput = document.getElementById('newPanelSelectedPackageId');
            const packageId = selectedPackageIdInput?.value || '';

            // Get manual price override if any
            const priceOverrideInput = document.getElementById('newPanelPriceOverride');
            const priceOverride = priceOverrideInput?.value || '';

            // Get payment fields
            const paymentTicketInput = document.getElementById('newPanelPaymentTicket');
            const paymentMethodSelect = document.getElementById('newPanelPaymentMethod');

            // Get payment values for auto-toggle paid logic
            const paymentTicketValue = paymentTicketInput?.value.trim() || null;
            const paymentMethodValue = paymentMethodSelect?.value || null;

            // Create reservation using map quick-reservation endpoint
            const payload = {
                customer_id: finalCustomerId,
                furniture_ids: this.state.selectedFurniture.map(f => f.id),
                dates: selectedDates,
                num_people: parseInt(this.numPeopleInput.value) || 2,
                time_slot: 'all_day',
                notes: this.notesInput.value.trim(),
                preferences: this.state.preferences,
                tag_ids: this.state.selectedTags,
                charge_to_room: document.getElementById('newPanelChargeToRoom')?.checked || false,
                payment_ticket_number: paymentTicketValue,
                payment_method: paymentMethodValue,
                // Auto-toggle paid when payment details are provided
                paid: (paymentTicketValue || paymentMethodValue) ? 1 : 0
            };

            // Add package_id if selected (otherwise use minimum consumption)
            if (packageId) {
                payload.package_id = parseInt(packageId);
            }

            // Add manual price override if user edited the price
            if (priceOverride) {
                payload.price_override = parseFloat(priceOverride);
            }

            const response = await fetch(`${this.options.apiBaseUrl}/map/quick-reservation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(result.message || 'Reserva creada exitosamente', 'success');

                // Mark waitlist entry as converted if this reservation came from waitlist
                // Note: API returns 'reservation_id', not 'parent_id'
                const reservationId = result.reservation_id || result.parent_id;
                if (this.state.waitlistEntryId && reservationId) {
                    await this.markWaitlistAsConverted(this.state.waitlistEntryId, reservationId);
                }

                this.close();

                // Notify callback
                if (this.options.onSave) {
                    this.options.onSave({ id: reservationId, ticket_number: result.ticket_number || result.parent_ticket });
                }
            } else {
                // Check if this is a conflict error (multi-day with unavailable furniture)
                if (result.unavailable && result.unavailable.length > 0) {
                    this.conflictResolver.handleConflictError(result, selectedDates);
                } else {
                    throw new Error(result.error || 'Error al crear reserva');
                }
            }

        } catch (error) {
            console.error('Create reservation error:', error);
            this.showToast(error.message, 'error');
        } finally {
            // Reset button state
            this.createBtn.disabled = false;
            this.createBtn.querySelector('.save-text').style.display = 'inline';
            this.createBtn.querySelector('.save-loading').style.display = 'none';
        }
    }

    /**
     * Show toast message
     */
    showToast(message, type = 'info') {
        if (window.PuroBeach && window.PuroBeach.showToast) {
            window.PuroBeach.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Check if panel is open
     */
    isOpen() {
        return this.state.isOpen;
    }

    /**
     * Delegate methods to DateAvailabilityHandler
     */
    showCapacityWarning(guestCount, capacity) {
        this.dateAvailabilityHandler.showCapacityWarning(guestCount, capacity);
    }

    hideCapacityWarning() {
        this.dateAvailabilityHandler.hideCapacityWarning();
    }

    addFurniture(furniture) {
        this.dateAvailabilityHandler.addFurniture(furniture);
    }

    /**
     * Mark a waitlist entry as converted after reservation creation
     * @param {number} entryId - Waitlist entry ID
     * @param {number} reservationId - Created reservation ID
     */
    async markWaitlistAsConverted(entryId, reservationId) {
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
                // Dispatch event to update waitlist badge count
                window.dispatchEvent(new CustomEvent('waitlist:countUpdate'));
            } else {
                console.error('Error marking waitlist as converted:', data.error);
            }
        } catch (error) {
            console.error('Error marking waitlist as converted:', error);
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NewReservationPanel;
}
