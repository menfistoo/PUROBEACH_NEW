/**
 * Move Mode Controller
 * Manages furniture reassignment operations during move mode
 */

import { getCSRFToken, showToast } from './utils.js';

/**
 * Move Mode Manager Class
 * Handles unassigning and assigning furniture, undo operations,
 * and coordination with the pool panel
 */
export class MoveMode {
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

        // Event callbacks (arrays to support multiple listeners)
        this.callbacks = {
            onActivate: [],
            onDeactivate: [],
            onPoolUpdate: [],
            onSelectionChange: [],
            onFurnitureHighlight: [],
            onUndo: [],
            onError: []
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
     */
    async activate(date) {
        if (this.active) return;

        this.active = true;
        this.currentDate = date;
        this.pool = [];
        this.selectedReservationId = null;
        this.undoStack = [];

        this.emit('onActivate', { date });
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
        if (existingIndex >= 0 && this.pool[existingIndex].initialFurniture) {
            return this.pool[existingIndex].initialFurniture;
        }
        if (initialFurnitureOverride && initialFurnitureOverride.length > 0) {
            return initialFurnitureOverride;
        }
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
                    this.pool.splice(existingIndex, 1);
                    if (this.selectedReservationId === reservationId) {
                        this.deselectReservation();
                    }
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
