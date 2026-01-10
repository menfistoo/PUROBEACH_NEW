# Offline Functionality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable staff to view today's map and reservations when internet connection fails.

**Architecture:** IndexedDB storage with connectivity detection. OfflineManager orchestrates sync, storage, and UI state. BeachMap.js loads cached data when offline.

**Tech Stack:** JavaScript ES6 modules, IndexedDB API, Navigator online/offline events

---

## Task 1: Create IndexedDB Storage Module

**Files:**
- Create: `static/js/offline/storage.js`

**Step 1: Create the storage module**

```javascript
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
export async function openDatabase() {
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
export async function saveMapData(date, data) {
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
export async function getMapData(date) {
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
export async function saveSyncMeta(meta) {
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
export async function getSyncMeta() {
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
export async function clearOldData(todayDate) {
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
```

**Step 2: Commit**

```bash
git add static/js/offline/storage.js
git commit -m "feat(offline): add IndexedDB storage module

Handles map data persistence with date-keyed storage.
Includes sync metadata and old data cleanup."
```

---

## Task 2: Create Connectivity Manager

**Files:**
- Create: `static/js/offline/connectivity.js`

**Step 1: Create the connectivity module**

```javascript
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
export class ConnectivityManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.callbacks = {
            online: [],
            offline: []
        };
        this.healthCheckTimer = null;
    }

    /**
     * Start monitoring connectivity
     */
    start() {
        // Browser events
        window.addEventListener('online', () => this._handleOnline());
        window.addEventListener('offline', () => this._handleOffline());

        // Periodic health check (confirms actual connectivity)
        this._startHealthCheck();

        // Initial check
        this._checkHealth();
    }

    /**
     * Stop monitoring
     */
    stop() {
        window.removeEventListener('online', this._handleOnline);
        window.removeEventListener('offline', this._handleOffline);

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
```

**Step 2: Commit**

```bash
git add static/js/offline/connectivity.js
git commit -m "feat(offline): add connectivity manager

Monitors network status using browser events and health checks.
Notifies registered callbacks on state changes."
```

---

## Task 3: Create Offline Manager (Orchestrator)

**Files:**
- Create: `static/js/offline/offline-manager.js`

**Step 1: Create the offline manager module**

```javascript
/**
 * Offline Manager
 * Orchestrates sync, storage, and UI state for offline functionality
 */

import { ConnectivityManager } from './connectivity.js';
import {
    saveMapData,
    getMapData,
    saveSyncMeta,
    getSyncMeta,
    clearOldData
} from './storage.js';

const SYNC_INTERVAL = 5 * 60 * 1000; // 5 minutes
const STALE_THRESHOLD = 5 * 60 * 1000; // 5 minutes

/**
 * OfflineManager class
 * Main controller for offline functionality
 */
export class OfflineManager {
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
     * @returns {boolean}
     */
    isOnline() {
        return this.connectivity.isOnline;
    }

    /**
     * Get last sync time
     * @returns {Date|null}
     */
    getLastSyncTime() {
        return this.lastSyncTime;
    }

    /**
     * Format last sync time for display (HH:MM)
     * @returns {string}
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
     * @returns {Promise<Object|null>} - Synced data or null on failure
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
     * @returns {Promise<Object|null>}
     */
    async loadCachedData() {
        const cached = await getMapData(this.currentDate);
        return cached ? cached.data : null;
    }

    /**
     * Update current date (when user changes date)
     * @param {string} date - New date YYYY-MM-DD
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
     */
    async _handleOnline() {
        this.callbacks.onOnline();

        // Auto-sync when reconnecting
        await this.sync();
    }

    /**
     * Handle going offline
     * @private
     */
    _handleOffline() {
        this.callbacks.onOffline();
    }

    /**
     * Check if cached data is stale
     * @private
     * @returns {boolean}
     */
    _isDataStale() {
        if (!this.lastSyncTime) return true;
        return (Date.now() - this.lastSyncTime.getTime()) > STALE_THRESHOLD;
    }

    /**
     * Start auto-sync timer
     * @private
     */
    _startAutoSync() {
        this.syncTimer = setInterval(() => {
            if (this.connectivity.isOnline) {
                this.sync();
            }
        }, SYNC_INTERVAL);
    }
}
```

**Step 2: Commit**

