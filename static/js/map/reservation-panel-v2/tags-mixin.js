/**
 * ReservationPanel Tags Mixin
 *
 * Handles reservation tag functionality:
 * - Rendering tags section with chips
 * - Entering/exiting tags edit mode
 * - Loading all available tags
 * - Toggling tag selections
 *
 * @module reservation-panel-v2/tags-mixin
 */

// =============================================================================
// TAGS MIXIN
// =============================================================================

export const TagsMixin = (Base) => class extends Base {

    // =========================================================================
    // TAGS SECTION RENDERING
    // =========================================================================

    /**
     * Render tags section with chips (view mode)
     * @param {Object} reservation - Reservation data
     */
    renderTagsSection(reservation) {
        if (!this.tagChipsContainer) return;

        const tags = reservation?.tags || [];

        if (this.tagsSection) {
            this.tagsSection.style.display = 'block';
        }

        if (tags.length === 0) {
            this.tagChipsContainer.innerHTML =
                '<span class="text-muted small">Sin etiquetas</span>';
            return;
        }

        const chipsHtml = tags.map(tag => {
            const color = tag.color || '#6C757D';
            return `
                <span class="tag-chip" style="--tag-color: ${color};" title="${tag.description || tag.name}">
                    <i class="fas fa-tag"></i>
                    <span>${tag.name}</span>
                </span>
            `;
        }).join('');

        this.tagChipsContainer.innerHTML = chipsHtml;
    }

    // =========================================================================
    // TAGS EDIT MODE
    // =========================================================================

    /**
     * Enter tags edit mode
     * Loads all available tags and renders them as toggleable chips
     */
    async enterTagsEditMode() {
        if (this.tagsEditState.allTags.length === 0) {
            await this.loadAllTags();
        }

        const currentTags = this.state.data?.reservation?.tags || [];
        this.tagsEditState.selectedIds = currentTags.map(t => t.id);
        this.tagsEditState.originalIds = [...this.tagsEditState.selectedIds];
        this.tagsEditState.isEditing = true;

        this.renderAllTagChips();

        if (this.tagsViewMode) {
            this.tagsViewMode.style.display = 'none';
        }
        if (this.tagsEditModeEl) {
            this.tagsEditModeEl.style.display = 'block';
        }
        if (this.tagsSection) {
            this.tagsSection.style.display = 'block';
        }
    }

    /**
     * Exit tags edit mode
     * @param {boolean} discard - Whether to discard changes
     */
    exitTagsEditMode(discard = false) {
        this.tagsEditState.isEditing = false;

        if (this.tagsViewMode) {
            this.tagsViewMode.style.display = 'block';
        }
        if (this.tagsEditModeEl) {
            this.tagsEditModeEl.style.display = 'none';
        }

        const reservation = this.state.data?.reservation;
        if (reservation) {
            this.renderTagsSection(reservation);
        }
    }

    // =========================================================================
    // TAGS DATA LOADING
    // =========================================================================

    /**
     * Load all available tags from server
     */
    async loadAllTags() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/tags`);
            if (response.ok) {
                const result = await response.json();
                this.tagsEditState.allTags = result.tags || [];
            }
        } catch (error) {
            console.error('Failed to load tags:', error);
        }
    }

    // =========================================================================
    // TAGS CHIPS RENDERING
    // =========================================================================

    /**
     * Render all tags as toggleable chips (edit mode)
     */
    renderAllTagChips() {
        if (!this.tagsAllChips) return;

        const allTags = this.tagsEditState.allTags;
        const selectedIds = this.tagsEditState.selectedIds;

        if (allTags.length === 0) {
            this.tagsAllChips.innerHTML =
                '<span class="text-muted small">No hay etiquetas disponibles</span>';
            return;
        }

        const chipsHtml = allTags.map(tag => {
            const isSelected = selectedIds.includes(tag.id);
            const color = tag.color || '#6C757D';
            return `
                <button type="button" class="tag-chip toggleable ${isSelected ? 'active' : ''}"
                        data-tag-id="${tag.id}"
                        style="--tag-color: ${color};"
                        title="${tag.description || tag.name}">
                    <i class="fas fa-tag"></i>
                    <span>${tag.name}</span>
                </button>
            `;
        }).join('');

        this.tagsAllChips.innerHTML = chipsHtml;

        this._attachTagChipHandlers();
    }

    /**
     * Attach click handlers to toggleable tag chips
     * @private
     */
    _attachTagChipHandlers() {
        if (!this.tagsAllChips) return;

        this.tagsAllChips
            .querySelectorAll('.tag-chip.toggleable')
            .forEach(chip => {
                chip.addEventListener('click', () => {
                    this.toggleTag(parseInt(chip.dataset.tagId));
                });
            });
    }

    // =========================================================================
    // TAGS SELECTION
    // =========================================================================

    /**
     * Toggle a tag selection
     * @param {number} tagId - The tag ID to toggle
     */
    toggleTag(tagId) {
        const index = this.tagsEditState.selectedIds.indexOf(tagId);
        if (index >= 0) {
            this.tagsEditState.selectedIds.splice(index, 1);
        } else {
            this.tagsEditState.selectedIds.push(tagId);
        }
        this.renderAllTagChips();
    }
};
