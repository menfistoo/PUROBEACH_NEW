/**
 * Block Manager Module
 * Handles furniture blocking/unblocking API calls and modal interactions
 */

import { showToast } from './utils.js';

/**
 * Block type definitions
 */
const BLOCK_TYPES = {
    'maintenance': { name: 'Mantenimiento', color: '#9CA3AF', icon: '🔧' },
    'vip_hold': { name: 'Reserva VIP', color: '#D4AF37', icon: '⭐' },
    'event': { name: 'Evento', color: '#3B82F6', icon: '📅' },
    'other': { name: 'Otro', color: '#6B7280', icon: '🚫' }
};

/**
 * BlockManager class
 * Manages the block furniture modal and API calls
 */
export class BlockManager {
    /**
     * @param {Object} options - Configuration options
     * @param {Function} options.onBlockSuccess - Callback when block is successful
     * @param {Function} options.onUnblockSuccess - Callback when unblock is successful
     * @param {Function} options.getCurrentDate - Function to get current map date
     * @param {Function} options.getBlockInfo - Function to get block info for furniture
     */
    constructor(options = {}) {
        this.onBlockSuccess = options.onBlockSuccess || (() => {});
        this.onUnblockSuccess = options.onUnblockSuccess || (() => {});
        this.getCurrentDate = options.getCurrentDate || (() => new Date().toISOString().split('T')[0]);
        this.getBlockInfo = options.getBlockInfo || (() => null);

        this.modal = null;
        this.unblockModal = null;
        this.furnitureToBlock = [];
        this.furnitureNumbers = [];

        // Unblock state
        this.furnitureToUnblock = null;
        this.furnitureNumberToUnblock = null;
        this.currentBlockInfo = null;

        this.init();
    }

    /**
     * Initialize the block manager
     */
    init() {
        this.modal = document.getElementById('block-furniture-modal');
        this.unblockModal = document.getElementById('unblock-furniture-modal');

        if (!this.modal) {
            console.warn('Block furniture modal not found');
        }
        if (!this.unblockModal) {
            console.warn('Unblock furniture modal not found');
        }

        this.setupEventListeners();
        this.setupUnblockEventListeners();
    }

    /**
     * Setup event listeners for the block modal
     */
    setupEventListeners() {
        // Confirm block button
        const confirmBtn = document.getElementById('confirm-block-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmBlock());
        }

        // Reset form when modal closes
        this.modal?.addEventListener('hidden.bs.modal', () => this.resetForm());
    }

    /**
     * Setup event listeners for the unblock modal
     */
    setupUnblockEventListeners() {
        // Radio button toggle for date range visibility
        const fullRadio = document.getElementById('unblock-type-full');
        const partialRadio = document.getElementById('unblock-type-partial');
        const dateRangeDiv = document.getElementById('unblock-date-range');

        if (fullRadio && partialRadio && dateRangeDiv) {
            fullRadio.addEventListener('change', () => {
                dateRangeDiv.style.display = 'none';
            });
            partialRadio.addEventListener('change', () => {
                dateRangeDiv.style.display = 'flex';
            });
        }

        // Confirm unblock button
        const confirmUnblockBtn = document.getElementById('confirm-unblock-btn');
        if (confirmUnblockBtn) {
            confirmUnblockBtn.addEventListener('click', () => this.confirmUnblock());
        }

        // Reset form when modal closes
        this.unblockModal?.addEventListener('hidden.bs.modal', () => this.resetUnblockForm());
    }

