// =============================================================================
// MAP CORE BUNDLE - BeachMap, managers, utilities
// Source files preserved individually for maintainability
// =============================================================================


// --- utils.js ---
/**
 * Map Utilities Module
 * Color functions, CSS variable loading, and helper utilities
 */

// =============================================================================
// HTML & SECURITY UTILITIES
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
// CSS & COLOR UTILITIES
// =============================================================================

/**
 * Load CSS variables for map configuration
 * @returns {Object} Configuration object with colors and numeric values
 */
function loadCSSVariables() {
    const style = getComputedStyle(document.documentElement);
    const getVar = (name, fallback) => {
        const value = style.getPropertyValue(name).trim();
        return value || fallback;
    };
    const getNumVar = (name, fallback) => {
        const value = style.getPropertyValue(name).trim();
        return value ? parseFloat(value) : fallback;
    };

    return {
        autoRefreshMs: getNumVar('--map-auto-refresh-ms', 30000),
        minZoom: getNumVar('--map-min-zoom', 0.1),
        maxZoom: getNumVar('--map-max-zoom', 3),
        snapGrid: getNumVar('--map-snap-grid', 10),
        colors: {
            availableFill: getVar('--map-available-fill', '#F5E6D3'),
            availableStroke: getVar('--map-available-stroke', '#D4AF37'),
            selectedFill: getVar('--map-selected-fill', '#D4AF37'),
            selectedStroke: getVar('--map-selected-stroke', '#8B6914'),
            zoneLabel: getVar('--map-zone-label', '#1A3A5C'),
            tooltipBg: getVar('--map-tooltip-bg', '#1A3A5C'),
            poolPrimary: getVar('--map-pool-primary', '#87CEEB'),
            poolSecondary: getVar('--map-pool-secondary', '#5DADE2'),
            primary: getVar('--color-primary', '#D4AF37'),
            secondary: getVar('--color-secondary', '#1A3A5C')
        }
    };
}

/**
 * Darken a hex color by a percentage
 * @param {string} color - Hex color string
 * @param {number} percent - Percentage to darken (0-100)
 * @returns {string} Darkened hex color
 */
function darkenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max(0, (num >> 16) - amt);
    const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
    const B = Math.max(0, (num & 0x0000FF) - amt);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

/**
 * Get contrasting text color (black or white) for a background
 * @param {string} hexcolor - Background hex color
 * @param {Object} colors - Colors object with secondary color
 * @returns {string} Contrasting color for text
 */
function getContrastColor(hexcolor, colors) {
    const r = parseInt(hexcolor.slice(1, 3), 16);
    const g = parseInt(hexcolor.slice(3, 5), 16);
    const b = parseInt(hexcolor.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? colors.secondary : '#FFFFFF';
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token or empty string
 */
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type (info, success, error, warning)
 */
function showToast(message, type = 'info') {
    if (window.PuroBeach && window.PuroBeach.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
        console.log(`[${type}] ${message}`);
    }
}

/**
 * Format a date string for display in Spanish
 * @param {string} dateStr - Date string YYYY-MM-DD
 * @returns {string} Formatted date string
 */
function formatDateDisplay(dateStr) {
    const date = new Date(dateStr + 'T12:00:00');
    const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
    return date.toLocaleDateString('es-ES', options);
}


// --- modal-state-manager.js ---
/**
 * Modal State Manager
 * Central coordinator for all panel states and map interaction
 * Ensures mutual exclusion, controls map read-only state, and manages bottom bar
 */

class ModalStateManager {
    constructor() {
        this.activeModal = null;      // 'waitlist' | 'new-reservation' | 'reservation' | 'move-mode' | null
        this.collapsedModal = null;    // Same values as activeModal
        this.modalInstances = {};      // Stores references to panel instances
        this.bottomBar = null;         // Reference to bottom action bar
        this.mapContainer = null;      // Reference to map container

        // Manager references
        this.interactionManager = null;
        this.selectionManager = null;

        console.log('[ModalStateManager] Initialized');
    }

    /**
     * Initialize manager with DOM references
     * @param {Object} options - Configuration options
     */
    initialize(options = {}) {
        this.bottomBar = document.getElementById('selection-bar');
        this.mapContainer = document.querySelector('.beach-map-container');

        // Store manager references
        this.interactionManager = options.interactionManager || null;
        this.selectionManager = options.selectionManager || null;

        console.log('[ModalStateManager] DOM references cached');
    }

    /**
     * Determine if map should be interactive
     * CRITICAL: Move-mode is the ONLY exception - always interactive
     * @returns {boolean} True if map should accept interactions
     */
    shouldMapBeInteractive() {
        // Move-mode is the ONLY exception - always interactive
        if (this.activeModal === 'move-mode') return true;

        // ANY other modal (open or collapsed) makes map read-only
        if (this.activeModal !== null) return false;

        // No modal open → map is interactive
        return true;
    }

    /**
     * Open a modal and coordinate state
     * @param {string} modalName - Name of modal ('waitlist', 'new-reservation', 'reservation', 'move-mode')
     * @param {Object} instance - Reference to the modal instance
     */
    openModal(modalName, instance) {
        console.log(`[ModalStateManager] Opening modal: ${modalName}`);

        // 1. Close OTHER modals (not self)
        Object.keys(this.modalInstances).forEach(name => {
            if (name !== modalName && this.modalInstances[name]) {
                console.log(`[ModalStateManager] Auto-closing modal: ${name}`);
                try {
                    this.modalInstances[name].close();
                } catch (error) {
                    console.warn(`[ModalStateManager] Failed to close ${name}:`, error);
                }
            }
        });

        // 2. Close bottom bar
        this.closeBottomBar();

        // 3. Register new modal
        this.activeModal = modalName;
        this.modalInstances[modalName] = instance;
        this.collapsedModal = null; // Modal is opening, not collapsed

        // 4. Update map state
        this.updateMapInteraction();
    }

    /**
     * Close a modal and update state
     * @param {string} modalName - Name of modal to close
     */
    closeModal(modalName) {
        console.log(`[ModalStateManager] Closing modal: ${modalName}`);

        // Remove from active state
        if (this.activeModal === modalName) {
            this.activeModal = null;
        }

        if (this.collapsedModal === modalName) {
            this.collapsedModal = null;
        }

        // Remove instance reference
        delete this.modalInstances[modalName];

        // Update map state
        this.updateMapInteraction();
    }

    /**
     * Collapse a modal
     * @param {string} modalName - Name of modal to collapse
     */
    collapseModal(modalName) {
        console.log(`[ModalStateManager] Collapsing modal: ${modalName}`);

        this.collapsedModal = modalName;

        // Collapsed modal still keeps map read-only (except move-mode)
        this.updateMapInteraction();
    }

    /**
     * Expand a collapsed modal
     * @param {string} modalName - Name of modal to expand
     */
    expandModal(modalName) {
        console.log(`[ModalStateManager] Expanding modal: ${modalName}`);

        if (this.collapsedModal === modalName) {
            this.collapsedModal = null;
        }

        // Still active, map state unchanged
        this.updateMapInteraction();
    }

    /**
     * Close bottom selection bar
     */
    closeBottomBar() {
        if (this.bottomBar) {
            this.bottomBar.classList.remove('show');
            console.log('[ModalStateManager] Bottom bar closed');

            // Clear selections if needed
            this.clearMapSelections();
        }
    }

    /**
     * Clear map selections
     */
    clearMapSelections() {
        if (this.selectionManager && typeof this.selectionManager.clear === 'function') {
            this.selectionManager.clear();
        }
    }

    /**
     * Update map interaction state based on active modal
     */
    updateMapInteraction() {
        if (!this.mapContainer) return;

        const interactive = this.shouldMapBeInteractive();

        console.log(`[ModalStateManager] Map interactive: ${interactive} (active: ${this.activeModal})`);

        if (interactive) {
            this.mapContainer.classList.remove('read-only');
            this.enableMapInteractions();
        } else {
            this.mapContainer.classList.add('read-only');
            this.disableMapInteractions();
        }
    }

    /**
     * Disable map interactions
     */
    disableMapInteractions() {
        // Clear any active selections
        this.clearMapSelections();

        // Notify interaction manager
        if (this.interactionManager && typeof this.interactionManager.setReadOnly === 'function') {
            this.interactionManager.setReadOnly(true);
        }

        // Notify selection manager
        if (this.selectionManager && typeof this.selectionManager.setReadOnly === 'function') {
            this.selectionManager.setReadOnly(true);
        }

        console.log('[ModalStateManager] Map interactions disabled');
    }

    /**
     * Enable map interactions
     */
    enableMapInteractions() {
        // Notify interaction manager
        if (this.interactionManager && typeof this.interactionManager.setReadOnly === 'function') {
            this.interactionManager.setReadOnly(false);
        }

        // Notify selection manager
        if (this.selectionManager && typeof this.selectionManager.setReadOnly === 'function') {
            this.selectionManager.setReadOnly(false);
        }

        console.log('[ModalStateManager] Map interactions enabled');
    }

    /**
     * Get current state (for debugging)
     * @returns {Object} Current manager state
     */
    getState() {
        return {
            activeModal: this.activeModal,
            collapsedModal: this.collapsedModal,
            isMapInteractive: this.shouldMapBeInteractive(),
            openModals: Object.keys(this.modalInstances)
        };
    }
}

// Create singleton instance
window.modalStateManager = new ModalStateManager();



// --- connectivity.js ---
/**
 * Connectivity Manager
 * Detects online/offline state using browser events and health checks
 */

const HEALTH_CHECK_URL = '/api/health';
const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds

/**
 * ConnectivityManager class
 * Monitors network status and notifies callbacks
 */
class ConnectivityManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.callbacks = {
            online: [],
            offline: []
        };
        this.healthCheckTimer = null;

        // Bound handlers for proper event listener removal
        this._boundHandleOnline = () => this._handleOnline();
        this._boundHandleOffline = () => this._handleOffline();
    }

    /**
     * Start monitoring connectivity
     */
    start() {
        // Browser events
        window.addEventListener('online', this._boundHandleOnline);
        window.addEventListener('offline', this._boundHandleOffline);

        // Periodic health check (confirms actual connectivity)
        this._startHealthCheck();

        // Initial check
        this._checkHealth();
    }

    /**
     * Stop monitoring
     */
    stop() {
        window.removeEventListener('online', this._boundHandleOnline);
        window.removeEventListener('offline', this._boundHandleOffline);

        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
            this.healthCheckTimer = null;
        }
    }

    /**
     * Register callback for online event
     * @param {Function} callback
     */
    onOnline(callback) {
        this.callbacks.online.push(callback);
    }

    /**
     * Register callback for offline event
     * @param {Function} callback
     */
    onOffline(callback) {
        this.callbacks.offline.push(callback);
    }

    /**
     * Check current connectivity status
     * @returns {Promise<boolean>}
     */
    async checkConnectivity() {
        return this._checkHealth();
    }

    /**
     * Handle browser online event
     * @private
     */
    _handleOnline() {
        // Verify with health check before confirming online
        this._checkHealth();
    }

    /**
     * Handle browser offline event
     * @private
     */
    _handleOffline() {
        if (this.isOnline) {
            this.isOnline = false;
            this._notifyOffline();
        }
    }

    /**
     * Perform health check to verify connectivity
     * @private
     * @returns {Promise<boolean>}
     */
    async _checkHealth() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const response = await fetch(HEALTH_CHECK_URL, {
                method: 'GET',
                signal: controller.signal,
                cache: 'no-store'
            });

            clearTimeout(timeoutId);

            if (response.ok && !this.isOnline) {
                this.isOnline = true;
                this._notifyOnline();
            }

            return response.ok;
        } catch (error) {
            if (this.isOnline) {
                this.isOnline = false;
                this._notifyOffline();
            }
            return false;
        }
    }

    /**
     * Start periodic health checks
     * @private
     */
    _startHealthCheck() {
        this.healthCheckTimer = setInterval(() => {
            this._checkHealth();
        }, HEALTH_CHECK_INTERVAL);
    }

    /**
     * Notify online callbacks
     * @private
     */
    _notifyOnline() {
        this.callbacks.online.forEach(cb => {
            try {
                cb();
            } catch (e) {
                console.error('Error in online callback:', e);
            }
        });
    }

    /**
     * Notify offline callbacks
     * @private
     */
    _notifyOffline() {
        this.callbacks.offline.forEach(cb => {
            try {
                cb();
            } catch (e) {
                console.error('Error in offline callback:', e);
            }
        });
    }
}


// --- storage.js ---
/**
 * IndexedDB Storage for Offline Data
 * Handles map and reservation data persistence
 */

const DB_NAME = 'purobeach_offline';
const DB_VERSION = 1;

/**
 * Open or create the IndexedDB database
 * @returns {Promise<IDBDatabase>}
 */
async function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            // Store for map data (zones, furniture, availability)
            if (!db.objectStoreNames.contains('map_data')) {
                db.createObjectStore('map_data', { keyPath: 'date' });
            }

            // Store for sync metadata
            if (!db.objectStoreNames.contains('sync_meta')) {
                db.createObjectStore('sync_meta', { keyPath: 'key' });
            }
        };
    });
}

/**
 * Save map data for a specific date
 * @param {string} date - Date string YYYY-MM-DD
 * @param {Object} data - Map data (zones, furniture, availability, reservations)
 * @returns {Promise<void>}
 */
async function saveMapData(date, data) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('map_data', 'readwrite');
        const store = tx.objectStore('map_data');

        const record = {
            date,
            data,
            savedAt: new Date().toISOString()
        };

        const request = store.put(record);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();

        tx.oncomplete = () => db.close();
    });
}

/**
 * Get map data for a specific date
 * @param {string} date - Date string YYYY-MM-DD
 * @returns {Promise<Object|null>}
 */
async function getMapData(date) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('map_data', 'readonly');
        const store = tx.objectStore('map_data');

        const request = store.get(date);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result || null);

        tx.oncomplete = () => db.close();
    });
}

/**
 * Save sync metadata
 * @param {Object} meta - Sync metadata
 * @returns {Promise<void>}
 */
async function saveSyncMeta(meta) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('sync_meta', 'readwrite');
        const store = tx.objectStore('sync_meta');

        const record = { key: 'current', ...meta };
        const request = store.put(record);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();

        tx.oncomplete = () => db.close();
    });
}

/**
 * Get sync metadata
 * @returns {Promise<Object|null>}
 */
async function getSyncMeta() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('sync_meta', 'readonly');
        const store = tx.objectStore('sync_meta');

        const request = store.get('current');
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result || null);

        tx.oncomplete = () => db.close();
    });
}

/**
 * Clear old data (dates other than today)
 * @param {string} todayDate - Today's date YYYY-MM-DD
 * @returns {Promise<void>}
 */
async function clearOldData(todayDate) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('map_data', 'readwrite');
        const store = tx.objectStore('map_data');

        const request = store.openCursor();
        request.onerror = () => reject(request.error);

        request.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor) {
                if (cursor.key !== todayDate) {
                    cursor.delete();
                }
                cursor.continue();
            }
        };

        tx.oncomplete = () => {
            db.close();
            resolve();
        };
    });
}


// --- offline-manager.js ---
/**
 * Offline Manager
 * Orchestrates sync, storage, and UI state for offline functionality
 */


const SYNC_INTERVAL = 5 * 60 * 1000; // 5 minutes
const STALE_THRESHOLD = 5 * 60 * 1000; // 5 minutes

/**
 * OfflineManager class
 * Main controller for offline functionality
 */
class OfflineManager {
    /**
     * @param {Object} options
     * @param {string} options.apiUrl - Map data API URL
     * @param {Function} options.onOffline - Callback when going offline
     * @param {Function} options.onOnline - Callback when coming online
     * @param {Function} options.onSyncStart - Callback when sync starts
     * @param {Function} options.onSyncComplete - Callback when sync completes
     * @param {Function} options.onSyncError - Callback on sync error
     */
    constructor(options = {}) {
        this.apiUrl = options.apiUrl || '/beach/api/map/data';
        this.callbacks = {
            onOffline: options.onOffline || (() => {}),
            onOnline: options.onOnline || (() => {}),
            onSyncStart: options.onSyncStart || (() => {}),
            onSyncComplete: options.onSyncComplete || (() => {}),
            onSyncError: options.onSyncError || (() => {})
        };

        this.connectivity = new ConnectivityManager();
        this.syncTimer = null;
        this.currentDate = null;
        this.lastSyncTime = null;
        this.isSyncing = false;
    }

    /**
     * Initialize offline manager
     * @param {string} date - Current date YYYY-MM-DD
     * @returns {Promise<void>}
     */
    async init(date) {
        this.currentDate = date;

        // Clear old cached data
        await clearOldData(date);

        // Load sync metadata
        const meta = await getSyncMeta();
        if (meta && meta.lastSyncDate === date) {
            this.lastSyncTime = new Date(meta.lastSyncTime);
        }

        // Setup connectivity monitoring
        this.connectivity.onOnline(() => this._handleOnline());
        this.connectivity.onOffline(() => this._handleOffline());
        this.connectivity.start();

        // Start auto-sync timer
        this._startAutoSync();

        // Initial sync if data is stale
        if (this._isDataStale()) {
            await this.sync();
        }
    }

    /**
     * Stop offline manager
     * Cleans up timers and connectivity monitoring
     * @returns {void}
     */
    stop() {
        this.connectivity.stop();
        if (this.syncTimer) {
            clearInterval(this.syncTimer);
            this.syncTimer = null;
        }
    }

    /**
     * Check if currently online
     * @returns {boolean} True if online, false if offline
     */
    isOnline() {
        return this.connectivity.isOnline;
    }

    /**
     * Get last sync time
     * @returns {Date|null} Last sync time or null if never synced
     */
    getLastSyncTime() {
        return this.lastSyncTime;
    }

