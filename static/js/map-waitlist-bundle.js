// =============================================================================
// MAP WAITLIST BUNDLE - WaitlistManager and all modules
// Source files preserved individually for maintainability
// =============================================================================


// --- waitlist/utils.js ---
/**
 * Waitlist Utilities Module
 *
 * Pure utility functions for the WaitlistManager.
 * No dependencies on class state - all functions are standalone.
 */

// =============================================================================
// DATE UTILITIES
// =============================================================================

/**
 * Get today's date as YYYY-MM-DD string
 * @returns {string} Today's date in ISO format
 */
function getTodayDate() {
    const today = new Date();
    return today.toISOString().split('T')[0];
}

/**
 * Format date for display (weekday, day, month in es-ES)
 * @param {string} dateStr - Date string in YYYY-MM-DD format
 * @returns {string} Formatted date (e.g., "lun, 15 ene")
 */
function formatDateDisplay(dateStr) {
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

/**
 * Format date as DD/MM
 * @param {string} dateStr - Date string in YYYY-MM-DD format
 * @returns {string} Formatted date (e.g., "15/01")
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
 * Format relative time (hace X min, hace Xh, etc.)
 * @param {string} dateStr - ISO date string
 * @returns {string} Relative time in Spanish
 */
function formatTimeAgo(dateStr) {
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

// =============================================================================
// LABEL UTILITIES
// =============================================================================

/**
 * Get Spanish label for waitlist status
 * @param {string} status - Status code (waiting, contacted, etc.)
 * @returns {string} Spanish label
 */
function getStatusLabel(status) {
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

/**
 * Get Spanish label for time preference
 * @param {string} pref - Time preference code
 * @returns {string} Spanish label
 */
function getTimePreferenceLabel(pref) {
    const labels = {
        'morning': 'Mañana',
        'manana': 'Mañana',
        'afternoon': 'Tarde',
        'tarde': 'Tarde',
        'mediodia': 'Mediodía',
        'all_day': 'Todo el día',
        'todo_el_dia': 'Todo el día'
    };
    return labels[pref] || pref;
}

// =============================================================================
// SECURITY UTILITIES
// =============================================================================

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} str - String to escape
 * @returns {string} HTML-escaped string
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// =============================================================================
// UI UTILITIES
// =============================================================================

/**
 * Show toast notification via PuroBeach global
 * @param {string} message - Message to display
 * @param {string} type - Toast type (success, error, info, warning)
 */
function showToast(message, type = 'info') {
    if (window.PuroBeach?.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}


// --- waitlist/state.js ---
/**
 * Waitlist State Management Module
 *
 * Provides factory functions for creating initial state and callbacks
 * for the WaitlistManager. Centralizes state structure definition.
 */


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
function createInitialState(options = {}) {
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
function createCallbacks(options = {}) {
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
function createOptions(options = {}) {
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
function getDefaultFormState() {
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
function getDefaultDataState() {
    return {
        entries: [],
        historyEntries: []
    };
}


// --- waitlist/dom.js ---
/**
 * Waitlist DOM Caching Module
 * Cache all DOM element references for the WaitlistManager
 *
 * @module waitlist/dom
 */

/**
 * Cache all DOM elements used by WaitlistManager
 * @returns {Object|null} Object containing all DOM element references, or null if panel not found
 */
function cacheElements() {
    // Panel elements (check panel first)
    const panel = document.getElementById('waitlistPanel');
    const backdrop = document.getElementById('waitlistPanelBackdrop');

    if (!panel) {
        console.warn('WaitlistManager: Panel element not found');
        return null;
    }

    return {
        // Panel
        panel,
        backdrop,

        // Header
        closeBtn: document.getElementById('waitlistPanelCloseBtn'),
        collapseBtn: document.getElementById('waitlistCollapseBtn'),
        collapseBtnHeader: document.getElementById('waitlistCollapseBtnHeader'),
        addBtn: document.getElementById('waitlistAddBtn'),
        dateDisplay: document.getElementById('waitlistPanelDate'),

        // Tabs
        tabPending: document.getElementById('waitlistTabPending'),
        tabHistory: document.getElementById('waitlistTabHistory'),
        pendingCount: document.getElementById('waitlistPendingCount'),

        // Content
        loadingEl: document.getElementById('waitlistPanelLoading'),
        contentPending: document.getElementById('waitlistContentPending'),
        contentHistory: document.getElementById('waitlistContentHistory'),
        entriesPending: document.getElementById('waitlistEntriesPending'),
        entriesHistory: document.getElementById('waitlistEntriesHistory'),
        emptyPending: document.getElementById('waitlistEmptyPending'),
        emptyHistory: document.getElementById('waitlistEmptyHistory'),

        // Footer
        footerAddBtn: document.getElementById('waitlistFooterAddBtn'),

        // Modal elements
        modal: document.getElementById('waitlistAddModal'),
        modalBackdrop: document.getElementById('waitlistModalBackdrop'),
        modalCloseBtn: document.getElementById('waitlistModalCloseBtn'),
        modalCancelBtn: document.getElementById('waitlistModalCancelBtn'),
        modalSaveBtn: document.getElementById('waitlistModalSaveBtn'),
        addForm: document.getElementById('waitlistAddForm'),

        // Customer type toggles
        typeInterno: document.getElementById('waitlistTypeInterno'),
        typeExterno: document.getElementById('waitlistTypeExterno'),

        // Room search (interno)
        roomSearchGroup: document.getElementById('waitlistRoomSearchGroup'),
        roomSearchInput: document.getElementById('waitlistRoomSearch'),
        roomResults: document.getElementById('waitlistRoomResults'),
        selectedGuestEl: document.getElementById('waitlistSelectedGuest'),
        guestNameEl: document.getElementById('waitlistGuestName'),
        guestRoomEl: document.getElementById('waitlistGuestRoom'),
        clearGuestBtn: document.getElementById('waitlistClearGuest'),

        // Customer search (externo)
        customerSearchGroup: document.getElementById('waitlistCustomerSearchGroup'),
        customerSearchInput: document.getElementById('waitlistCustomerSearch'),
        customerResults: document.getElementById('waitlistCustomerResults'),
        selectedCustomerEl: document.getElementById('waitlistSelectedCustomer'),
        customerNameEl: document.getElementById('waitlistCustomerName'),
        customerPhoneEl: document.getElementById('waitlistCustomerPhone'),
        clearCustomerBtn: document.getElementById('waitlistClearCustomer'),
        createCustomerBtn: document.getElementById('waitlistCreateCustomerBtn'),

        // Form fields
        dateInput: document.getElementById('waitlistDate'),
        numPeopleInput: document.getElementById('waitlistNumPeople'),
        timePreferenceSelect: document.getElementById('waitlistTimePreference'),
        zonePreferenceSelect: document.getElementById('waitlistZonePreference'),
        furnitureTypeSelect: document.getElementById('waitlistFurnitureType'),
        notesInput: document.getElementById('waitlistNotes'),
        reservationTypeRadios: document.querySelectorAll('input[name="reservationType"]'),
        packageGroup: document.getElementById('waitlistPackageGroup'),
        packageSelect: document.getElementById('waitlistPackageSelect'),

        // Hidden fields
        customerIdInput: document.getElementById('waitlistCustomerId'),
        customerTypeInput: document.getElementById('waitlistCustomerType'),
        hotelGuestIdInput: document.getElementById('waitlistHotelGuestId'),

        // CSRF Token
        csrfToken: document.getElementById('waitlistCsrfToken')?.value ||
                   document.querySelector('meta[name="csrf-token"]')?.content || ''
    };
}


// --- waitlist/api.js ---
/**
 * Waitlist API Module
 * Centralizes all API calls for the WaitlistManager
 *
 * All functions are pure and take their dependencies as parameters,
 * making them easy to test and reuse.
 */

// =============================================================================
// PENDING & HISTORY ENTRIES
// =============================================================================

/**
 * Load pending waitlist entries for a specific date
 * @param {string} apiBaseUrl - Base API URL (e.g., '/beach/api')
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<{success: boolean, entries: Array, count: number, error?: string}>}
 */
async function loadPendingEntries(apiBaseUrl, date) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist?date=${date}`);
        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entries: data.entries || [],
                count: data.count || 0
            };
        } else {
            return {
                success: false,
                entries: [],
                count: 0,
                error: data.error || 'Error al cargar lista'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error loading pending entries', error);
        return {
            success: false,
            entries: [],
            count: 0,
            error: 'Error de conexion'
        };
    }
}

/**
 * Load waitlist history entries for a specific date
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<{success: boolean, entries: Array, error?: string}>}
 */
async function loadHistoryEntries(apiBaseUrl, date) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/history?date=${date}`);
        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entries: data.entries || []
            };
        } else {
            return {
                success: false,
                entries: [],
                error: data.error || 'Error al cargar historial'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error loading history entries', error);
        return {
            success: false,
            entries: [],
            error: 'Error de conexion'
        };
    }
}

// =============================================================================
// DROPDOWN OPTIONS
// =============================================================================

/**
 * Load zones for dropdown selection
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<Array>} Array of zone objects with id and name
 */
async function loadZones(apiBaseUrl) {
    try {
        const response = await fetch(`${apiBaseUrl}/zones`);
        const data = await response.json();

        if (data.success && data.zones) {
            return data.zones;
        }
        return [];
    } catch (error) {
        console.error('WaitlistAPI: Error loading zones', error);
        return [];
    }
}

/**
 * Load furniture types for dropdown selection
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<Array>} Array of furniture type objects
 */
async function loadFurnitureTypes(apiBaseUrl) {
    try {
        const response = await fetch(`${apiBaseUrl}/furniture-types`);
        const data = await response.json();

        if (data.success && data.furniture_types) {
            return data.furniture_types;
        }
        return [];
    } catch (error) {
        console.error('WaitlistAPI: Error loading furniture types', error);
        return [];
    }
}

/**
 * Load all dropdown options (zones and furniture types) in parallel
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<{zones: Array, furnitureTypes: Array}>}
 */
async function loadDropdownOptions(apiBaseUrl) {
    const [zones, furnitureTypes] = await Promise.all([
        loadZones(apiBaseUrl),
        loadFurnitureTypes(apiBaseUrl)
    ]);

    return { zones, furnitureTypes };
}

/**
 * Load available packages
 * @param {string} apiBaseUrl - Base API URL
 * @returns {Promise<Array>} Array of package objects
 */
async function loadPackages(apiBaseUrl) {
    try {
        const response = await fetch(`${apiBaseUrl}/packages`);
        const data = await response.json();

        if (data.success && data.packages) {
            return data.packages;
        }
        return [];
    } catch (error) {
        console.error('WaitlistAPI: Error loading packages', error);
        return [];
    }
}

// =============================================================================
// ENTRY STATUS UPDATES
// =============================================================================

/**
 * Update a waitlist entry's status
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} entryId - Waitlist entry ID
 * @param {string} newStatus - New status value (contacted, declined, no_answer)
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function updateEntryStatus(apiBaseUrl, csrfToken, entryId, newStatus) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/${entryId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ status: newStatus })
        });

        const data = await response.json();

        if (data.success) {
            return { success: true };
        } else {
            return {
                success: false,
                error: data.error || 'Error al actualizar'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error updating entry status', error);
        return {
            success: false,
            error: 'Error de conexion'
        };
    }
}

/**
 * Mark a waitlist entry as converted to a reservation
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} entryId - Waitlist entry ID
 * @param {number} reservationId - Created reservation ID
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function markEntryAsConverted(apiBaseUrl, csrfToken, entryId, reservationId) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/${entryId}/convert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ reservation_id: reservationId })
        });

        const data = await response.json();

        if (data.success) {
            return { success: true };
        } else {
            return {
                success: false,
                error: data.error || 'Error al convertir'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error marking as converted', error);
        return {
            success: false,
            error: 'Error de conexion'
        };
    }
}

// =============================================================================
// ENTRY CREATION & UPDATE
// =============================================================================

/**
 * Create a new waitlist entry
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {Object} payload - Entry data
 * @returns {Promise<{success: boolean, entry?: Object, message?: string, error?: string}>}
 */
async function createEntry(apiBaseUrl, csrfToken, payload) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entry: data.entry,
                message: data.message || 'Agregado a lista de espera'
            };
        } else {
            return {
                success: false,
                error: data.error || 'Error al crear entrada'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error creating entry', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}

/**
 * Update an existing waitlist entry
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} entryId - Entry ID to update
 * @param {Object} payload - Updated entry data
 * @returns {Promise<{success: boolean, entry?: Object, error?: string}>}
 */
async function updateEntry(apiBaseUrl, csrfToken, entryId, payload) {
    try {
        const response = await fetch(`${apiBaseUrl}/waitlist/${entryId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                entry: data.entry
            };
        } else {
            return {
                success: false,
                error: data.error || 'Error al actualizar entrada'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error updating entry', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}

// =============================================================================
// SEARCH FUNCTIONS
// =============================================================================

/**
 * Search for hotel guests by room number or name
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} query - Search query (room number or name)
 * @returns {Promise<{success: boolean, guests: Array}>}
 */
async function searchHotelGuests(apiBaseUrl, query) {
    try {
        const response = await fetch(
            `${apiBaseUrl}/hotel-guests/search?q=${encodeURIComponent(query)}`
        );
        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                guests: data.guests || []
            };
        }
        return { success: false, guests: [] };
    } catch (error) {
        console.error('WaitlistAPI: Error searching hotel guests', error);
        return { success: false, guests: [] };
    }
}

/**
 * Search for external customers
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} query - Search query (name or phone)
 * @returns {Promise<{success: boolean, customers: Array}>}
 */
async function searchCustomers(apiBaseUrl, query) {
    try {
        const response = await fetch(
            `${apiBaseUrl}/customers/search?q=${encodeURIComponent(query)}&type=externo`
        );
        const data = await response.json();

        if (data.success || data.customers) {
            return {
                success: true,
                customers: data.customers || []
            };
        }
        return { success: false, customers: [] };
    } catch (error) {
        console.error('WaitlistAPI: Error searching customers', error);
        return { success: false, customers: [] };
    }
}

// =============================================================================
// CUSTOMER CONVERSION
// =============================================================================

/**
 * Convert a hotel guest to a customer record
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {number} hotelGuestId - Hotel guest ID to convert
 * @returns {Promise<{success: boolean, customer?: Object, error?: string}>}
 */
async function convertHotelGuestToCustomer(apiBaseUrl, csrfToken, hotelGuestId) {
    try {
        const response = await fetch(`${apiBaseUrl}/customers/from-hotel-guest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ hotel_guest_id: parseInt(hotelGuestId) })
        });

        const data = await response.json();

        if (data.success) {
            return {
                success: true,
                customer: data.customer
            };
        } else {
            return {
                success: false,
                error: data.error || 'Error al convertir huesped'
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error converting hotel guest', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}

// =============================================================================
// COMPOSITE OPERATIONS
// =============================================================================

/**
 * Submit a waitlist entry (handles both create and edit modes)
 * Automatically converts hotel guest to customer if needed
 *
 * @param {string} apiBaseUrl - Base API URL
 * @param {string} csrfToken - CSRF token for authentication
 * @param {Object} options - Submission options
 * @param {string} options.customerType - 'interno' or 'externo'
 * @param {number|null} options.customerId - Existing customer ID
 * @param {number|null} options.hotelGuestId - Hotel guest ID (for interno)
 * @param {Object} options.payload - Entry data payload
 * @param {number|null} options.editingEntryId - Entry ID if editing, null if creating
 * @returns {Promise<{success: boolean, message?: string, error?: string}>}
 */
async function apiSubmitEntry(apiBaseUrl, csrfToken, options) {
    const { customerType, customerId, hotelGuestId, payload, editingEntryId } = options;

    try {
        let finalCustomerId = customerId;

        // If interno (hotel guest), convert to customer first
        if (customerType === 'interno' && hotelGuestId && !customerId) {
            const convertResult = await convertHotelGuestToCustomer(
                apiBaseUrl,
                csrfToken,
                hotelGuestId
            );

            if (!convertResult.success) {
                return {
                    success: false,
                    error: convertResult.error
                };
            }
            finalCustomerId = convertResult.customer.id;
        }

        // Add customer ID to payload if we have one
        if (finalCustomerId) {
            payload.customer_id = parseInt(finalCustomerId);
        }

        // Determine if this is an edit or create
        if (editingEntryId) {
            const result = await updateEntry(apiBaseUrl, csrfToken, editingEntryId, payload);
            return {
                success: result.success,
                message: result.success ? 'Entrada actualizada' : undefined,
                error: result.error
            };
        } else {
            const result = await createEntry(apiBaseUrl, csrfToken, payload);
            return {
                success: result.success,
                message: result.message,
                error: result.error
            };
        }
    } catch (error) {
        console.error('WaitlistAPI: Error submitting entry', error);
        return {
            success: false,
            error: error.message || 'Error de conexion'
        };
    }
}


// --- waitlist/renderers.js ---
/**
 * Waitlist Renderers
 * Entry card rendering and list display
 */


/**
 * Render a single entry card
 * @param {Object} entry - Entry data
 * @param {number|null} position - Position in list (null for history)
 * @param {boolean} isHistory - Whether this is a history entry
 * @returns {string} HTML string
 */
function renderEntryCard(entry, position, isHistory) {
    const statusClass = `status-${entry.status}`;
    const statusLabel = getStatusLabel(entry.status);
    const timeAgo = formatTimeAgo(entry.created_at);
    const historyClass = isHistory ? 'history-entry' : '';
    const convertedClass = entry.status === 'converted' ? 'converted' : '';

    // Build preferences chips
    let prefsHtml = '';
    if (entry.zone_name) {
        prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(entry.zone_name)}</span>`;
    }
    if (entry.furniture_type_name) {
        prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-umbrella-beach"></i> ${escapeHtml(entry.furniture_type_name)}</span>`;
    }
    if (entry.time_preference) {
        const timeLabel = getTimePreferenceLabel(entry.time_preference);
        prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-clock"></i> ${timeLabel}</span>`;
    }

    // Build actions (only for pending entries)
    let actionsHtml = '';
    if (!isHistory && (entry.status === 'waiting' || entry.status === 'contacted' || entry.status === 'no_answer')) {
        actionsHtml = `
            <div class="waitlist-entry-actions">
                <button type="button" class="btn-action btn-edit" data-action="edit" data-id="${entry.id}">
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button type="button" class="btn-action btn-convert" data-action="convert" data-id="${entry.id}">
                    <i class="fas fa-check"></i> Convertir
                </button>
                <button type="button" class="btn-action btn-danger" data-action="declined" data-id="${entry.id}">
                    <i class="fas fa-times"></i> Cancelar
                </button>
            </div>
        `;
    }

    return `
        <div class="waitlist-entry ${historyClass} ${convertedClass}" data-entry-id="${entry.id}">
            <div class="waitlist-entry-header">
                ${position ? `<div class="waitlist-entry-priority">${position}</div>` : ''}
                <div class="waitlist-entry-customer">
                    <div class="waitlist-entry-name">${escapeHtml(entry.customer_name || 'Sin nombre')}</div>
                    <div class="waitlist-entry-meta">
                        ${entry.room_number ? `<i class="fas fa-door-open"></i> Hab. ${escapeHtml(entry.room_number)}` : ''}
                        ${entry.phone ? `<i class="fas fa-phone"></i> ${escapeHtml(entry.phone)}` : ''}
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
                        <i class="fas fa-calendar"></i> ${formatDateShort(entry.requested_date)}
                    </span>
                    ${entry.package_name ? `
                        <span class="waitlist-entry-detail">
                            <i class="fas fa-gift"></i> ${escapeHtml(entry.package_name)}
                        </span>
                    ` : ''}
                </div>
                ${prefsHtml ? `<div class="waitlist-entry-preferences">${prefsHtml}</div>` : ''}
                ${entry.notes ? `<div class="waitlist-entry-notes">${escapeHtml(entry.notes)}</div>` : ''}
                ${actionsHtml}
            </div>
        </div>
    `;
}

/**
 * Render pending entries list
 * @param {Object} elements - DOM elements cache
 * @param {Array} entries - Entry data array
 * @param {Function} onActionClick - Callback for action button clicks
 */
function renderPendingEntries(elements, entries, onActionClick) {
    if (!elements.entriesPending) return;

    if (entries.length === 0) {
        elements.entriesPending.innerHTML = '';
        elements.emptyPending.style.display = 'flex';
        return;
    }

    elements.emptyPending.style.display = 'none';

    const html = entries.map((entry, index) => renderEntryCard(entry, index + 1, false)).join('');
    elements.entriesPending.innerHTML = html;

    // Attach action listeners
    attachEntryListeners(elements.entriesPending, onActionClick);
}

/**
 * Render history entries list
 * @param {Object} elements - DOM elements cache
 * @param {Array} entries - Entry data array
 */
function renderHistoryEntries(elements, entries) {
    if (!elements.entriesHistory) return;

    if (entries.length === 0) {
        elements.entriesHistory.innerHTML = '';
        elements.emptyHistory.style.display = 'flex';
        return;
    }

    elements.emptyHistory.style.display = 'none';

    const html = entries.map((entry) => renderEntryCard(entry, null, true)).join('');
    elements.entriesHistory.innerHTML = html;
}

/**
 * Attach click listeners to entry action buttons
 * @param {HTMLElement} container - Container element
 * @param {Function} onActionClick - Callback (entryId, action)
 */
function attachEntryListeners(container, onActionClick) {
    container.querySelectorAll('.btn-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            const entryId = parseInt(btn.dataset.id);
            if (onActionClick) {
                onActionClick(entryId, action);
            }
        });
    });
}

/**
 * Populate zones dropdown
 * @param {HTMLSelectElement} selectEl - Select element
 * @param {Array} zones - Zone data array
 */
function populateZonesDropdown(selectEl, zones) {
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Sin preferencia</option>';
    zones.forEach(zone => {
        const option = document.createElement('option');
        option.value = zone.id;
        option.textContent = zone.name;
        selectEl.appendChild(option);
    });
}

/**
 * Populate furniture types dropdown
 * @param {HTMLSelectElement} selectEl - Select element
 * @param {Array} furnitureTypes - Furniture type data array
 */
function populateFurnitureTypesDropdown(selectEl, furnitureTypes) {
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Sin preferencia</option>';
    furnitureTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = type.display_name || type.name;
        selectEl.appendChild(option);
    });
}

