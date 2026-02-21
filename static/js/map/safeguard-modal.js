/**
 * SafeguardModal - Reusable warning modal for reservation safeguards
 * Shows warnings before potentially problematic actions
 */
function _sgEscape(str) {
    if (!str) return '';
    const s = String(str);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class SafeguardModal {
    constructor() {
        this.modal = null;
        this.backdrop = null;
        this.resolvePromise = null;
        this.init();
    }

    /**
     * Initialize the modal DOM elements
     */
    init() {
        // Create backdrop
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'safeguard-backdrop';
        this.backdrop.addEventListener('click', () => this.dismiss());

        // Create modal
        this.modal = document.createElement('div');
        this.modal.className = 'safeguard-modal';
        this.modal.setAttribute('role', 'dialog');
        this.modal.setAttribute('aria-modal', 'true');

        // Append to body
        document.body.appendChild(this.backdrop);
        document.body.appendChild(this.modal);

        // Escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.dismiss();
            }
        });
    }

    /**
     * Check if modal is currently open
     */
    isOpen() {
        return this.modal.classList.contains('open');
    }

    /**
     * Show a safeguard warning
     * @param {Object} options - Modal options
     * @param {string} options.code - Safeguard code (e.g., 'SG-01')
     * @param {string} options.title - Modal title
     * @param {string} options.message - Warning message (supports HTML)
     * @param {string} options.type - 'warning', 'error', or 'info'
     * @param {Array} options.buttons - Button configurations
     * @returns {Promise<string|null>} - Returns button action or null if dismissed
     */
    show(options) {
        const {
            code = '',
            title = 'Advertencia',
            message = '',
            type = 'warning',
            buttons = [{ label: 'Entendido', action: 'ok', style: 'primary' }]
        } = options;

        // Build modal content
        this.modal.innerHTML = `
            <div class="safeguard-modal-header ${type}">
                <div class="safeguard-icon">
                    ${this.getIcon(type)}
                </div>
                <div class="safeguard-title-group">
                    <h3 class="safeguard-title">${title}</h3>
                    ${code ? `<span class="safeguard-code">${code}</span>` : ''}
                </div>
                <button type="button" class="safeguard-close" aria-label="Cerrar">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="safeguard-modal-body">
                <div class="safeguard-message">${message}</div>
            </div>
            <div class="safeguard-modal-footer">
                ${buttons.map(btn => `
                    <button type="button"
                            class="safeguard-btn ${btn.style || 'secondary'}"
                            data-action="${btn.action}">
                        ${btn.icon ? `<i class="${btn.icon}"></i>` : ''}
                        ${btn.label}
                    </button>
                `).join('')}
            </div>
        `;

        // Attach button handlers
        this.modal.querySelectorAll('.safeguard-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.close(btn.dataset.action);
            });
        });

        // Close button handler
        this.modal.querySelector('.safeguard-close').addEventListener('click', () => {
            this.dismiss();
        });

        // Show modal
        this.backdrop.classList.add('show');
        this.modal.classList.add('open');
        document.body.style.overflow = 'hidden';

        // Focus first button
        const firstBtn = this.modal.querySelector('.safeguard-btn');
        if (firstBtn) firstBtn.focus();

        // Return promise
        return new Promise(resolve => {
            this.resolvePromise = resolve;
        });
    }

    /**
     * Get icon for modal type
     */
    getIcon(type) {
        switch (type) {
            case 'error':
                return '<i class="fas fa-exclamation-circle"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle"></i>';
            case 'info':
                return '<i class="fas fa-info-circle"></i>';
            case 'success':
                return '<i class="fas fa-check-circle"></i>';
            default:
                return '<i class="fas fa-exclamation-triangle"></i>';
        }
    }

    /**
     * Close the modal with an action
     */
    close(action) {
        this.backdrop.classList.remove('show');
        this.modal.classList.remove('open');
        document.body.style.overflow = '';

        if (this.resolvePromise) {
            this.resolvePromise(action);
            this.resolvePromise = null;
        }
    }

    /**
     * Dismiss the modal (no action)
     */
    dismiss() {
        this.close(null);
    }

    // =========================================================================
    // STATIC HELPER METHODS FOR COMMON SAFEGUARDS
    // =========================================================================

    /**
     * Show duplicate reservation warning
     * @param {Object} existingReservation - The existing reservation data
     * @returns {Promise<string|null>}
     */
    static async showDuplicateWarning(existingReservation) {
        const instance = SafeguardModal.getInstance();
        const res = existingReservation;

        const furnitureList = (res.furniture || [])
            .map(f => _sgEscape(f.number || f.furniture_number || `#${f.id}`))
            .join(', ') || 'Sin mobiliario';

        return instance.show({
            code: 'SG-01',
            title: 'Reserva duplicada',
            type: 'warning',
            message: `
                <p>Este cliente ya tiene una reserva para esta fecha:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Ticket:</span>
                        <span class="detail-value">#${_sgEscape(res.ticket_number || res.id)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Mobiliario:</span>
                        <span class="detail-value">${furnitureList}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Estado:</span>
                        <span class="detail-value">${_sgEscape(res.current_state || res.state || 'Pendiente')}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Deseas crear otra reserva de todas formas?</p>
            `,
            buttons: [
                { label: 'Cancelar', action: 'cancel', style: 'secondary' },
                { label: 'Ver existente', action: 'view', style: 'outline', icon: 'fas fa-eye' },
                { label: 'Crear de todas formas', action: 'proceed', style: 'warning' }
            ]
        });
    }

    /**
     * Show hotel stay date warning
     * @param {Object} guest - Hotel guest data with arrival/departure
     * @param {Array} outOfRangeDates - Dates outside stay
     * @returns {Promise<string|null>}
     */
    static async showHotelStayWarning(guest, outOfRangeDates) {
        const instance = SafeguardModal.getInstance();

        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        };

        return instance.show({
            code: 'SG-03',
            title: 'Fechas fuera de estadia',
            type: 'warning',
            message: `
                <p>Las siguientes fechas estan fuera de la estadia del huesped:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Check-in:</span>
                        <span class="detail-value">${formatDate(guest.arrival_date)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Check-out:</span>
                        <span class="detail-value">${formatDate(guest.departure_date)}</span>
                    </div>
                    <div class="detail-row highlight">
                        <span class="detail-label">Fuera de rango:</span>
                        <span class="detail-value">${outOfRangeDates.map(formatDate).join(', ')}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Continuar de todas formas?</p>
            `,
            buttons: [
                { label: 'Ajustar fechas', action: 'adjust', style: 'secondary' },
                { label: 'Continuar', action: 'proceed', style: 'warning' }
            ]
        });
    }

    /**
     * Show past date error
     * @param {Array} pastDates - Past dates selected
     * @returns {Promise<string|null>}
     */
    static async showPastDateError(pastDates) {
        const instance = SafeguardModal.getInstance();

        const formatDate = (dateStr) => {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
        };

        return instance.show({
            code: 'SG-05',
            title: 'Fechas no validas',
            type: 'error',
            message: `
                <p>No se pueden crear reservas para fechas pasadas:</p>
                <div class="safeguard-detail-box error">
                    <div class="past-dates-list">
                        ${pastDates.map(d => `<span class="past-date">${formatDate(d)}</span>`).join('')}
                    </div>
                </div>
                <p>Por favor selecciona fechas validas (hoy o futuro).</p>
            `,
            buttons: [
                { label: 'Entendido', action: 'ok', style: 'primary' }
            ]
        });
    }

    /**
     * Show capacity mismatch warning
     * @param {number} requestedPeople - Number of people requested
     * @param {number} maxCapacity - Maximum furniture capacity
     * @returns {Promise<string|null>}
     */
    static async showCapacityWarning(requestedPeople, maxCapacity) {
        const instance = SafeguardModal.getInstance();

        return instance.show({
            code: 'SG-04',
            title: 'Capacidad excedida',
            type: 'warning',
            message: `
                <p>El numero de personas excede la capacidad del mobiliario:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Personas indicadas:</span>
                        <span class="detail-value highlight">${requestedPeople}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Capacidad maxima:</span>
                        <span class="detail-value">${maxCapacity}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Ajustar a ${maxCapacity} personas?</p>
            `,
            buttons: [
                { label: 'Mantener ' + requestedPeople, action: 'keep', style: 'secondary' },
                { label: 'Ajustar a ' + maxCapacity, action: 'adjust', style: 'primary' }
            ]
        });
    }

    /**
     * Show excess capacity warning (more sunbeds than guests)
     * @param {number} numPeople - Number of people
     * @param {number} capacity - Furniture capacity
     * @returns {Promise<string|null>}
     */
    static async showExcessCapacityWarning(numPeople, capacity) {
        const instance = SafeguardModal.getInstance();
        const excess = capacity - numPeople;

        return instance.show({
            code: 'SG-04b',
            title: 'Mobiliario excedente',
            type: 'warning',
            message: `
                <p>El mobiliario seleccionado tiene mas capacidad de la necesaria:</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Huespedes:</span>
                        <span class="detail-value">${numPeople}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Capacidad mobiliario:</span>
                        <span class="detail-value highlight">${capacity}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Plazas sobrantes:</span>
                        <span class="detail-value highlight">${excess}</span>
                    </div>
                </div>
                <p class="safeguard-question">¿Desea continuar con esta seleccion?</p>
            `,
            buttons: [
                { label: 'Cancelar', action: 'cancel', style: 'secondary' },
                { label: 'Continuar', action: 'proceed', style: 'primary' }
            ]
        });
    }

    /**
     * Show furniture availability error
     * @param {Array} conflicts - List of furniture conflicts
     * @returns {Promise<string|null>}
     */
    static async showFurnitureConflictError(conflicts) {
        const instance = SafeguardModal.getInstance();

        const formatDate = (dateStr) => {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
        };

        const conflictList = conflicts.map(c => `
            <div class="conflict-item">
                <span class="conflict-furniture">${_sgEscape(c.furniture_number || 'Mobiliario #' + c.furniture_id)}</span>
                <span class="conflict-date">${formatDate(c.date)}</span>
                <span class="conflict-reservation">
                    Reserva #${_sgEscape(c.ticket_number || c.reservation_id)}
                    ${c.customer_name ? ` - ${_sgEscape(c.customer_name)}` : ''}
                </span>
            </div>
        `).join('');

        return instance.show({
            code: 'SG-02',
            title: 'Mobiliario no disponible',
            type: 'error',
            message: `
                <p>El mobiliario seleccionado no esta disponible:</p>
                <div class="safeguard-detail-box error">
                    ${conflictList}
                </div>
                <p>Selecciona otro mobiliario o cambia las fechas.</p>
            `,
            buttons: [
                { label: 'Entendido', action: 'ok', style: 'primary' }
            ]
        });
    }

    /**
     * Show non-contiguous furniture warning
     * @param {Object} contiguityResult - Result from validate-contiguity endpoint
     * @returns {Promise<string|null>}
     */
    static async showContiguityWarning(contiguityResult) {
        const instance = SafeguardModal.getInstance();

        const gapCount = contiguityResult.gap_count || 0;
        const blockingFurniture = contiguityResult.blocking_furniture || [];

        // Build blocking furniture list
        const blockingList = blockingFurniture.length > 0
            ? blockingFurniture.map(f => `
                <span class="blocking-item">${_sgEscape(f.number || '#' + f.id)}</span>
            `).join('')
            : '<span class="no-blocking">Mobiliario disperso en diferentes filas</span>';

        return instance.show({
            code: 'SG-07',
            title: 'Mobiliario no agrupado',
            type: 'warning',
            message: `
                <p>El mobiliario seleccionado no esta agrupado.</p>
                <div class="safeguard-detail-box">
                    <div class="detail-row">
                        <span class="detail-label">Separaciones:</span>
                        <span class="detail-value highlight">${gapCount}</span>
                    </div>
                    ${blockingFurniture.length > 0 ? `
                    <div class="detail-row">
                        <span class="detail-label">Mobiliario entre seleccion:</span>
                        <div class="blocking-list">${blockingList}</div>
                    </div>
                    ` : ''}
                </div>
                <p class="safeguard-note">
                    <i class="fas fa-info-circle"></i>
                    Esto puede resultar en una experiencia fragmentada para el cliente.
                </p>
                <p class="safeguard-question">¿Continuar con esta seleccion?</p>
            `,
            buttons: [
                { label: 'Seleccionar otro', action: 'cancel', style: 'secondary' },
                { label: 'Continuar', action: 'proceed', style: 'warning' }
            ]
        });
    }

    /**
     * Get singleton instance
     */
    static getInstance() {
        if (!SafeguardModal._instance) {
            SafeguardModal._instance = new SafeguardModal();
        }
        return SafeguardModal._instance;
    }
}

// Initialize singleton
SafeguardModal._instance = null;

// Export for use
window.SafeguardModal = SafeguardModal;