    /**
     * Format last sync time for display (HH:MM)
     * @returns {string} Formatted time string or '--:--' if never synced
     */
    getLastSyncTimeFormatted() {
        if (!this.lastSyncTime) return '--:--';
        return this.lastSyncTime.toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Sync data from server
     * Fetches fresh map data and stores it in IndexedDB
     * @returns {Promise<Object|null>} Synced data or null on failure
     */
    async sync() {
        if (this.isSyncing || !this.connectivity.isOnline) {
            return null;
        }

        this.isSyncing = true;
        this.callbacks.onSyncStart();

        try {
            const response = await fetch(`${this.apiUrl}?date=${this.currentDate}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Save to IndexedDB
            await saveMapData(this.currentDate, data);

            // Update sync metadata
            this.lastSyncTime = new Date();
            await saveSyncMeta({
                lastSyncDate: this.currentDate,
                lastSyncTime: this.lastSyncTime.toISOString()
            });

            this.callbacks.onSyncComplete(data);
            return data;
        } catch (error) {
            console.error('Sync failed:', error);
            this.callbacks.onSyncError(error);
            return null;
        } finally {
            this.isSyncing = false;
        }
    }

    /**
     * Load cached data for current date
     * Retrieves map data from IndexedDB if available
     * @returns {Promise<Object|null>} Cached data or null if not found
     */
    async loadCachedData() {
        const cached = await getMapData(this.currentDate);
        return cached ? cached.data : null;
    }

    /**
     * Update current date (when user changes date)
     * Resets sync time tracking for the new date
     * @param {string} date - New date YYYY-MM-DD
     * @returns {Promise<void>}
     */
    async setDate(date) {
        this.currentDate = date;

        // Check if we have cached data for this date
        const meta = await getSyncMeta();
        if (meta && meta.lastSyncDate === date) {
            this.lastSyncTime = new Date(meta.lastSyncTime);
        } else {
            this.lastSyncTime = null;
        }
    }

    /**
     * Handle coming online
     * @private
     * @returns {Promise<void>}
     */
    async _handleOnline() {
        this.callbacks.onOnline();

        // Auto-sync when reconnecting
        await this.sync();
    }

    /**
     * Handle going offline
     * @private
     * @returns {void}
     */
    _handleOffline() {
        this.callbacks.onOffline();
    }

    /**
     * Check if cached data is stale
     * @private
     * @returns {boolean} True if data is stale or never synced
     */
    _isDataStale() {
        if (!this.lastSyncTime) return true;
        return (Date.now() - this.lastSyncTime.getTime()) > STALE_THRESHOLD;
    }

    /**
     * Start auto-sync timer
     * @private
     * @returns {void}
     */
    _startAutoSync() {
        this.syncTimer = setInterval(() => {
            if (this.connectivity.isOnline) {
                this.sync();
            }
        }, SYNC_INTERVAL);
    }
}


// --- tooltips.js ---
/**
 * Map Tooltips Module
 * Handles tooltip creation, display, and positioning for furniture items
 */

/**
 * Create and manage tooltips for the beach map
 */
class TooltipManager {
    constructor(container, colors) {
        this.container = container;
        this.colors = colors;
        this.tooltip = null;
    }

    /**
     * Get label text for customer (room# for interno, name for externo)
     * @param {Object} availability - Availability data with customer info
     * @returns {string} Customer label
     */
    getCustomerLabel(availability) {
        if (!availability) return '';

        if (availability.customer_type === 'interno' && availability.room_number) {
            return availability.room_number;
        } else if (availability.first_name) {
            const name = availability.first_name;
            return name.length > 6 ? name.substring(0, 5) + '.' : name;
        } else if (availability.customer_name) {
            const firstName = availability.customer_name.split(' ')[0];
            return firstName.length > 6 ? firstName.substring(0, 5) + '.' : firstName;
        }
        return '';
    }

    /**
     * Show tooltip with customer information
     * @param {Event} event - Mouse event
     * @param {Object} availability - Availability data
     */
    show(event, availability) {
        if (!this.tooltip) {
            this.create();
        }

        const name = this._escape(availability.customer_name || 'Sin nombre');
        let content = `<strong>${name}</strong>`;

        if (availability.customer_type === 'interno' && availability.room_number) {
            content += `<br><small>Hab. ${this._escape(availability.room_number)}</small>`;
        }

        if (availability.vip_status) {
            content += ` <span class="badge bg-warning text-dark" style="font-size: 9px;">VIP</span>`;
        }

        if (availability.num_people) {
            const n = parseInt(availability.num_people, 10) || 0;
            content += `<br><small>${n} persona${n > 1 ? 's' : ''}</small>`;
        }

        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.move(event);
    }

    /**
     * Show tooltip with block information
     * @param {Event} event - Mouse event
     * @param {Object} blockInfo - Block information from API
     * @param {string} furnitureNumber - Furniture number/code
     */
    showBlock(event, blockInfo, furnitureNumber) {
        if (!this.tooltip) {
            this.create();
        }

        const blockTypeNames = {
            'maintenance': 'Mantenimiento',
            'vip_hold': 'Reserva VIP',
            'event': 'Evento',
            'other': 'Bloqueado'
        };

        const typeName = blockTypeNames[blockInfo.block_type] || this._escape(blockInfo.name) || 'Bloqueado';
        let content = `<strong>${typeName}</strong>`;
        content += `<br><small>Mobiliario: ${this._escape(furnitureNumber)}</small>`;

        if (blockInfo.reason) {
            content += `<br><small>Motivo: ${this._escape(blockInfo.reason)}</small>`;
        }

        if (blockInfo.end_date) {
            content += `<br><small>Hasta: ${this._escape(blockInfo.end_date)}</small>`;
        }

        // Add visual indicator of block color
        const safeColor = this._sanitizeColor(blockInfo.color) || '#999';
        content = `<span style="display: inline-block; width: 10px; height: 10px; background: ${safeColor}; border-radius: 2px; margin-right: 6px;"></span>${content}`;

        this.tooltip.innerHTML = content;
        this.tooltip.style.display = 'block';
        this.move(event);
    }

    /**
     * Hide the tooltip
     */
    hide() {
        if (this.tooltip) {
            this.tooltip.style.display = 'none';
        }
    }

    /**
     * Move tooltip to follow cursor
     * @param {Event} event - Mouse event
     */
    move(event) {
        if (!this.tooltip) return;

        const offsetX = 10;
        const offsetY = -10;
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();

        let left = event.clientX - containerRect.left + offsetX;
        let top = event.clientY - containerRect.top + offsetY - tooltipRect.height;

        // Keep tooltip within container bounds
        if (left + tooltipRect.width > containerRect.width) {
            left = event.clientX - containerRect.left - tooltipRect.width - offsetX;
        }
        if (top < 0) {
            top = event.clientY - containerRect.top + 20;
        }

        this.tooltip.style.left = `${left}px`;
        this.tooltip.style.top = `${top}px`;
    }

    /**
     * Create the tooltip DOM element
     */
    create() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'map-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            display: none;
            background: ${this.colors.tooltipBg};
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            max-width: 200px;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            line-height: 1.4;
            opacity: 0.95;
        `;
        this.container.style.position = 'relative';
        this.container.appendChild(this.tooltip);
    }

    /**
     * Escape HTML entities to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     * @private
     */
    _escape(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Sanitize a CSS color value
     * @param {string} color - Color value
     * @returns {string|null} Sanitized color or null
     * @private
     */
    _sanitizeColor(color) {
        if (!color) return null;
        if (/^#[0-9A-Fa-f]{3,8}$/.test(color)) return color;
        if (/^(rgb|hsl)a?\([^)]+\)$/.test(color)) return color;
        if (/^[a-zA-Z]+$/.test(color)) return color;
        return null;
    }

    /**
     * Clean up tooltip element
     */
    destroy() {
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
            this.tooltip = null;
        }
    }
}


// --- selection.js ---
/**
 * Map Selection Module
 * Handles furniture selection state and panel updates
 */

/**
 * Selection manager for beach map furniture
 */
class SelectionManager {
    constructor() {
        this.selectedFurniture = new Set();
        this.readOnly = false;  // Read-only state (controlled by ModalStateManager)
        this.callbacks = {
            onSelect: null,
            onDeselect: null
        };
    }

    /**
     * Set callback functions
     * @param {string} eventName - Event name (onSelect, onDeselect)
     * @param {Function} callback - Callback function
     */
    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
        return this;
    }

    /**
     * Set read-only state (controlled by ModalStateManager)
     * @param {boolean} readOnly - True to disable selections
     */
    setReadOnly(readOnly) {
        this.readOnly = readOnly;
        console.log(`[SelectionManager] Read-only mode: ${readOnly}`);
    }

    /**
     * Check if selections are currently allowed
     * @returns {boolean} True if selections are allowed
     */
    canSelect() {
        return !this.readOnly;
    }

    /**
     * Select or toggle furniture selection
     * @param {number} id - Furniture ID
     * @param {boolean} addToSelection - Whether to add to existing selection
     * @returns {boolean} Whether selection changed
     */
    select(id, addToSelection = false) {
        // Block selections in read-only mode
        if (this.readOnly) {
            console.log('[SelectionManager] Selection blocked - read-only mode active');
            return false;
        }

        if (!addToSelection) {
            this.selectedFurniture.clear();
        }

        if (this.selectedFurniture.has(id)) {
            this.selectedFurniture.delete(id);
            if (this.callbacks.onDeselect) {
                this.callbacks.onDeselect(id);
            }
            return true;
        } else {
            this.selectedFurniture.add(id);
            if (this.callbacks.onSelect) {
                this.callbacks.onSelect(id);
            }
            return true;
        }
    }

    /**
     * Deselect a specific furniture item
     * @param {number} id - Furniture ID
     */
    deselect(id) {
        this.selectedFurniture.delete(id);
    }

    /**
     * Clear all selections
     */
    clear() {
        this.selectedFurniture.clear();
    }

    /**
     * Get selected furniture IDs as array
     * @returns {number[]} Array of selected IDs
     */
    getSelected() {
        return Array.from(this.selectedFurniture);
    }

    /**
     * Get the Set of selected furniture
     * @returns {Set} Selected furniture Set
     */
    getSelectedSet() {
        return this.selectedFurniture;
    }

    /**
     * Check if furniture is selected
     * @param {number} id - Furniture ID
     * @returns {boolean}
     */
    isSelected(id) {
        return this.selectedFurniture.has(id);
    }

    /**
     * Get count of selected items
     * @returns {number}
     */
    count() {
        return this.selectedFurniture.size;
    }

    /**
     * Get selected furniture data from map data
     * @param {Object} data - Map data with furniture array
     * @returns {Object[]} Array of selected furniture objects
     */
    getSelectedData(data) {
        if (!data || !data.furniture) return [];
        return data.furniture.filter(f => this.selectedFurniture.has(f.id));
    }

    /**
     * Update the selection panel UI
     * @param {Object} data - Map data with furniture array
     */
    updatePanel(data) {
        const panel = document.getElementById('selection-panel');
        if (!panel) return;

        const selected = this.getSelectedData(data);
        if (selected.length === 0) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'block';
        const countEl = panel.querySelector('.selection-count');
        const listEl = panel.querySelector('.selection-list');
        const capacityEl = panel.querySelector('.selection-capacity');

        if (countEl) countEl.textContent = selected.length;
        if (listEl) listEl.textContent = selected.map(f => f.number).join(', ');
        if (capacityEl) {
            const totalCapacity = selected.reduce((sum, f) => sum + (f.capacity || 2), 0);
            capacityEl.textContent = totalCapacity;
        }
    }
}


// --- navigation.js ---
/**
 * Map Navigation Module
 * Handles date navigation, zoom/pan, and keyboard shortcuts
 */

/**
 * Navigation manager for beach map
 */
class NavigationManager {
    constructor(options = {}) {
        this.zoom = 1;
        this.pan = { x: 0, y: 0 };
        this.options = {
            minZoom: options.minZoom || 0.1,
            maxZoom: options.maxZoom || 3,
            ...options
        };
        this.callbacks = {
            onDateChange: null,
            onZoomChange: null
        };
        this.keydownHandler = null;
    }

    /**
     * Set callback functions
     * @param {string} eventName - Event name
     * @param {Function} callback - Callback function
     */
    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
        return this;
    }

    /**
     * Update options (e.g., from server config)
     * @param {Object} newOptions - New option values
     */
    updateOptions(newOptions) {
        Object.assign(this.options, newOptions);
    }

    // =========================================================================
    // DATE NAVIGATION
    // =========================================================================

    /**
     * Navigate to a specific date
     * @param {string} dateStr - Date string YYYY-MM-DD
     * @param {Function} loadDataFn - Async function to reload data
     */
    async goToDate(dateStr, loadDataFn) {
        if (this.callbacks.onDateChange) {
            this.callbacks.onDateChange(dateStr);
        }
        if (loadDataFn) {
            await loadDataFn();
        }
    }

    /**
     * Navigate to previous day
     * @param {string} currentDate - Current date string
     * @param {Function} loadDataFn - Async function to reload data
     * @returns {string} New date string
     */
    async goToPreviousDay(currentDate, loadDataFn) {
        const date = new Date(currentDate);
        date.setDate(date.getDate() - 1);
        const newDate = date.toISOString().split('T')[0];
        await this.goToDate(newDate, loadDataFn);
        return newDate;
    }

    /**
     * Navigate to next day
     * @param {string} currentDate - Current date string
     * @param {Function} loadDataFn - Async function to reload data
     * @returns {string} New date string
     */
    async goToNextDay(currentDate, loadDataFn) {
        const date = new Date(currentDate);
        date.setDate(date.getDate() + 1);
        const newDate = date.toISOString().split('T')[0];
        await this.goToDate(newDate, loadDataFn);
        return newDate;
    }

    // =========================================================================
    // ZOOM & PAN
    // =========================================================================

    /**
     * Zoom in by a factor
     * @param {number} factor - Zoom increment
     */
    zoomIn(factor = 0.25) {
        this.setZoom(this.zoom + factor);
    }

    /**
     * Zoom out by a factor
     * @param {number} factor - Zoom decrement
     */
    zoomOut(factor = 0.25) {
        this.setZoom(this.zoom - factor);
    }

    /**
     * Reset zoom to 100%
     */
    zoomReset() {
        this.setZoom(1);
        this.pan = { x: 0, y: 0 };
    }

    /**
     * Set zoom level with bounds checking
     * @param {number} level - New zoom level
     */
    setZoom(level) {
        this.zoom = Math.max(this.options.minZoom, Math.min(this.options.maxZoom, level));
        if (this.callbacks.onZoomChange) {
            this.callbacks.onZoomChange(this.zoom);
        }
    }

    /**
     * Get current zoom level
     * @returns {number}
     */
    getZoom() {
        return this.zoom;
    }

    /**
     * Apply zoom to SVG element
     * @param {SVGSVGElement} svg - SVG element
     * @param {Object} data - Map data with dimensions
     */
    applyZoom(svg, data) {
        if (!svg || !data) return;

        const viewBox = svg.getAttribute('viewBox');
        if (!viewBox) return;

        const [, , width, height] = viewBox.split(' ').map(Number);

        svg.style.width = `${width * this.zoom}px`;
        svg.style.height = `${height * this.zoom}px`;
    }

    // =========================================================================
    // KEYBOARD NAVIGATION
    // =========================================================================

    /**
     * Setup keyboard event listener
     * @param {Object} handlers - Object with handler functions
     */
    setupKeyboard(handlers) {
        this.keydownHandler = (event) => {
            // Skip if user is typing in an input field
            const tagName = event.target.tagName.toLowerCase();
            const isInputField = tagName === 'input' || tagName === 'textarea' || tagName === 'select';

            // Escape to clear selection
            if (event.key === 'Escape') {
                if (handlers.onEscape) handlers.onEscape();
                return;
            }

            // Arrow keys for date navigation (only when not in input fields)
            if (!isInputField) {
                if (event.key === 'ArrowLeft' && event.altKey) {
                    event.preventDefault();
                    if (handlers.onPrevDay) handlers.onPrevDay();
                } else if (event.key === 'ArrowRight' && event.altKey) {
                    event.preventDefault();
                    if (handlers.onNextDay) handlers.onNextDay();
                }
            }

            // Zoom with + and - (only when not in input fields)
            if (!isInputField) {
                if (event.key === '+' || event.key === '=') {
                    this.zoomIn();
                    if (handlers.onZoom) handlers.onZoom();
                } else if (event.key === '-') {
                    this.zoomOut();
                    if (handlers.onZoom) handlers.onZoom();
                }
            }

            // Search shortcut: Ctrl+F or / (only when not in input fields)
            if (!isInputField) {
                if ((event.ctrlKey && event.key === 'f') || event.key === '/') {
                    event.preventDefault();
                    if (handlers.onSearchFocus) handlers.onSearchFocus();
                }
            }
        };

        document.addEventListener('keydown', this.keydownHandler);
    }

    /**
     * Remove keyboard event listener
     */
    removeKeyboard() {
        if (this.keydownHandler) {
            document.removeEventListener('keydown', this.keydownHandler);
            this.keydownHandler = null;
        }
    }
}


// --- context-menu.js ---
/**
 * Context Menu Module
 * Handles right-click context menu for furniture items
 */


/**
 * Block type definitions (should match backend)
 */
const BLOCK_TYPES = {
    'maintenance': { name: 'Mantenimiento', color: '#9CA3AF', icon: '🔧' },
    'vip_hold': { name: 'Reserva VIP', color: '#D4AF37', icon: '⭐' },
    'event': { name: 'Evento', color: '#3B82F6', icon: '📅' },
    'other': { name: 'Otro', color: '#6B7280', icon: '🚫' }
};

/**
 * Context menu manager for beach map
 */
class ContextMenuManager {
    /**
     * @param {Object} options - Configuration options
     * @param {HTMLElement} options.container - Map container element
     * @param {Function} options.onBlock - Callback when block action is selected
     * @param {Function} options.onUnblock - Callback when unblock action is selected
     * @param {Function} options.onAddTemporary - Callback when add temporary action is selected
     * @param {Function} options.onDeleteTemporary - Callback when delete temporary action is selected
     * @param {Function} options.getData - Function to get current map data
     * @param {Function} options.getZoneAtPosition - Function to get zone at SVG coordinates
     */
    constructor(options) {
        this.container = options.container;
        this.onBlock = options.onBlock || (() => {});
        this.onUnblock = options.onUnblock || (() => {});
        this.onAddTemporary = options.onAddTemporary || (() => {});
        this.onDeleteTemporary = options.onDeleteTemporary || (() => {});
        this.getData = options.getData || (() => null);
        this.getZoneAtPosition = options.getZoneAtPosition || (() => null);

        this.menuElement = null;
        this.emptySpaceMenuElement = null;
        this.currentFurnitureId = null;
        this.currentFurnitureNumber = null;
        this.currentFurnitureIsTemp = false;
        this.currentSelection = []; // Array of IDs for multi-select operations
        this.currentClickPosition = { x: 0, y: 0 };
        this.currentZoneId = null;

        this.init();
    }

    /**
     * Initialize context menu
     */
    init() {
        this.createMenuElement();
        this.createEmptySpaceMenuElement();
        this.setupEventListeners();
        this.setupEmptySpaceEventListeners();
    }

    /**
     * Create the context menu DOM element for furniture
     */
    createMenuElement() {
        // Remove existing if any
        const existing = document.getElementById('furniture-context-menu');
        if (existing) existing.remove();

        this.menuElement = document.createElement('div');
        this.menuElement.id = 'furniture-context-menu';
        this.menuElement.className = 'furniture-context-menu';
        this.menuElement.setAttribute('role', 'menu');
        this.menuElement.setAttribute('aria-label', 'Menu de mobiliario');
        this.menuElement.innerHTML = `
            <div class="context-menu-header" id="ctx-header">
                <span class="ctx-furniture-number"></span>
            </div>
            <div class="context-menu-item ctx-block" id="ctx-block" tabindex="0" role="menuitem">
                <i class="fas fa-ban"></i>
                <span>Bloquear</span>
            </div>
            <div class="context-menu-item ctx-unblock" id="ctx-unblock" tabindex="0" role="menuitem">
                <i class="fas fa-lock-open"></i>
                <span>Desbloquear</span>
            </div>
            <div class="context-menu-divider" role="separator"></div>
            <div class="context-menu-item ctx-view-block" id="ctx-view-block" tabindex="0" role="menuitem">
                <i class="fas fa-info-circle"></i>
                <span>Ver detalles del bloqueo</span>
            </div>
            <div class="context-menu-divider ctx-temp-divider" role="separator"></div>
            <div class="context-menu-item ctx-delete-temp" id="ctx-delete-temp" tabindex="0" role="menuitem">
                <i class="fas fa-trash"></i>
                <span>Eliminar Mobiliario Temporal</span>
            </div>
        `;

        document.body.appendChild(this.menuElement);
    }

    /**
     * Create the context menu DOM element for empty space
     */
    createEmptySpaceMenuElement() {
        // Remove existing if any
        const existing = document.getElementById('empty-space-context-menu');
        if (existing) existing.remove();

        this.emptySpaceMenuElement = document.createElement('div');
        this.emptySpaceMenuElement.id = 'empty-space-context-menu';
        this.emptySpaceMenuElement.className = 'furniture-context-menu';
        this.emptySpaceMenuElement.setAttribute('role', 'menu');
        this.emptySpaceMenuElement.setAttribute('aria-label', 'Menu de espacio vacio');
        this.emptySpaceMenuElement.innerHTML = `
            <div class="context-menu-header" id="ctx-empty-header">
                <span class="ctx-zone-name">Zona</span>
            </div>
            <div class="context-menu-item ctx-add-temp" id="ctx-add-temp" tabindex="0" role="menuitem">
                <i class="fas fa-plus-circle"></i>
                <span>Añadir Mobiliario Temporal</span>
            </div>
        `;

        document.body.appendChild(this.emptySpaceMenuElement);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Block option click/keyboard
        const blockItem = this.menuElement.querySelector('#ctx-block');
        const handleBlock = () => {
            // Check if multi-select or single
            if (this.currentSelection.length > 0) {
                // Multi-select: get furniture data for all selected items
                const beachMap = this.getData()?.beachMap;
                if (beachMap) {
                    const selectedData = beachMap.getSelectedFurnitureData();
                    const ids = selectedData.map(f => f.id);
                    const numbers = selectedData.map(f => f.number);
                    this.hide();
                    this.onBlock(ids, numbers);
                }
            } else {
                // Single selection
                const furnitureId = this.currentFurnitureId;
                const furnitureNumber = this.currentFurnitureNumber;
                this.hide();
                if (furnitureId) {
                    this.onBlock([furnitureId], [furnitureNumber]);
                }
            }
        };
        blockItem?.addEventListener('click', handleBlock);
        blockItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleBlock();
            }
        });

        // Unblock option click/keyboard
        const unblockItem = this.menuElement.querySelector('#ctx-unblock');
        const handleUnblock = () => {
            // Check if multi-select or single
            if (this.currentSelection.length > 0) {
                // Multi-select: get furniture data for all selected items
                const beachMap = this.getData()?.beachMap;
                if (beachMap) {
                    const selectedData = beachMap.getSelectedFurnitureData();
                    const ids = selectedData.map(f => f.id);
                    const numbers = selectedData.map(f => f.number);
                    this.hide();
                    this.onUnblock(ids, numbers);
                }
            } else {
                // Single selection
                const furnitureId = this.currentFurnitureId;
                const furnitureNumber = this.currentFurnitureNumber;
                this.hide();
                if (furnitureId) {
                    this.onUnblock([furnitureId], [furnitureNumber]);
                }
            }
        };
        unblockItem?.addEventListener('click', handleUnblock);
        unblockItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleUnblock();
            }
        });

        // View block details click/keyboard
        const viewBlockItem = this.menuElement.querySelector('#ctx-view-block');
        const handleViewBlock = () => {
            // Save value before hide() clears it
            const furnitureId = this.currentFurnitureId;
            this.hide();
            if (furnitureId) {
                this.showBlockDetails(furnitureId);
            }
        };
        viewBlockItem?.addEventListener('click', handleViewBlock);
        viewBlockItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleViewBlock();
            }
        });

        // Delete temporary furniture click/keyboard
        const deleteTempItem = this.menuElement.querySelector('#ctx-delete-temp');
        const handleDeleteTemp = () => {
            // Check if multi-select or single
            if (this.currentSelection.length > 0) {
                // Multi-select: get furniture data for all selected items
                const beachMap = this.getData()?.beachMap;
                if (beachMap) {
                    const selectedData = beachMap.getSelectedFurnitureData();
                    const ids = selectedData.map(f => f.id);
                    const numbers = selectedData.map(f => f.number);
                    this.hide();
                    this.onDeleteTemporary(ids, numbers);
                }
            } else {
                // Single selection
                const furnitureId = this.currentFurnitureId;
                const furnitureNumber = this.currentFurnitureNumber;
                this.hide();
                if (furnitureId) {
                    this.onDeleteTemporary([furnitureId], [furnitureNumber]);
                }
            }
        };
        deleteTempItem?.addEventListener('click', handleDeleteTemp);
        deleteTempItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleDeleteTemp();
            }
        });

        // Hide on click outside
        document.addEventListener('click', (e) => {
            if (!this.menuElement.contains(e.target) &&
                !this.emptySpaceMenuElement?.contains(e.target)) {
                this.hide();
                this.hideEmptySpaceMenu();
            }
        });

        // Hide on scroll
        document.addEventListener('scroll', () => {
            this.hide();
            this.hideEmptySpaceMenu();
        }, true);

        // Hide on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hide();
                this.hideEmptySpaceMenu();
            }
        });
    }

    /**
     * Setup event listeners for empty space menu
     */
    setupEmptySpaceEventListeners() {
        // Add temporary furniture click/keyboard
        const addTempItem = this.emptySpaceMenuElement?.querySelector('#ctx-add-temp');
        const handleAddTemp = () => {
            const position = { ...this.currentClickPosition };
            const zoneId = this.currentZoneId;
            this.hideEmptySpaceMenu();
            this.onAddTemporary(position.x, position.y, zoneId);
        };
        addTempItem?.addEventListener('click', handleAddTemp);
        addTempItem?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleAddTemp();
            }
        });
    }

    /**
     * Show the context menu at the specified position
     * @param {MouseEvent} event - Right-click event
     * @param {Object} furniture - Furniture item data
     */
    show(event, furniture) {
        event.preventDefault();
        event.stopPropagation();

        // Hide empty space menu if open
        this.hideEmptySpaceMenu();

        // Check if this furniture is part of a multi-selection
        const beachMap = this.getData()?.beachMap;
        const selectedIds = beachMap ? beachMap.getSelectedFurniture() : [];
        const isMultiSelect = selectedIds.length > 1 && selectedIds.includes(furniture.id);

        if (isMultiSelect) {
            // Store all selected IDs for multi-select operations
            this.currentSelection = selectedIds;
            this.currentFurnitureId = null; // Clear single ID to indicate multi-select
            this.currentFurnitureNumber = null;
        } else {
            // Single selection
            this.currentSelection = [];
            this.currentFurnitureId = furniture.id;
            this.currentFurnitureNumber = furniture.number;
        }

        this.currentFurnitureIsTemp = !!furniture.is_temporary;

        // Update header
        const header = this.menuElement.querySelector('.ctx-furniture-number');
        if (header) {
            if (isMultiSelect) {
                header.textContent = `${selectedIds.length} items seleccionados`;
            } else {
                const tempLabel = furniture.is_temporary ? ' (Temporal)' : '';
                header.textContent = `Mobiliario ${furniture.number}${tempLabel}`;
            }
        }

        // Check if blocked
        const data = this.getData();
        const isBlocked = data?.blocks && data.blocks[furniture.id];
        const isTemporary = !!furniture.is_temporary;

        // Show/hide appropriate options
        const blockItem = this.menuElement.querySelector('.ctx-block');
        const unblockItem = this.menuElement.querySelector('.ctx-unblock');
        const viewBlockItem = this.menuElement.querySelector('.ctx-view-block');
        const tempDivider = this.menuElement.querySelector('.ctx-temp-divider');
        const deleteTempItem = this.menuElement.querySelector('.ctx-delete-temp');

        if (isBlocked) {
            blockItem.style.display = 'none';
            unblockItem.style.display = 'flex';
            viewBlockItem.style.display = 'flex';
        } else {
            blockItem.style.display = 'flex';
            unblockItem.style.display = 'none';
            viewBlockItem.style.display = 'none';
        }

        // Show delete option only for temporary furniture
        if (isTemporary) {
            tempDivider.style.display = 'block';
            deleteTempItem.style.display = 'flex';
        } else {
            tempDivider.style.display = 'none';
            deleteTempItem.style.display = 'none';
        }

        // Position the menu
        this.positionMenu(event.clientX, event.clientY);

        // Show
        this.menuElement.classList.add('visible');
    }

    /**
     * Show the empty space context menu
     * @param {MouseEvent} event - Right-click event
     * @param {number} svgX - SVG X coordinate
     * @param {number} svgY - SVG Y coordinate
     * @param {Object|null} zone - Zone data if click is within a zone
     */
    showEmptySpaceMenu(event, svgX, svgY, zone = null) {
        event.preventDefault();
        event.stopPropagation();

        // Hide furniture menu if open
        this.hide();

        this.currentClickPosition = { x: svgX, y: svgY };
        this.currentZoneId = zone?.id || null;

        // Update header with zone name
        const header = this.emptySpaceMenuElement?.querySelector('.ctx-zone-name');
        if (header) {
            header.textContent = zone ? zone.name : 'Mapa';
        }

        // Position the menu
        this.positionEmptySpaceMenu(event.clientX, event.clientY);

        // Show
        this.emptySpaceMenuElement?.classList.add('visible');
    }

    /**
     * Position the empty space menu at coordinates
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     */
    positionEmptySpaceMenu(x, y) {
        const menu = this.emptySpaceMenuElement;
        if (!menu) return;

        // Temporarily show for measurement (visibility:hidden keeps it invisible to user)
        menu.style.visibility = 'hidden';
        menu.classList.add('visible');
        const menuWidth = menu.offsetWidth || 180;
        const menuHeight = menu.offsetHeight || 200;
        menu.classList.remove('visible');
        menu.style.visibility = '';

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Adjust X if menu would overflow right
        if (x + menuWidth > viewportWidth) {
            x = viewportWidth - menuWidth - 10;
        }

        // Adjust Y if menu would overflow bottom
        if (y + menuHeight > viewportHeight) {
            y = viewportHeight - menuHeight - 10;
        }

        menu.style.left = `${Math.max(10, x)}px`;
        menu.style.top = `${Math.max(10, y)}px`;
    }

    /**
     * Hide the empty space context menu
     */
    hideEmptySpaceMenu() {
        this.emptySpaceMenuElement?.classList.remove('visible');
        this.currentClickPosition = { x: 0, y: 0 };
        this.currentZoneId = null;
    }

    /**
     * Position the menu at coordinates, adjusting for viewport edges
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     */
    positionMenu(x, y) {
        const menu = this.menuElement;

        // Temporarily show for measurement (visibility:hidden keeps it invisible to user)
        menu.style.visibility = 'hidden';
        menu.classList.add('visible');
        const menuWidth = menu.offsetWidth || 180;
        const menuHeight = menu.offsetHeight || 200;
        menu.classList.remove('visible');
        menu.style.visibility = '';

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Adjust X if menu would overflow right
        if (x + menuWidth > viewportWidth) {
            x = viewportWidth - menuWidth - 10;
        }

        // Adjust Y if menu would overflow bottom
        if (y + menuHeight > viewportHeight) {
            y = viewportHeight - menuHeight - 10;
        }

        menu.style.left = `${Math.max(10, x)}px`;
        menu.style.top = `${Math.max(10, y)}px`;
    }

    /**
     * Hide the context menu
     */
    hide() {
        this.menuElement?.classList.remove('visible');
        this.currentFurnitureId = null;
        this.currentFurnitureNumber = null;
        this.currentFurnitureIsTemp = false;
    }

    /**
     * Show block details in a toast
     * @param {number} furnitureId - Furniture ID (optional, uses currentFurnitureId if not provided)
     */
    showBlockDetails(furnitureId = null) {
        const data = this.getData();
        const id = furnitureId || this.currentFurnitureId;
        const blockInfo = data?.blocks?.[id];

        if (!blockInfo) {
            showToast('No hay información de bloqueo', 'info');
            return;
        }

        const blockType = BLOCK_TYPES[blockInfo.block_type] || BLOCK_TYPES.other;
        let message = `${blockType.icon} ${blockType.name}`;

        if (blockInfo.reason) {
            message += ` - ${blockInfo.reason}`;
        }

        if (blockInfo.end_date) {
            message += ` (Hasta: ${blockInfo.end_date})`;
        }

        showToast(message, 'info');
    }

    /**
     * Check if furniture is blocked
     * @param {number} furnitureId - Furniture ID
     * @returns {boolean}
     */
    isBlocked(furnitureId) {
        const data = this.getData();
        return !!(data?.blocks && data.blocks[furnitureId]);
    }

    /**
     * Get block info for furniture
     * @param {number} furnitureId - Furniture ID
     * @returns {Object|null}
     */
    getBlockInfo(furnitureId) {
        const data = this.getData();
        return data?.blocks?.[furnitureId] || null;
    }

    /**
     * Check if furniture is temporary
     * @param {number} furnitureId - Furniture ID
     * @returns {boolean}
     */
    isTemporary(furnitureId) {
        const data = this.getData();
        const furniture = data?.furniture?.find(f => f.id === furnitureId);
        return !!furniture?.is_temporary;
    }

    /**
     * Clean up
     */
    destroy() {
        this.menuElement?.remove();
        this.menuElement = null;
        this.emptySpaceMenuElement?.remove();
        this.emptySpaceMenuElement = null;
    }
}