    /**
     * Show the block modal for specified furniture
     * @param {number[]} furnitureIds - Array of furniture IDs to block
     * @param {string[]} furnitureNumbers - Array of furniture numbers/codes
     */
    showBlockModal(furnitureIds, furnitureNumbers) {
        if (!this.modal) {
            showToast('Modal de bloqueo no disponible', 'error');
            return;
        }

        this.furnitureToBlock = furnitureIds;
        this.furnitureNumbers = furnitureNumbers;

        // Populate furniture list
        const listEl = document.getElementById('block-furniture-list');
        if (listEl) {
            listEl.innerHTML = furnitureNumbers.map(num =>
                `<span class="block-furniture-badge">${num}</span>`
            ).join('');
        }

        // Set default date to current map date
        const startDateInput = document.getElementById('block-start-date');
        if (startDateInput) {
            startDateInput.value = this.getCurrentDate();
        }

        // Clear end date and reason
        const endDateInput = document.getElementById('block-end-date');
        const reasonInput = document.getElementById('block-reason');
        if (endDateInput) endDateInput.value = '';
        if (reasonInput) reasonInput.value = '';

        // Reset block type to default
        const blockTypeSelect = document.getElementById('block-type');
        if (blockTypeSelect) blockTypeSelect.value = 'maintenance';

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.modal);
        bsModal.show();
    }

    /**
     * Confirm and execute the block operation
     */
    async confirmBlock() {
        const blockType = document.getElementById('block-type')?.value || 'maintenance';
        const startDate = document.getElementById('block-start-date')?.value;
        const endDate = document.getElementById('block-end-date')?.value || null;
        const reason = document.getElementById('block-reason')?.value || '';

        if (!startDate) {
            showToast('La fecha de inicio es requerida', 'warning');
            return;
        }

        if (this.furnitureToBlock.length === 0) {
            showToast('No hay mobiliario seleccionado', 'warning');
            return;
        }

        // Disable button while processing
        const confirmBtn = document.getElementById('confirm-block-btn');
        if (window.PuroBeach) {
            window.PuroBeach.setButtonLoading(confirmBtn, true, 'Bloqueando...');
        }

        try {
            // Block each furniture item
            const results = await Promise.all(
                this.furnitureToBlock.map(id => this.blockFurniture(id, {
                    block_type: blockType,
                    start_date: startDate,
                    end_date: endDate,
                    reason: reason
                }))
            );

            // Check for errors
            const errors = results.filter(r => !r.success);
            if (errors.length > 0) {
                showToast(`Error al bloquear ${errors.length} elemento(s)`, 'error');
            } else {
                const blockTypeName = BLOCK_TYPES[blockType]?.name || 'Bloqueo';
                showToast(`${this.furnitureToBlock.length} elemento(s) bloqueado(s) - ${blockTypeName}`, 'success');
            }

            // Close modal
            const bsModal = bootstrap.Modal.getInstance(this.modal);
            bsModal?.hide();

            // Trigger refresh
            this.onBlockSuccess();

        } catch (error) {
            console.error('Block error:', error);
            showToast('Error al bloquear mobiliario', 'error');
        } finally {
            if (window.PuroBeach) {
                window.PuroBeach.setButtonLoading(confirmBtn, false);
            }
        }
    }

    /**
     * Block a single furniture item via API
     * @param {number} furnitureId - Furniture ID
     * @param {Object} blockData - Block data (block_type, start_date, end_date, reason)
     * @returns {Promise<Object>} API response
     */
    async blockFurniture(furnitureId, blockData) {
        try {
            const response = await fetch(`/beach/api/map/furniture/${furnitureId}/block`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(blockData)
            });

            return await response.json();
        } catch (error) {
            console.error(`Error blocking furniture ${furnitureId}:`, error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Show the unblock modal for a furniture item
     * @param {number|Array<number>} furnitureId - Furniture ID(s)
     * @param {string|Array<string>} furnitureNumber - Furniture number(s) for display
     * @param {Object} blockInfo - Block information (optional, will fetch if not provided)
     */
    async showUnblockModal(furnitureId, furnitureNumber, blockInfo = null) {
        if (!this.unblockModal) {
            showToast('Modal de desbloqueo no disponible', 'error');
            return;
        }

        // Handle arrays for multi-unblock
        const isMultiUnblock = Array.isArray(furnitureId) && furnitureId.length > 1;

        if (isMultiUnblock) {
            // For multi-unblock, show simplified confirmation and unblock all
            await this.handleMultiUnblock(furnitureId, furnitureNumber);
            return;
        }

        // Single unblock - extract from array if needed
        const singleId = Array.isArray(furnitureId) ? furnitureId[0] : furnitureId;
        const singleNumber = Array.isArray(furnitureNumber) ? furnitureNumber[0] : furnitureNumber;

        this.furnitureToUnblock = singleId;
        this.furnitureNumberToUnblock = singleNumber;
        this.currentBlockInfo = blockInfo || this.getBlockInfo(singleId);

        if (!this.currentBlockInfo) {
            showToast('No se encontró información del bloqueo', 'error');
            return;
        }

        // Populate modal
        const numberEl = document.getElementById('unblock-furniture-number');
        if (numberEl) numberEl.textContent = furnitureNumber;

        const blockType = BLOCK_TYPES[this.currentBlockInfo.block_type] || BLOCK_TYPES.other;
        const typeEl = document.getElementById('unblock-block-type');
        if (typeEl) typeEl.textContent = `${blockType.icon} ${blockType.name}`;

        const startEl = document.getElementById('unblock-block-start');
        if (startEl) startEl.textContent = this.formatDate(this.currentBlockInfo.start_date);

        const endEl = document.getElementById('unblock-block-end');
        if (endEl) endEl.textContent = this.formatDate(this.currentBlockInfo.end_date);

        const reasonEl = document.getElementById('unblock-block-reason');
        const reasonRow = document.getElementById('unblock-block-reason-row');
        if (reasonEl && reasonRow) {
            if (this.currentBlockInfo.reason) {
                reasonEl.textContent = this.currentBlockInfo.reason;
                reasonRow.style.display = '';
            } else {
                reasonRow.style.display = 'none';
            }
        }

        // Set default dates to current block dates
        const startDateInput = document.getElementById('unblock-start-date');
        const endDateInput = document.getElementById('unblock-end-date');
        const currentDate = this.getCurrentDate();

        if (startDateInput) {
            startDateInput.value = currentDate;
            startDateInput.min = this.currentBlockInfo.start_date;
            startDateInput.max = this.currentBlockInfo.end_date;
        }
        if (endDateInput) {
            endDateInput.value = currentDate;
            endDateInput.min = this.currentBlockInfo.start_date;
            endDateInput.max = this.currentBlockInfo.end_date;
        }

        // Reset to full unblock
        const fullRadio = document.getElementById('unblock-type-full');
        const dateRangeDiv = document.getElementById('unblock-date-range');
        if (fullRadio) fullRadio.checked = true;
        if (dateRangeDiv) dateRangeDiv.style.display = 'none';

        // Show modal
        const bsModal = bootstrap.Modal.getOrCreateInstance(this.unblockModal);
        bsModal.show();
    }

    /**
     * Handle unblocking of multiple furniture items
     * @param {Array<number>} furnitureIds - Array of furniture IDs to unblock
     * @param {Array<string>} furnitureNumbers - Array of furniture numbers for display
     */
    async handleMultiUnblock(furnitureIds, furnitureNumbers) {
        // Show confirmation with count
        const count = furnitureIds.length;
        const confirmed = await confirmAction({
            title: 'Confirmar desbloqueo',
            message: `¿Está seguro de desbloquear ${count} mobiliarios?<br><br>Esto desbloqueará completamente:<br>${furnitureNumbers.join(', ')}`,
            confirmText: 'Desbloquear',
            confirmClass: 'btn-warning',
            iconClass: 'fa-unlock'
        });

        if (!confirmed) {
            return;
        }

        let successCount = 0;
        let errorCount = 0;

        // Unblock each item individually
        for (let i = 0; i < furnitureIds.length; i++) {
            try {
                const blockInfo = this.getBlockInfo(furnitureIds[i]);
                if (!blockInfo) {
                    console.warn(`No block info found for furniture ${furnitureNumbers[i]}`);
                    errorCount++;
                    continue;
                }

                const response = await fetch(`/beach/api/map/furniture/${furnitureIds[i]}/block`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });

                const result = await response.json();

                if (result.success) {
                    successCount++;
                } else {
                    console.error(`Error unblocking furniture ${furnitureNumbers[i]}:`, result.error);
                    errorCount++;
                }
            } catch (error) {
                console.error(`Error unblocking furniture ${furnitureNumbers[i]}:`, error);
                errorCount++;
            }
        }

        // Show result message
        if (errorCount === 0) {
            showToast(`${successCount} mobiliarios desbloqueados`, 'success');
        } else if (successCount === 0) {
            showToast(`Error al desbloquear mobiliarios`, 'error');
        } else {
            showToast(`${successCount} desbloqueados, ${errorCount} con errores`, 'warning');
        }

        // Refresh map
        if (this.onUnblockSuccess) {
            this.onUnblockSuccess();
        }
    }

    /**
     * Confirm and execute the unblock operation
     */
    async confirmUnblock() {
        const unblockType = document.querySelector('input[name="unblock-type"]:checked')?.value || 'full';

        // Disable button while processing
        const confirmBtn = document.getElementById('confirm-unblock-btn');
        if (window.PuroBeach) {
            window.PuroBeach.setButtonLoading(confirmBtn, true, 'Desbloqueando...');
        }

        try {
            let result;

            if (unblockType === 'full') {
                // Full unblock - delete the entire block
                result = await this.executeFullUnblock();
            } else {
                // Partial unblock - unblock specific date range
                const startDate = document.getElementById('unblock-start-date')?.value;
                const endDate = document.getElementById('unblock-end-date')?.value;

                if (!startDate || !endDate) {
                    showToast('Las fechas son requeridas para desbloqueo parcial', 'warning');
                    return;
                }

                if (startDate > endDate) {
                    showToast('La fecha de inicio no puede ser posterior a la fecha fin', 'warning');
                    return;
                }

                result = await this.executePartialUnblock(startDate, endDate);
            }

            if (result.success) {
                showToast(`Mobiliario ${this.furnitureNumberToUnblock} desbloqueado`, 'success');

                // Close modal
                const bsModal = bootstrap.Modal.getInstance(this.unblockModal);
                bsModal?.hide();

                // Trigger refresh
                this.onUnblockSuccess();
            } else {
                showToast(result.error || 'Error al desbloquear', 'error');
            }

        } catch (error) {
            console.error('Unblock error:', error);
            showToast('Error al desbloquear mobiliario', 'error');
        } finally {
            if (window.PuroBeach) {
                window.PuroBeach.setButtonLoading(confirmBtn, false);
            }
        }
    }

    /**
     * Execute full unblock (delete entire block)
     * @returns {Promise<Object>} API response
     */
    async executeFullUnblock() {
        const blockId = this.currentBlockInfo?.id;
        const date = this.getCurrentDate();

        const url = blockId
            ? `/beach/api/map/furniture/${this.furnitureToUnblock}/block?block_id=${blockId}`
            : `/beach/api/map/furniture/${this.furnitureToUnblock}/block?date=${date}`;

        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        });

        return await response.json();
    }

    /**
     * Execute partial unblock (unblock specific date range)
     * @param {string} startDate - Start date to unblock
     * @param {string} endDate - End date to unblock
     * @returns {Promise<Object>} API response
     */
    async executePartialUnblock(startDate, endDate) {
        const response = await fetch(`/beach/api/map/furniture/${this.furnitureToUnblock}/unblock-partial`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                block_id: this.currentBlockInfo?.id,
                unblock_start: startDate,
                unblock_end: endDate
            })
        });

        return await response.json();
    }

    /**
     * Format date for display
     * @param {string} dateStr - Date string (YYYY-MM-DD or ISO format)
     * @returns {string} Formatted date
     */
    formatDate(dateStr) {
        if (!dateStr) return '-';

        let date;
        // Handle different date formats
        if (typeof dateStr === 'string') {
            // If it's already in YYYY-MM-DD format
            if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                date = new Date(dateStr + 'T00:00:00');
            } else {
                // Try parsing as-is (handles ISO format, etc.)
                date = new Date(dateStr);
            }
        } else if (dateStr instanceof Date) {
            date = dateStr;
        } else {
            return '-';
        }

        if (isNaN(date.getTime())) return '-';

        return date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }

    /**
     * Reset the unblock form fields
     */
    resetUnblockForm() {
        this.furnitureToUnblock = null;
        this.furnitureNumberToUnblock = null;
        this.currentBlockInfo = null;

        const fullRadio = document.getElementById('unblock-type-full');
        const dateRangeDiv = document.getElementById('unblock-date-range');
        if (fullRadio) fullRadio.checked = true;
        if (dateRangeDiv) dateRangeDiv.style.display = 'none';
    }

    /**
     * Reset the block form fields
     */
    resetForm() {
        this.furnitureToBlock = [];
        this.furnitureNumbers = [];

        const listEl = document.getElementById('block-furniture-list');
        if (listEl) listEl.innerHTML = '';

        const startDateInput = document.getElementById('block-start-date');
        const endDateInput = document.getElementById('block-end-date');
        const reasonInput = document.getElementById('block-reason');
        const blockTypeSelect = document.getElementById('block-type');

        if (startDateInput) startDateInput.value = '';
        if (endDateInput) endDateInput.value = '';
        if (reasonInput) reasonInput.value = '';
        if (blockTypeSelect) blockTypeSelect.value = 'maintenance';
    }

    /**
     * Get CSRF token from meta tag or cookie
     * @returns {string} CSRF token
     */
    getCSRFToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        // Try cookie
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }

        // Try hidden input
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            return csrfInput.value;
        }

        return '';
    }

    /**
     * Destroy the manager
     */
    destroy() {
        this.modal = null;
        this.furnitureToBlock = [];
        this.furnitureNumbers = [];
    }
}

export default BlockManager;
