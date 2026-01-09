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