// --- interaction.js ---
/**
 * Map Interaction Module
 * Handles drag-drop functionality and edit mode for furniture positioning
 */


/**
 * Interaction manager for drag-drop and edit mode
 */
class InteractionManager {
    constructor(options = {}) {
        this.editMode = false;
        this.readOnly = false;  // Read-only state (controlled by ModalStateManager)
        this.isDragging = false;
        this.dragTarget = null;
        this.dragStart = null;
        this.options = {
            snapToGrid: options.snapToGrid || 10,
            ...options
        };
        this.zoom = 1;
        this.container = null;
        this.furnitureLayer = null;

        // Callback for when position is saved (used to trigger refresh)
        this.onPositionSaved = options.onPositionSaved || null;

        // Callback for updating local data cache after position change
        this.onPositionUpdate = options.onPositionUpdate || null;

        // Temporary furniture drag state (always enabled, no edit mode required)
        this.isDraggingTemp = false;
        this.tempDragTarget = null;
        this.tempDragStartMouse = null;
        this.tempDragStartPos = null;
        this.tempDragThreshold = 5; // pixels before drag activates
        this.tempDragThresholdMet = false;

        // Bind methods
        this.handleDrag = this.handleDrag.bind(this);
        this.handleDragEnd = this.handleDragEnd.bind(this);
    }

    /**
     * Update options (e.g., from server config)
     * @param {Object} newOptions - New option values
     */
    updateOptions(newOptions) {
        Object.assign(this.options, newOptions);
    }

    /**
     * Set current zoom level (needed for drag calculations)
     * @param {number} zoom - Current zoom level
     */
    setZoom(zoom) {
        this.zoom = zoom;
    }

    /**
     * Set read-only state (controlled by ModalStateManager)
     * @param {boolean} readOnly - True to disable interactions
     */
    setReadOnly(readOnly) {
        this.readOnly = readOnly;
        console.log(`[InteractionManager] Read-only mode: ${readOnly}`);

        // If entering read-only, cancel any ongoing drags
        if (readOnly && this.isDragging) {
            this.cancelDrag();
        }
        if (readOnly && this.isDraggingTemp) {
            this.cancelTempDrag();
        }
    }

    /**
     * Check if interactions are currently allowed
     * @returns {boolean} True if interactions are allowed
     */
    canInteract() {
        return !this.readOnly;
    }

    /**
     * Enable edit mode for furniture positioning
     * @param {HTMLElement} container - Map container element
     * @param {SVGGElement} furnitureLayer - Furniture layer element
     */
    enableEditMode(container, furnitureLayer) {
        this.editMode = true;
        this.container = container;
        this.furnitureLayer = furnitureLayer;
        container.classList.add('edit-mode');
        this.setupDragDrop();
    }

    /**
     * Disable edit mode
     */
    disableEditMode() {
        this.editMode = false;
        if (this.container) {
            this.container.classList.remove('edit-mode');
        }
        this.removeDragDrop();
    }

    /**
     * Check if edit mode is enabled
     * @returns {boolean}
     */
    isEditMode() {
        return this.editMode;
    }

    /**
     * Setup drag-drop event listeners
     */
    setupDragDrop() {
        if (!this.editMode || !this.furnitureLayer) return;

        this.furnitureLayer.querySelectorAll('.furniture-item').forEach(group => {
            group.style.cursor = 'move';
            group.addEventListener('mousedown', (e) => this.handleDragStart(e));
        });

        document.addEventListener('mousemove', this.handleDrag);
        document.addEventListener('mouseup', this.handleDragEnd);
    }

    /**
     * Remove drag-drop event listeners
     */
    removeDragDrop() {
        document.removeEventListener('mousemove', this.handleDrag);
        document.removeEventListener('mouseup', this.handleDragEnd);
    }

    /**
     * Handle drag start
     * @param {MouseEvent} event
     */
    handleDragStart(event) {
        if (!this.editMode) return;

        const group = event.target.closest('.furniture-item');
        if (!group) return;

        this.isDragging = true;
        this.dragTarget = group;
        this.dragStart = {
            x: event.clientX,
            y: event.clientY
        };

        // Get current position from transform
        const transform = group.getAttribute('transform');
        const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
        if (match) {
            this.dragStart.itemX = parseFloat(match[1]);
            this.dragStart.itemY = parseFloat(match[2]);
        }

        group.classList.add('dragging');
    }

    /**
     * Handle drag movement
     * @param {MouseEvent} event
     */
    handleDrag(event) {
        if (!this.isDragging || !this.dragTarget) return;

        const dx = (event.clientX - this.dragStart.x) / this.zoom;
        const dy = (event.clientY - this.dragStart.y) / this.zoom;

        let newX = this.dragStart.itemX + dx;
        let newY = this.dragStart.itemY + dy;

        // Snap to grid
        if (this.options.snapToGrid) {
            newX = Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid;
            newY = Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid;
        }

        // Preserve rotation
        const rotation = this.dragTarget.getAttribute('transform').match(/rotate\(([^)]+)\)/);
        const rotationStr = rotation ? ` rotate(${rotation[1]})` : '';

        this.dragTarget.setAttribute('transform', `translate(${newX}, ${newY})${rotationStr}`);
    }

    /**
     * Handle drag end
     * @param {MouseEvent} event
     */
    async handleDragEnd(event) {
        if (!this.isDragging || !this.dragTarget) return;

        const group = this.dragTarget;
        const furnitureId = parseInt(group.dataset.furnitureId);

        // Get final position
        const transform = group.getAttribute('transform');
        const match = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);

        if (match) {
            const x = parseFloat(match[1]);
            const y = parseFloat(match[2]);

            // Save position to server
            await this.savePosition(furnitureId, x, y);
        }

        group.classList.remove('dragging');
        this.isDragging = false;
        this.dragTarget = null;
    }

    /**
     * Save furniture position to server
     * @param {number} furnitureId - Furniture ID
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {number|null} rotation - Rotation angle (optional)
     * @returns {Promise<Object>} Result from server
     */
    async savePosition(furnitureId, x, y, rotation = null) {
        try {
            const response = await fetch(`/beach/api/map/furniture/${furnitureId}/position`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ x, y, rotation })
            });

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Error desconocido');
            }

            showToast('Posición actualizada', 'success');
            return result;
        } catch (error) {
            console.error('Error saving position:', error);
            showToast('Error al mover mobiliario', 'error');
            throw error; // Re-throw for caller to handle
        }
    }

    // =========================================================================
    // TEMPORARY FURNITURE DRAG (always enabled, no edit mode required)
    // =========================================================================

    /**
     * Check if an element is draggable temporary furniture
     * @param {Element} element - DOM element to check
     * @returns {Object|null} Furniture data if temp and draggable, null otherwise
     */
    isTemporaryFurniture(element) {
        const furnitureGroup = element.closest('.furniture-item');
        if (!furnitureGroup) return null;

        // Must be temporary and not blocked
        if (!furnitureGroup.classList.contains('temporary')) return null;
        if (furnitureGroup.classList.contains('blocked')) return null;

        return {
            element: furnitureGroup,
            id: parseInt(furnitureGroup.dataset.furnitureId)
        };
    }

    /**
     * Parse position and rotation from SVG transform attribute
     * @param {string} transform - Transform attribute value
     * @returns {Object} {x, y, rotation}
     */
    parseTransform(transform) {
        const translateMatch = transform?.match(/translate\(([^,]+),\s*([^)]+)\)/);
        const rotateMatch = transform?.match(/rotate\(([^)]+)\)/);

        return {
            x: translateMatch ? parseFloat(translateMatch[1]) : 0,
            y: translateMatch ? parseFloat(translateMatch[2]) : 0,
            rotation: rotateMatch ? parseFloat(rotateMatch[1]) : 0
        };
    }

    /**
     * Handle temp furniture drag start
     * @param {MouseEvent} event
     * @param {Object} tempFurniture - {element, id}
     */
    handleTempDragStart(event, tempFurniture) {
        event.preventDefault();

        this.isDraggingTemp = true;
        this.tempDragTarget = tempFurniture.element;
        this.tempDragThresholdMet = false;

        // Store initial mouse position
        this.tempDragStartMouse = {
            x: event.clientX,
            y: event.clientY
        };

        // Store initial element position
        const transform = this.tempDragTarget.getAttribute('transform');
        this.tempDragStartPos = this.parseTransform(transform);
    }

    /**
     * Handle temp furniture drag movement
     * @param {MouseEvent} event
     * @returns {boolean} True if drag is active
     */
    handleTempDrag(event) {
        if (!this.isDraggingTemp || !this.tempDragTarget) return false;

        const deltaX = event.clientX - this.tempDragStartMouse.x;
        const deltaY = event.clientY - this.tempDragStartMouse.y;

        // Check drag threshold
        if (!this.tempDragThresholdMet) {
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            if (distance < this.tempDragThreshold) return false;

            this.tempDragThresholdMet = true;
            this.tempDragTarget.classList.add('dragging');
        }

        // Calculate new position (zoom-aware)
        const newX = this.tempDragStartPos.x + (deltaX / this.zoom);
        const newY = this.tempDragStartPos.y + (deltaY / this.zoom);

        // Apply grid snapping
        const snappedX = this.options.snapToGrid
            ? Math.round(newX / this.options.snapToGrid) * this.options.snapToGrid
            : newX;
        const snappedY = this.options.snapToGrid
            ? Math.round(newY / this.options.snapToGrid) * this.options.snapToGrid
            : newY;

        // Update visual position (preserve rotation)
        const rotation = this.tempDragStartPos.rotation;
        const rotationStr = rotation ? ` rotate(${rotation})` : '';
        this.tempDragTarget.setAttribute(
            'transform',
            `translate(${snappedX}, ${snappedY})${rotationStr}`
        );

        return true;
    }

    /**
     * Handle temp furniture drag end
     * @param {MouseEvent} event
     * @returns {Promise<boolean>} True if a drag occurred (click should be suppressed)
     */
    async handleTempDragEnd(event) {
        if (!this.isDraggingTemp) return false;

        const target = this.tempDragTarget;
        const wasDrag = this.tempDragThresholdMet;
        const startPos = this.tempDragStartPos;

        // Remove visual dragging state
        if (target) {
            target.classList.remove('dragging');
        }

        // Reset threshold flag (but keep isDraggingTemp true until save completes)
        this.tempDragThresholdMet = false;

        if (!wasDrag) {
            // Was a click, not a drag - let click handler process it
            this.isDraggingTemp = false;
            this.tempDragTarget = null;
            this.tempDragStartMouse = null;
            this.tempDragStartPos = null;
            return false;
        }

        // Get final position from transform
        const transform = target.getAttribute('transform');
        const finalPos = this.parseTransform(transform);
        const furnitureId = parseInt(target.dataset.furnitureId);

        // Update local data cache IMMEDIATELY (true optimistic update)
        // This ensures any render during save uses the new position
        if (this.onPositionUpdate) {
            this.onPositionUpdate(furnitureId, finalPos.x, finalPos.y);
        }

        // Save to backend (keep isDraggingTemp true to block auto-refresh)
        try {
            await this.savePosition(furnitureId, finalPos.x, finalPos.y, finalPos.rotation || null);
        } catch (error) {
            // Revert cache and DOM to original position on error
            if (startPos) {
                // Revert cache
                if (this.onPositionUpdate) {
                    this.onPositionUpdate(furnitureId, startPos.x, startPos.y);
                }
                // Revert DOM
                const rotationStr = startPos.rotation ? ` rotate(${startPos.rotation})` : '';
                const revertTransform = `translate(${startPos.x}, ${startPos.y})${rotationStr}`;
                const freshTarget = document.querySelector(`[data-furniture-id="${furnitureId}"]`);
                if (freshTarget) {
                    freshTarget.setAttribute('transform', revertTransform);
                }
            }
        }

        // Clean up drag state after save completes
        this.isDraggingTemp = false;
        this.tempDragTarget = null;
        this.tempDragStartMouse = null;
        this.tempDragStartPos = null;

        return true; // Signal that drag was handled, suppress click
    }

    /**
     * Cancel any in-progress temp drag
     */
    cancelTempDrag() {
        if (!this.isDraggingTemp || !this.tempDragTarget) return;

        // Revert to original position
        if (this.tempDragStartPos) {
            const orig = this.tempDragStartPos;
            const rotationStr = orig.rotation ? ` rotate(${orig.rotation})` : '';
            this.tempDragTarget.setAttribute(
                'transform',
                `translate(${orig.x}, ${orig.y})${rotationStr}`
            );
        }

        this.tempDragTarget.classList.remove('dragging');
        this.isDraggingTemp = false;
        this.tempDragTarget = null;
        this.tempDragStartMouse = null;
        this.tempDragStartPos = null;
        this.tempDragThresholdMet = false;
    }

    /**
     * Clean up event listeners
     */
    destroy() {
        this.removeDragDrop();
        this.cancelTempDrag();
    }
}


// --- renderer.js ---
/**
 * Map Renderer Module
 * Handles SVG creation and rendering of zones, furniture, and decorative elements
 */


/**
 * SVG namespace for creating elements
 */
const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Create the main SVG element with layers
 * @param {HTMLElement} container - Container element
 * @param {Object} colors - Color configuration
 * @returns {Object} SVG element and layer references
 */
function createSVG(container, colors) {
    container.innerHTML = '';

    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('id', 'beach-map');
    svg.setAttribute('class', 'beach-map-svg');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    // Create defs for patterns and filters
    const defs = document.createElementNS(SVG_NS, 'defs');
    defs.innerHTML = `
        <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <filter id="reservation-highlight-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feColorMatrix type="matrix" values="0 0 0 0 0.83  0 0 0 0 0.69  0 0 0 0 0.22  0 0 0 1 0" result="gold"/>
            <feGaussianBlur in="gold" stdDeviation="6" result="glow"/>
            <feMerge>
                <feMergeNode in="glow"/>
                <feMergeNode in="glow"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <pattern id="zone-pattern" patternUnits="userSpaceOnUse" width="20" height="20">
            <rect width="20" height="20" fill="rgba(245, 230, 211, 0.3)"/>
            <circle cx="10" cy="10" r="1" fill="rgba(212, 175, 55, 0.2)"/>
        </pattern>
        <pattern id="pool-pattern" patternUnits="userSpaceOnUse" width="10" height="10">
            <rect width="10" height="10" fill="${colors.poolPrimary}"/>
            <rect x="0" y="0" width="5" height="5" fill="${colors.poolSecondary}" opacity="0.3"/>
            <rect x="5" y="5" width="5" height="5" fill="${colors.poolSecondary}" opacity="0.3"/>
        </pattern>
        <pattern id="blocked-stripes" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
            <rect width="4" height="8" fill="rgba(0,0,0,0.15)"/>
        </pattern>
    `;
    svg.appendChild(defs);

    // Create layers (order matters: zones -> decorative -> furniture -> selection)
    const zonesLayer = document.createElementNS(SVG_NS, 'g');
    zonesLayer.setAttribute('id', 'zones-layer');

    const decorativeLayer = document.createElementNS(SVG_NS, 'g');
    decorativeLayer.setAttribute('id', 'decorative-layer');

    const furnitureLayer = document.createElementNS(SVG_NS, 'g');
    furnitureLayer.setAttribute('id', 'furniture-layer');

    const selectionLayer = document.createElementNS(SVG_NS, 'g');
    selectionLayer.setAttribute('id', 'selection-layer');

    svg.appendChild(zonesLayer);
    svg.appendChild(decorativeLayer);
    svg.appendChild(furnitureLayer);
    svg.appendChild(selectionLayer);

    container.appendChild(svg);

    return {
        svg,
        zonesLayer,
        decorativeLayer,
        furnitureLayer,
        selectionLayer
    };
}

/**
 * Render zone backgrounds and labels
 * @param {SVGGElement} layer - Zones layer
 * @param {Object} data - Map data with zones and zone_bounds
 * @param {Object} colors - Color configuration
 */
function renderZones(layer, data, colors) {
    layer.innerHTML = '';

    if (!data.zones || !data.zone_bounds) return;

    data.zones.forEach(zone => {
        const bounds = data.zone_bounds[zone.id];
        if (!bounds) return;

        const group = document.createElementNS(SVG_NS, 'g');
        group.setAttribute('class', 'zone-group');
        group.setAttribute('data-zone-id', zone.id);

        // Zone background
        const rect = document.createElementNS(SVG_NS, 'rect');
        rect.setAttribute('x', bounds.x);
        rect.setAttribute('y', bounds.y);
        rect.setAttribute('width', bounds.width);
        rect.setAttribute('height', bounds.height);
        rect.setAttribute('fill', 'url(#zone-pattern)');
        rect.setAttribute('stroke', zone.color || '#D4AF37');
        rect.setAttribute('stroke-width', '2');
        rect.setAttribute('stroke-dasharray', '8 4');
        rect.setAttribute('rx', '8');

        // Zone label
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', bounds.x + 15);
        label.setAttribute('y', bounds.y + 25);
        label.setAttribute('class', 'zone-label');
        label.setAttribute('fill', colors.zoneLabel);
        label.setAttribute('font-size', '14');
        label.setAttribute('font-weight', '600');
        label.textContent = zone.name;

        group.appendChild(rect);
        group.appendChild(label);
        layer.appendChild(group);
    });
}

/**
 * Render decorative items (pools, umbrellas, etc.)
 * @param {SVGGElement} layer - Decorative layer
 * @param {Object} data - Map data
 * @param {Object} colors - Color configuration
 * @param {SVGSVGElement} svg - Main SVG element for pattern creation
 */
function renderDecorativeItems(layer, data, colors, svg) {
    layer.innerHTML = '';

    if (!data.furniture) return;

    const decorativeItems = data.furniture.filter(item => {
        const typeConfig = data.furniture_types[item.furniture_type] || {};
        return typeConfig.is_decorative === 1;
    });

    decorativeItems.forEach(item => {
        const group = createDecorativeElement(item, data, colors, svg);
        layer.appendChild(group);
    });
}

/**
 * Create a single decorative element
 */
function createDecorativeElement(item, data, colors, svg) {
    const group = document.createElementNS(SVG_NS, 'g');
    group.setAttribute('class', 'decorative-item');
    group.setAttribute('data-furniture-id', item.id);
    group.setAttribute('data-furniture-type', item.furniture_type);

    const posX = item.position_x ?? 0;
    const posY = item.position_y ?? 0;
    const rotation = item.rotation ?? 0;
    group.setAttribute('transform', `translate(${posX}, ${posY}) rotate(${rotation})`);

    const typeConfig = data.furniture_types[item.furniture_type] || {};
    const width = item.width || typeConfig.default_width || 100;
    const height = item.height || typeConfig.default_height || 60;

    let fillColor, strokeColor, fillPattern;

    if (item.furniture_type === 'piscina') {
        const poolFill = typeConfig.fill_color || colors.poolPrimary;
        const poolStroke = typeConfig.stroke_color || colors.poolSecondary;
        fillPattern = getPoolPattern(svg, item.id, poolFill, poolStroke);
        strokeColor = poolStroke;
    } else {
        fillColor = item.fill_color || typeConfig.fill_color || '#E8E8E8';
        strokeColor = typeConfig.stroke_color || '#CCCCCC';
    }

    const shape = createShape(typeConfig.map_shape || 'rounded_rect', width, height,
        fillPattern || fillColor, strokeColor);
    shape.setAttribute('stroke-width', '3');
    shape.setAttribute('opacity', '0.9');
    group.appendChild(shape);

    // Add label for non-pool decorative items
    if (item.furniture_type !== 'piscina') {
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', width / 2);
        label.setAttribute('y', height / 2);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('dominant-baseline', 'middle');
        label.setAttribute('fill', '#666666');
        label.setAttribute('font-size', '11');
        label.setAttribute('font-style', 'italic');
        label.setAttribute('pointer-events', 'none');
        label.textContent = item.number;
        group.appendChild(label);
    }

    return group;
}

/**
 * Render reservable furniture items
 * @param {SVGGElement} layer - Furniture layer
 * @param {Object} data - Map data
 * @param {Set} selectedFurniture - Set of selected furniture IDs
 * @param {Object} colors - Color configuration
 * @param {Function} onFurnitureClick - Click handler
 * @param {Object} tooltipManager - Tooltip manager instance
 * @param {Function} onFurnitureContextMenu - Right-click context menu handler
 */
function renderFurniture(layer, data, selectedFurniture, colors, onFurnitureClick, tooltipManager, onFurnitureContextMenu, highlightedFurniture = new Set(), hoveredReservationFurniture = new Set()) {
    layer.innerHTML = '';

    if (!data.furniture) return;

    const reservableFurniture = data.furniture.filter(item => {
        const typeConfig = data.furniture_types[item.furniture_type] || {};
        return typeConfig.is_decorative !== 1;
    });

    reservableFurniture.forEach(item => {
        const group = createFurnitureElement(item, data, selectedFurniture, colors, onFurnitureClick, tooltipManager, onFurnitureContextMenu, highlightedFurniture, hoveredReservationFurniture);
        layer.appendChild(group);
    });
}

/**
 * Apply gold highlight to all furniture sharing the same reservation on hover.
 * Mutates hoveredReservationFurniture Set and applies DOM styling directly.
 */
function applyReservationHoverHighlight(furnitureId, data, hoveredSet, selectedSet, highlightedSet) {
    const availability = data.availability[furnitureId];
    if (!availability || !availability.reservation_id) return;

    const reservationId = availability.reservation_id;

    // Find all furniture with the same reservation
    const siblingIds = [];
    for (const [id, avail] of Object.entries(data.availability)) {
        if (avail.reservation_id === reservationId) {
            siblingIds.push(Number(id));
        }
    }

    // Update the shared Set (survives re-renders)
    siblingIds.forEach(id => hoveredSet.add(id));

    // Apply DOM styling directly (instant, no re-render)
    siblingIds.forEach(id => {
        if (selectedSet.has(id) || highlightedSet.has(id)) return;
        const el = document.querySelector(`[data-furniture-id="${id}"]`);
        if (!el) return;
        el.classList.add('reservation-glow');
        el.setAttribute('filter', 'url(#reservation-highlight-glow)');
        const shape = el.querySelector('rect, circle, ellipse');
        if (shape) {
            shape.setAttribute('stroke', '#D4AF37');
            shape.setAttribute('stroke-width', '4');
        }
    });
}

/**
 * Compute the correct stroke color for an occupied furniture item.
 * Used to restore stroke after hover highlight is removed.
 */
function getOccupiedStrokeColor(furnitureId, data, colors) {
    const availability = data.availability[furnitureId];
    const state = availability ? availability.state : null;

    if (state && data.state_colors[state]) {
        return darkenColor(data.state_colors[state], 30);
    }

    const item = data.furniture.find(f => f.id === furnitureId);
    if (item) {
        const typeConfig = data.furniture_types[item.furniture_type] || {};
        return typeConfig.stroke_color || '#654321';
    }

    return '#654321';
}

/**
 * Clear hover highlight from all furniture in the hovered Set.
 * Preserves panel highlights (highlightedFurniture).
 * Computes correct stroke color from data instead of relying on stored state.
 */
function clearReservationHoverHighlight(hoveredSet, highlightedSet, data, colors) {
    if (hoveredSet.size === 0) return;

    hoveredSet.forEach(id => {
        if (highlightedSet.has(id)) return;
        const el = document.querySelector(`[data-furniture-id="${id}"]`);
        if (!el) return;
        el.classList.remove('reservation-glow');
        el.removeAttribute('filter');
        const shape = el.querySelector('rect, circle, ellipse');
        if (shape) {
            shape.setAttribute('stroke', getOccupiedStrokeColor(id, data, colors));
            shape.setAttribute('stroke-width', '2');
        }
    });

    hoveredSet.clear();
}

/**
 * Create a single furniture element
 */
