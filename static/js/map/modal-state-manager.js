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

export default window.modalStateManager;
