/**
 * Waitlist State Management Module
 *
 * Provides factory functions for creating initial state and callbacks
 * for the WaitlistManager. Centralizes state structure definition.
 */

import { getTodayDate } from './utils.js';

// =============================================================================
// STATE FACTORY
// =============================================================================

/**
 * Create initial state object for WaitlistManager
 *
 * State properties:
 * - isOpen: Whether the panel is currently open
 * - currentDate: The date being viewed (YYYY-MM-DD)
 * - currentTab: Active tab ('pending' or 'history')
 * - entries: Array of pending waitlist entries
 * - historyEntries: Array of historical entries
 * - isLoading: Loading state flag
 * - selectedCustomerId: ID of selected existing customer
 * - selectedHotelGuestId: ID of selected hotel guest
 * - customerType: Type of customer ('interno' or 'externo')
 * - zones: Available beach zones
 * - furnitureTypes: Available furniture types
 * - packages: Available packages
 * - editingEntryId: ID of entry currently being edited
 *
 * @param {Object} options - Options that may override defaults
 * @param {string} [options.currentDate] - Initial date (defaults to today)
 * @returns {Object} Initial state object
 */
export function createInitialState(options = {}) {
    return {
        // Panel state
        isOpen: false,
        currentDate: options.currentDate || getTodayDate(),
        currentTab: 'pending',

        // Data collections
        entries: [],
        historyEntries: [],

        // Loading state
        isLoading: false,

        // Form state
        selectedCustomerId: null,
        selectedHotelGuestId: null,
        customerType: 'interno',

        // Reference data
        zones: [],
        furnitureTypes: [],
        packages: [],

        // Edit mode
        editingEntryId: null
    };
}

// =============================================================================
// CALLBACKS FACTORY
// =============================================================================

/**
 * Create callbacks object for WaitlistManager
 *
 * Callbacks:
 * - onConvert: Called when an entry is converted to a reservation
 * - onCountUpdate: Called when the pending count changes
 *
 * @param {Object} options - Options containing callback functions
 * @param {Function} [options.onConvert] - Callback for entry conversion
 * @param {Function} [options.onCountUpdate] - Callback for count updates
 * @returns {Object} Callbacks object
 */
export function createCallbacks(options = {}) {
    return {
        onConvert: options.onConvert || null,
        onCountUpdate: options.onCountUpdate || null
    };
}

// =============================================================================
// OPTIONS FACTORY
// =============================================================================

/**
 * Create default options merged with provided options
 *
 * @param {Object} options - User-provided options
 * @param {string} [options.apiBaseUrl='/beach/api'] - Base URL for API calls
 * @param {number} [options.debounceMs=300] - Debounce delay in milliseconds
 * @returns {Object} Merged options object
 */
export function createOptions(options = {}) {
    return {
        apiBaseUrl: '/beach/api',
        debounceMs: 300,
        ...options
    };
}

// =============================================================================
// STATE RESET HELPERS
// =============================================================================

/**
 * Get default form state values (for resetting form)
 * @returns {Object} Default form state
 */
export function getDefaultFormState() {
    return {
        selectedCustomerId: null,
        selectedHotelGuestId: null,
        customerType: 'interno',
        editingEntryId: null
    };
}

/**
 * Get default data state values (for clearing data)
 * @returns {Object} Default data state
 */
export function getDefaultDataState() {
    return {
        entries: [],
        historyEntries: []
    };
}