function createFurnitureElement(item, data, selectedFurniture, colors, onFurnitureClick, tooltipManager, onFurnitureContextMenu, highlightedFurniture = new Set(), hoveredReservationFurniture = new Set()) {
    const group = document.createElementNS(SVG_NS, 'g');
    group.setAttribute('class', 'furniture-item');
    group.setAttribute('data-furniture-id', item.id);

    const posX = item.position_x ?? 0;
    const posY = item.position_y ?? 0;
    const rotation = item.rotation ?? 0;
    group.setAttribute('transform', `translate(${posX}, ${posY}) rotate(${rotation})`);
    group.style.cursor = 'pointer';

    const typeConfig = data.furniture_types[item.furniture_type] || {};
    const availability = data.availability[item.id];
    const isAvailable = !availability || availability.available;
    const state = availability ? availability.state : null;

    let fillColor, strokeColor;
    if (isAvailable) {
        fillColor = colors.availableFill;
        strokeColor = colors.availableStroke;
    } else if (state && data.state_colors[state]) {
        fillColor = data.state_colors[state];
        strokeColor = darkenColor(fillColor, 30);
    } else {
        fillColor = typeConfig.fill_color || '#A0522D';
        strokeColor = typeConfig.stroke_color || '#654321';
    }

    // Check if blocked
    const blockInfo = data.blocks && data.blocks[item.id];
    if (blockInfo) {
        fillColor = blockInfo.color || '#9CA3AF';
        strokeColor = darkenColor(fillColor, 30);
        group.classList.add('blocked');
        group.setAttribute('data-block-type', blockInfo.block_type);
        group.style.cursor = 'not-allowed';
    }

    // Check if temporary furniture
    if (item.is_temporary) {
        group.classList.add('temporary');
        group.setAttribute('data-temp-start', item.temp_start_date || '');
        group.setAttribute('data-temp-end', item.temp_end_date || '');
        // Use sky blue fill for available temp furniture (not reserved, not blocked)
        if (isAvailable && !blockInfo) {
            fillColor = '#E0F2FE';
            strokeColor = '#0EA5E9';
        }
        // Set move cursor for draggable temp furniture (not blocked)
        if (!blockInfo) {
            group.style.cursor = 'move';
        }
    }

    // Check if selected (selection overrides blocked visual for highlighting)
    if (selectedFurniture.has(item.id)) {
        fillColor = colors.selectedFill;
        strokeColor = colors.selectedStroke;
        group.setAttribute('filter', 'url(#selected-glow)');
    }

    // Check if highlighted (reservation panel or hover) — gold stroke
    const isHighlighted = (highlightedFurniture.has(item.id) || hoveredReservationFurniture.has(item.id))
        && !selectedFurniture.has(item.id);
    if (isHighlighted) {
        strokeColor = '#D4AF37';
        group.classList.add('reservation-glow');
        group.setAttribute('filter', 'url(#reservation-highlight-glow)');
    }

    // Create shape
    const width = item.width || typeConfig.default_width || 60;
    const height = item.height || typeConfig.default_height || 40;
    const shape = createShape(typeConfig.map_shape || 'rounded_rect', width, height, fillColor, strokeColor);
    if (isHighlighted) {
        shape.setAttribute('stroke-width', '4');
    }
    group.appendChild(shape);

    // Add stripes overlay for blocked furniture
    if (blockInfo && !selectedFurniture.has(item.id)) {
        const stripesOverlay = document.createElementNS(SVG_NS, 'rect');
        stripesOverlay.setAttribute('x', '2');
        stripesOverlay.setAttribute('y', '2');
        stripesOverlay.setAttribute('width', width - 4);
        stripesOverlay.setAttribute('height', height - 4);
        stripesOverlay.setAttribute('fill', 'url(#blocked-stripes)');
        stripesOverlay.setAttribute('rx', '5');
        stripesOverlay.setAttribute('ry', '5');
        stripesOverlay.setAttribute('pointer-events', 'none');
        group.appendChild(stripesOverlay);
    }

    // Add labels
    if (blockInfo) {
        // Blocked furniture: show icon + furniture number
        const blockIcons = {
            'maintenance': '🔧',
            'vip_hold': '⭐',
            'event': '📅',
            'other': '🚫'
        };
        const icon = blockIcons[blockInfo.block_type] || '🚫';

        const iconLabel = document.createElementNS(SVG_NS, 'text');
        iconLabel.setAttribute('x', width / 2);
        iconLabel.setAttribute('y', height / 2 - 4);
        iconLabel.setAttribute('text-anchor', 'middle');
        iconLabel.setAttribute('dominant-baseline', 'middle');
        iconLabel.setAttribute('font-size', '12');
        iconLabel.setAttribute('pointer-events', 'none');
        iconLabel.textContent = icon;
        group.appendChild(iconLabel);

        const numberLabel = document.createElementNS(SVG_NS, 'text');
        numberLabel.setAttribute('x', width / 2);
        numberLabel.setAttribute('y', height / 2 + 10);
        numberLabel.setAttribute('text-anchor', 'middle');
        numberLabel.setAttribute('dominant-baseline', 'middle');
        numberLabel.setAttribute('fill', getContrastColor(fillColor, colors));
        numberLabel.setAttribute('font-size', '9');
        numberLabel.setAttribute('font-weight', '600');
        numberLabel.setAttribute('pointer-events', 'none');
        numberLabel.textContent = item.number;
        group.appendChild(numberLabel);
    } else if (!isAvailable && availability) {
        const customerLabel = tooltipManager.getCustomerLabel(availability);

        const primaryLabel = document.createElementNS(SVG_NS, 'text');
        primaryLabel.setAttribute('x', width / 2);
        primaryLabel.setAttribute('y', height / 2 - 4);
        primaryLabel.setAttribute('text-anchor', 'middle');
        primaryLabel.setAttribute('dominant-baseline', 'middle');
        primaryLabel.setAttribute('fill', getContrastColor(fillColor, colors));
        primaryLabel.setAttribute('font-size', '11');
        primaryLabel.setAttribute('font-weight', '600');
        primaryLabel.setAttribute('pointer-events', 'none');
        primaryLabel.textContent = customerLabel;
        group.appendChild(primaryLabel);

        const secondaryLabel = document.createElementNS(SVG_NS, 'text');
        secondaryLabel.setAttribute('x', width / 2);
        secondaryLabel.setAttribute('y', height / 2 + 8);
        secondaryLabel.setAttribute('text-anchor', 'middle');
        secondaryLabel.setAttribute('dominant-baseline', 'middle');
        secondaryLabel.setAttribute('fill', getContrastColor(fillColor, colors));
        secondaryLabel.setAttribute('font-size', '8');
        secondaryLabel.setAttribute('font-weight', '400');
        secondaryLabel.setAttribute('pointer-events', 'none');
        secondaryLabel.setAttribute('opacity', '0.8');
        secondaryLabel.textContent = item.number;
        group.appendChild(secondaryLabel);
    } else {
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', width / 2);
        label.setAttribute('y', height / 2);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('dominant-baseline', 'middle');
        label.setAttribute('fill', getContrastColor(fillColor, colors));
        label.setAttribute('font-size', '12');
        label.setAttribute('font-weight', '600');
        label.setAttribute('pointer-events', 'none');
        label.textContent = item.number;
        group.appendChild(label);
    }

    // Lock icon for locked furniture (top-right corner)
    if (availability && availability.is_furniture_locked) {
        const lockIcon = document.createElementNS(SVG_NS, 'text');
        lockIcon.setAttribute('x', width - 8);
        lockIcon.setAttribute('y', 12);
        lockIcon.setAttribute('text-anchor', 'middle');
        lockIcon.setAttribute('dominant-baseline', 'middle');
        lockIcon.setAttribute('font-size', '10');
        lockIcon.setAttribute('pointer-events', 'none');
        lockIcon.setAttribute('class', 'furniture-lock-icon');
        lockIcon.textContent = '🔒';
        group.appendChild(lockIcon);
    }

    // Event listeners
    group.addEventListener('click', (e) => onFurnitureClick(e, item));

    // Right-click context menu
    if (onFurnitureContextMenu) {
        group.addEventListener('contextmenu', (e) => onFurnitureContextMenu(e, item));
    }

    // Hover handlers for tooltip and reservation highlight
    if (blockInfo) {
        // Show block info on hover
        group.addEventListener('mouseenter', (e) => tooltipManager.showBlock(e, blockInfo, item.number));
        group.addEventListener('mouseleave', () => tooltipManager.hide());
        group.addEventListener('mousemove', (e) => tooltipManager.move(e));
    } else if (!isAvailable && availability && availability.customer_name) {
        group.addEventListener('mouseenter', (e) => {
            tooltipManager.show(e, availability);
            applyReservationHoverHighlight(item.id, data, hoveredReservationFurniture, selectedFurniture, highlightedFurniture);
        });
        group.addEventListener('mouseleave', () => {
            tooltipManager.hide();
            clearReservationHoverHighlight(hoveredReservationFurniture, highlightedFurniture, data, colors);
        });
        group.addEventListener('mousemove', (e) => tooltipManager.move(e));
    }

    return group;
}

/**
 * Create an SVG shape element
 * @param {string} shapeType - Shape type (circle, ellipse, rectangle, rounded_rect)
 * @param {number} width - Shape width
 * @param {number} height - Shape height
 * @param {string} fillColor - Fill color or pattern URL
 * @param {string} strokeColor - Stroke color
 * @returns {SVGElement} Shape element
 */
function createShape(shapeType, width, height, fillColor, strokeColor) {
    const strokeWidth = 2;
    let shape;

    switch (shapeType) {
        case 'circle':
            shape = document.createElementNS(SVG_NS, 'circle');
            const radius = Math.min(width, height) / 2 - strokeWidth;
            shape.setAttribute('cx', width / 2);
            shape.setAttribute('cy', height / 2);
            shape.setAttribute('r', radius);
            break;

        case 'ellipse':
            shape = document.createElementNS(SVG_NS, 'ellipse');
            shape.setAttribute('cx', width / 2);
            shape.setAttribute('cy', height / 2);
            shape.setAttribute('rx', width / 2 - strokeWidth);
            shape.setAttribute('ry', height / 2 - strokeWidth);
            break;

        case 'rectangle':
        case 'rounded_rect':
        default:
            shape = document.createElementNS(SVG_NS, 'rect');
            shape.setAttribute('x', strokeWidth);
            shape.setAttribute('y', strokeWidth);
            shape.setAttribute('width', width - 2 * strokeWidth);
            shape.setAttribute('height', height - 2 * strokeWidth);
            if (shapeType === 'rounded_rect') {
                shape.setAttribute('rx', '5');
                shape.setAttribute('ry', '5');
            }
            break;
    }

    shape.setAttribute('fill', fillColor);
    shape.setAttribute('stroke', strokeColor);
    shape.setAttribute('stroke-width', strokeWidth);

    return shape;
}

/**
 * Get or create a pool pattern for a specific item
 * @param {SVGSVGElement} svg - Main SVG element
 * @param {number} itemId - Furniture item ID
 * @param {string} fillColor - Primary pool color
 * @param {string} strokeColor - Secondary pool color
 * @returns {string} Pattern URL reference
 */
function getPoolPattern(svg, itemId, fillColor, strokeColor) {
    const patternId = `pool-pattern-${itemId}`;

    let pattern = svg.querySelector(`#${patternId}`);
    if (!pattern) {
        const defs = svg.querySelector('defs');
        pattern = document.createElementNS(SVG_NS, 'pattern');
        pattern.setAttribute('id', patternId);
        pattern.setAttribute('patternUnits', 'userSpaceOnUse');
        pattern.setAttribute('width', '10');
        pattern.setAttribute('height', '10');
        pattern.innerHTML = `
            <rect width="10" height="10" fill="${fillColor}"/>
            <rect x="0" y="0" width="5" height="5" fill="${strokeColor}" opacity="0.3"/>
            <rect x="5" y="5" width="5" height="5" fill="${strokeColor}" opacity="0.3"/>
        `;
        defs.appendChild(pattern);
    }
    return `url(#${patternId})`;
}

/**
 * Update the legend with state colors
 * @param {Object} data - Map data with states
 * @param {Object} colors - Color configuration
 */
function updateLegend(data, colors) {
    const legend = document.getElementById('map-legend');
    if (!legend || !data.states) return;

    const safeFill = sanitizeColor(colors.availableFill) || '#F5E6D3';
    const safeStroke = sanitizeColor(colors.availableStroke) || '#D4AF37';

    let html = '<div class="legend-items d-flex flex-wrap gap-2">';

    // Available state
    html += `
        <div class="legend-item d-flex align-items-center">
            <span class="legend-color" style="background-color: ${safeFill}; border: 2px solid ${safeStroke};"></span>
            <span class="ms-1">Disponible</span>
        </div>
    `;

    // State colors from database
    data.states.forEach(state => {
        if (state.active) {
            const stateColor = sanitizeColor(state.color) || '#999';
            html += `
                <div class="legend-item d-flex align-items-center">
                    <span class="legend-color" style="background-color: ${stateColor};"></span>
                    <span class="ms-1">${escapeHtml(state.name)}</span>
                </div>
            `;
        }
    });

    html += '</div>';
    legend.innerHTML = html;
}


// --- pinch-zoom.js ---
/**
 * Pinch Zoom Handler
 * Handles 2-finger pinch gestures for zoom on mobile devices.
 *
 * This handler works alongside TouchHandler (which handles single-touch)
 * and uses the existing zoom API to avoid conflicts.
 */
class PinchZoomHandler {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            minZoom: options.minZoom || 0.1,
            maxZoom: options.maxZoom || 3,
            ...options
        };

        // Callbacks for zoom integration
        this.getZoom = options.getZoom || (() => 1);
        this.setZoom = options.setZoom || (() => {});
        this.getMapWrapper = options.getMapWrapper || (() => null);
        this.getSvg = options.getSvg || (() => null);

        // Pinch state
        this.isPinching = false;
        this.pinchStartDistance = 0;
        this.pinchStartZoom = 1;
        this.pinchCenter = { x: 0, y: 0 };

        // Bind methods
        this.handleTouchStart = this.handleTouchStart.bind(this);
        this.handleTouchMove = this.handleTouchMove.bind(this);
        this.handleTouchEnd = this.handleTouchEnd.bind(this);

        this.bindEvents();
    }

    bindEvents() {
        this.container.addEventListener('touchstart', this.handleTouchStart, { passive: false });
        this.container.addEventListener('touchmove', this.handleTouchMove, { passive: false });
        this.container.addEventListener('touchend', this.handleTouchEnd, { passive: false });
        this.container.addEventListener('touchcancel', this.handleTouchEnd, { passive: false });
    }

    /**
     * Calculate distance between two touch points
     */
    getDistance(touch1, touch2) {
        const dx = touch2.clientX - touch1.clientX;
        const dy = touch2.clientY - touch1.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    /**
     * Calculate midpoint between two touch points
     */
    getMidpoint(touch1, touch2) {
        return {
            x: (touch1.clientX + touch2.clientX) / 2,
            y: (touch1.clientY + touch2.clientY) / 2
        };
    }

    handleTouchStart(e) {
        if (e.touches.length === 2) {
            // Prevent native gestures when pinching
            e.preventDefault();

            this.isPinching = true;
            this.pinchStartDistance = this.getDistance(e.touches[0], e.touches[1]);
            this.pinchStartZoom = this.getZoom();
            this.pinchCenter = this.getMidpoint(e.touches[0], e.touches[1]);
        }
    }

    handleTouchMove(e) {
        if (!this.isPinching || e.touches.length !== 2) return;

        e.preventDefault();

        const currentDistance = this.getDistance(e.touches[0], e.touches[1]);
        const currentCenter = this.getMidpoint(e.touches[0], e.touches[1]);

        // Calculate new zoom based on distance ratio
        const zoomRatio = currentDistance / this.pinchStartDistance;
        let newZoom = this.pinchStartZoom * zoomRatio;

        // Clamp to limits
        newZoom = Math.max(this.options.minZoom, Math.min(this.options.maxZoom, newZoom));

        // Apply zoom and adjust scroll to keep pinch center stable
        this.applyZoomToPoint(newZoom, currentCenter);
    }

    handleTouchEnd(e) {
        if (e.touches.length < 2) {
            this.isPinching = false;
        }
    }

    /**
     * Apply zoom centered on a specific point (keeps point under fingers)
     * Adapted from the wheel zoom logic in map.html
     */
    applyZoomToPoint(newZoom, point) {
        const svg = this.getSvg();
        const wrapper = this.getMapWrapper();
        if (!svg || !wrapper) return;

        const currentZoom = this.getZoom();
        if (Math.abs(newZoom - currentZoom) < 0.001) return;

        const svgRect = svg.getBoundingClientRect();
        const wrapperRect = wrapper.getBoundingClientRect();

        // Point position in wrapper viewport
        const pointXInWrapper = point.x - wrapperRect.left;
        const pointYInWrapper = point.y - wrapperRect.top;

        // Convert to canvas coordinates (before zoom change)
        const canvasX = Math.max(0, (point.x - svgRect.left)) / currentZoom;
        const canvasY = Math.max(0, (point.y - svgRect.top)) / currentZoom;

        // Apply zoom through the standard API
        this.setZoom(newZoom);

        // Adjust scroll to keep point under fingers
        requestAnimationFrame(() => {
            const newSvgRect = svg.getBoundingClientRect();
            const padding = 10;

            // Calculate centering offset (for when SVG is smaller than viewport)
            const availableWidth = wrapper.clientWidth - padding * 2;
            const availableHeight = wrapper.clientHeight - padding * 2;
            const newCenterOffsetX = Math.max(0, (availableWidth - newSvgRect.width) / 2);
            const newCenterOffsetY = Math.max(0, (availableHeight - newSvgRect.height) / 2);

            // New point position in zoomed SVG
            const newPointXInSvg = canvasX * newZoom;
            const newPointYInSvg = canvasY * newZoom;

            // Target scroll position
            const targetScrollX = padding + newCenterOffsetX + newPointXInSvg - pointXInWrapper;
            const targetScrollY = padding + newCenterOffsetY + newPointYInSvg - pointYInWrapper;

            wrapper.scrollLeft = Math.max(0, targetScrollX);
            wrapper.scrollTop = Math.max(0, targetScrollY);
        });
    }

    destroy() {
        this.container.removeEventListener('touchstart', this.handleTouchStart);
        this.container.removeEventListener('touchmove', this.handleTouchMove);
        this.container.removeEventListener('touchend', this.handleTouchEnd);
        this.container.removeEventListener('touchcancel', this.handleTouchEnd);
    }
}

// Export for non-module usage
window.PinchZoomHandler = PinchZoomHandler;


// --- BeachMap.js ---
/**
 * Beach Map Interactive Controller
 * Main class that coordinates all map modules
 */


/**
 * Main BeachMap class
 */
