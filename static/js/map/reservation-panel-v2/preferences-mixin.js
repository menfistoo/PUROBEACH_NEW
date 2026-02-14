/**
 * ReservationPanel Preferences Mixin
 *
 * Handles all customer preferences functionality:
 * - Rendering preferences section with chips
 * - Entering/exiting preferences edit mode
 * - Loading all available preferences
 * - Toggling preference selections
 *
 * @module reservation-panel-v2/preferences-mixin
 */

// =============================================================================
// PREFERENCES MIXIN
// =============================================================================

/**
 * Preferences mixin factory function
 * Adds customer preferences display and edit functionality to the panel
 *
 * @param {class} Base - Base class to extend
 * @returns {class} Extended class with preferences functionality
 *
 * @example
 * class ReservationPanel extends PreferencesMixin(CustomerMixin(BasePanel)) {
 *     // Panel implementation
 * }
 */
export const PreferencesMixin = (Base) => class extends Base {

    // =========================================================================
    // PREFERENCES SECTION RENDERING
    // =========================================================================

    /**
     * Render preferences section with chips
     * Displays customer preferences as styled chip elements
     *
     * @param {Object|null} customer - Customer data object
     * @param {Array} customer.preferences - Array of preference objects
     * @param {string} customer.preferences[].code - Preference code
     * @param {string} customer.preferences[].name - Preference display name
     * @param {string} customer.preferences[].icon - FontAwesome icon class
     */
    renderPreferencesSection(customer) {
        if (!this.preferencesChipsContainer) return;

        // Prefer reservation-specific characteristics over customer defaults
        const reservationChars = this.state.data?.reservation_characteristics || [];
        const preferences = reservationChars.length > 0 ? reservationChars : (customer?.preferences || []);

        // Hide section if no preferences
        if (this.preferencesSection) {
            this.preferencesSection.style.display = preferences.length > 0 ? 'block' : 'none';
        }

        if (preferences.length === 0) {
            this.preferencesChipsContainer.innerHTML =
                '<span class="text-muted small">Sin preferencias registradas</span>';
            return;
        }

        const chipsHtml = preferences.map(pref => {
            const icon = this._normalizeIconClass(pref.icon);
            return `
                <span class="preference-chip" title="${pref.name}">
                    <i class="${icon}"></i>
                    <span>${pref.name}</span>
                </span>
            `;
        }).join('');

        this.preferencesChipsContainer.innerHTML = chipsHtml;
    }

    // =========================================================================
    // PREFERENCES EDIT MODE
    // =========================================================================

    /**
     * Enter preferences edit mode
     * Loads all available preferences and renders them as toggleable chips
     *
     * @returns {Promise<void>}
     */
    async enterPreferencesEditMode() {
        // Load all available preferences if not already loaded
        if (this.preferencesEditState.allPreferences.length === 0) {
            await this.loadAllPreferences();
        }

        // Get current preferences - prefer reservation-specific over customer defaults
        const reservationChars = this.state.data?.reservation_characteristics || [];
        const customerPrefs = this.state.data?.customer?.preferences || [];
        const activePrefs = reservationChars.length > 0 ? reservationChars : customerPrefs;
        this.preferencesEditState.selectedCodes = activePrefs.map(p => p.code);
        this.preferencesEditState.originalCodes = [...this.preferencesEditState.selectedCodes];
        this.preferencesEditState.isEditing = true;

        // Render all preferences as toggleable chips
        this.renderAllPreferencesChips();

        // Show edit mode, hide view mode
        if (this.preferencesViewMode) {
            this.preferencesViewMode.style.display = 'none';
        }
        if (this.preferencesEditMode) {
            this.preferencesEditMode.style.display = 'block';
        }

        // Always show the section in edit mode
        if (this.preferencesSection) {
            this.preferencesSection.style.display = 'block';
        }
    }

    /**
     * Exit preferences edit mode
     * Optionally discards changes and returns to view mode
     *
     * @param {boolean} discard - Whether to discard changes (default: false)
     */
    exitPreferencesEditMode(discard = false) {
        this.preferencesEditState.isEditing = false;

        // Show view mode, hide edit mode
        if (this.preferencesViewMode) {
            this.preferencesViewMode.style.display = 'block';
        }
        if (this.preferencesEditMode) {
            this.preferencesEditMode.style.display = 'none';
        }

        // Re-render view mode with current preferences
        const customer = this.state.data?.customer;
        if (customer) {
            this.renderPreferencesSection(customer);
        }
    }

    // =========================================================================
    // PREFERENCES DATA LOADING
    // =========================================================================

    /**
     * Load all available preferences from server
     * Fetches the complete list of preferences that can be assigned to customers
     *
     * @returns {Promise<void>}
     */
    async loadAllPreferences() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/preferences`);
            if (response.ok) {
                const result = await response.json();
                this.preferencesEditState.allPreferences = result.preferences || [];
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
        }
    }

    // =========================================================================
    // PREFERENCES CHIPS RENDERING
    // =========================================================================

    /**
     * Render all preferences as toggleable chips
     * Used in edit mode to show all available preferences with selection state
     */
    renderAllPreferencesChips() {
        if (!this.preferencesAllChips) return;

        const allPrefs = this.preferencesEditState.allPreferences;
        const selectedCodes = this.preferencesEditState.selectedCodes;

        if (allPrefs.length === 0) {
            this.preferencesAllChips.innerHTML =
                '<span class="text-muted small">No hay preferencias disponibles</span>';
            return;
        }

        const chipsHtml = allPrefs.map(pref => {
            const isSelected = selectedCodes.includes(pref.code);
            const icon = this._normalizeIconClass(pref.icon);
            return `
                <span class="preference-chip toggleable ${isSelected ? 'selected' : ''}"
                      data-code="${pref.code}"
                      title="${pref.name}">
                    <i class="${icon}"></i>
                    <span>${pref.name}</span>
                </span>
            `;
        }).join('');

        this.preferencesAllChips.innerHTML = chipsHtml;

        // Attach click handlers
        this._attachPreferenceChipHandlers();
    }

    /**
     * Attach click handlers to toggleable preference chips
     * @private
     */
    _attachPreferenceChipHandlers() {
        if (!this.preferencesAllChips) return;

        this.preferencesAllChips
            .querySelectorAll('.preference-chip.toggleable')
            .forEach(chip => {
                chip.addEventListener('click', () => {
                    this.togglePreference(chip.dataset.code);
                });
            });
    }

    // =========================================================================
    // PREFERENCES SELECTION
    // =========================================================================

    /**
     * Toggle a preference selection
     * Adds or removes the preference code from selected list
     *
     * @param {string} code - The preference code to toggle
     */
    togglePreference(code) {
        const index = this.preferencesEditState.selectedCodes.indexOf(code);
        if (index >= 0) {
            // Remove from selection
            this.preferencesEditState.selectedCodes.splice(index, 1);
        } else {
            // Add to selection
            this.preferencesEditState.selectedCodes.push(code);
        }
        // Re-render chips to update selection state
        this.renderAllPreferencesChips();
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    /**
     * Normalize icon class to ensure proper FontAwesome prefix
     * Icons are stored as 'fa-umbrella', need to add 'fas ' prefix if missing
     *
     * @private
     * @param {string} icon - Icon class string
     * @returns {string} Normalized icon class with proper prefix
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
};
