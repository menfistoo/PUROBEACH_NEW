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