class BeachMap {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container #${containerId} not found`);
        }

        // Load CSS variables for configurable values
        const cssVars = loadCSSVariables();

        // Configuration (with CSS variable fallbacks)
        this.options = {
            apiUrl: '/beach/api/map/data',
            autoRefreshInterval: cssVars.autoRefreshMs,
            enableDragDrop: false,
            enableZoom: true,
            minZoom: cssVars.minZoom,
            maxZoom: cssVars.maxZoom,
            snapToGrid: cssVars.snapGrid,
            ...options
        };

        // Store colors from CSS variables
        this.colors = cssVars.colors;

        // State
        this.currentDate = this.options.initialDate || new Date().toISOString().split('T')[0];
        this.data = null;
        this.autoRefreshTimer = null;

        // DOM elements
        this.svg = null;
        this.zonesLayer = null;
        this.decorativeLayer = null;
        this.furnitureLayer = null;
        this.selectionLayer = null;

        // Highlighted furniture (reservation panel)
        this.highlightedFurniture = new Set();

        // Hovered reservation furniture (hover on map)
        this.hoveredReservationFurniture = new Set();

        // Initialize managers
        this.selection = new SelectionManager();
        this.navigation = new NavigationManager({
            minZoom: this.options.minZoom,
            maxZoom: this.options.maxZoom
        });
        this.interaction = new InteractionManager({
            snapToGrid: this.options.snapToGrid,
            // Optimistic update: sync local data cache when position changes
            onPositionUpdate: (furnitureId, x, y) => {
                const furniture = this.data?.furniture?.find(f => f.id === furnitureId);
                if (furniture) {
                    furniture.position_x = x;
                    furniture.position_y = y;
                }
            }
        });
        this.tooltipManager = new TooltipManager(this.container, this.colors);

        // Initialize Modal State Manager
        if (window.modalStateManager) {
            window.modalStateManager.initialize({
                interactionManager: this.interaction,
                selectionManager: this.selection
            });
            console.log('[BeachMap] Modal State Manager initialized');
        }

        // Offline manager
        this.offlineManager = null;
        this.isOfflineMode = false;

        // Context menu manager (initialized after container is ready)
        this.contextMenu = new ContextMenuManager({
            container: this.container,
            getData: () => ({ ...this.data, beachMap: this }),
            onBlock: (furnitureIds, furnitureNumbers) => {
                if (this.callbacks.onBlockRequest) {
                    // Context menu now passes arrays directly
                    this.callbacks.onBlockRequest(furnitureIds, furnitureNumbers);
                }
            },
            onUnblock: (furnitureIds, furnitureNumbers) => {
                if (this.callbacks.onUnblockRequest) {
                    // Context menu now passes arrays directly
                    this.callbacks.onUnblockRequest(furnitureIds, furnitureNumbers);
                }
            },
            onAddTemporary: (x, y, zoneId) => {
                if (this.callbacks.onAddTemporaryRequest) {
                    this.callbacks.onAddTemporaryRequest(x, y, zoneId);
                }
            },
            onDeleteTemporary: (furnitureIds, furnitureNumbers) => {
                if (this.callbacks.onDeleteTemporaryRequest) {
                    // Context menu now passes arrays directly
                    this.callbacks.onDeleteTemporaryRequest(furnitureIds, furnitureNumbers);
                }
            },
            getZoneAtPosition: (x, y) => this.getZoneAtPosition(x, y)
        });

        // Event callbacks
        this.callbacks = {
            onSelect: null,
            onDeselect: null,
            onDateChange: null,
            onFurnitureClick: null,
            onBlockRequest: null,
            onUnblockRequest: null,
            onAddTemporaryRequest: null,
            onDeleteTemporaryRequest: null,
            onError: null,
            onRender: null
        };

        // Wire up selection callbacks
        this.selection.on('onSelect', (id) => {
            if (this.callbacks.onSelect) this.callbacks.onSelect(id);
        });
        this.selection.on('onDeselect', (id) => {
            if (this.callbacks.onDeselect) this.callbacks.onDeselect(id);
        });

        // Wire up navigation callbacks
        this.navigation.on('onDateChange', (date) => {
            if (this.callbacks.onDateChange) this.callbacks.onDateChange(date);
        });
        this.navigation.on('onZoomChange', () => {
            this.applyZoom();
            this.interaction.setZoom(this.navigation.getZoom());
        });

        // Click suppression for drag-end
        this._suppressNextClick = false;

        // Bind methods
        this.handleFurnitureClick = this.handleFurnitureClick.bind(this);
        this.handleFurnitureContextMenu = this.handleFurnitureContextMenu.bind(this);
        this.handleTempFurnitureMouseDown = this.handleTempFurnitureMouseDown.bind(this);
        this.handleTempFurnitureMouseMove = this.handleTempFurnitureMouseMove.bind(this);
        this.handleTempFurnitureMouseUp = this.handleTempFurnitureMouseUp.bind(this);
        // Touch handlers for mobile temp furniture drag
        this.handleTempFurnitureTouchStart = this.handleTempFurnitureTouchStart.bind(this);
        this.handleTempFurnitureTouchMove = this.handleTempFurnitureTouchMove.bind(this);
        this.handleTempFurnitureTouchEnd = this.handleTempFurnitureTouchEnd.bind(this);

        // Initialize
        this.init();
    }

    async init() {
        this.createSVG();
        this.setupEventListeners();
        await this.loadData();
        this.render();

        // Initialize offline functionality
        await this.initOffline();
    }

    /**
     * Initialize offline functionality
     */
    async initOffline() {
        // Get UI elements
        const banner = document.getElementById('offline-banner');
        const syncButton = document.getElementById('sync-button');
        const syncButtonText = document.getElementById('sync-button-text');
        const offlineSyncTime = document.getElementById('offline-sync-time');

        if (!banner || !syncButton) {
            console.warn('Offline UI elements not found');
            return;
        }

        this.offlineManager = new OfflineManager({
            apiUrl: this.options.apiUrl,

            onOffline: () => {
                this.isOfflineMode = true;
                document.body.classList.add('offline-mode');
                banner.classList.add('visible');
                offlineSyncTime.textContent = this.offlineManager.getLastSyncTimeFormatted();

                syncButton.className = 'sync-button offline';
                syncButton.querySelector('i').className = 'fas fa-times';
                syncButtonText.textContent = 'Sin conexion';

                showToast('Modo offline activado', 'warning');
            },

            onOnline: () => {
                this.isOfflineMode = false;
                document.body.classList.remove('offline-mode');
                banner.classList.remove('visible');

                showToast('Conexion restaurada', 'success');
            },

            onSyncStart: () => {
                syncButton.className = 'sync-button syncing';
                syncButton.querySelector('i').className = 'fas fa-sync-alt';
                syncButtonText.textContent = 'Sincronizando...';
            },

            onSyncComplete: (data) => {
                syncButton.className = 'sync-button synced';
                syncButton.querySelector('i').className = 'fas fa-check';
                syncButtonText.textContent = `Sincronizado ${this.offlineManager.getLastSyncTimeFormatted()}`;

                // Update map with fresh data if online
                if (!this.isOfflineMode && data) {
                    this.data = data;
                    this.render();
                }
            },

            onSyncError: (error) => {
                syncButton.className = 'sync-button stale';
                syncButton.querySelector('i').className = 'fas fa-download';
                syncButtonText.textContent = 'Descargar Dia';
            }
        });

        // Manual sync button click
        syncButton.addEventListener('click', async () => {
            if (this.offlineManager.isOnline() && !syncButton.classList.contains('syncing')) {
                await this.offlineManager.sync();
            } else if (!this.offlineManager.isOnline()) {
                showToast('Funcion no disponible en modo offline', 'warning');
            }
        });

        // Initialize with current date
        await this.offlineManager.init(this.currentDate);

        // Update sync button initial state
        if (this.offlineManager.getLastSyncTime()) {
            syncButton.className = 'sync-button synced';
            syncButtonText.textContent = `Sincronizado ${this.offlineManager.getLastSyncTimeFormatted()}`;
        } else {
            syncButton.className = 'sync-button stale';
            syncButton.querySelector('i').className = 'fas fa-download';
            syncButtonText.textContent = 'Descargar Dia';
        }
    }

    createSVG() {
        const result = createSVG(this.container, this.colors);
        this.svg = result.svg;
        this.zonesLayer = result.zonesLayer;
        this.decorativeLayer = result.decorativeLayer;
        this.furnitureLayer = result.furnitureLayer;
        this.selectionLayer = result.selectionLayer;
    }

    setupEventListeners() {
        // Keyboard navigation
        this.navigation.setupKeyboard({
            onEscape: () => this.clearSelection(),
            onPrevDay: () => this.goToPreviousDay(),
            onNextDay: () => this.goToNextDay(),
            onZoom: () => this.applyZoom()
        });

        // SVG click for deselection
        this.svg.addEventListener('click', (e) => {
            if (e.target === this.svg || e.target.closest('#zones-layer')) {
                this.clearSelection();
            }
        });

        // SVG right-click for empty space context menu
        this.svg.addEventListener('contextmenu', (e) => {
            // Only handle if click is on empty space (not furniture)
            const furnitureGroup = e.target.closest('.furniture-item');
            if (!furnitureGroup) {
                // Convert screen coordinates to SVG coordinates
                const svgPoint = this.screenToSVGCoordinates(e.clientX, e.clientY);
                const zone = this.getZoneAtPosition(svgPoint.x, svgPoint.y);
                this.contextMenu.showEmptySpaceMenu(e, svgPoint.x, svgPoint.y, zone);
            }
        });

        // Temporary furniture drag handling (always enabled)
        this.svg.addEventListener('mousedown', this.handleTempFurnitureMouseDown);
        document.addEventListener('mousemove', this.handleTempFurnitureMouseMove);
        document.addEventListener('mouseup', this.handleTempFurnitureMouseUp);

        // Touch handlers for mobile temp furniture drag
        this.svg.addEventListener('touchstart', this.handleTempFurnitureTouchStart, { passive: false });
        document.addEventListener('touchmove', this.handleTempFurnitureTouchMove, { passive: false });
        document.addEventListener('touchend', this.handleTempFurnitureTouchEnd, { passive: false });
        document.addEventListener('touchcancel', this.handleTempFurnitureTouchEnd, { passive: false });
    }

    /**
     * Convert screen coordinates to SVG coordinates
     * @param {number} clientX - Screen X coordinate
     * @param {number} clientY - Screen Y coordinate
     * @returns {Object} SVG coordinates {x, y}
     */
    screenToSVGCoordinates(clientX, clientY) {
        const pt = this.svg.createSVGPoint();
        pt.x = clientX;
        pt.y = clientY;
        const svgPoint = pt.matrixTransform(this.svg.getScreenCTM().inverse());
        return { x: svgPoint.x, y: svgPoint.y };
    }

    /**
     * Get zone at SVG coordinates
     * @param {number} x - SVG X coordinate
     * @param {number} y - SVG Y coordinate
     * @returns {Object|null} Zone data or null
     */
    getZoneAtPosition(x, y) {
        if (!this.data?.zone_bounds) return null;

        for (const zone of (this.data.zones || [])) {
            const bounds = this.data.zone_bounds[zone.id];
            if (bounds &&
                x >= bounds.x && x <= bounds.x + bounds.width &&
                y >= bounds.y && y <= bounds.y + bounds.height) {
                return zone;
            }
        }
        return null;
    }

    async loadData() {
        try {
            const response = await fetch(`${this.options.apiUrl}?date=${this.currentDate}`);
            if (!response.ok) throw new Error('Error loading map data');

            const result = await response.json();

            if (result.success) {
                this.data = result;

                // Apply map config
                if (result.map_config) {
                    this.options.autoRefreshInterval = result.map_config.auto_refresh_ms || this.options.autoRefreshInterval;
                    this.options.minZoom = result.map_config.min_zoom || this.options.minZoom;
                    this.options.maxZoom = result.map_config.max_zoom || this.options.maxZoom;
                    this.options.snapToGrid = result.map_config.snap_grid || this.options.snapToGrid;

                    // Update managers with new config
                    this.navigation.updateOptions({
                        minZoom: this.options.minZoom,
                        maxZoom: this.options.maxZoom
                    });
                    this.interaction.updateOptions({
                        snapToGrid: this.options.snapToGrid
                    });
                }
            }

            return true;
        } catch (error) {
            console.warn('Failed to load from server, trying cache:', error);

            // Try to load from cache when offline
            if (this.offlineManager) {
                const cachedData = await this.offlineManager.loadCachedData();
                if (cachedData) {
                    this.data = cachedData;
                    showToast('Mostrando datos en cache', 'info');
                    return true;
                }
            }

            console.error('No cached data available');
            showToast('Error al cargar datos del mapa', 'error');
            return false;
        }
    }

    render() {
        if (!this.data) return;

        // Preserve scroll position before re-rendering
        const wrapper = this.container.closest('.map-canvas-wrapper');
        const scrollLeft = wrapper?.scrollLeft || 0;
        const scrollTop = wrapper?.scrollTop || 0;

        const { width, height } = this.data.map_dimensions;
        this.svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        renderZones(this.zonesLayer, this.data, this.colors);
        renderDecorativeItems(this.decorativeLayer, this.data, this.colors, this.svg);
        renderFurniture(
            this.furnitureLayer,
            this.data,
            this.selection.getSelectedSet(),
            this.colors,
            this.handleFurnitureClick,
            this.tooltipManager,
            this.handleFurnitureContextMenu,
            this.highlightedFurniture,
            this.hoveredReservationFurniture
        );
        updateLegend(this.data, this.colors);

        // Apply zoom
        this.applyZoom();

        // Restore scroll position after browser processes DOM changes
        if (wrapper) {
            requestAnimationFrame(() => {
                wrapper.scrollLeft = scrollLeft;
                wrapper.scrollTop = scrollTop;
            });
        }

        // Notify render complete
        if (this.callbacks.onRender) {
            this.callbacks.onRender(this.data);
        }
    }

    // =========================================================================
    // SELECTION
    // =========================================================================

    handleFurnitureClick(event, item) {
        event.stopPropagation();

        // Suppress click if it was actually end of a drag
        if (this._suppressNextClick) {
            this._suppressNextClick = false;
            return;
        }

        // Check if furniture is blocked - prevent selection for new reservations
        if (this.data?.blocks && this.data.blocks[item.id]) {
            const blockInfo = this.data.blocks[item.id];
            const blockTypeNames = {
                'maintenance': 'mantenimiento',
                'vip_hold': 'reserva VIP',
                'event': 'evento',
                'other': 'bloqueo'
            };
            const typeName = blockTypeNames[blockInfo.block_type] || 'bloqueo';
            showToast(`Este mobiliario está bloqueado por ${typeName}`, 'warning');
            return; // Do not allow selection
        }

        // Always multi-select on tap (mobile-first)
        this.selection.select(item.id, true);
        this.updateFurnitureSelectionVisuals();
        this.selection.updatePanel(this.data);

        if (this.callbacks.onFurnitureClick) {
            this.callbacks.onFurnitureClick(item, this.getSelectedFurniture());
        }
    }

    handleFurnitureContextMenu(event, item) {
        this.contextMenu.show(event, item);
    }

    selectFurniture(id, addToSelection = false) {
        this.selection.select(id, addToSelection);
        this.updateFurnitureSelectionVisuals();
        this.selection.updatePanel(this.data);
    }

    deselectFurniture(id) {
        this.selection.deselect(id);
        this.updateFurnitureSelectionVisuals();
        this.selection.updatePanel(this.data);
    }

    clearSelection() {
        this.selection.clear();
        this.updateFurnitureSelectionVisuals();
        this.selection.updatePanel(this.data);
    }

    getSelectedFurniture() {
        return this.selection.getSelected();
    }

    isSelected(id) {
        return this.selection.isSelected(id);
    }

    getSelectedFurnitureData() {
        return this.selection.getSelectedData(this.data);
    }

    updateSelectionPanel() {
        this.selection.updatePanel(this.data);
    }

    /**
     * Update furniture selection visuals without full re-render
     * This preserves scroll position by only updating CSS classes/styles
     */
    updateFurnitureSelectionVisuals() {
        const selectedSet = this.selection.getSelectedSet();
        const furnitureGroups = this.furnitureLayer.querySelectorAll('g[data-furniture-id]');

        furnitureGroups.forEach(group => {
            const id = parseInt(group.getAttribute('data-furniture-id'));
            const rect = group.querySelector('rect');
            if (!rect) return;

            const isSelected = selectedSet.has(id);

            // Get furniture data to determine base colors
            const item = this.data?.furniture?.find(f => f.id === id);
            if (!item) return;

            // Determine availability status
            const availStatus = this.data?.availability?.[id];
            const blockInfo = this.data?.blocks?.[id];

            if (isSelected) {
                // Apply selection styling
                rect.setAttribute('fill', this.colors.selectedFill);
                rect.setAttribute('stroke', this.colors.selectedStroke);
                group.setAttribute('filter', 'url(#selected-glow)');
            } else {
                // Remove selection styling, restore base colors
                group.removeAttribute('filter');

                if (blockInfo) {
                    // Blocked furniture - use color from block data or default gray
                    const blockFill = blockInfo.color || '#9CA3AF';
                    rect.setAttribute('fill', blockFill);
                    rect.setAttribute('stroke', this.darkenColor(blockFill, 30));
                } else if (availStatus && !availStatus.available) {
                    // Occupied furniture - use state colors from data
                    const state = availStatus.state;
                    const stateColor = state && this.data?.state_colors?.[state];
                    if (stateColor) {
                        rect.setAttribute('fill', stateColor);
                        rect.setAttribute('stroke', this.darkenColor(stateColor, 30));
                    } else {
                        // Fallback if no state color defined
                        const typeConfig = this.data?.furniture_types?.[item.furniture_type] || {};
                        rect.setAttribute('fill', typeConfig.fill_color || '#A0522D');
                        rect.setAttribute('stroke', typeConfig.stroke_color || '#654321');
                    }
                } else {
                    // Available furniture - check if temporary
                    if (item.is_temporary) {
                        rect.setAttribute('fill', '#E0F2FE');
                        rect.setAttribute('stroke', '#0EA5E9');
                    } else {
                        rect.setAttribute('fill', this.colors.availableFill);
                        rect.setAttribute('stroke', this.colors.availableStroke);
                    }
                }
            }
        });
    }

    /**
     * Darken a hex color by a percentage
     * @param {string} color - Hex color string
     * @param {number} percent - Percentage to darken (0-100)
     * @returns {string} Darkened hex color
     */
    darkenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.max(0, (num >> 16) - amt);
        const G = Math.max(0, ((num >> 8) & 0x00FF) - amt);
        const B = Math.max(0, (num & 0x0000FF) - amt);
        return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
    }

    // =========================================================================
    // DATE NAVIGATION
    // =========================================================================

    async goToDate(dateStr) {
        this.currentDate = dateStr;

        // Update offline manager date
        if (this.offlineManager) {
            await this.offlineManager.setDate(dateStr);
        }

        await this.loadData();
        this.render();

        if (this.callbacks.onDateChange) {
            this.callbacks.onDateChange(dateStr);
        }
    }

    async goToPreviousDay() {
        const date = new Date(this.currentDate);
        date.setDate(date.getDate() - 1);
        await this.goToDate(date.toISOString().split('T')[0]);
    }

    async goToNextDay() {
        const date = new Date(this.currentDate);
        date.setDate(date.getDate() + 1);
        await this.goToDate(date.toISOString().split('T')[0]);
    }

    formatDateDisplay(dateStr) {
        return formatDateDisplay(dateStr);
    }

    // =========================================================================
    // ZOOM & PAN
    // =========================================================================

    zoomIn(factor = 0.25) {
        this.navigation.zoomIn(factor);
    }

    zoomOut(factor = 0.25) {
        this.navigation.zoomOut(factor);
    }

    zoomReset() {
        this.navigation.zoomReset();
        this.applyZoom();
    }

    setZoom(level) {
        this.navigation.setZoom(level);
        // Keep interaction manager zoom in sync
        this.interaction.setZoom(this.navigation.getZoom());
    }

    getZoom() {
        return this.navigation.getZoom();
    }

    applyZoom() {
        this.navigation.applyZoom(this.svg, this.data);
        // Keep interaction manager zoom in sync
        this.interaction.setZoom(this.navigation.getZoom());
    }

    // =========================================================================
    // AUTO-REFRESH
    // =========================================================================

    startAutoRefresh(intervalMs = null) {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }

        const interval = intervalMs || this.options.autoRefreshInterval;
        this.autoRefreshTimer = setInterval(() => {
            this.refreshAvailability();
        }, interval);
    }

    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
        }
    }

    async refreshAvailability() {
        // Skip refresh if temp furniture drag is in progress
        if (this.interaction.isDraggingTemp) {
            return;
        }

        try {
            await this.loadData();
            this.render();
        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }

    // =========================================================================
    // EDIT MODE
    // =========================================================================

    enableEditMode() {
        this.interaction.enableEditMode(this.container, this.furnitureLayer);
    }

    disableEditMode() {
        this.interaction.disableEditMode();
    }

    // =========================================================================
    // TEMPORARY FURNITURE DRAG (always enabled)
    // =========================================================================

    /**
     * Handle mousedown on SVG - check for temp furniture drag
     * @param {MouseEvent} event
     */
    handleTempFurnitureMouseDown(event) {
        // Only left mouse button
        if (event.button !== 0) return;

        // Check if clicking on temp furniture
        const tempFurniture = this.interaction.isTemporaryFurniture(event.target);
        if (!tempFurniture) return;

        // Stop auto-refresh during drag to prevent race conditions
        this.stopAutoRefresh();

        // Start drag tracking
        this.interaction.handleTempDragStart(event, tempFurniture);
    }

    /**
     * Handle mousemove for temp furniture drag
     * @param {MouseEvent} event
     */
    handleTempFurnitureMouseMove(event) {
        this.interaction.handleTempDrag(event);
    }

    /**
     * Handle mouseup for temp furniture drag
     * @param {MouseEvent} event
     */
    async handleTempFurnitureMouseUp(event) {
        const wasDrag = await this.interaction.handleTempDragEnd(event);

        // Restart auto-refresh after drag (with delay to let DB commit)
        setTimeout(() => this.startAutoRefresh(), 500);

        // If was a drag, suppress the click event
        if (wasDrag) {
            this._suppressNextClick = true;
        }
    }

    // =========================================================================
    // TOUCH HANDLERS FOR MOBILE TEMP FURNITURE DRAG
    // =========================================================================

    /**
     * Handle touchstart for temp furniture drag on mobile
     * @param {TouchEvent} event
     */
    handleTempFurnitureTouchStart(event) {
        // Only handle single touch
        if (event.touches.length !== 1) return;

        // Check if touching temp furniture
        const tempFurniture = this.interaction.isTemporaryFurniture(event.target);
        if (!tempFurniture) return;

        // Store touch info for drag detection
        this._tempTouchStartTime = Date.now();
        this._tempTouchStartX = event.touches[0].clientX;
        this._tempTouchStartY = event.touches[0].clientY;
        this._tempTouchTarget = tempFurniture;
        this._tempTouchDragStarted = false;

        // Stop auto-refresh during potential drag
        this.stopAutoRefresh();
    }

    /**
     * Handle touchmove for temp furniture drag on mobile
     * @param {TouchEvent} event
     */
    handleTempFurnitureTouchMove(event) {
        if (!this._tempTouchTarget || event.touches.length !== 1) return;

        const touch = event.touches[0];
        const deltaX = Math.abs(touch.clientX - this._tempTouchStartX);
        const deltaY = Math.abs(touch.clientY - this._tempTouchStartY);
        const moveThreshold = 10;

        // Start drag if moved enough (before long-press triggers)
        if (!this._tempTouchDragStarted && (deltaX > moveThreshold || deltaY > moveThreshold)) {
            // Only start drag if within first 400ms (before long-press at 500ms)
            const elapsed = Date.now() - this._tempTouchStartTime;
            if (elapsed < 400) {
                this._tempTouchDragStarted = true;

                // Create synthetic mousedown event to start drag
                const syntheticEvent = {
                    button: 0,
                    clientX: this._tempTouchStartX,
                    clientY: this._tempTouchStartY,
                    target: this._tempTouchTarget.element,
                    preventDefault: () => {}
                };
                this.interaction.handleTempDragStart(syntheticEvent, this._tempTouchTarget);

                // Haptic feedback
                if (navigator.vibrate) {
                    navigator.vibrate(30);
                }
            }
        }

        // If drag started, continue dragging
        if (this._tempTouchDragStarted) {
            event.preventDefault(); // Prevent scroll while dragging

            const syntheticEvent = {
                clientX: touch.clientX,
                clientY: touch.clientY
            };
            this.interaction.handleTempDrag(syntheticEvent);
        }
    }

    /**
     * Handle touchend/touchcancel for temp furniture drag on mobile
     * @param {TouchEvent} event
     */
    async handleTempFurnitureTouchEnd(event) {
        if (!this._tempTouchTarget) return;

        if (this._tempTouchDragStarted) {
            // End the drag
            const touch = event.changedTouches?.[0];
            const syntheticEvent = {
                clientX: touch?.clientX || this._tempTouchStartX,
                clientY: touch?.clientY || this._tempTouchStartY
            };

            const wasDrag = await this.interaction.handleTempDragEnd(syntheticEvent);

            if (wasDrag) {
                this._suppressNextClick = true;
            }
        }

        // Restart auto-refresh after drag
        setTimeout(() => this.startAutoRefresh(), 500);

        // Reset touch state
        this._tempTouchTarget = null;
        this._tempTouchDragStarted = false;
        this._tempTouchStartTime = 0;
        this._tempTouchStartX = 0;
        this._tempTouchStartY = 0;
    }

    // =========================================================================
    // SEARCH HIGHLIGHT & PAN
    // =========================================================================

    /**
     * Highlight furniture and pan/scroll to center it in view
     * @param {number} furnitureId - ID of furniture to highlight
     */
    highlightAndPanToFurniture(furnitureId) {
        // Find the furniture element
        const furnitureEl = this.furnitureLayer.querySelector(`[data-furniture-id="${furnitureId}"]`);
        if (!furnitureEl) {
            console.warn(`Furniture #${furnitureId} not found on map`);
            return;
        }

        // Clear previous highlights
        this._clearSearchHighlights();

        // Add highlight class (pulsing animation)
        furnitureEl.classList.add('search-highlight');

        // Get furniture position from data
        const furniture = this.data?.furniture?.find(f => f.id === furnitureId);
        if (furniture) {
            this._panToPosition(furniture.position_x, furniture.position_y);
        }

        // Auto-remove highlight after 3 seconds
        setTimeout(() => {
            furnitureEl.classList.remove('search-highlight');
        }, 3000);
    }

    /**
     * Clear all search highlights
     */
    _clearSearchHighlights() {
        this.furnitureLayer.querySelectorAll('.search-highlight').forEach(el => {
            el.classList.remove('search-highlight');
        });
    }

    /**
     * Pan/scroll the map to center on a position
     * @param {number} x - X coordinate in SVG units
     * @param {number} y - Y coordinate in SVG units
     */
    _panToPosition(x, y) {
        const wrapper = this.container.closest('.map-canvas-wrapper');
        if (!wrapper) return;

        const wrapperRect = wrapper.getBoundingClientRect();
        const zoom = this.navigation.getZoom();

        // Calculate scroll position to center the target
        const targetX = (x * zoom) - (wrapperRect.width / 2);
        const targetY = (y * zoom) - (wrapperRect.height / 2);

        wrapper.scrollTo({
            left: Math.max(0, targetX),
            top: Math.max(0, targetY),
            behavior: 'smooth'
        });
    }

    // =========================================================================
    // MOVE MODE PREFERENCE HIGHLIGHTS
    // =========================================================================

    /**
     * Highlight furniture items that match customer preferences (for move mode)
     * Supports tiered highlighting: full match vs partial match
     * @param {Array} fullMatchIds - Furniture IDs with 100% preference match
     * @param {Array} partialMatchIds - Furniture IDs with partial match (>0% but <100%)
     */
    applyPreferenceHighlights(fullMatchIds = [], partialMatchIds = []) {
        // Clear previous preference highlights
        this.clearPreferenceHighlights();

        // Add full match highlight (strong green glow)
        fullMatchIds.forEach(id => {
            const furnitureEl = this.furnitureLayer.querySelector(`[data-furniture-id="${id}"]`);
            if (furnitureEl) {
                furnitureEl.classList.add('preference-match-full');
            }
        });

        // Add partial match highlight (lighter highlight)
        partialMatchIds.forEach(id => {
            const furnitureEl = this.furnitureLayer.querySelector(`[data-furniture-id="${id}"]`);
            if (furnitureEl) {
                furnitureEl.classList.add('preference-match-partial');
            }
        });
    }

    /**
     * Clear all preference match highlights
     */
    clearPreferenceHighlights() {
        this.furnitureLayer.querySelectorAll('.preference-match-full').forEach(el => {
            el.classList.remove('preference-match-full');
        });
        this.furnitureLayer.querySelectorAll('.preference-match-partial').forEach(el => {
            el.classList.remove('preference-match-partial');
        });
    }

    /**
     * Set furniture IDs to highlight for a reservation (survives re-renders)
     * @param {number[]} ids - Furniture IDs to highlight
     */
    setHighlightedFurniture(ids) {
        this.highlightedFurniture = new Set(ids);
        this.render();
    }

    /**
     * Clear reservation furniture highlights
     */
    clearHighlightedFurniture() {
        if (this.highlightedFurniture.size === 0) return;
        this.highlightedFurniture = new Set();
        this.render();
    }

    // =========================================================================
    // UTILITIES
    // =========================================================================

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger m-3';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${escapeHtml(message)}`;
        this.container.appendChild(errorDiv);
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    on(eventName, callback) {
        if (this.callbacks.hasOwnProperty(eventName)) {
            this.callbacks[eventName] = callback;
        }
        return this;
    }

    getCurrentDate() {
        return this.currentDate;
    }

    getData() {
        return this.data;
    }

    destroy() {
        this.stopAutoRefresh();
        this.navigation.removeKeyboard();
        this.interaction.destroy();
        this.tooltipManager.destroy();
        this.contextMenu.destroy();

        // Remove temp furniture drag listeners
        this.svg?.removeEventListener('mousedown', this.handleTempFurnitureMouseDown);
        document.removeEventListener('mousemove', this.handleTempFurnitureMouseMove);
        document.removeEventListener('mouseup', this.handleTempFurnitureMouseUp);

        // Remove touch listeners
        this.svg?.removeEventListener('touchstart', this.handleTempFurnitureTouchStart);
        document.removeEventListener('touchmove', this.handleTempFurnitureTouchMove);
        document.removeEventListener('touchend', this.handleTempFurnitureTouchEnd);
        document.removeEventListener('touchcancel', this.handleTempFurnitureTouchEnd);
    }
}

// Export for use as module and global


// --- SearchManager.js ---
/**
 * Map Search Manager
 * Handles search functionality for the beach map
 *
 * Enhanced: Groups by reservation, includes all states, supports filters
 */

class SearchManager {
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


// --- block-manager.js ---
/**
 * Block Manager Module
 * Handles furniture blocking/unblocking API calls and modal interactions
 */


// BLOCK_TYPES already defined in context-menu.js section above

/**
 * BlockManager class
 * Manages the block furniture modal and API calls
 */
class BlockManager {
    /**
     * @param {Object} options - Configuration options
     * @param {Function} options.onBlockSuccess - Callback when block is successful
     * @param {Function} options.onUnblockSuccess - Callback when unblock is successful
     * @param {Function} options.getCurrentDate - Function to get current map date
     * @param {Function} options.getBlockInfo - Function to get block info for furniture
     */
    constructor(options = {}) {
        this.onBlockSuccess = options.onBlockSuccess || (() => {});
        this.onUnblockSuccess = options.onUnblockSuccess || (() => {});
        this.getCurrentDate = options.getCurrentDate || (() => new Date().toISOString().split('T')[0]);
        this.getBlockInfo = options.getBlockInfo || (() => null);

        this.modal = null;
        this.unblockModal = null;
        this.furnitureToBlock = [];
        this.furnitureNumbers = [];

        // Unblock state
        this.furnitureToUnblock = null;
        this.furnitureNumberToUnblock = null;
        this.currentBlockInfo = null;

        this.init();
    }

    /**
     * Initialize the block manager
     */
    init() {
        this.modal = document.getElementById('block-furniture-modal');
        this.unblockModal = document.getElementById('unblock-furniture-modal');

        if (!this.modal) {
            console.warn('Block furniture modal not found');
        }
        if (!this.unblockModal) {
            console.warn('Unblock furniture modal not found');
        }

        this.setupEventListeners();
        this.setupUnblockEventListeners();
    }

    /**
     * Setup event listeners for the block modal
     */
    setupEventListeners() {
        // Confirm block button
        const confirmBtn = document.getElementById('confirm-block-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmBlock());
        }

        // Reset form when modal closes
        this.modal?.addEventListener('hidden.bs.modal', () => this.resetForm());
    }

    /**
     * Setup event listeners for the unblock modal
     */
    setupUnblockEventListeners() {
        // Radio button toggle for date range visibility
        const fullRadio = document.getElementById('unblock-type-full');
        const partialRadio = document.getElementById('unblock-type-partial');
        const dateRangeDiv = document.getElementById('unblock-date-range');

        if (fullRadio && partialRadio && dateRangeDiv) {
            fullRadio.addEventListener('change', () => {
                dateRangeDiv.style.display = 'none';
            });
            partialRadio.addEventListener('change', () => {
                dateRangeDiv.style.display = 'flex';
            });
        }

        // Confirm unblock button
        const confirmUnblockBtn = document.getElementById('confirm-unblock-btn');
        if (confirmUnblockBtn) {
            confirmUnblockBtn.addEventListener('click', () => this.confirmUnblock());
        }

        // Reset form when modal closes
        this.unblockModal?.addEventListener('hidden.bs.modal', () => this.resetUnblockForm());
    }

