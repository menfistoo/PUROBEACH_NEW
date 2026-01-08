/**
 * Details Mixin for ReservationPanel
 *
 * Handles the details and payment sections display, including:
 * - renderDetailsSection() - Display num_people and notes in view mode
 * - renderPaymentSection() - Display payment ticket and method in view mode
 *
 * Dependencies: None
 *
 * Expected instance properties:
 * - detailNumPeople, detailNotes - View mode elements for details
 * - editNumPeople, editNotes - Edit mode elements for details
 * - paymentSection - Payment section container
 * - detailPaymentTicket, detailPaymentMethod - View mode payment elements
 * - editPaymentTicket, editPaymentMethod - Edit mode payment elements
 * - state: { numPeopleManuallyEdited }
 */

// =============================================================================
// DETAILS MIXIN
// =============================================================================

/**
 * Mixin that adds details and payment functionality to ReservationPanel
 * @param {Class} Base - The base class to extend
 * @returns {Class} Extended class with details methods
 */
export const DetailsMixin = (Base) => class extends Base {

    // =========================================================================
    // DETAILS SECTION
    // =========================================================================

    /**
     * Render details section (view mode)
     *
     * Displays number of people and notes in the reservation panel.
     * Also pre-fills edit mode fields for seamless transition.
     *
     * @param {Object} reservation - Reservation data with details
     * @param {number} [reservation.num_people=1] - Number of people in reservation
     * @param {string} [reservation.notes] - Reservation notes
     * @param {string} [reservation.observations] - Alternative field for notes
     */
    renderDetailsSection(reservation) {
        // Number of people
        if (this.detailNumPeople) {
            this.detailNumPeople.textContent = reservation.num_people || 1;
        }

        // Notes - check both possible field names
        const notes = reservation.notes || reservation.observations;

        if (this.detailNotes) {
            if (notes) {
                this.detailNotes.textContent = notes;
                this.detailNotes.classList.remove('empty');
            } else {
                this.detailNotes.textContent = 'Sin notas';
                this.detailNotes.classList.add('empty');
            }
        }

        // Pre-fill edit fields (only if not manually edited for num_people)
        if (this.editNumPeople && !this.state.numPeopleManuallyEdited) {
            this.editNumPeople.value = reservation.num_people || 1;
        }
        if (this.editNotes) {
            this.editNotes.value = notes || '';
        }
    }

    // =========================================================================
    // PAYMENT SECTION
    // =========================================================================

    /**
     * Payment method labels for Spanish display
     * @type {Object.<string, string>}
     */
    static PAYMENT_METHOD_LABELS = {
        'efectivo': 'Efectivo',
        'tarjeta': 'Tarjeta',
        'cargo_habitacion': 'Cargo a habitación'
    };

    /**
     * Render payment section (view mode)
     *
     * Displays payment ticket number and method in the reservation panel.
     * Translates internal payment method values to Spanish labels.
     * Also pre-fills edit mode fields.
     *
     * @param {Object} reservation - Reservation data with payment info
     * @param {string} [reservation.payment_ticket_number] - Payment ticket number
     * @param {string} [reservation.payment_method] - Payment method code (efectivo, tarjeta, cargo_habitacion)
     */
    renderPaymentSection(reservation) {
        if (!this.paymentSection) return;

        // Payment ticket number
        const ticketNumber = reservation.payment_ticket_number || '-';

        if (this.detailPaymentTicket) {
            this.detailPaymentTicket.textContent = ticketNumber;
        }
        if (this.editPaymentTicket) {
            this.editPaymentTicket.value = reservation.payment_ticket_number || '';
        }

        // Payment method - translate to Spanish for display
        const methodValue = reservation.payment_method || '';
        const methodLabels = this.constructor.PAYMENT_METHOD_LABELS;
        const methodDisplay = methodLabels[methodValue] || '-';

        if (this.detailPaymentMethod) {
            this.detailPaymentMethod.textContent = methodDisplay;
        }
        if (this.editPaymentMethod) {
            this.editPaymentMethod.value = methodValue;
        }
    }
};
