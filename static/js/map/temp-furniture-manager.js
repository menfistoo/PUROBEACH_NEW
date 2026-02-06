/**
 * Temporary Furniture Manager Module
 * Handles creating/deleting temporary furniture on the map
 */

import { showToast } from './utils.js';

/**
 * TempFurnitureManager class
 * Manages temporary furniture creation/deletion modals and API calls
 */
export class TempFurnitureManager {
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
        // Show simplified confirmation with count
        const count = furnitureIds.length;
        const confirmed = confirm(`¿Está seguro de eliminar ${count} mobiliarios temporales?\n\nEsto eliminará completamente:\n${furnitureNumbers.join(', ')}`);

        if (!confirmed) {
            return;
        }

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

export default TempFurnitureManager;