    /**
     * Show the block modal for specified furniture
     * @param {number[]} furnitureIds - Array of furniture IDs to block
     * @param {string[]} furnitureNumbers - Array of furniture numbers/codes
     */
    showBlockModal(furnitureIds, furnitureNumbers) {
        if (!this.modal) {
            showToast('Modal de bloqueo no disponible', 'error');
            return;
        }

        this.furnitureToBlock = furnitureIds;
        this.furnitureNumbers = furnitureNumbers;

        // Populate furniture list
        const listEl = document.getElementById('block-furniture-list');
        if (listEl) {
            listEl.innerHTML = furnitureNumbers.map(num =>
                `<span class="block-furniture-badge">${num}</span>`
            ).join('');
        }

        // Set default date to current map date
        const startDateInput = document.getElementById('block-start-date');
        if (startDateInput) {
            startDateInput.value = this.getCurrentDate();
        }

        // Clear end date and reason
        const endDateInput = document.getElementById('block-end-date');
        const reasonInput = document.getElementById('block-reason');
        if (endDateInput) endDateInput.value = '';
        if (reasonInput) reasonInput.value = '';

        // Reset block type to default
        const blockTypeSelect = document.getElementById('block-type');
        if (blockTypeSelect) blockTypeSelect.value = 'maintenance';

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.modal);
        bsModal.show();
    }

    /**
     * Confirm and execute the block operation
     */
    async confirmBlock() {
        const blockType = document.getElementById('block-type')?.value || 'maintenance';
        const startDate = document.getElementById('block-start-date')?.value;
        const endDate = document.getElementById('block-end-date')?.value || null;
        const reason = document.getElementById('block-reason')?.value || '';

        if (!startDate) {
            showToast('La fecha de inicio es requerida', 'warning');
            return;
        }

        if (this.furnitureToBlock.length === 0) {
            showToast('No hay mobiliario seleccionado', 'warning');
            return;
        }

        // Disable button while processing
        const confirmBtn = document.getElementById('confirm-block-btn');
        if (window.PuroBeach) {
            window.PuroBeach.setButtonLoading(confirmBtn, true, 'Bloqueando...');
        }

        try {
            // Block each furniture item
            const results = await Promise.all(
                this.furnitureToBlock.map(id => this.blockFurniture(id, {
                    block_type: blockType,
                    start_date: startDate,
                    end_date: endDate,
                    reason: reason
                }))
            );

            // Check for errors
            const errors = results.filter(r => !r.success);
            if (errors.length > 0) {
                showToast(`Error al bloquear ${errors.length} elemento(s)`, 'error');
            } else {
                const blockTypeName = BLOCK_TYPES[blockType]?.name || 'Bloqueo';
                showToast(`${this.furnitureToBlock.length} elemento(s) bloqueado(s) - ${blockTypeName}`, 'success');
            }

            // Close modal
            const bsModal = bootstrap.Modal.getInstance(this.modal);
            bsModal?.hide();

            // Trigger refresh
            this.onBlockSuccess();

        } catch (error) {
            console.error('Block error:', error);
            showToast('Error al bloquear mobiliario', 'error');
        } finally {
            if (window.PuroBeach) {
                window.PuroBeach.setButtonLoading(confirmBtn, false);
            }
        }
    }

    /**
     * Block a single furniture item via API
     * @param {number} furnitureId - Furniture ID
     * @param {Object} blockData - Block data (block_type, start_date, end_date, reason)
     * @returns {Promise<Object>} API response
     */
    async blockFurniture(furnitureId, blockData) {
        try {
            const response = await fetch(`/beach/api/map/furniture/${furnitureId}/block`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(blockData)
            });

            return await response.json();
        } catch (error) {
            console.error(`Error blocking furniture ${furnitureId}:`, error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Show the unblock modal for a furniture item
     * @param {number|Array<number>} furnitureId - Furniture ID(s)
     * @param {string|Array<string>} furnitureNumber - Furniture number(s) for display
     * @param {Object} blockInfo - Block information (optional, will fetch if not provided)
     */
    async showUnblockModal(furnitureId, furnitureNumber, blockInfo = null) {
        if (!this.unblockModal) {
            showToast('Modal de desbloqueo no disponible', 'error');
            return;
        }

        // Handle arrays for multi-unblock
        const isMultiUnblock = Array.isArray(furnitureId) && furnitureId.length > 1;

        if (isMultiUnblock) {
            // For multi-unblock, show simplified confirmation and unblock all
            await this.handleMultiUnblock(furnitureId, furnitureNumber);
            return;
        }

        // Single unblock - extract from array if needed
        const singleId = Array.isArray(furnitureId) ? furnitureId[0] : furnitureId;
        const singleNumber = Array.isArray(furnitureNumber) ? furnitureNumber[0] : furnitureNumber;

        this.furnitureToUnblock = singleId;
        this.furnitureNumberToUnblock = singleNumber;
        this.currentBlockInfo = blockInfo || this.getBlockInfo(singleId);

        if (!this.currentBlockInfo) {
            showToast('No se encontró información del bloqueo', 'error');
            return;
        }

        // Populate modal
        const numberEl = document.getElementById('unblock-furniture-number');
        if (numberEl) numberEl.textContent = furnitureNumber;

        const blockType = BLOCK_TYPES[this.currentBlockInfo.block_type] || BLOCK_TYPES.other;
        const typeEl = document.getElementById('unblock-block-type');
        if (typeEl) typeEl.textContent = `${blockType.icon} ${blockType.name}`;

        const startEl = document.getElementById('unblock-block-start');
        if (startEl) startEl.textContent = this.formatDate(this.currentBlockInfo.start_date);

        const endEl = document.getElementById('unblock-block-end');
        if (endEl) endEl.textContent = this.formatDate(this.currentBlockInfo.end_date);

        const reasonEl = document.getElementById('unblock-block-reason');
        const reasonRow = document.getElementById('unblock-block-reason-row');
        if (reasonEl && reasonRow) {
            if (this.currentBlockInfo.reason) {
                reasonEl.textContent = this.currentBlockInfo.reason;
                reasonRow.style.display = '';
            } else {
                reasonRow.style.display = 'none';
            }
        }

        // Set default dates to current block dates
        const startDateInput = document.getElementById('unblock-start-date');
        const endDateInput = document.getElementById('unblock-end-date');
        const currentDate = this.getCurrentDate();

        if (startDateInput) {
            startDateInput.value = currentDate;
            startDateInput.min = this.currentBlockInfo.start_date;
            startDateInput.max = this.currentBlockInfo.end_date;
        }
        if (endDateInput) {
            endDateInput.value = currentDate;
            endDateInput.min = this.currentBlockInfo.start_date;
            endDateInput.max = this.currentBlockInfo.end_date;
        }

        // Reset to full unblock
        const fullRadio = document.getElementById('unblock-type-full');
        const dateRangeDiv = document.getElementById('unblock-date-range');
        if (fullRadio) fullRadio.checked = true;
        if (dateRangeDiv) dateRangeDiv.style.display = 'none';

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.unblockModal);
        bsModal.show();
    }

    /**
     * Handle unblocking of multiple furniture items
     * @param {Array<number>} furnitureIds - Array of furniture IDs to unblock
     * @param {Array<string>} furnitureNumbers - Array of furniture numbers for display
     */
    async handleMultiUnblock(furnitureIds, furnitureNumbers) {
        // Show confirmation with count
        const count = furnitureIds.length;
        const confirmed = confirm(`¿Está seguro de desbloquear ${count} mobiliarios?\n\nEsto desbloqueará completamente:\n${furnitureNumbers.join(', ')}`);

        if (!confirmed) {
            return;
        }

        let successCount = 0;
        let errorCount = 0;

        // Unblock each item individually
        for (let i = 0; i < furnitureIds.length; i++) {
            try {
                const blockInfo = this.getBlockInfo(furnitureIds[i]);
                if (!blockInfo) {
                    console.warn(`No block info found for furniture ${furnitureNumbers[i]}`);
                    errorCount++;
                    continue;
                }

                const response = await fetch(`/beach/api/map/furniture/${furnitureIds[i]}/block`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });

                const result = await response.json();

                if (result.success) {
                    successCount++;
                } else {
                    console.error(`Error unblocking furniture ${furnitureNumbers[i]}:`, result.error);
                    errorCount++;
                }
            } catch (error) {
                console.error(`Error unblocking furniture ${furnitureNumbers[i]}:`, error);
                errorCount++;
            }
        }

        // Show result message
        if (errorCount === 0) {
            showToast(`${successCount} mobiliarios desbloqueados`, 'success');
        } else if (successCount === 0) {
            showToast(`Error al desbloquear mobiliarios`, 'error');
        } else {
            showToast(`${successCount} desbloqueados, ${errorCount} con errores`, 'warning');
        }

        // Refresh map
        if (this.onUnblockSuccess) {
            this.onUnblockSuccess();
        }
    }

    /**
     * Confirm and execute the unblock operation
     */
    async confirmUnblock() {
        const unblockType = document.querySelector('input[name="unblock-type"]:checked')?.value || 'full';

        // Disable button while processing
        const confirmBtn = document.getElementById('confirm-unblock-btn');
        if (window.PuroBeach) {
            window.PuroBeach.setButtonLoading(confirmBtn, true, 'Desbloqueando...');
        }

        try {
            let result;

            if (unblockType === 'full') {
                // Full unblock - delete the entire block
                result = await this.executeFullUnblock();
            } else {
                // Partial unblock - unblock specific date range
                const startDate = document.getElementById('unblock-start-date')?.value;
                const endDate = document.getElementById('unblock-end-date')?.value;

                if (!startDate || !endDate) {
                    showToast('Las fechas son requeridas para desbloqueo parcial', 'warning');
                    return;
                }

                if (startDate > endDate) {
                    showToast('La fecha de inicio no puede ser posterior a la fecha fin', 'warning');
                    return;
                }

                result = await this.executePartialUnblock(startDate, endDate);
            }

            if (result.success) {
                showToast(`Mobiliario ${this.furnitureNumberToUnblock} desbloqueado`, 'success');

                // Close modal
                const bsModal = bootstrap.Modal.getInstance(this.unblockModal);
                bsModal?.hide();

                // Trigger refresh
                this.onUnblockSuccess();
            } else {
                showToast(result.error || 'Error al desbloquear', 'error');
            }

        } catch (error) {
            console.error('Unblock error:', error);
            showToast('Error al desbloquear mobiliario', 'error');
        } finally {
            if (window.PuroBeach) {
                window.PuroBeach.setButtonLoading(confirmBtn, false);
            }
        }
    }

    /**
     * Execute full unblock (delete entire block)
     * @returns {Promise<Object>} API response
     */
    async executeFullUnblock() {
        const blockId = this.currentBlockInfo?.id;
        const date = this.getCurrentDate();

        const url = blockId
            ? `/beach/api/map/furniture/${this.furnitureToUnblock}/block?block_id=${blockId}`
            : `/beach/api/map/furniture/${this.furnitureToUnblock}/block?date=${date}`;

        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        });

        return await response.json();
    }

    /**
     * Execute partial unblock (unblock specific date range)
     * @param {string} startDate - Start date to unblock
     * @param {string} endDate - End date to unblock
     * @returns {Promise<Object>} API response
     */
    async executePartialUnblock(startDate, endDate) {
        const response = await fetch(`/beach/api/map/furniture/${this.furnitureToUnblock}/unblock-partial`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                block_id: this.currentBlockInfo?.id,
                unblock_start: startDate,
                unblock_end: endDate
            })
        });

        return await response.json();
    }

    /**
     * Format date for display
     * @param {string} dateStr - Date string (YYYY-MM-DD or ISO format)
     * @returns {string} Formatted date
     */
    formatDate(dateStr) {
        if (!dateStr) return '-';

        let date;
        // Handle different date formats
        if (typeof dateStr === 'string') {
            // If it's already in YYYY-MM-DD format
            if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                date = new Date(dateStr + 'T00:00:00');
            } else {
                // Try parsing as-is (handles ISO format, etc.)
                date = new Date(dateStr);
            }
        } else if (dateStr instanceof Date) {
            date = dateStr;
        } else {
            return '-';
        }

        if (isNaN(date.getTime())) return '-';

        return date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }

    /**
     * Reset the unblock form fields
     */
    resetUnblockForm() {
        this.furnitureToUnblock = null;
        this.furnitureNumberToUnblock = null;
        this.currentBlockInfo = null;

        const fullRadio = document.getElementById('unblock-type-full');
        const dateRangeDiv = document.getElementById('unblock-date-range');
        if (fullRadio) fullRadio.checked = true;
        if (dateRangeDiv) dateRangeDiv.style.display = 'none';
    }

    /**
     * Reset the block form fields
     */
    resetForm() {
        this.furnitureToBlock = [];
        this.furnitureNumbers = [];

        const listEl = document.getElementById('block-furniture-list');
        if (listEl) listEl.innerHTML = '';

        const startDateInput = document.getElementById('block-start-date');
        const endDateInput = document.getElementById('block-end-date');
        const reasonInput = document.getElementById('block-reason');
        const blockTypeSelect = document.getElementById('block-type');

        if (startDateInput) startDateInput.value = '';
        if (endDateInput) endDateInput.value = '';
        if (reasonInput) reasonInput.value = '';
        if (blockTypeSelect) blockTypeSelect.value = 'maintenance';
    }

    /**
     * Get CSRF token from meta tag or cookie
     * @returns {string} CSRF token
     */
    getCSRFToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        // Try cookie
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }

        // Try hidden input
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            return csrfInput.value;
        }

        return '';
    }

    /**
     * Destroy the manager
     */
    destroy() {
        this.modal = null;
        this.furnitureToBlock = [];
        this.furnitureNumbers = [];
    }
}



// --- temp-furniture-manager.js ---
/**
 * Temporary Furniture Manager Module
 * Handles creating/deleting temporary furniture on the map
 */


/**
 * TempFurnitureManager class
 * Manages temporary furniture creation/deletion modals and API calls
 */
class TempFurnitureManager {
    /**
     * @param {Object} options - Configuration options
     * @param {Function} options.onCreateSuccess - Callback when creation is successful
     * @param {Function} options.onDeleteSuccess - Callback when deletion is successful
     * @param {Function} options.getCurrentDate - Function to get current map date
     * @param {Function} options.getZones - Function to get available zones
     * @param {Function} options.getFurnitureTypes - Function to get furniture types
     */
    constructor(options = {}) {
        this.onCreateSuccess = options.onCreateSuccess || (() => {});
        this.onDeleteSuccess = options.onDeleteSuccess || (() => {});
        this.getCurrentDate = options.getCurrentDate || (() => new Date().toISOString().split('T')[0]);
        this.getZones = options.getZones || (() => []);
        this.getFurnitureTypes = options.getFurnitureTypes || (() => ({}));

        this.modal = null;
        this.deleteModal = null;
        this.clickPosition = { x: 100, y: 100 };
        this.selectedZoneId = null;

        // Delete state
        this.furnitureToDelete = null;
        this.furnitureNumberToDelete = null;
        this.isMultiDay = false;
        this.dateInfo = null;

        this.init();
    }

    /**
     * Initialize the manager
     */
    init() {
        this.modal = document.getElementById('temp-furniture-modal');
        this.deleteModal = document.getElementById('delete-temp-modal');

        if (!this.modal) {
            console.warn('Temporary furniture modal not found');
        }
        if (!this.deleteModal) {
            console.warn('Delete temporary furniture modal not found');
        }

        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Confirm create button
        const confirmBtn = document.getElementById('confirm-temp-create-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmCreate());
        }

        // Confirm delete button
        const confirmDeleteBtn = document.getElementById('confirm-temp-delete-btn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => this.confirmDelete());
        }

        // Reset form when modal closes
        this.modal?.addEventListener('hidden.bs.modal', () => this.resetForm());
        this.deleteModal?.addEventListener('hidden.bs.modal', () => this.resetDeleteForm());

        // Auto-generate number when type or zone changes
        const typeSelect = document.getElementById('temp-furniture-type');
        const zoneSelect = document.getElementById('temp-zone');
        if (typeSelect) {
            typeSelect.addEventListener('change', () => this.fetchNextNumber());
        }
        if (zoneSelect) {
            zoneSelect.addEventListener('change', () => this.fetchNextNumber());
        }
    }

    /**
     * Get CSRF token from page
     */
    getCSRFToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) return metaTag.getAttribute('content');

        // Try cookie
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') return value;
        }

        // Try hidden input
        const hiddenInput = document.querySelector('input[name="csrf_token"]');
        if (hiddenInput) return hiddenInput.value;

        return '';
    }

    /**
     * Fetch the next available number from the API
     */
    async fetchNextNumber() {
        const typeSelect = document.getElementById('temp-furniture-type');
        const zoneSelect = document.getElementById('temp-zone');
        const numberInput = document.getElementById('temp-number');

        if (!typeSelect || !numberInput) return;

        const furnitureType = typeSelect.value;
        const zoneId = zoneSelect?.value || '';

        try {
            const url = `/beach/api/map/temporary-furniture/next-number?furniture_type=${furnitureType}&zone_id=${zoneId}`;
            const response = await fetch(url);
            const result = await response.json();

            if (result.success && result.number) {
                numberInput.value = result.number;
            }
        } catch (error) {
            console.warn('Could not fetch next number:', error);
        }
    }

    /**
     * Populate zones dropdown
     * @param {number|null} selectedZoneId - Pre-select this zone
     */
    populateZones(selectedZoneId = null) {
        const zoneSelect = document.getElementById('temp-zone');
        if (!zoneSelect) return;

        const zones = this.getZones();
        zoneSelect.innerHTML = zones.map(zone =>
            `<option value="${zone.id}" ${zone.id === selectedZoneId ? 'selected' : ''}>${zone.name}</option>`
        ).join('');

        // Store selected zone for position calculation
        this.selectedZoneId = selectedZoneId || (zones.length > 0 ? zones[0].id : null);
    }

    /**
     * Populate furniture types dropdown
     */
    populateFurnitureTypes() {
        const typeSelect = document.getElementById('temp-furniture-type');
        if (!typeSelect) return;

        const types = this.getFurnitureTypes();
        const typeEntries = Object.entries(types)
            .filter(([code, type]) => !type.is_decorative) // Only reservable types
            .sort((a, b) => (a[1].display_order || 0) - (b[1].display_order || 0));

        typeSelect.innerHTML = typeEntries.map(([code, type]) =>
            `<option value="${code}">${type.display_name || code}</option>`
        ).join('');
    }

    /**
     * Show the create modal
     * @param {number} x - X position on map
     * @param {number} y - Y position on map
     * @param {number|null} zoneId - Pre-selected zone
     */
    showCreateModal(x = null, y = null, zoneId = null) {
        if (!this.modal) {
            showToast('Modal no disponible', 'error');
            return;
        }

        // Store click position
        this.clickPosition = { x: x || 100, y: y || 100 };

        // Populate dropdowns
        this.populateZones(zoneId);
        this.populateFurnitureTypes();

        // Set default dates
        const startDateInput = document.getElementById('temp-start-date');
        const endDateInput = document.getElementById('temp-end-date');
        if (startDateInput) {
            startDateInput.value = this.getCurrentDate();
        }
        if (endDateInput) {
            endDateInput.value = '';
        }

        // Set default capacity
        const capacityInput = document.getElementById('temp-capacity');
        if (capacityInput) {
            capacityInput.value = '2';
        }

        // Fetch next available number
        this.fetchNextNumber();

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.modal);
        bsModal.show();
    }

    /**
     * Confirm create action
     */
    async confirmCreate() {
        const zoneId = document.getElementById('temp-zone')?.value;
        const furnitureType = document.getElementById('temp-furniture-type')?.value;
        const number = document.getElementById('temp-number')?.value;
        const capacity = document.getElementById('temp-capacity')?.value;
        const orientation = document.getElementById('temp-orientation')?.value || '0';
        const startDate = document.getElementById('temp-start-date')?.value;
        const endDate = document.getElementById('temp-end-date')?.value || startDate;

        // Validation
        if (!zoneId) {
            showToast('Seleccione una zona', 'warning');
            return;
        }
        if (!furnitureType) {
            showToast('Seleccione un tipo de mobiliario', 'warning');
            return;
        }
        if (!startDate) {
            showToast('Ingrese la fecha de inicio', 'warning');
            return;
        }
        if (startDate > endDate) {
            showToast('La fecha de inicio no puede ser posterior a la fecha de fin', 'warning');
            return;
        }

        // Disable button during request
        const confirmBtn = document.getElementById('confirm-temp-create-btn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creando...';
        }

        try {
            const response = await fetch('/beach/api/map/temporary-furniture', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    zone_id: parseInt(zoneId),
                    furniture_type: furnitureType,
                    number: number || null, // Let API auto-generate if empty
                    capacity: parseInt(capacity) || 2,
                    position_x: this.clickPosition.x,
                    position_y: this.clickPosition.y,
                    start_date: startDate,
                    end_date: endDate,
                    rotation: parseInt(orientation) || 0
                })
            });

            const result = await response.json();

            if (result.success) {
                showToast(`Mobiliario temporal ${result.number} creado`, 'success');
                bootstrap.Modal.getInstance(this.modal)?.hide();
                this.onCreateSuccess();
            } else {
                showToast(result.error || 'Error al crear mobiliario', 'error');
            }
        } catch (error) {
            console.error('Error creating temporary furniture:', error);
            showToast('Error de conexion', 'error');
        } finally {
            // Re-enable button
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-plus me-1"></i>Crear';
            }
        }
    }

    /**
     * Show the delete confirmation modal
     * @param {number|Array<number>} furnitureId - Furniture ID(s) to delete
     * @param {string|Array<string>} furnitureNumber - Furniture number(s) for display
     */
    async showDeleteModal(furnitureId, furnitureNumber) {
        if (!this.deleteModal) {
            showToast('Modal no disponible', 'error');
            return;
        }

        // Handle arrays for multi-delete
        const isMultiDelete = Array.isArray(furnitureId) && furnitureId.length > 1;

        if (isMultiDelete) {
            // For multi-delete, show simplified confirmation and delete all
            await this.handleMultiDelete(furnitureId, furnitureNumber);
            return;
        }

        // Single delete - extract from array if needed
        const singleId = Array.isArray(furnitureId) ? furnitureId[0] : furnitureId;
        const singleNumber = Array.isArray(furnitureNumber) ? furnitureNumber[0] : furnitureNumber;

        this.furnitureToDelete = singleId;
        this.furnitureNumberToDelete = singleNumber;
        this.isMultiDay = false;

        // Update modal content
        const numberEl = document.getElementById('delete-temp-number');
        if (numberEl) {
            numberEl.textContent = furnitureNumber;
        }

        // Fetch date info to determine if multi-day
        try {
            const response = await fetch(`/beach/api/map/temporary-furniture/${furnitureId}/info`);
            const result = await response.json();

            const optionsEl = document.getElementById('delete-temp-options');
            const singleDayMsgEl = document.getElementById('delete-temp-single-day-msg');
            const startEl = document.getElementById('delete-temp-start');
            const endEl = document.getElementById('delete-temp-end');
            const currentDateEl = document.getElementById('delete-temp-current-date');

            // Always show date range info
            if (result.success) {
                if (startEl) startEl.textContent = this.formatDate(result.start_date);
                if (endEl) endEl.textContent = this.formatDate(result.end_date);
            }

            if (result.success && result.is_multi_day) {
                this.isMultiDay = true;
                this.dateInfo = result;

                // Show delete options, hide single day message
                if (currentDateEl) currentDateEl.textContent = this.formatDate(this.getCurrentDate());
                if (optionsEl) optionsEl.style.display = 'block';
                if (singleDayMsgEl) singleDayMsgEl.style.display = 'none';

                // Reset radio to "day only"
                const dayOnlyRadio = document.getElementById('delete-day-only');
                if (dayOnlyRadio) dayOnlyRadio.checked = true;
            } else {
                // Single day - hide options, show single day message
                if (optionsEl) optionsEl.style.display = 'none';
                if (singleDayMsgEl) singleDayMsgEl.style.display = 'block';
            }
        } catch (error) {
            console.warn('Could not fetch date info:', error);
            // Hide options on error, show single day message
            const optionsEl = document.getElementById('delete-temp-options');
            const singleDayMsgEl = document.getElementById('delete-temp-single-day-msg');
            if (optionsEl) optionsEl.style.display = 'none';
            if (singleDayMsgEl) singleDayMsgEl.style.display = 'block';
        }

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.deleteModal);
        bsModal.show();
    }

    /**
     * Format date for display
     * @param {string} dateStr - Date string YYYY-MM-DD
     * @returns {string} Formatted date
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        const [year, month, day] = dateStr.split('-');
        return `${day}/${month}/${year}`;
    }

    /**
     * Handle deletion of multiple temporary furniture items
     * @param {Array<number>} furnitureIds - Array of furniture IDs to delete
     * @param {Array<string>} furnitureNumbers - Array of furniture numbers for display
     */
    async handleMultiDelete(furnitureIds, furnitureNumbers) {
        if (!this.deleteModal) {
            showToast('Modal no disponible', 'error');
            return;
        }

        // Store for later use
        this.furnitureToDelete = furnitureIds;
        this.furnitureNumberToDelete = furnitureNumbers;
        this.isMultiDay = false;

        // Update modal for multi-delete
        const numberEl = document.getElementById('delete-temp-number');
        if (numberEl) {
            numberEl.innerHTML = `<strong>${furnitureIds.length} mobiliarios temporales</strong>`;
        }

        // Show list of items to be deleted
        const optionsEl = document.getElementById('delete-temp-options');
        const singleDayMsgEl = document.getElementById('delete-temp-single-day-msg');
        const dateInfoEl = document.getElementById('delete-temp-date-info');

        // Hide options and single day message
        if (optionsEl) optionsEl.style.display = 'none';
        if (singleDayMsgEl) singleDayMsgEl.style.display = 'none';

        // Show list of furniture to delete
        if (dateInfoEl) {
            dateInfoEl.innerHTML = `
                <div class="alert alert-warning mb-3">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Se eliminarán completamente los siguientes mobiliarios:
                </div>
                <div class="d-flex flex-wrap gap-2 mb-3">
                    ${furnitureNumbers.map(num =>
                        `<span class="badge bg-secondary fs-6">${num}</span>`
                    ).join('')}
                </div>
            `;
        }

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.deleteModal);
        bsModal.show();
    }

    /**
     * Execute multi-delete after modal confirmation
     * @param {Array<number>} furnitureIds - Array of furniture IDs
     * @param {Array<string>} furnitureNumbers - Array of furniture numbers
     */
    async executeMultiDelete(furnitureIds, furnitureNumbers) {
        let successCount = 0;
        let errorCount = 0;

        // Delete each item individually
        for (let i = 0; i < furnitureIds.length; i++) {
            try {
                const url = `/beach/api/map/temporary-furniture/${furnitureIds[i]}?delete_type=all`;
                const response = await fetch(url, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });

                const result = await response.json();

                if (result.success) {
                    successCount++;
                } else {
                    console.error(`Error deleting furniture ${furnitureNumbers[i]}:`, result.error);
                    errorCount++;
                }
            } catch (error) {
                console.error(`Error deleting furniture ${furnitureNumbers[i]}:`, error);
                errorCount++;
            }
        }

        // Show result message
        if (errorCount === 0) {
            showToast(`${successCount} mobiliarios temporales eliminados`, 'success');
        } else if (successCount === 0) {
            showToast(`Error al eliminar mobiliarios temporales`, 'error');
        } else {
            showToast(`${successCount} eliminados, ${errorCount} con errores`, 'warning');
        }

        // Refresh map
        this.onDeleteSuccess();
    }

    /**
     * Confirm delete action
     */
    async confirmDelete() {
        if (!this.furnitureToDelete) {
            showToast('No se selecciono mobiliario', 'error');
            return;
        }

        // Check if this is a multi-delete
        if (Array.isArray(this.furnitureToDelete)) {
            // Disable button during request
            const confirmBtn = document.getElementById('confirm-temp-delete-btn');
            if (confirmBtn) {
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Eliminando...';
            }

            try {
                await this.executeMultiDelete(this.furnitureToDelete, this.furnitureNumberToDelete);
                bootstrap.Modal.getInstance(this.deleteModal)?.hide();
            } finally {
                // Re-enable button
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-trash me-1"></i>Eliminar';
                }
            }
            return;
        }

        // Single delete continues below
        // Determine delete type from radio selection
        let deleteType = 'all';
        let deleteDate = '';

        if (this.isMultiDay) {
            const selectedRadio = document.querySelector('input[name="deleteType"]:checked');
            deleteType = selectedRadio?.value || 'all';

            if (deleteType === 'day') {
                deleteDate = this.getCurrentDate();
            }
        }

        // Disable button during request
        const confirmBtn = document.getElementById('confirm-temp-delete-btn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Eliminando...';
        }

        try {
            // Build URL with query params
            let url = `/beach/api/map/temporary-furniture/${this.furnitureToDelete}?delete_type=${deleteType}`;
            if (deleteType === 'day' && deleteDate) {
                url += `&date=${deleteDate}`;
            }

            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();

            if (result.success) {
                const message = deleteType === 'day'
                    ? `Mobiliario ${this.furnitureNumberToDelete} eliminado para ${this.formatDate(deleteDate)}`
                    : `Mobiliario temporal ${this.furnitureNumberToDelete} eliminado completamente`;
                showToast(message, 'success');
                bootstrap.Modal.getInstance(this.deleteModal)?.hide();
                this.onDeleteSuccess();
            } else {
                showToast(result.error || 'Error al eliminar mobiliario', 'error');
            }
        } catch (error) {
            console.error('Error deleting temporary furniture:', error);
            showToast('Error de conexion', 'error');
        } finally {
            // Re-enable button
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-trash me-1"></i>Eliminar';
            }
        }
    }

    /**
     * Reset create form
     */
    resetForm() {
        const numberInput = document.getElementById('temp-number');
        const capacityInput = document.getElementById('temp-capacity');
        const orientationSelect = document.getElementById('temp-orientation');
        const startDateInput = document.getElementById('temp-start-date');
        const endDateInput = document.getElementById('temp-end-date');

        if (numberInput) numberInput.value = '';
        if (capacityInput) capacityInput.value = '2';
        if (orientationSelect) orientationSelect.value = '0';
        if (startDateInput) startDateInput.value = '';
        if (endDateInput) endDateInput.value = '';

        this.clickPosition = { x: 100, y: 100 };
        this.selectedZoneId = null;
    }

    /**
     * Reset delete form
     */
    resetDeleteForm() {
        this.furnitureToDelete = null;
        this.furnitureNumberToDelete = null;
        this.isMultiDay = false;
        this.dateInfo = null;

        // Hide options, show single day message (default state)
        const optionsEl = document.getElementById('delete-temp-options');
        const singleDayMsgEl = document.getElementById('delete-temp-single-day-msg');
        if (optionsEl) optionsEl.style.display = 'none';
        if (singleDayMsgEl) singleDayMsgEl.style.display = 'block';
    }
}