```bash
git add static/js/offline/offline-manager.js
git commit -m "feat(offline): add offline manager orchestrator

Coordinates sync, storage, and UI state.
Auto-syncs every 5 minutes when online."
```

---

## Task 4: Create Module Index

**Files:**
- Create: `static/js/offline/index.js`

**Step 1: Create the index module**

```javascript
/**
 * Offline Module Exports
 */

export { OfflineManager } from './offline-manager.js';
export { ConnectivityManager } from './connectivity.js';
export {
    openDatabase,
    saveMapData,
    getMapData,
    saveSyncMeta,
    getSyncMeta,
    clearOldData
} from './storage.js';
```

**Step 2: Commit**

```bash
git add static/js/offline/index.js
git commit -m "feat(offline): add module index exports"
```

---

## Task 5: Add Health Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/map_data.py`

**Step 1: Add health endpoint to the register_routes function**

After the existing routes in `register_routes`, add:

```python
    @bp.route('/health')
    def health_check():
        """
        Health check endpoint for connectivity detection.
        Returns simple OK response.
        """
        return jsonify({'status': 'ok'})
```

**Step 2: Commit**

```bash
git add blueprints/beach/routes/api/map_data.py
git commit -m "feat(offline): add health check endpoint

Simple /api/health endpoint for connectivity detection."
```

---

## Task 6: Add Offline CSS Styles

**Files:**
- Create: `static/css/offline.css`

**Step 1: Create the CSS file**

```css
/**
 * Offline Functionality Styles
 * Uses PuroBeach Design System variables
 */

/* =============================================================================
   OFFLINE BANNER
   ============================================================================= */

.offline-banner {
    position: fixed;
    top: 0;
    left: var(--sidebar-width);
    right: 0;
    background: linear-gradient(135deg, var(--color-warning) 0%, #CC8C2E 100%);
    color: var(--color-white);
    padding: var(--space-3) var(--space-6);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    font-weight: 600;
    font-size: 14px;
    z-index: var(--z-sticky);
    box-shadow: var(--shadow-md);
    transform: translateY(-100%);
    transition: transform var(--transition-normal);
}

.offline-banner.visible {
    transform: translateY(0);
}

.offline-banner i {
    font-size: 16px;
}

/* Adjust content when banner is visible */
.offline-mode .map-page {
    padding-top: 44px;
}

/* Collapsed sidebar support */
html.sidebar-collapsed .offline-banner {
    left: var(--sidebar-collapsed-width);
}

/* =============================================================================
   SYNC BUTTON
   ============================================================================= */

.sync-button {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: 4px 10px;
    border-radius: var(--border-radius-full);
    font-size: 12px;
    font-weight: 500;
    border: none;
    cursor: pointer;
    transition: var(--transition-normal);
}

/* Synced state - success green */
.sync-button.synced {
    background: rgba(74, 124, 89, 0.15);
    color: var(--color-success);
}

.sync-button.synced:hover {
    background: rgba(74, 124, 89, 0.25);
}

/* Syncing state - primary gold with animation */
.sync-button.syncing {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: var(--color-white);
    cursor: wait;
}

.sync-button.syncing i {
    animation: spin 1s linear infinite;
}

/* Stale state - secondary outline */
.sync-button.stale {
    background: var(--color-white);
    color: var(--color-secondary);
    border: 1px solid var(--color-primary);
}

.sync-button.stale:hover {
    background: rgba(212, 175, 55, 0.1);
}

/* Offline state - disabled */
.sync-button.offline {
    background: var(--color-light-gray);
    color: var(--color-medium-gray);
    cursor: not-allowed;
    opacity: 0.7;
}

/* =============================================================================
   DISABLED ACTIONS (OFFLINE MODE)
   ============================================================================= */

.offline-disabled {
    opacity: 0.5;
    pointer-events: none;
    cursor: not-allowed;
    position: relative;
}

.offline-disabled::after {
    content: '';
    position: absolute;
    inset: 0;
    cursor: not-allowed;
}

/* Specific elements to disable */
.offline-mode #newReservationBtn,
.offline-mode .btn-new-reservation,
.offline-mode .reservation-panel .btn-save,
.offline-mode .reservation-panel .btn-edit {
    opacity: 0.5;
    pointer-events: none;
    cursor: not-allowed;
}

/* =============================================================================
   TOAST STYLES FOR OFFLINE
   ============================================================================= */

.toast-offline {
    background: var(--color-warning);
    color: var(--color-white);
}

.toast-online {
    background: var(--color-success);
    color: var(--color-white);
}
```

