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

import { showToast } from './utils.js';

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
export const StateMixin = (Base) => class extends Base {

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
                    ${currentState || 'Sin estado'}
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
                    ${state.name}
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
                            ${item.status_type}
                        </span>
                        <span class="history-meta">
                            ${dateStr}
                            ${item.changed_by ? `• ${item.changed_by}` : ''}
                        </span>
                        ${item.notes ? `<span class="history-notes">${item.notes}</span>` : ''}
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