/**
 * Populate packages dropdown
 * @param {HTMLSelectElement} selectEl - Select element
 * @param {Array} packages - Package data array
 */
function populatePackagesDropdown(selectEl, packages) {
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Seleccionar paquete...</option>';
    packages.forEach(pkg => {
        const option = document.createElement('option');
        option.value = pkg.id;
        option.textContent = `${pkg.package_name} - ${pkg.base_price}`;
        selectEl.appendChild(option);
    });
}

/**
 * Render room search results
 * @param {HTMLElement} resultsEl - Results container
 * @param {Array} guests - Guest data array
 * @param {Function} onSelect - Callback when guest selected
 */
function renderRoomResults(resultsEl, guests, onSelect) {
    if (!resultsEl) return;

    if (guests.length === 0) {
        resultsEl.innerHTML = '<div class="p-3 text-muted">No se encontraron huespedes</div>';
        resultsEl.classList.add('show');
        return;
    }

    const html = guests.map(guest => {
        const guestName = guest.guest_name || `${guest.first_name || ''} ${guest.last_name || ''}`.trim();
        const phone = guest.phone || '';
        const guestCount = guest.guest_count || 1;
        const countDisplay = guestCount > 1 ? ` - x${guestCount}` : '';
        return `
            <div class="cs-item" data-guest-id="${guest.id}" data-guest-name="${escapeHtml(guestName)}" data-room="${guest.room_number}" data-phone="${escapeHtml(phone)}" data-guest-count="${guestCount}">
                <div class="cs-info">
                    <div class="cs-name">Hab. ${guest.room_number} - ${escapeHtml(guestName)}${countDisplay}</div>
                    <div class="cs-details">
                        ${phone ? `<i class="fas fa-phone"></i> ${escapeHtml(phone)}` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    resultsEl.innerHTML = html;
    resultsEl.classList.add('show');

    // Attach click listeners
    resultsEl.querySelectorAll('.cs-item').forEach(item => {
        item.addEventListener('click', () => onSelect(item));
    });
}

/**
 * Render customer search results
 * @param {HTMLElement} resultsEl - Results container
 * @param {Array} customers - Customer data array
 * @param {Function} onSelect - Callback when customer selected
 */
function renderCustomerResults(resultsEl, customers, onSelect) {
    if (!resultsEl) return;

    if (customers.length === 0) {
        resultsEl.innerHTML = '<div class="p-3 text-muted">No se encontraron clientes</div>';
        resultsEl.classList.add('show');
        return;
    }

    const html = customers.map(customer => {
        const name = customer.display_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim();
        return `
            <div class="cs-item" data-customer-id="${customer.id}" data-customer-name="${escapeHtml(name)}" data-phone="${customer.phone || ''}">
                <div class="cs-info">
                    <div class="cs-name">${escapeHtml(name)}</div>
                    <div class="cs-details">${customer.phone ? `<i class="fas fa-phone"></i> ${customer.phone}` : ''}</div>
                </div>
            </div>
        `;
    }).join('');

    resultsEl.innerHTML = html;
    resultsEl.classList.add('show');

    // Attach click listeners
    resultsEl.querySelectorAll('.cs-item').forEach(item => {
        item.addEventListener('click', () => onSelect(item));
    });
}


// --- waitlist/actions.js ---
/**
 * Waitlist Actions
 * Entry actions: convert, edit, status changes
 */


/**
 * Handle entry action button click
 * @param {Object} context - Manager context (state, callbacks, elements, etc.)
 * @param {number} entryId - Entry ID
 * @param {string} action - Action type (convert, edit, contacted, declined, no_answer)
 */
async function handleEntryAction(context, entryId, action) {
    if (action === 'convert') {
        handleConvert(context, entryId);
        return;
    }

    if (action === 'edit') {
        handleEdit(context, entryId);
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
        const result = await updateEntryStatus(context.options.apiBaseUrl, context.csrfToken, entryId, newStatus);

        if (result.success) {
            showToast('Estado actualizado', 'success');
            await context.refresh();
            dispatchCountUpdate(context);
        } else {
            showToast(result.error || 'Error al actualizar', 'error');
        }
    } catch (error) {
        console.error('WaitlistManager: Error updating status', error);
        showToast('Error de conexion', 'error');
    }
}

/**
 * Handle convert action - close panel and trigger conversion
 * @param {Object} context - Manager context
 * @param {number} entryId - Entry ID
 */
function handleConvert(context, entryId) {
    // Find the entry
    const entry = context.state.entries.find(e => e.id === entryId);
    if (!entry) return;

    // Close waitlist panel
    context.close();

    // Call conversion callback
    if (context.callbacks.onConvert) {
        context.callbacks.onConvert(entry);
    } else {
        // Dispatch event for other components to handle
        document.dispatchEvent(new CustomEvent('waitlist:convert', {
            detail: { entry, entryId }
        }));
    }
}

/**
 * Handle edit action - open modal in edit mode
 * @param {Object} context - Manager context
 * @param {number} entryId - Entry ID
 */
function handleEdit(context, entryId) {
    const entry = context.state.entries.find(e => e.id === entryId);
    if (!entry) return;

    const { elements, state } = context;

    // Reset form first (clears editingEntryId and resets title/button)
    context.resetForm();

    // Then store entry being edited (after reset)
    state.editingEntryId = entryId;

    // Set customer type (this also updates the UI)
    context.setCustomerType(entry.customer_type || 'interno');

    // Pre-fill customer info
    if (entry.customer_id) {
        // Customer already exists (converted hotel guest or existing external)
        state.selectedCustomerId = entry.customer_id;
        if (elements.customerIdInput) elements.customerIdInput.value = entry.customer_id;

        // Display customer name in appropriate section
        if (entry.customer_type === 'interno') {
            // For internal, show in selected guest display
            const guestDisplay = document.getElementById('waitlistSelectedGuest');
            const guestName = document.getElementById('waitlistGuestName');
            const guestRoom = document.getElementById('waitlistGuestRoom');
            const searchWrapper = document.querySelector('#waitlistRoomSearchGroup .room-search-wrapper');

            if (guestDisplay && guestName) {
                guestName.textContent = entry.customer_name || 'Huésped';
                if (guestRoom && entry.room_number) {
                    guestRoom.textContent = `Hab. ${entry.room_number}`;
                }
                guestDisplay.style.display = 'flex';
                if (searchWrapper) searchWrapper.style.display = 'none';
            }
        } else {
            // For external with customer_id, show name in externo fields
            const externoNameInput = document.getElementById('waitlistExternoName');
            const externoPhoneInput = document.getElementById('waitlistExternoPhone');
            if (externoNameInput) externoNameInput.value = entry.customer_name || '';
            if (externoPhoneInput) externoPhoneInput.value = entry.phone || '';
        }
    } else if (entry.external_name) {
        // External customer (not yet converted to customer record)
        const externoNameInput = document.getElementById('waitlistExternoName');
        const externoPhoneInput = document.getElementById('waitlistExternoPhone');
        if (externoNameInput) externoNameInput.value = entry.external_name;
        if (externoPhoneInput) externoPhoneInput.value = entry.external_phone || '';
    }

    // Pre-fill date
    if (elements.dateInput && entry.requested_date) {
        // Normalize to ISO format
        let isoDate = entry.requested_date;
        if (!/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) {
            try {
                const d = new Date(isoDate);
                if (!isNaN(d.getTime())) {
                    isoDate = d.toISOString().split('T')[0];
                }
            } catch (e) { /* ignore */ }
        }
        elements.dateInput.value = isoDate;
    }

    // Pre-fill num_people
    if (elements.numPeopleInput && entry.num_people) {
        elements.numPeopleInput.value = entry.num_people;
    }

    // Pre-fill preferences
    if (elements.zonePreferenceSelect && entry.preferred_zone_id) {
        elements.zonePreferenceSelect.value = entry.preferred_zone_id;
    }
    if (elements.furnitureTypeSelect && entry.preferred_furniture_type_id) {
        elements.furnitureTypeSelect.value = entry.preferred_furniture_type_id;
    }
    if (elements.timePreferenceSelect && entry.time_preference) {
        elements.timePreferenceSelect.value = entry.time_preference;
    }

    // Pre-fill reservation type
    if (entry.reservation_type) {
        const typeRadio = document.querySelector(`input[name="reservationType"][value="${entry.reservation_type}"]`);
        if (typeRadio) {
            typeRadio.checked = true;
            context.onReservationTypeChange(); // Show/hide package group based on selection
        }
    }

    // Pre-fill package
    if (elements.packageSelect && entry.package_id) {
        elements.packageSelect.value = entry.package_id;
    }

    // Pre-fill notes
    if (elements.notesInput && entry.notes) {
        elements.notesInput.value = entry.notes;
    }

    // Update modal title for edit mode
    const modalTitle = document.getElementById('waitlistModalTitle');
    if (modalTitle) {
        modalTitle.innerHTML = '<i class="fas fa-edit me-2"></i> Editar en Lista de Espera';
    }

    // Update submit button text (keep save-text/save-loading structure)
    const saveText = elements.modalSaveBtn?.querySelector('.save-text');
    if (saveText) {
        saveText.innerHTML = '<i class="fas fa-save me-1"></i> Guardar Cambios';
    }

    // Open modal
    context.openAddModal();
}

/**
 * Mark an entry as converted after reservation created
 * @param {Object} context - Manager context
 * @param {number} entryId - Waitlist entry ID
 * @param {number} reservationId - Created reservation ID
 */
async function markAsConverted(context, entryId, reservationId) {
    try {
        const result = await markEntryAsConverted(
            context.options.apiBaseUrl,
            context.csrfToken,
            entryId,
            reservationId
        );

        if (result.success) {
            showToast('Entrada convertida a reserva', 'success');
            dispatchCountUpdate(context);
        } else {
            showToast(result.error || 'Error al convertir', 'error');
        }
    } catch (error) {
        console.error('WaitlistManager: Error marking as converted', error);
    }
}

/**
 * Dispatch count update event and callback
 * @param {Object} context - Manager context
 */
function dispatchCountUpdate(context) {
    const count = context.state.entries.filter(e => e.status === 'waiting').length;

    // Dispatch event for badge updates
    document.dispatchEvent(new CustomEvent('waitlist:countUpdate', {
        detail: { count }
    }));

    // Call callback if provided
    if (context.callbacks.onCountUpdate) {
        context.callbacks.onCountUpdate(count);
    }
}


// --- waitlist/modal.js ---
/**
 * Waitlist Modal
 * Modal open/close/reset functionality
 */


/**
 * Open the add entry modal
 * @param {Object} context - Manager context
 */
function openAddModal(context) {
    const { elements, state } = context;
    if (!elements.modal) return;

    // Only reset form if not in edit mode (edit mode pre-fills before calling this)
    if (!state.editingEntryId) {
        resetForm(context);

        // Set default date to current date
        if (elements.dateInput) {
            elements.dateInput.value = state.currentDate;
            elements.dateInput.min = getTodayDate();
        }
    } else {
        // In edit mode, just set min date
        if (elements.dateInput) {
            elements.dateInput.min = getTodayDate();
        }
    }

    // Show modal
    elements.modal.style.display = 'flex';
}

/**
 * Close the add entry modal
 * @param {Object} context - Manager context
 */
function closeAddModal(context) {
    const { elements } = context;
    if (!elements.modal) return;
    elements.modal.style.display = 'none';
}

/**
 * Reset the form to default state
 * @param {Object} context - Manager context
 */
function resetForm(context) {
    const { elements, state } = context;

    // Clear editing state
    state.editingEntryId = null;

    // Reset customer type to interno
    setCustomerType(context, 'interno');

    // Clear selections
    clearSelectedGuest(context);
    clearSelectedCustomer(context);

    // Reset form fields
    if (elements.roomSearchInput) elements.roomSearchInput.value = '';
    if (elements.customerSearchInput) elements.customerSearchInput.value = '';
    if (elements.numPeopleInput) elements.numPeopleInput.value = '2';
    if (elements.timePreferenceSelect) elements.timePreferenceSelect.value = '';
    if (elements.zonePreferenceSelect) elements.zonePreferenceSelect.value = '';
    if (elements.furnitureTypeSelect) elements.furnitureTypeSelect.value = '';
    if (elements.notesInput) elements.notesInput.value = '';
    if (elements.packageSelect) elements.packageSelect.value = '';

    // Reset reservation type - 'incluido' for interno by default
    const defaultRadio = document.querySelector('input[name="reservationType"][value="incluido"]');
    if (defaultRadio) defaultRadio.checked = true;
    if (elements.packageGroup) elements.packageGroup.style.display = 'none';

    // Reset external guest name/phone fields
    const externoNameInput = document.getElementById('waitlistExternoName');
    const externoPhoneInput = document.getElementById('waitlistExternoPhone');
    if (externoNameInput) externoNameInput.value = '';
    if (externoPhoneInput) externoPhoneInput.value = '';

    // Hide search results
    if (elements.roomResults) elements.roomResults.classList.remove('show');
    if (elements.customerResults) elements.customerResults.classList.remove('show');

    // Reset modal title and button text to defaults
    const modalTitle = document.getElementById('waitlistModalTitle');
    if (modalTitle) {
        modalTitle.innerHTML = '<i class="fas fa-user-plus me-2"></i> Anadir a Lista de Espera';
    }
    const saveText = elements.modalSaveBtn?.querySelector('.save-text');
    if (saveText) {
        saveText.innerHTML = '<i class="fas fa-check me-1"></i> Anadir';
    }
}

/**
 * Set customer type (interno/externo)
 * @param {Object} context - Manager context
 * @param {string} type - Customer type ('interno' or 'externo')
 */
function setCustomerType(context, type) {
    const { elements, state } = context;
    state.customerType = type;

    if (elements.customerTypeInput) {
        elements.customerTypeInput.value = type;
    }

    // Update toggle buttons
    if (type === 'interno') {
        elements.typeInterno?.classList.add('active');
        elements.typeExterno?.classList.remove('active');
        if (elements.roomSearchGroup) elements.roomSearchGroup.style.display = 'block';
        if (elements.customerSearchGroup) elements.customerSearchGroup.style.display = 'none';
        // Set default reservation type to 'incluido' for internal guests
        const incluidoRadio = document.querySelector('input[name="reservationType"][value="incluido"]');
        if (incluidoRadio) incluidoRadio.checked = true;
    } else {
        elements.typeInterno?.classList.remove('active');
        elements.typeExterno?.classList.add('active');
        if (elements.roomSearchGroup) elements.roomSearchGroup.style.display = 'none';
        if (elements.customerSearchGroup) elements.customerSearchGroup.style.display = 'block';
        // Set default reservation type to 'consumo_minimo' for external guests
        const consumoRadio = document.querySelector('input[name="reservationType"][value="consumo_minimo"]');
        if (consumoRadio) consumoRadio.checked = true;
    }

    // Clear selections when switching
    clearSelectedGuest(context);
    clearSelectedCustomer(context);
}

/**
 * Handle reservation type change (show/hide package group)
 * @param {Object} context - Manager context
 */
async function onReservationTypeChange(context) {
    const { elements, state, options, csrfToken } = context;
    const selected = document.querySelector('input[name="reservationType"]:checked');
    if (!selected) return;

    if (selected.value === 'paquete') {
        if (elements.packageGroup) elements.packageGroup.style.display = 'block';
        // Load packages
        try {
            const result = await loadPackages(options.apiBaseUrl);
            if (result.success && result.packages) {
                state.packages = result.packages;
                // Populate dropdown
                if (elements.packageSelect) {
                    elements.packageSelect.innerHTML = '<option value="">Seleccionar paquete...</option>';
                    result.packages.forEach(pkg => {
                        const option = document.createElement('option');
                        option.value = pkg.id;
                        option.textContent = `${pkg.package_name} - ${pkg.base_price}`;
                        elements.packageSelect.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading packages', error);
        }
    } else {
        if (elements.packageGroup) elements.packageGroup.style.display = 'none';
    }
}

/**
 * Clear selected hotel guest
 * @param {Object} context - Manager context
 */
function clearSelectedGuest(context) {
    const { elements, state } = context;
    state.selectedHotelGuestId = null;
    if (elements.hotelGuestIdInput) elements.hotelGuestIdInput.value = '';
    if (elements.customerIdInput) elements.customerIdInput.value = '';
    if (elements.selectedGuestEl) elements.selectedGuestEl.style.display = 'none';

    // Show the search wrapper and input
    const searchWrapper = document.querySelector('#waitlistRoomSearchGroup .room-search-wrapper');
    if (searchWrapper) searchWrapper.style.display = 'block';
    if (elements.roomSearchInput) {
        elements.roomSearchInput.style.display = 'block';
        elements.roomSearchInput.value = '';
    }
}

/**
 * Clear selected customer
 * @param {Object} context - Manager context
 */
function clearSelectedCustomer(context) {
    const { elements, state } = context;
    state.selectedCustomerId = null;
    if (elements.customerIdInput) elements.customerIdInput.value = '';
    if (elements.selectedCustomerEl) elements.selectedCustomerEl.style.display = 'none';
    if (elements.customerSearchInput) {
        elements.customerSearchInput.style.display = 'block';
        elements.customerSearchInput.value = '';
    }
}

/**
 * Select a hotel guest from search results
 * @param {Object} context - Manager context
 * @param {HTMLElement} item - Selected item element
 */
function selectGuest(context, item) {
    const { elements, state } = context;
    const guestId = item.dataset.guestId;
    const guestName = item.dataset.guestName;
    const roomNumber = item.dataset.room;
    const phone = item.dataset.phone || '';

    // Update state
    state.selectedHotelGuestId = guestId;
    state.selectedGuestPhone = phone;

    // Update hidden fields
    if (elements.hotelGuestIdInput) elements.hotelGuestIdInput.value = guestId;

    // Show selected guest with phone
    if (elements.selectedGuestEl) {
        elements.selectedGuestEl.style.display = 'flex';
        if (elements.guestNameEl) elements.guestNameEl.textContent = guestName;
        if (elements.guestRoomEl) {
            const escapeHtml = (str) => {
                if (!str) return '';
                const div = document.createElement('div');
                div.textContent = str;
                return div.innerHTML;
            };
            elements.guestRoomEl.innerHTML = `Hab. ${roomNumber}${phone ? ` <span class="guest-phone"><i class="fas fa-phone"></i> ${escapeHtml(phone)}</span>` : ''}`;
        }
    }

    // Hide search
    if (elements.roomSearchInput) elements.roomSearchInput.style.display = 'none';
    if (elements.roomResults) elements.roomResults.classList.remove('show');
}

/**
 * Select a customer from search results
 * @param {Object} context - Manager context
 * @param {HTMLElement} item - Selected item element
 */
function selectCustomer(context, item) {
    const { elements, state } = context;
    const customerId = item.dataset.customerId;
    const customerName = item.dataset.customerName;
    const phone = item.dataset.phone;

    // Update state
    state.selectedCustomerId = customerId;

    // Update hidden fields
    if (elements.customerIdInput) elements.customerIdInput.value = customerId;

    // Show selected customer
    if (elements.selectedCustomerEl) {
        elements.selectedCustomerEl.style.display = 'flex';
        if (elements.customerNameEl) elements.customerNameEl.textContent = customerName;
        if (elements.customerPhoneEl) elements.customerPhoneEl.textContent = phone || '-';
    }

    // Hide search
    if (elements.customerSearchInput) elements.customerSearchInput.style.display = 'none';
    if (elements.customerResults) elements.customerResults.classList.remove('show');
}

/**
 * Navigate to create customer page
 */
function showCreateCustomer() {
    // Navigate to customer creation page with return URL
    const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/beach/customers/create?type=externo&return_url=${returnUrl}`;
}


// --- waitlist/search.js ---
/**
 * Waitlist Search
 * Room and customer search functionality
 */


/**
 * Handle room search input
 * @param {Object} context - Manager context
 * @param {Event} e - Input event
 */
function onRoomSearch(context, e) {
    const query = e.target.value.trim();

    if (context.searchTimeout) {
        clearTimeout(context.searchTimeout);
    }

    if (query.length < 1) {
        if (context.elements.roomResults) {
            context.elements.roomResults.classList.remove('show');
        }
        return;
    }

    context.searchTimeout = setTimeout(
        () => performRoomSearch(context, query),
        context.options.debounceMs
    );
}

/**
 * Perform room search API call
 * @param {Object} context - Manager context
 * @param {string} query - Search query
 */
async function performRoomSearch(context, query) {
    const { elements, options } = context;

    try {
        const result = await searchHotelGuests(options.apiBaseUrl, query);

        if (result.success || result.guests) {
            renderRoomResults(
                elements.roomResults,
                result.guests || [],
                (item) => selectGuest(context, item)
            );
        }
    } catch (error) {
        console.error('WaitlistManager: Error searching rooms', error);
    }
}

/**
 * Handle customer search input
 * @param {Object} context - Manager context
 * @param {Event} e - Input event
 */
function onCustomerSearch(context, e) {
    const query = e.target.value.trim();

    if (context.searchTimeout) {
        clearTimeout(context.searchTimeout);
    }

    if (query.length < 2) {
        if (context.elements.customerResults) {
            context.elements.customerResults.classList.remove('show');
        }
        return;
    }

    context.searchTimeout = setTimeout(
        () => performCustomerSearch(context, query),
        context.options.debounceMs
    );
}

/**
 * Perform customer search API call
 * @param {Object} context - Manager context
 * @param {string} query - Search query
 */
async function performCustomerSearch(context, query) {
    const { elements, options } = context;

    try {
        const result = await searchCustomers(options.apiBaseUrl, query, 'externo');

        if (result.success || result.customers) {
            renderCustomerResults(
                elements.customerResults,
                result.customers || [],
                (item) => selectCustomer(context, item)
            );
        }
    } catch (error) {
        console.error('WaitlistManager: Error searching customers', error);
    }
}

/**
 * Create a debounced search function
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(fn, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}


// --- waitlist/form-handler.js ---
/**
 * Waitlist Form Handler
 * Form submission and validation logic
 */


/**
 * Submit the waitlist entry form (create or update)
 * @param {Object} context - Manager context
 */
async function submitEntry(context) {
    const { elements, state, options, csrfToken, callbacks } = context;

    // Validate customer selection
    const customerId = elements.customerIdInput?.value;
    const hotelGuestId = elements.hotelGuestIdInput?.value;

    // For external guests, get name and phone from the simple entry fields
    const externoName = document.getElementById('waitlistExternoName')?.value?.trim();
    const externoPhone = document.getElementById('waitlistExternoPhone')?.value?.trim();

    if (state.customerType === 'interno' && !hotelGuestId && !customerId) {
        showToast('Selecciona un huesped', 'warning');
        return;
    }

    if (state.customerType === 'externo' && !externoName) {
        showToast('Ingresa el nombre del cliente', 'warning');
        return;
    }

    if (state.customerType === 'externo' && !externoPhone) {
        showToast('Ingresa el telefono del cliente', 'warning');
        return;
    }

    // Validate date
    const requestedDate = elements.dateInput?.value;
    if (!requestedDate) {
        showToast('La fecha es requerida', 'warning');
        return;
    }

    // Validate reservation type
    const reservationType = document.querySelector('input[name="reservationType"]:checked')?.value || 'consumo_minimo';
    if (reservationType === 'paquete' && !elements.packageSelect?.value) {
        showToast('Selecciona un paquete', 'warning');
        return;
    }

    // Show loading
    setSubmitButtonLoading(elements, true);

    try {
        // If interno (hotel guest), we need to convert to customer first
        let finalCustomerId = customerId;

        if (state.customerType === 'interno' && hotelGuestId) {
            // Convert hotel guest to customer
            const convertResult = await convertHotelGuestToCustomer(
                options.apiBaseUrl,
                csrfToken,
                parseInt(hotelGuestId)
            );

            if (!convertResult.success) {
                throw new Error(convertResult.error || 'Error al convertir huesped');
            }
            finalCustomerId = convertResult.customer.id;
        }

        // Build payload
        const payload = buildPayload(elements, state, finalCustomerId, externoName, externoPhone, requestedDate, reservationType);

        // Determine if this is an edit or create
        const isEdit = !!state.editingEntryId;
        let result;

        if (isEdit) {
            result = await updateEntry(options.apiBaseUrl, csrfToken, state.editingEntryId, payload);
        } else {
            result = await createEntry(options.apiBaseUrl, csrfToken, payload);
        }

        if (result.success) {
            const message = isEdit
                ? 'Entrada actualizada'
                : (result.message || 'Agregado a lista de espera');
            showToast(message, 'success');
            context.closeAddModal();
            await context.refresh();
            dispatchCountUpdate(context);
        } else {
            const errorMsg = isEdit
                ? (result.error || 'Error al actualizar entrada')
                : (result.error || 'Error al crear entrada');
            showToast(errorMsg, 'error');
        }
    } catch (error) {
        console.error('WaitlistManager: Error submitting entry', error);
        showToast(error.message || 'Error de conexion', 'error');
    } finally {
        setSubmitButtonLoading(elements, false);
    }
}

/**
 * Build the payload object for creating/updating an entry
 * @param {Object} elements - DOM elements
 * @param {Object} state - Manager state
 * @param {number|string} finalCustomerId - Customer ID (if interno)
 * @param {string} externoName - External customer name
 * @param {string} externoPhone - External customer phone
 * @param {string} requestedDate - Requested date
 * @param {string} reservationType - Reservation type
 * @returns {Object} Payload object
 */
function buildPayload(elements, state, finalCustomerId, externoName, externoPhone, requestedDate, reservationType) {
    const payload = {
        requested_date: requestedDate,
        num_people: parseInt(elements.numPeopleInput?.value) || 2,
        preferred_zone_id: elements.zonePreferenceSelect?.value ? parseInt(elements.zonePreferenceSelect.value) : null,
        preferred_furniture_type_id: elements.furnitureTypeSelect?.value ? parseInt(elements.furnitureTypeSelect.value) : null,
        time_preference: elements.timePreferenceSelect?.value || null,
        reservation_type: reservationType,
        package_id: reservationType === 'paquete' ? parseInt(elements.packageSelect?.value) : null,
        notes: elements.notesInput?.value?.trim() || null
    };

    // Add customer info based on type
    if (state.customerType === 'interno' && finalCustomerId) {
        payload.customer_id = parseInt(finalCustomerId);
    } else if (state.customerType === 'externo') {
        // External guests use name+phone, customer created on convert
        payload.external_name = externoName;
        payload.external_phone = externoPhone;
    }

    return payload;
}

/**
 * Set submit button loading state
 * @param {Object} elements - DOM elements
 * @param {boolean} loading - Whether button should show loading
 */
function setSubmitButtonLoading(elements, loading) {
    if (!elements.modalSaveBtn) return;

    elements.modalSaveBtn.disabled = loading;
    const saveText = elements.modalSaveBtn.querySelector('.save-text');
    const saveLoading = elements.modalSaveBtn.querySelector('.save-loading');

    if (loading) {
        if (saveText) saveText.style.display = 'none';
        if (saveLoading) saveLoading.style.display = 'flex';
    } else {
        if (saveText) saveText.style.display = 'inline-flex';
        if (saveLoading) saveLoading.style.display = 'none';
    }
}

/**
 * Validate form fields
 * @param {Object} elements - DOM elements
 * @param {Object} state - Manager state
 * @returns {Object} Validation result { valid: boolean, error: string }
 */
function validateForm(elements, state) {
    const customerId = elements.customerIdInput?.value;
    const hotelGuestId = elements.hotelGuestIdInput?.value;
    const externoName = document.getElementById('waitlistExternoName')?.value?.trim();
    const externoPhone = document.getElementById('waitlistExternoPhone')?.value?.trim();
    const requestedDate = elements.dateInput?.value;
    const reservationType = document.querySelector('input[name="reservationType"]:checked')?.value || 'consumo_minimo';

    if (state.customerType === 'interno' && !hotelGuestId && !customerId) {
        return { valid: false, error: 'Selecciona un huesped' };
    }

    if (state.customerType === 'externo' && !externoName) {
        return { valid: false, error: 'Ingresa el nombre del cliente' };
    }

    if (state.customerType === 'externo' && !externoPhone) {
        return { valid: false, error: 'Ingresa el telefono del cliente' };
    }

    if (!requestedDate) {
        return { valid: false, error: 'La fecha es requerida' };
    }

    if (reservationType === 'paquete' && !elements.packageSelect?.value) {
        return { valid: false, error: 'Selecciona un paquete' };
    }

    return { valid: true, error: null };
}


// --- Namespace objects for WaitlistManager (replaces import * as X) ---
const _waitlistApi = {
    loadPendingEntries, loadHistoryEntries, loadZones, loadFurnitureTypes,
    loadDropdownOptions, loadPackages, updateEntryStatus, markEntryAsConverted,
    createEntry, updateEntry, searchHotelGuests, searchCustomers,
    convertHotelGuestToCustomer, submitEntry: apiSubmitEntry
};
const _waitlistRenderers = {
    renderEntryCard, renderPendingEntries, renderHistoryEntries,
    attachEntryListeners, populateZonesDropdown, populateFurnitureTypesDropdown,
    populatePackagesDropdown, renderRoomResults, renderCustomerResults
};
const _waitlistActions = {
    handleEntryAction, handleConvert, handleEdit, markAsConverted, dispatchCountUpdate
};
const _waitlistModal = {
    openAddModal, closeAddModal, resetForm, setCustomerType,
    onReservationTypeChange, clearSelectedGuest, clearSelectedCustomer,
    selectGuest, selectCustomer, showCreateCustomer
};
const _waitlistSearch = {
    onRoomSearch, onCustomerSearch, debounce
};
const _waitlistFormHandler = {
    submitEntry: submitEntry, validateForm
};


// --- waitlist/index.js ---
/**
 * WaitlistManager - Main Entry Point
 * Coordinates all modules into the WaitlistManager class
 */


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

        // Collapse buttons
        elements.collapseBtn?.addEventListener('click', () => this.toggleCollapse());
        elements.collapseBtnHeader?.addEventListener('click', () => this.toggleCollapse());

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
        elements.roomSearchInput?.addEventListener('input', (e) => _waitlistSearch.onRoomSearch(this, e));
        elements.clearGuestBtn?.addEventListener('click', () => _waitlistModal.clearSelectedGuest(this));

        // Customer search
        elements.customerSearchInput?.addEventListener('input', (e) => _waitlistSearch.onCustomerSearch(this, e));
        elements.clearCustomerBtn?.addEventListener('click', () => _waitlistModal.clearSelectedCustomer(this));
        elements.createCustomerBtn?.addEventListener('click', () => _waitlistModal.showCreateCustomer());

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

        // Notify modal state manager (closes other modals, bottom bar, controls map)
        if (window.modalStateManager) {
            window.modalStateManager.openModal('waitlist', this);
        }

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

        // Notify modal state manager
        if (window.modalStateManager) {
            window.modalStateManager.closeModal('waitlist');
        }

        this.elements.panel.classList.remove('open');
        this.elements.panel.classList.remove('collapsed');
        this.elements.backdrop?.classList.remove('show');
        document.body.style.overflow = '';
    }

    /**
     * Toggle panel collapsed state
     */
    toggleCollapse() {
        if (!this.elements.panel) return;

        const isCurrentlyCollapsed = this.elements.panel.classList.contains('collapsed');
        this.elements.panel.classList.toggle('collapsed');

        // Notify modal state manager
        if (window.modalStateManager) {
            if (isCurrentlyCollapsed) {
                window.modalStateManager.expandModal('waitlist');
            } else {
                window.modalStateManager.collapseModal('waitlist');
            }
        }
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
        await _waitlistActions.markAsConverted(this, entryId, reservationId);
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
            const result = await _waitlistApi.loadPendingEntries(this.options.apiBaseUrl, this.state.currentDate);

            if (result.success) {
                this.state.entries = result.entries || [];
                _waitlistRenderers.renderPendingEntries(
                    this.elements,
                    this.state.entries,
                    (entryId, action) => _waitlistActions.handleEntryAction(this, entryId, action)
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
            const result = await _waitlistApi.loadHistoryEntries(this.options.apiBaseUrl, this.state.currentDate);

            if (result.success) {
                this.state.historyEntries = result.entries || [];
                _waitlistRenderers.renderHistoryEntries(this.elements, this.state.historyEntries);
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
            // Load zones (loadZones returns a plain array)
            const zones = await _waitlistApi.loadZones(this.options.apiBaseUrl);
            if (zones && zones.length > 0) {
                this.state.zones = zones;
                _waitlistRenderers.populateZonesDropdown(this.elements.zonePreferenceSelect, this.state.zones);
            }

            // Load furniture types (loadFurnitureTypes returns a plain array)
            const furnitureTypes = await _waitlistApi.loadFurnitureTypes(this.options.apiBaseUrl);
            if (furnitureTypes && furnitureTypes.length > 0) {
                this.state.furnitureTypes = furnitureTypes;
                _waitlistRenderers.populateFurnitureTypesDropdown(this.elements.furnitureTypeSelect, this.state.furnitureTypes);
            }
        } catch (error) {
            console.error('WaitlistManager: Error loading options', error);
        }
    }

    // =========================================================================
    // MODAL METHODS (delegated)
    // =========================================================================

    openAddModal() {
        _waitlistModal.openAddModal(this);
    }

    closeAddModal() {
        _waitlistModal.closeAddModal(this);
    }

    resetForm() {
        _waitlistModal.resetForm(this);
    }

    setCustomerType(type) {
        _waitlistModal.setCustomerType(this, type);
    }

    onReservationTypeChange() {
        _waitlistModal.onReservationTypeChange(this);
    }

    // =========================================================================
    // FORM SUBMISSION
    // =========================================================================

    async _submitEntry() {
        await _waitlistFormHandler.submitEntry(this);
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

// Also expose on window for legacy compatibility
window.WaitlistManager = WaitlistManager;

window.WaitlistManager = WaitlistManager;