// --- MoveMode.js ---
/**
 * Move Mode Controller
 * Manages furniture reassignment operations during move mode
 */


/**
 * Move Mode Manager Class
 * Handles unassigning and assigning furniture, undo operations,
 * and coordination with the pool panel
 */
class MoveMode {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/beach/api/move-mode',
            maxUndoStack: 20,
            ...options
        };

        // State
        this.active = false;
        this.currentDate = null;
        this.pool = [];  // Reservations in the pool
        this.selectedReservationId = null;
        this.undoStack = [];
        this.triggeredByConflict = null;  // Store conflict context if activated from conflict

        // Event callbacks (arrays to support multiple listeners)
        this.callbacks = {
            onActivate: [],
            onDeactivate: [],
            onPoolUpdate: [],
            onSelectionChange: [],
            onFurnitureHighlight: [],
            onUndo: [],
            onError: [],
            onLockBlocked: []
        };
    }

    /**
     * Register event callback
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (event in this.callbacks) {
            this.callbacks[event].push(callback);
        }
    }

    /**
     * Emit event to registered callbacks
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(cb => cb(data));
        }
    }

    /**
     * Check if move mode is active
     * @returns {boolean}
     */
    isActive() {
        return this.active;
    }

    /**
     * Activate move mode
     * @param {string} date - Current date in YYYY-MM-DD format
     * @param {Object} conflictContext - Optional conflict context if triggered by conflict resolution
     */
    async activate(date, conflictContext = null) {
        if (this.active) return;

        this.active = true;
        this.currentDate = date;
        this.pool = [];
        this.selectedReservationId = null;
        this.undoStack = [];
        this.triggeredByConflict = conflictContext;

        this.emit('onActivate', { date, conflictContext });
        showToast('Modo Mover activado', 'info');

        // Load any reservations that already need furniture assignments
        await this.loadUnassignedReservations();
    }

    /**
     * Load all reservations that have insufficient furniture for the current date
     */
    async loadUnassignedReservations() {
        try {
            const url = `${this.options.apiBaseUrl}/unassigned?date=${this.currentDate}`;
            console.log('[MoveMode] Loading unassigned reservations from:', url);

            const response = await fetch(url, {
                headers: { 'X-CSRFToken': getCSRFToken() }
            });

            if (!response.ok) {
                console.error('[MoveMode] API error:', response.status, response.statusText);
                return;
            }

            const data = await response.json();
            console.log('[MoveMode] Unassigned response:', data);

            if (data.reservation_ids && data.reservation_ids.length > 0) {
                // Load each unassigned reservation into the pool
                for (const resId of data.reservation_ids) {
                    await this.loadReservationToPool(resId);
                }
                showToast(`${data.reservation_ids.length} reserva(s) sin asignar`, 'warning');
            }
        } catch (error) {
            console.error('[MoveMode] Error loading unassigned reservations:', error);
        }
    }

    /**
     * Reset internal state to initial values
     * @private
     */
    _resetState() {
        this.active = false;
        this.currentDate = null;
        this.pool = [];
        this.selectedReservationId = null;
        this.undoStack = [];
        this.triggeredByConflict = null;
    }

    /**
     * Change the current date and refresh the pool
     * Called when user navigates to a different date while in move mode
     * @param {string} newDate - New date in YYYY-MM-DD format
     */
    async setDate(newDate) {
        if (!this.active || this.currentDate === newDate) return;

        console.log('[MoveMode] Date changed from', this.currentDate, 'to', newDate);

        // Update date
        this.currentDate = newDate;

        // Clear pool and selection (reservations from old date don't apply)
        this.pool = [];
        this.selectedReservationId = null;
        this.undoStack = []; // Undo actions are date-specific

        // Notify UI to clear
        this.emit('onPoolUpdate', { pool: this.pool });

        // Load unassigned reservations for the new date
        await this.loadUnassignedReservations();
    }

    /**
     * Deactivate move mode
     * @returns {boolean} True if deactivated, false if pool not empty
     */
    deactivate() {
        if (!this.active) return true;

        // Check if pool is empty
        const unassignedCount = this.pool.filter(r =>
            r.assignedCount < r.totalNeeded
        ).length;

        if (unassignedCount > 0) {
            showToast('Asigna todas las reservas antes de salir', 'warning');
            this.emit('onError', {
                type: 'exit_blocked',
                message: 'Pool not empty'
            });
            return false;
        }

        this._resetState();
        this.emit('onDeactivate', {});
        showToast('Modo Mover desactivado', 'info');
        return true;
    }

    /**
     * Force deactivate (used when user confirms abandoning unassigned reservations)
     */
    forceDeactivate() {
        this._resetState();
        this.emit('onDeactivate', { forced: true });
    }

    /**
     * Cancel move mode and return to conflict resolution if applicable
     * @returns {Object} Result with conflictContext if was triggered by conflict
     */
    cancelToConflict() {
        const conflictContext = this.triggeredByConflict;

        // Reset state
        this._resetState();
        this.emit('onDeactivate', {
            forced: true,
            returnToConflict: !!conflictContext,
            conflictContext
        });

        return { conflictContext };
    }

    /**
     * Get current pool
     * @returns {Array} Pool reservations
     */
    getPool() {
        return [...this.pool];
    }

    /**
     * Get selected reservation
     * @returns {Object|null} Selected reservation or null
     */
    getSelectedReservation() {
        return this.pool.find(r => r.reservation_id === this.selectedReservationId) || null;
    }

    /**
     * Select a reservation in the pool
     * @param {number} reservationId - Reservation ID to select
     */
    selectReservation(reservationId) {
        const reservation = this.pool.find(r => r.reservation_id === reservationId);
        if (!reservation) return;

        this.selectedReservationId = reservationId;
        this.emit('onSelectionChange', { reservation });

        // Request furniture highlighting based on preferences
        this.requestPreferenceHighlights(reservation.preferences);
    }

    /**
     * Deselect current reservation
     */
    deselectReservation() {
        this.selectedReservationId = null;
        this.emit('onSelectionChange', { reservation: null });
        this.emit('onFurnitureHighlight', { furniture: [], preferences: [] });
    }

    /**
     * Request preference-based furniture highlights
     * @param {Array} preferences - Preference objects
     */
    async requestPreferenceHighlights(preferences = []) {
        try {
            const preferenceCodes = preferences.map(p => p.code).join(',');
            const url = `${this.options.apiBaseUrl}/preferences-match?date=${this.currentDate}&preferences=${preferenceCodes}`;

            const response = await fetch(url, {
                headers: { 'X-CSRFToken': getCSRFToken() }
            });

            if (!response.ok) throw new Error('Error al cargar coincidencias');

            const data = await response.json();
            this.emit('onFurnitureHighlight', {
                furniture: data.furniture,
                preferences: preferences
            });
        } catch (error) {
            console.error('Error loading preference matches:', error);
        }
    }

    /**
     * Unassign furniture from a reservation
     * @param {number} reservationId - Reservation ID
     * @param {Array} furnitureIds - Furniture IDs to unassign
     * @param {boolean} isCtrlClick - Whether Ctrl was held (single furniture mode)
     * @param {Array} initialFurnitureOverride - Optional: all furniture before any unassigning (for pool tracking)
     * @returns {Promise<Object>} Result object
     */
    async unassignFurniture(reservationId, furnitureIds, isCtrlClick = false, initialFurnitureOverride = null) {
        if (!this.active) {
            return { success: false, error: 'Move mode not active' };
        }

        try {
            const result = await this._callApi('unassign', reservationId, furnitureIds);

            if (result.success && result.unassigned_count > 0) {
                this.pushUndo({
                    type: 'unassign',
                    reservation_id: reservationId,
                    furniture_ids: result.furniture_ids,
                    date: this.currentDate
                });

                await this.loadReservationToPool(reservationId, initialFurnitureOverride);
                showToast(`${result.unassigned_count} mobiliario liberado`, 'success');
            } else if (result.error === 'locked') {
                // Furniture is locked - trigger shake animation
                this.emit('onLockBlocked', {
                    reservationId,
                    furnitureIds
                });
                return result;
            } else if (result.success && result.unassigned_count === 0) {
                // Nothing was unassigned - warn user (helps debug move mode issues)
                console.warn('[MoveMode] unassign returned 0 count:', {
                    reservationId,
                    furnitureIds,
                    date: this.currentDate,
                    not_found: result.not_found
                });
                showToast('Mobiliario no encontrado para esta reserva', 'warning');
            }

            return result;
        } catch (error) {
            console.error('Error unassigning furniture:', error);
            this.emit('onError', { type: 'unassign', error });
            showToast('Error al liberar mobiliario', 'error');
            return { success: false, error: error.message };
        }
    }

    /**
     * Assign furniture to a reservation
     * @param {number} reservationId - Reservation ID
     * @param {Array} furnitureIds - Furniture IDs to assign
     * @returns {Promise<Object>} Result object
     */
    async assignFurniture(reservationId, furnitureIds) {
        if (!this.active) {
            return { success: false, error: 'Move mode not active' };
        }

        try {
            const result = await this._callApi('assign', reservationId, furnitureIds);

            if (result.success) {
                this.pushUndo({
                    type: 'assign',
                    reservation_id: reservationId,
                    furniture_ids: result.furniture_ids,
                    date: this.currentDate
                });

                await this.loadReservationToPool(reservationId);
                showToast('Asignado a mobiliario', 'success');
            } else if (result.error) {
                showToast(result.error, 'warning');
            }

            return result;
        } catch (error) {
            console.error('Error assigning furniture:', error);
            this.emit('onError', { type: 'assign', error });
            showToast('Error al asignar mobiliario', 'error');
            return { success: false, error: error.message };
        }
    }

    /**
     * Calculate the sum of furniture capacities
     * @private
     * @param {Array} furniture - Array of furniture objects
     * @returns {number} Total capacity
     */
    _calculateCapacity(furniture) {
        if (!furniture || furniture.length === 0) return 0;
        return furniture.reduce((sum, f) => sum + (f.capacity || 1), 0);
    }

    /**
     * Determine initial furniture for a pool entry
     * @private
     * @param {number} existingIndex - Index in pool, or -1 if not found
     * @param {Array} initialFurnitureOverride - Override from caller
     * @param {Array} apiFurniture - Furniture from API response
     * @returns {Array} Initial furniture to use
     */
    _resolveInitialFurniture(existingIndex, initialFurnitureOverride, apiFurniture) {
        // Check existing pool entry has non-empty initialFurniture
        // Note: empty array [] is truthy, so we must check .length
        if (existingIndex >= 0 && this.pool[existingIndex].initialFurniture?.length > 0) {
            return this.pool[existingIndex].initialFurniture;
        }
        // Use override if provided (from caller who knows the original state)
        if (initialFurnitureOverride && initialFurnitureOverride.length > 0) {
            return initialFurnitureOverride;
        }
        // Fallback to current API furniture
        return apiFurniture || [];
    }

    /**
     * Load reservation data into the pool
     * @param {number} reservationId - Reservation ID
     * @param {Array} initialFurnitureOverride - Optional: furniture that was assigned before entering pool
     */
    async loadReservationToPool(reservationId, initialFurnitureOverride = null) {
        try {
            const url = `${this.options.apiBaseUrl}/pool-data?reservation_id=${reservationId}&date=${this.currentDate}`;
            const response = await fetch(url, {
                headers: { 'X-CSRFToken': getCSRFToken() }
            });

            if (!response.ok) throw new Error('Error al cargar datos');

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            const assignedCapacity = this._calculateCapacity(data.original_furniture);
            const totalNeeded = data.num_people || 1;
            const existingIndex = this.pool.findIndex(r => r.reservation_id === reservationId);
            const initialFurniture = this._resolveInitialFurniture(
                existingIndex,
                initialFurnitureOverride,
                data.original_furniture
            );

            const poolEntry = {
                ...data,
                assignedCount: assignedCapacity,
                totalNeeded,
                isComplete: assignedCapacity >= totalNeeded,
                initialFurniture
            };

            if (existingIndex >= 0) {
                if (poolEntry.isComplete) {
                    // First show the complete state in UI
                    this.pool[existingIndex] = poolEntry;
                    this.emit('onPoolUpdate', { pool: this.pool });

                    // Then remove after brief delay for visual feedback
                    setTimeout(() => {
                        const currentIndex = this.pool.findIndex(r => r.reservation_id === reservationId);
                        if (currentIndex >= 0) {
                            this.pool.splice(currentIndex, 1);
                            if (this.selectedReservationId === reservationId) {
                                this.deselectReservation();
                            }
                            this.emit('onPoolUpdate', { pool: this.pool });
                        }
                    }, 600);
                    return poolEntry;
                } else {
                    this.pool[existingIndex] = poolEntry;
                }
            } else if (!poolEntry.isComplete) {
                this.pool.push(poolEntry);
                if (this.pool.length === 1) {
                    this.selectReservation(reservationId);
                }
            }

            this.emit('onPoolUpdate', { pool: this.pool });

            // Re-apply preference highlights if reservation is still selected
            if (this.selectedReservationId === reservationId && !poolEntry.isComplete) {
                const selectedRes = this.pool.find(r => r.reservation_id === reservationId);
                if (selectedRes?.preferences?.length > 0) {
                    this.requestPreferenceHighlights(selectedRes.preferences);
                }
            }

            return poolEntry;
        } catch (error) {
            console.error('Error loading pool data:', error);
            this.emit('onError', { type: 'pool_load', error });
            return null;
        }
    }

    /**
     * Push action to undo stack
     * @param {Object} action - Action to push
     */
    pushUndo(action) {
        this.undoStack.push(action);
        if (this.undoStack.length > this.options.maxUndoStack) {
            this.undoStack.shift();
        }
    }

    /**
     * Undo last action
     * @returns {Promise<boolean>} Success
     */
    async undo() {
        if (this.undoStack.length === 0) {
            showToast('Nada que deshacer', 'info');
            return false;
        }

        const action = this.undoStack.pop();

        try {
            if (action.type === 'unassign') {
                // Undo unassign = assign back
                await this.assignFurnitureInternal(
                    action.reservation_id,
                    action.furniture_ids
                );
            } else if (action.type === 'assign') {
                // Undo assign = unassign
                await this.unassignFurnitureInternal(
                    action.reservation_id,
                    action.furniture_ids
                );
            }

            // Reload pool data
            await this.loadReservationToPool(action.reservation_id);

            this.emit('onUndo', { action });
            showToast('Acción deshecha', 'success');
            return true;
        } catch (error) {
            console.error('Error undoing action:', error);
            // Put action back on stack
            this.undoStack.push(action);
            showToast('Error al deshacer', 'error');
            return false;
        }
    }

    /**
     * Make a move mode API call
     * @private
     * @param {string} action - 'assign' or 'unassign'
     * @param {number} reservationId - Reservation ID
     * @param {Array} furnitureIds - Furniture IDs
     * @returns {Promise<Object>} API response
     */
    async _callApi(action, reservationId, furnitureIds) {
        const response = await fetch(`${this.options.apiBaseUrl}/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                reservation_id: reservationId,
                furniture_ids: furnitureIds,
                date: this.currentDate
            })
        });
        return response.json();
    }

    /**
     * Internal assign without undo tracking
     * @param {number} reservationId - Reservation ID
     * @param {Array} furnitureIds - Furniture IDs to assign
     * @returns {Promise<Object>} API response
     */
    async assignFurnitureInternal(reservationId, furnitureIds) {
        return this._callApi('assign', reservationId, furnitureIds);
    }

    /**
     * Internal unassign without undo tracking
     * @param {number} reservationId - Reservation ID
     * @param {Array} furnitureIds - Furniture IDs to unassign
     * @returns {Promise<Object>} API response
     */
    async unassignFurnitureInternal(reservationId, furnitureIds) {
        return this._callApi('unassign', reservationId, furnitureIds);
    }

    /**
     * Check if undo is available
     * @returns {boolean}
     */
    canUndo() {
        return this.undoStack.length > 0;
    }

    /**
     * Get undo stack size
     * @returns {number}
     */
    getUndoCount() {
        return this.undoStack.length;
    }

    /**
     * Handle keyboard shortcuts
     * @param {KeyboardEvent} event
     */
    handleKeyboard(event) {
        if (!this.active) return;

        // Ctrl+Z for undo
        if (event.ctrlKey && event.key === 'z') {
            event.preventDefault();
            this.undo();
        }

        // Escape to exit (if pool empty)
        if (event.key === 'Escape') {
            this.deactivate();
        }
    }
}


// --- MoveModePanel.js ---
/**
 * Move Mode Panel Component
 * Displays the pool of reservations waiting to be assigned during move mode
 */


/**
 * Move Mode Panel Class
 * Renders and manages the side panel showing unassigned reservations
 */
class MoveModePanel {
    // Interaction timing constants
    static DOUBLE_CLICK_THRESHOLD = 300;  // ms between clicks for double-click
    static LONG_PRESS_DELAY = 500;        // ms to trigger long-press
    static MOVE_THRESHOLD = 10;           // px movement to cancel long-press
    static TOOLTIP_AUTO_DISMISS = 3000;   // ms before mobile tooltip auto-hides

    constructor(containerId, moveMode) {
        this.container = document.getElementById(containerId);
        this.moveMode = moveMode;

        // Filter state
        this.filters = {
            type: 'all',  // all, interno, externo
            vip: false,
            hasPreferences: false
        };

        // Create panel structure if container exists
        if (this.container) {
            this.createPanelStructure();
            this.setupEventListeners();
        } else {
            console.warn(`MoveModePanel: Container #${containerId} not found`);
        }
    }

    /**
     * Create the panel HTML structure
     */
    createPanelStructure() {
        this.container.innerHTML = `
            <!-- Collapsed bar - always visible in the 48px strip when collapsed -->
            <div class="collapsed-bar">
                <button type="button" class="collapse-toggle" id="moveModeCollapseBtn" title="Colapsar panel">
                    <i class="fas fa-chevron-right"></i>
                </button>
                <div class="collapsed-thumbnails" id="collapsedThumbnails"></div>
            </div>
            <div class="move-mode-panel">
                <div class="move-mode-panel-header">
                    <h5>
                        <i class="fas fa-exchange-alt"></i>
                        Modo Mover
                        <span class="badge" id="moveModePoolCount">0</span>
                    </h5>
                    <div class="header-actions">
                        <button type="button" class="btn collapse-btn" id="moveModeCollapseBtnHeader" title="Colapsar panel" aria-label="Colapsar panel">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                        <button type="button" class="btn" id="moveModeExitBtn" title="Cerrar" aria-label="Cerrar panel">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>

                <div class="move-mode-filters" id="moveModeFilters">
                    <div class="filter-group">
                        <button type="button" class="filter-btn active" data-filter="type" data-value="all">Todos</button>
                        <button type="button" class="filter-btn" data-filter="type" data-value="interno">Interno</button>
                        <button type="button" class="filter-btn" data-filter="type" data-value="externo">Externo</button>
                    </div>
                    <div class="filter-toggles">
                        <label class="filter-toggle" title="Solo VIP">
                            <input type="checkbox" id="filterVip"> <i class="fas fa-star"></i>
                        </label>
                        <label class="filter-toggle" title="Con preferencias">
                            <input type="checkbox" id="filterPrefs"> <i class="fas fa-heart"></i>
                        </label>
                    </div>
                </div>

                <div class="move-mode-panel-body" id="moveModePoolList">
                    <div class="move-mode-empty-state">
                        <i class="fas fa-hand-pointer fa-2x text-muted mb-2"></i>
                        <p class="text-muted mb-0">Toca mobiliario ocupado para liberarlo</p>
                        <p class="text-muted small mb-0">Mantén presionado para liberar todo</p>
                    </div>
                </div>

                <!-- Keyboard shortcuts - desktop only -->
                <div class="move-mode-shortcuts">
                    <span><kbd>Clic</kbd> 1 item</span>
                    <span><kbd>Ctrl+Clic</kbd> Todos</span>
                    <span><kbd>Ctrl+Z</kbd> Deshacer</span>
                </div>

                <!-- Footer with action buttons -->
                <div class="move-mode-panel-footer">
                    <button type="button" class="move-mode-footer-btn btn-exit" id="moveModeExitFooterBtn">
                        Salir
                    </button>
                    <button type="button" class="move-mode-footer-btn btn-undo" id="moveModeUndoBtn" disabled>
                        <i class="fas fa-undo"></i>
                        <span>Deshacer</span>
                        <span class="undo-count" id="moveModeUndoCount"></span>
                    </button>
                </div>

                <div class="move-mode-legend" id="moveModeLegend" style="display: none;">
                    <div class="legend-header">Buscando:</div>
                    <div class="legend-items" id="moveModeLegendItems"></div>
                </div>
            </div>
        `;

        // Cache elements
        this.poolCount = document.getElementById('moveModePoolCount');
        this.poolList = document.getElementById('moveModePoolList');
        this.exitBtn = document.getElementById('moveModeExitBtn');
        this.exitFooterBtn = document.getElementById('moveModeExitFooterBtn');
        this.undoBtn = document.getElementById('moveModeUndoBtn');
        this.undoCount = document.getElementById('moveModeUndoCount');
        this.legend = document.getElementById('moveModeLegend');
        this.legendItems = document.getElementById('moveModeLegendItems');
        this.collapseBtn = document.getElementById('moveModeCollapseBtn');
        this.collapseBtnHeader = document.getElementById('moveModeCollapseBtnHeader');
        this.collapsedThumbnails = document.getElementById('collapsedThumbnails');
        this.filterVip = document.getElementById('filterVip');
        this.filterPrefs = document.getElementById('filterPrefs');
        this.filterBtns = document.querySelectorAll('.filter-btn[data-filter="type"]');

        // Swipe gesture state
        this.swipeState = {
            startX: 0,
            currentX: 0,
            isDragging: false
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Exit button (header)
        this.exitBtn?.addEventListener('click', () => {
            this.moveMode.deactivate();
        });

        // Exit button (footer)
        this.exitFooterBtn?.addEventListener('click', () => {
            this.moveMode.deactivate();
        });

        // Undo button
        this.undoBtn?.addEventListener('click', () => {
            this.moveMode.undo();
        });

        // Collapse button (in collapsed bar)
        this.collapseBtn?.addEventListener('click', () => {
            this.toggleCollapse();
        });

        // Collapse button (in header - visible when expanded)
        this.collapseBtnHeader?.addEventListener('click', () => {
            this.toggleCollapse();
        });

        // Filter type buttons
        this.filterBtns?.forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.filters.type = btn.dataset.value;
                this.renderPool(this.moveMode.getPool());
            });
        });

        // Filter VIP checkbox
        this.filterVip?.addEventListener('change', () => {
            this.filters.vip = this.filterVip.checked;
            this.renderPool(this.moveMode.getPool());
        });

        // Filter preferences checkbox
        this.filterPrefs?.addEventListener('change', () => {
            this.filters.hasPreferences = this.filterPrefs.checked;
            this.renderPool(this.moveMode.getPool());
        });

        // Setup swipe-to-close gesture
        this.setupSwipeGesture();

        // MoveMode events
        this.moveMode.on('onPoolUpdate', (data) => this.renderPool(data.pool));
        this.moveMode.on('onSelectionChange', (data) => this.updateSelection(data.reservation));
        this.moveMode.on('onFurnitureHighlight', (data) => this.updateLegend(data.preferences));
        this.moveMode.on('onActivate', () => this.show());
        this.moveMode.on('onDeactivate', () => this.hide());
        this.moveMode.on('onUndo', () => this.updateUndoState());
    }

    /**
     * Setup swipe-to-close gesture for mobile
     */
    setupSwipeGesture() {
        if (!this.container) return;

        const panel = this.container;

        panel.addEventListener('touchstart', (e) => {
            // Only initiate from left edge (first 50px)
            if (e.touches[0].clientX < 50) {
                this.swipeState.startX = e.touches[0].clientX;
                this.swipeState.isDragging = true;
                panel.classList.add('dragging');
            }
        }, { passive: true });

        panel.addEventListener('touchmove', (e) => {
            if (!this.swipeState.isDragging) return;
            this.swipeState.currentX = e.touches[0].clientX;
            const deltaX = this.swipeState.currentX - this.swipeState.startX;

            // Only allow swipe right (to close)
            if (deltaX > 0) {
                panel.style.transform = `translateX(${deltaX}px)`;
            }
        }, { passive: true });

        panel.addEventListener('touchend', () => {
            if (!this.swipeState.isDragging) return;
            this.swipeState.isDragging = false;
            panel.classList.remove('dragging');

            const deltaX = this.swipeState.currentX - this.swipeState.startX;
            if (deltaX > 100) { // Threshold to close
                this.moveMode.deactivate();
            } else {
                panel.style.transform = '';
            }
            this.swipeState.startX = 0;
            this.swipeState.currentX = 0;
        });

        panel.addEventListener('touchcancel', () => {
            this.swipeState.isDragging = false;
            panel.classList.remove('dragging');
            panel.style.transform = '';
            this.swipeState.startX = 0;
            this.swipeState.currentX = 0;
        });
    }

    /**
     * Show the panel
     */
    show() {
        this.container?.classList.add('visible');

        // Notify modal state manager (closes other modals, bottom bar, keeps map interactive)
        if (window.modalStateManager) {
            window.modalStateManager.openModal('move-mode', this);
        }

        this.updateUndoState();
    }

    /**
     * Hide the panel
     */
    hide() {
        this.container?.classList.remove('visible');
        this.container?.classList.remove('collapsed');

        // Notify modal state manager
        if (window.modalStateManager) {
            window.modalStateManager.closeModal('move-mode');
        }

        this._hideThumbnailTooltip();
    }

    /**
     * Toggle panel collapsed state
     */
    toggleCollapse() {
        const isCurrentlyCollapsed = this.container?.classList.contains('collapsed');
        this.container?.classList.toggle('collapsed');

        // Notify modal state manager
        if (window.modalStateManager) {
            if (isCurrentlyCollapsed) {
                window.modalStateManager.expandModal('move-mode');
            } else {
                window.modalStateManager.collapseModal('move-mode');
            }
        }
    }

    /**
     * Check if reservation has VIP status
     * @private
     * @param {Object} res - Reservation object
     * @returns {boolean} True if VIP
     */
    _isVip(res) {
        if (res.is_vip) return true;
        return res.tags?.some(t =>
            t.name?.toLowerCase().includes('vip') ||
            t.code?.toLowerCase().includes('vip')
        ) || false;
    }

    /**
     * Apply filters to pool
     * @param {Array} pool - Full pool
     * @returns {Array} Filtered pool
     */
    applyFilters(pool) {
        return pool.filter(res => {
            if (this.filters.type !== 'all' && res.customer_type !== this.filters.type) {
                return false;
            }
            if (this.filters.vip && !this._isVip(res)) {
                return false;
            }
            if (this.filters.hasPreferences && (!res.preferences || res.preferences.length === 0)) {
                return false;
            }
            return true;
        });
    }

    /**
     * Render the pool of reservations
     * @param {Array} pool - Pool reservations
     */
    renderPool(pool) {
        if (!this.poolList) return;

        // Apply filters
        const filteredPool = this.applyFilters(pool);

        // Update count badge (show filtered/total)
        this.poolCount.textContent = filteredPool.length === pool.length
            ? pool.length
            : `${filteredPool.length}/${pool.length}`;

        if (pool.length === 0) {
            this.poolList.innerHTML = `
                <div class="move-mode-empty-state">
                    <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
                    <p class="text-muted mb-0">Todas las reservas asignadas</p>
                </div>
            `;
            // Clear collapsed thumbnails when pool is empty
            this.renderCollapsedThumbnails(pool);
            return;
        }

        if (filteredPool.length === 0) {
            this.poolList.innerHTML = `
                <div class="move-mode-empty-state">
                    <i class="fas fa-filter fa-2x text-muted mb-2"></i>
                    <p class="text-muted mb-0">Sin resultados con estos filtros</p>
                </div>
            `;
            // Still show collapsed thumbnails for full pool (unfiltered)
            this.renderCollapsedThumbnails(pool);
            return;
        }

        this.poolList.innerHTML = filteredPool.map(res => this.renderReservationCard(res)).join('');

        // Add click handlers to cards
        this.poolList.querySelectorAll('.move-mode-card').forEach(card => {
            card.addEventListener('click', () => {
                const resId = parseInt(card.dataset.reservationId);
                this.moveMode.selectReservation(resId);
            });
        });

        // Add restore handlers
        this.poolList.querySelectorAll('.restore-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const card = btn.closest('.move-mode-card');
                const resId = parseInt(card.dataset.reservationId);
                const res = this.moveMode.pool.find(r => r.reservation_id === resId);

                // If triggered by conflict, cancel and return to conflict view - Issue #7
                if (this.moveMode.triggeredByConflict) {
                    const result = this.moveMode.cancelToConflict();
                    if (result.conflictContext) {
                        document.dispatchEvent(new CustomEvent('moveMode:returnToConflict', {
                            detail: result.conflictContext
                        }));
                    }
                    return;
                }

                // Normal restore: assign back to original furniture
                // Use initialFurniture (what it had when first entering pool)
                if (!res || !res.initialFurniture?.length) {
                    showToast('No hay posición original para restaurar', 'warning');
                    return;
                }

                // Get original furniture IDs (furniture_id is the actual furniture, id is the assignment record)
                const originalIds = res.initialFurniture.map(f => f.furniture_id || f.id);

                // Assign back to original furniture
                const result = await this.moveMode.assignFurniture(resId, originalIds);
                if (result.success) {
                    showToast('Posición original restaurada', 'success');
                }
            });
        });

        // Edit button handlers - Issue #8
        this.poolList.querySelectorAll('.edit-reservation-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const resId = parseInt(btn.dataset.reservationId);

                // Dispatch event to open edit modal
                document.dispatchEvent(new CustomEvent('moveMode:editReservation', {
                    detail: { reservationId: resId }
                }));
            });
        });

        this.updateUndoState();

        // Also update collapsed thumbnails
        this.renderCollapsedThumbnails(pool);
    }

    /**
     * Render mini-cards for collapsed state
     * @param {Array} pool - Pool reservations
     */
    renderCollapsedThumbnails(pool) {
        if (!this.collapsedThumbnails) return;

        if (pool.length === 0) {
            this.collapsedThumbnails.innerHTML = '';
            return;
        }

        const maxThumbnails = 4;
        const visiblePool = pool.slice(0, maxThumbnails);
        const remainingCount = pool.length - maxThumbnails;

        let html = visiblePool.map(res => {
            const isVip = this._isVip(res);
            const isSelected = res.reservation_id === this.moveMode.selectedReservationId;
            const isComplete = res.isComplete || res.assignedCount >= res.totalNeeded;
            const vipClass = isVip ? 'is-vip' : '';
            const selectedClass = isSelected ? 'selected' : '';
            const completeClass = isComplete ? 'is-complete' : '';
            const vipStar = isVip ? '<i class="fas fa-star vip-star"></i>' : '';

            // Mini progress dots (max 4 dots for space)
            const totalDots = Math.min(res.totalNeeded, 4);
            const filledDots = Math.min(res.assignedCount, totalDots);
            let progressHtml = '';
            for (let i = 0; i < totalDots; i++) {
                const filled = i < filledDots ? 'filled' : '';
                progressHtml += `<span class="mini-dot ${filled}"></span>`;
            }

            return `
                <div class="collapsed-thumbnail ${vipClass} ${selectedClass} ${completeClass}"
                     data-reservation-id="${res.reservation_id}"
                     data-customer-name="${res.customer_name || ''}"
                     data-room="${res.room_number || ''}">
                    ${vipStar}
                    <span class="person-count">${isComplete ? '✓' : res.num_people}</span>
                    <div class="mini-progress">${progressHtml}</div>
                    ${isSelected ? `<div class="selected-info">
                        <span class="selected-name">${res.customer_name?.split(' ')[0] || ''}</span>
                        ${res.room_number ? `<span class="selected-room">${res.room_number}</span>` : ''}
                    </div>` : ''}
                </div>
            `;
        }).join('');

        // Add "+N" badge if there are more reservations
        if (remainingCount > 0) {
            html += `
                <div class="collapsed-thumbnail more-badge">
                    +${remainingCount}
                </div>
            `;
        }

        this.collapsedThumbnails.innerHTML = html;

        // Setup interaction handlers (click, double-click, hover, touch)
        this._setupThumbnailInteractions(pool);
    }

    /**
     * Setup thumbnail interaction handlers (click, double-click, hover, touch)
     * @private
     * @param {Array} pool - Pool reservations
     */
    _setupThumbnailInteractions(pool) {
        const thumbnails = this.collapsedThumbnails.querySelectorAll(
            '.collapsed-thumbnail[data-reservation-id]'
        );

        thumbnails.forEach(thumb => {
            const resId = parseInt(thumb.dataset.reservationId);
            const reservation = pool.find(r => r.reservation_id === resId);
            if (!reservation) return;

            // Track click timing for double-click detection
            let lastClickTime = 0;

            // Click handler: select without expand, double-click expands
            thumb.addEventListener('click', () => {
                const now = Date.now();
                if (now - lastClickTime < MoveModePanel.DOUBLE_CLICK_THRESHOLD) {
                    // Double-click: expand + select
                    this.container?.classList.remove('collapsed');
                    this.moveMode.selectReservation(resId);
                } else {
                    // Single click: select only (no expand)
                    this.moveMode.selectReservation(resId);
                }
                lastClickTime = now;
            });

            // Hover handlers (desktop only)
            if (window.matchMedia('(hover: hover)').matches) {
                thumb.addEventListener('mouseenter', () => {
                    this._showThumbnailTooltip(thumb, reservation);
                });
                thumb.addEventListener('mouseleave', () => {
                    this._hideThumbnailTooltip();
                });
            }

            // Touch handlers (mobile)
            this._setupThumbnailTouchHandlers(thumb, reservation);
        });

        // "+N" badge just expands panel
        const moreBadge = this.collapsedThumbnails.querySelector('.more-badge');
        moreBadge?.addEventListener('click', () => {
            this.container?.classList.remove('collapsed');
        });
    }

    /**
     * Setup touch handlers for long-press tooltip on mobile
     * @private
     * @param {HTMLElement} thumb - Thumbnail element
     * @param {Object} reservation - Reservation data
     */
    _setupThumbnailTouchHandlers(thumb, reservation) {
        let longPressTimer = null;
        let touchStartX = 0;
        let touchStartY = 0;

        thumb.addEventListener('touchstart', (e) => {
            if (e.touches.length !== 1) return;

            const touch = e.touches[0];
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;

            longPressTimer = setTimeout(() => {
                // Haptic feedback
                if (navigator.vibrate) {
                    navigator.vibrate(50);
                }
                this._showThumbnailTooltip(thumb, reservation, true);
            }, MoveModePanel.LONG_PRESS_DELAY);
        }, { passive: true });

        thumb.addEventListener('touchmove', (e) => {
            if (!longPressTimer) return;

            const touch = e.touches[0];
            const deltaX = Math.abs(touch.clientX - touchStartX);
            const deltaY = Math.abs(touch.clientY - touchStartY);

            if (deltaX > MoveModePanel.MOVE_THRESHOLD || deltaY > MoveModePanel.MOVE_THRESHOLD) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        }, { passive: true });

        thumb.addEventListener('touchend', () => {
            if (longPressTimer) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        });

        thumb.addEventListener('touchcancel', () => {
            if (longPressTimer) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        });
    }

    /**
     * Create the tooltip element if not exists
     * @private
     */
    _createThumbnailTooltip() {
        if (this.thumbnailTooltip) return;

        this.thumbnailTooltip = document.createElement('div');
        this.thumbnailTooltip.className = 'collapsed-bar-tooltip';
        document.body.appendChild(this.thumbnailTooltip);
    }

    /**
     * Show tooltip for a thumbnail
     * @private
     * @param {HTMLElement} thumb - Thumbnail element
     * @param {Object} reservation - Reservation data
     * @param {boolean} isMobile - Whether triggered from mobile long-press
     */
    _showThumbnailTooltip(thumb, reservation, isMobile = false) {
        this._createThumbnailTooltip();

        // Build tooltip content
        let content = `<div class="tooltip-name">${reservation.customer_name}</div>`;

        if (reservation.room_number) {
            content += `<div class="tooltip-room">Hab. ${reservation.room_number}</div>`;
        }

        // Progress info
        content += `<div class="tooltip-progress">${reservation.assignedCount} de ${reservation.totalNeeded} asignados</div>`;

        // Render preferences (max 6 icons)
        if (reservation.preferences && reservation.preferences.length > 0) {
            const maxPrefs = 6;
            const visiblePrefs = reservation.preferences.slice(0, maxPrefs);
            const prefIcons = visiblePrefs.map(p => {
                const icon = this._normalizeIconClass(p.icon);
                return `<div class="tooltip-pref-icon" title="${p.name}"><i class="${icon}"></i></div>`;
            }).join('');
            content += `<div class="tooltip-preferences">${prefIcons}</div>`;

            if (reservation.preferences.length > maxPrefs) {
                content += `<div class="tooltip-room">+${reservation.preferences.length - maxPrefs} más</div>`;
            }
        }

        if (isMobile) {
            content += `<div class="tooltip-dismiss-hint">Toca para cerrar</div>`;
        }

        this.thumbnailTooltip.innerHTML = content;
        this.thumbnailTooltip.style.display = 'block';
        this.thumbnailTooltip.classList.remove('above'); // Reset position modifier

        // Position tooltip to the left of the thumbnail
        const thumbRect = thumb.getBoundingClientRect();
        const tooltipRect = this.thumbnailTooltip.getBoundingClientRect();

        let left = thumbRect.left - tooltipRect.width - 16; // 16px gap + arrow
        let top = thumbRect.top + (thumbRect.height / 2) - (tooltipRect.height / 2);

        // Keep within viewport
        if (top < 10) top = 10;
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = window.innerHeight - tooltipRect.height - 10;
        }
        if (left < 10) {
            // If not enough space on left, position above the thumbnail
            left = thumbRect.left - tooltipRect.width / 2;
            top = thumbRect.top - tooltipRect.height - 10;
            this.thumbnailTooltip.classList.add('above'); // Arrow points down
        }

        this.thumbnailTooltip.style.left = `${left}px`;
        this.thumbnailTooltip.style.top = `${top}px`;

        // Auto-dismiss on mobile
        if (isMobile) {
            this._clearTooltipDismissTimer();
            this.tooltipDismissTimer = setTimeout(() => {
                this._hideThumbnailTooltip();
            }, MoveModePanel.TOOLTIP_AUTO_DISMISS);

            // Also dismiss on next tap anywhere
            const dismissOnTap = () => {
                this._hideThumbnailTooltip();
                document.removeEventListener('touchstart', dismissOnTap);
            };
            setTimeout(() => {
                document.addEventListener('touchstart', dismissOnTap, { once: true });
            }, 100);
        }
    }

    /**
     * Hide the thumbnail tooltip
     * @private
     */
    _hideThumbnailTooltip() {
        if (this.thumbnailTooltip) {
            this.thumbnailTooltip.style.display = 'none';
        }
        this._clearTooltipDismissTimer();
    }

    /**
     * Clear the tooltip auto-dismiss timer
     * @private
     */
    _clearTooltipDismissTimer() {
        if (this.tooltipDismissTimer) {
            clearTimeout(this.tooltipDismissTimer);
            this.tooltipDismissTimer = null;
        }
    }

    /**
     * Normalize icon class to ensure proper FontAwesome prefix
     * @private
     * @param {string} icon - Icon class string
     * @returns {string} Normalized icon class
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

    /**
     * Update selected class on collapsed thumbnails
     * @private
     * @param {number|null} selectedId - Selected reservation ID
     */
    _updateCollapsedThumbnailSelection(selectedId) {
        if (!this.collapsedThumbnails) return;

        this.collapsedThumbnails.querySelectorAll('.collapsed-thumbnail[data-reservation-id]')
            .forEach(thumb => {
                const resId = parseInt(thumb.dataset.reservationId);
                if (resId === selectedId) {
                    thumb.classList.add('selected');
                } else {
                    thumb.classList.remove('selected');
                }
            });
    }

    /**
     * Get furniture numbers display string
     * @private
     * @param {Object} res - Reservation data
     * @returns {string} Comma-separated furniture numbers or '-'
     */
    _getFurnitureDisplay(res) {
        const furniture = res.initialFurniture?.length > 0
            ? res.initialFurniture
            : res.original_furniture;
        if (!furniture || furniture.length === 0) return '-';
        return furniture.map(f => f.number || f.furniture_number).join(', ');
    }

    /**
     * Render a single reservation card
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderReservationCard(res) {
        const isSelected = res.reservation_id === this.moveMode.selectedReservationId;
        const selectedClass = isSelected ? 'selected' : '';
        const progressDots = this.renderProgressDots(res.assignedCount, res.totalNeeded);
        const prefDots = this.renderPreferenceDots(res.preferences?.length || 0);
        const multidayBadge = res.is_multiday
            ? `<span class="badge bg-info ms-1" title="${res.total_days} días">📅${res.total_days}</span>`
            : '';
        const roomDisplay = res.room_number
            ? `<span class="badge bg-primary me-1"><i class="fas fa-door-open me-1"></i>${res.room_number}</span>`
            : '';

        return `
            <div class="move-mode-card ${selectedClass}" data-reservation-id="${res.reservation_id}">
                <div class="card-header">
                    ${roomDisplay}
                    <span class="customer-name">${res.customer_name}</span>
                    ${multidayBadge}
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span><i class="fas fa-users me-1"></i>${res.num_people} personas</span>
                        <span class="preference-dots">${prefDots}</span>
                    </div>
                    <div class="text-muted small">
                        <i class="fas fa-map-marker-alt me-1"></i>Era: ${this._getFurnitureDisplay(res)}
                    </div>
                    <div class="progress-indicator mt-2">
                        ${progressDots}
                        <span class="progress-text">${res.assignedCount} de ${res.totalNeeded}</span>
                    </div>
                </div>
                ${isSelected ? this.renderExpandedContent(res) : ''}
            </div>
        `;
    }

    /**
     * Render expanded content for selected reservation
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderExpandedContent(res) {
        const preferences = res.preferences?.map(p =>
            `<div class="preference-item"><span class="pref-icon">${p.icon || '⭐'}</span> ${p.name}</div>`
        ).join('') || '<span class="text-muted">Sin preferencias</span>';

        const notes = res.notes
            ? `<div class="notes-section"><i class="fas fa-sticky-note me-1"></i>${res.notes}</div>`
            : '';

        const dayAssignments = res.is_multiday && res.day_assignments
            ? this.renderDayAssignments(res)
            : '';

        // Dynamic button text based on conflict context - Issue #7
        const restoreButtonText = this.moveMode.triggeredByConflict
            ? 'Cancelar y volver'
            : 'Restaurar';
        const restoreButtonIcon = this.moveMode.triggeredByConflict
            ? 'fa-arrow-left'
            : 'fa-undo';

        return `
            <div class="card-expanded">
                <div class="preferences-section">
                    <strong>Preferencias:</strong>
                    ${preferences}
                </div>
                ${notes}
                ${dayAssignments}
                <div class="expanded-actions mt-2">
                    <button type="button" class="btn btn-sm btn-outline-primary edit-reservation-btn"
                            data-reservation-id="${res.reservation_id}">
                        <i class="fas fa-edit me-1"></i>Editar
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary restore-btn">
                        <i class="fas ${restoreButtonIcon} me-1"></i>${restoreButtonText}
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render day assignments for multi-day reservations
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderDayAssignments(res) {
        const days = Object.entries(res.day_assignments || {}).map(([date, furniture]) => {
            const isToday = date === res.target_date;
            const todayBadge = isToday ? ' <span class="badge bg-warning">hoy</span>' : '';
            return `<div class="day-assignment ${isToday ? 'today' : ''}">${formatDateDisplay(date)}${todayBadge}: ${furniture}</div>`;
        }).join('');

        return `
            <div class="days-section mt-2">
                <strong>Días de reserva:</strong>
                ${days}
            </div>
        `;
    }

    /**
     * Render progress dots
     * @param {number} assigned - Number assigned
     * @param {number} total - Total needed
     * @returns {string} HTML string
     */
    renderProgressDots(assigned, total) {
        const dots = [];
        for (let i = 0; i < total; i++) {
            const filled = i < assigned ? 'filled' : '';
            dots.push(`<span class="progress-dot ${filled}"></span>`);
        }
        return dots.join('');
    }

    /**
     * Render preference dots indicator
     * @param {number} count - Preference count
     * @returns {string} HTML string
     */
    renderPreferenceDots(count) {
        if (count === 0) return '';
        const filled = '●'.repeat(Math.min(count, 3));
        const empty = '○'.repeat(Math.max(0, 3 - count));
        return `<span title="${count} preferencias">${filled}${empty}</span>`;
    }

    /**
     * Update selection state
     * @param {Object|null} reservation - Selected reservation or null
     */
    updateSelection(reservation) {
        // Re-render to update selection state (for expanded cards)
        this.renderPool(this.moveMode.getPool());

        // Update collapsed thumbnail selection state directly (faster, no full re-render)
        this._updateCollapsedThumbnailSelection(reservation?.reservation_id);

        // Legend is hidden - furniture highlighting on map shows matches instead
        if (this.legend) {
            this.legend.style.display = 'none';
        }
    }

    /**
     * Update the preference legend
     * @param {Array} preferences - Preferences to display
     */
    updateLegend(preferences) {
        // Legend is hidden - furniture highlighting on map shows matches instead
        if (this.legend) {
            this.legend.style.display = 'none';
        }
    }

    /**
     * Update undo button state
     */
    updateUndoState() {
        const canUndo = this.moveMode.canUndo();
        const undoCount = this.moveMode.getUndoCount();

        if (this.undoBtn) {
            this.undoBtn.disabled = !canUndo;
        }

        if (this.undoCount) {
            this.undoCount.textContent = canUndo ? `(${undoCount})` : '';
        }
    }
}


// --- Global assignments (from map/index.js) ---
window.BeachMap = BeachMap;