**Step 2: Commit**

```bash
git add static/css/offline.css
git commit -m "feat(offline): add offline UI styles

Banner, sync button states, and disabled action styles.
Uses design system variables."
```

---

## Task 7: Add Offline UI to Map Template

**Files:**
- Modify: `templates/beach/map.html`

**Step 1: Add CSS import in extra_css block**

After line 18 (after waitlist.css), add:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/offline.css') }}">
```

**Step 2: Add offline banner HTML**

After `{% block content %}` and before `<div class="map-page">` (around line 764), add:

```html
<!-- Offline Banner -->
<div class="offline-banner" id="offline-banner">
    <i class="fas fa-wifi-slash"></i>
    <span>Modo Offline - Datos de las <span id="offline-sync-time">--:--</span></span>
</div>
```

**Step 3: Add sync button to toolbar**

After the refresh button (around line 826, after `</button>` for btn-refresh), add:

```html
        <!-- Sync Status Button -->
        <button type="button" class="sync-button synced" id="sync-button" title="Estado de sincronizacion">
            <i class="fas fa-check"></i>
            <span id="sync-button-text">Sincronizado</span>
        </button>
```

**Step 4: Commit**

```bash
git add templates/beach/map.html
git commit -m "feat(offline): add offline UI elements to map

Adds offline banner and sync status button to toolbar."
```

---

## Task 8: Integrate Offline Manager with BeachMap

**Files:**
- Modify: `static/js/map/BeachMap.js`

**Step 1: Add import at top of file**

After the existing imports (around line 18), add:

```javascript
import { OfflineManager } from '../offline/index.js';
```

**Step 2: Add offline manager initialization in constructor**

After `this.tooltipManager` initialization (around line 77), add:

```javascript
        // Offline manager
        this.offlineManager = null;
        this.isOfflineMode = false;
```

**Step 3: Add offline initialization method**

After the `init()` method, add a new method:

```javascript
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
```

**Step 4: Modify loadData to use cached data when offline**

Replace the `loadData` method with:

```javascript
    async loadData() {
        try {
            // Try to fetch from server
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
                    this.navigation.setZoomLimits(this.options.minZoom, this.options.maxZoom);
                    this.interaction.setSnapGrid(this.options.snapToGrid);
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
```

**Step 5: Call initOffline in init method**

In the `init()` method, after `await this.loadData()` and `this.render()`, add:

```javascript
        // Initialize offline functionality
        await this.initOffline();
```

**Step 6: Update date change handler**

In the `setDate` method, after updating `this.currentDate`, add:

```javascript
        // Update offline manager date
        if (this.offlineManager) {
            await this.offlineManager.setDate(date);
        }
```

**Step 7: Commit**

```bash
git add static/js/map/BeachMap.js
git commit -m "feat(offline): integrate offline manager with BeachMap

- Initialize offline functionality on map load
- Load from cache when server unavailable
- Show sync status in toolbar
- Update date in offline manager"
```

---

## Task 9: Final Testing & Cleanup

**Step 1: Run tests to ensure nothing is broken**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/feature-offline
python -m pytest tests/ -q
```

**Step 2: Test offline functionality manually**

1. Open browser DevTools > Network tab
2. Load `/beach/map`
3. Verify sync button shows "Sincronizado HH:MM"
4. Click "Descargar Dia" button
5. In DevTools, set network to "Offline"
6. Verify banner appears with "Modo Offline"
7. Verify buttons are disabled
8. Set network back to "Online"
9. Verify auto-refresh and toast notification

**Step 3: Final commit**

```bash
git add -A
git status
# If any uncommitted changes, commit them
```

---

## Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | `static/js/offline/storage.js` | IndexedDB wrapper |
| 2 | `static/js/offline/connectivity.js` | Network detection |
| 3 | `static/js/offline/offline-manager.js` | Main orchestrator |
| 4 | `static/js/offline/index.js` | Module exports |
| 5 | `blueprints/beach/routes/api/map_data.py` | Health endpoint |
| 6 | `static/css/offline.css` | UI styles |
| 7 | `templates/beach/map.html` | Banner & button HTML |
| 8 | `static/js/map/BeachMap.js` | Integration |
| 9 | - | Testing & cleanup |

**Total estimated commits:** 8
