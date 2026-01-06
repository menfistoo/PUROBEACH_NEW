/**
 * Reservation Panel Standalone Wrapper
 * Initializes the ReservationPanel in standalone mode (outside the map page)
 * For use in the reservations list page.
 */

class ReservationPanelStandalone {
    constructor() {
        this.panel = null;
        this.initialized = false;
    }

    /**
     * Initialize the standalone panel
     */
    async init() {
        if (this.initialized) return;

        // Wait for ReservationPanel class to be available
        if (typeof ReservationPanel === 'undefined') {
            console.error('ReservationPanel class not found. Include reservation-panel.js first.');
            return;
        }

        // Create the panel instance in standalone mode
        this.panel = new ReservationPanel({
            context: 'standalone',
            onClose: () => this.handlePanelClose(),
            onSave: (resId, changes) => this.handleSave(resId, changes),
            onStateChange: (resId, newState) => this.handleStateChange(resId, newState)
        });

        // Fetch states on init
        await this.panel.fetchStates();

        this.initialized = true;

        // Check for URL params to auto-open panel
        this.checkUrlParams();

        // Show message if present
        this.showUrlMessage();
    }

    /**
     * Open the panel for a reservation
     * @param {number} reservationId - The reservation ID
     * @param {string} date - The reservation date (YYYY-MM-DD)
     * @param {string} mode - 'view' or 'edit'
     */
    open(reservationId, date, mode = 'view') {
        if (!this.panel) {
            console.error('Panel not initialized. Call init() first.');
            return;
        }

        // Update URL without reload
        const url = new URL(window.location.href);
        url.searchParams.set('open_panel', reservationId);
        url.searchParams.set('mode', mode);
        if (date) {
            url.searchParams.set('panel_date', date);
        }
        window.history.replaceState({}, '', url.toString());

        // Open the panel
        this.panel.open(reservationId, date, mode);
    }

    /**
     * Close the panel
     */
    close() {
        if (this.panel) {
            this.panel.close();
        }
    }

    /**
     * Check URL params for auto-open
     */
    checkUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const openPanelId = params.get('open_panel');
        const mode = params.get('mode') || 'view';
        const panelDate = params.get('panel_date');

        if (openPanelId) {
            // Get the date from the reservation row or use today
            let date = panelDate;
            if (!date) {
                const row = document.querySelector(`tr[data-reservation-id="${openPanelId}"]`);
                date = row?.dataset.date || new Date().toISOString().split('T')[0];
            }
            this.open(parseInt(openPanelId), date, mode);
        }
    }

    /**
     * Show message from URL params (e.g., after furniture selection)
     */
    showUrlMessage() {
        const params = new URLSearchParams(window.location.search);
        const message = params.get('message');

        if (message) {
            const messages = {
                'furniture_updated': 'Mobiliario actualizado correctamente',
                'reservation_saved': 'Reserva guardada correctamente'
            };

            const displayMessage = messages[message] || message;
            if (window.PuroBeach?.showToast) {
                window.PuroBeach.showToast(displayMessage, 'success');
            }

            // Clean up URL
            const url = new URL(window.location.href);
            url.searchParams.delete('message');
            window.history.replaceState({}, '', url.toString());
        }
    }

    /**
     * Handle panel close
     */
    handlePanelClose() {
        // Clean up URL
        const url = new URL(window.location.href);
        url.searchParams.delete('open_panel');
        url.searchParams.delete('mode');
        url.searchParams.delete('panel_date');
        window.history.replaceState({}, '', url.toString());
    }

    /**
     * Handle save callback - refresh page to show updated data
     */
    handleSave(reservationId, changes) {
        // Refresh the page to show updated data in the table
        // Could also do a partial update via AJAX in the future
        window.location.reload();
    }

    /**
     * Handle state change - update the table row
     */
    handleStateChange(reservationId, newState) {
        // Update the state badge in the table
        const row = document.querySelector(`tr[data-reservation-id="${reservationId}"]`);
        if (row) {
            const stateBadge = row.querySelector('.state-badge');
            if (stateBadge) {
                stateBadge.textContent = newState;
                // Note: Color would need to be fetched or stored
            }
        }
    }
}

// Global instance
window.reservationPanelStandalone = new ReservationPanelStandalone();

// Auto-initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on the reservations page and panel elements exist
    if (document.getElementById('reservationPanel')) {
        window.reservationPanelStandalone.init();
    }
});

/**
 * Helper function to open panel from row click or button
 */
function openReservationPanel(reservationId, date, mode = 'view') {
    if (window.reservationPanelStandalone) {
        window.reservationPanelStandalone.open(reservationId, date, mode);
    }
}
