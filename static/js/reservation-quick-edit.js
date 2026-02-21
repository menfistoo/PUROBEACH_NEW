/**
 * Reservation Quick Edit Modal - Shared JS
 * Used by reservations list and customer detail pages.
 *
 * Requires:
 * - Bootstrap 5 (modal)
 * - CSRF token in a <input name="csrf_token"> or <meta name="csrf-token">
 * - #quickEditModal HTML partial included in the page
 */

let quickEditModal = null;
let currentReservation = null;
let allCharacteristics = [];
let allTags = [];

document.addEventListener('DOMContentLoaded', function() {
    const modalEl = document.getElementById('quickEditModal');
    if (!modalEl) return;

    quickEditModal = new bootstrap.Modal(modalEl);

    // State chip selection
    document.querySelectorAll('#quickEditModal .state-chip').forEach(chip => {
        chip.addEventListener('click', function() {
            document.querySelectorAll('#quickEditModal .state-chip').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
        });
    });

    // Paid checkbox change
    document.getElementById('edit-paid').addEventListener('change', updatePaidLabel);

    // Auto-toggle paid when payment details are filled
    document.getElementById('edit-payment-ticket').addEventListener('input', function() {
        if (this.value.trim()) {
            document.getElementById('edit-paid').checked = true;
            updatePaidLabel();
        }
    });

    document.getElementById('edit-payment-method').addEventListener('change', function() {
        if (this.value) {
            document.getElementById('edit-paid').checked = true;
            updatePaidLabel();
        }
    });
});

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        return `${day}/${month}/${year}`;
    } catch(e) {
        return dateStr;
    }
}

async function loadAllCharacteristics() {
    if (allCharacteristics.length > 0) return;
    try {
        const response = await fetch('/beach/api/preferences');
        if (response.ok) {
            const result = await response.json();
            allCharacteristics = result.preferences || [];
        }
    } catch (error) {
        console.error('Failed to load characteristics:', error);
    }
}

function renderCharacteristicsChips(selectedCharacteristics) {
    const container = document.getElementById('edit-characteristics-chips');
    if (!container || allCharacteristics.length === 0) {
        if (container) container.innerHTML = '<span class="text-muted small">Sin características disponibles</span>';
        return;
    }

    const selectedCodes = (selectedCharacteristics || []).map(c => c.code);

    container.innerHTML = allCharacteristics.map(char => {
        const isSelected = selectedCodes.includes(char.code);
        let icon = char.icon || 'fa-heart';
        if (icon && !icon.startsWith('fas ') && !icon.startsWith('far ') && !icon.startsWith('fab ')) {
            icon = 'fas ' + icon;
        }
        return `
            <button type="button" class="char-chip ${isSelected ? 'selected' : ''}"
                    data-code="${char.code}" title="${char.name}">
                <i class="${icon}"></i>
                <span>${char.name}</span>
            </button>
        `;
    }).join('');

    // Attach click handlers
    container.querySelectorAll('.char-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('selected');
        });
    });
}

async function loadAllTags() {
    if (allTags.length > 0) return;
    try {
        const response = await fetch('/beach/api/tags');
        if (response.ok) {
            const result = await response.json();
            allTags = result.tags || [];
        }
    } catch (error) {
        console.error('Failed to load tags:', error);
    }
}

function renderTagChips(selectedTags) {
    const container = document.getElementById('edit-tag-chips');
    if (!container || allTags.length === 0) {
        if (container) container.innerHTML = '<span class="text-muted small">Sin etiquetas disponibles</span>';
        return;
    }

    const selectedIds = (selectedTags || []).map(t => t.id);

    container.innerHTML = allTags.map(tag => {
        const isSelected = selectedIds.includes(tag.id);
        return `
            <button type="button" class="tag-chip ${isSelected ? 'selected' : ''}"
                    data-tag-id="${tag.id}" title="${tag.description || tag.name}"
                    style="--tag-color: ${tag.color || '#6C757D'};">
                <i class="fas fa-tag"></i>
                <span>${tag.name}</span>
            </button>
        `;
    }).join('');

    container.querySelectorAll('.tag-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chip.classList.toggle('selected');
        });
    });
}

async function openQuickEdit(reservationId) {
    try {
        const response = await fetch(`/beach/api/reservations/${reservationId}`);
        if (!response.ok) throw new Error('Error al cargar reserva');

        const result = await response.json();
        const data = result.data || result;
        currentReservation = data;

        // Basic info
        document.getElementById('edit-reservation-id').value = reservationId;
        document.getElementById('modal-ticket').textContent = data.ticket_number || `#${reservationId}`;

        // Info bar - Customer
        document.getElementById('edit-customer-name').textContent = data.customer_name || '-';
        const typeEl = document.getElementById('edit-customer-type');
        if (data.customer_type === 'interno') {
            typeEl.textContent = 'Interno';
            typeEl.style.background = '#4A90A4';
        } else {
            typeEl.textContent = 'Externo';
            typeEl.style.background = '#1A3A5C';
        }

        // Room number (interno only)
        const roomItem = document.getElementById('edit-room-item');
        if (data.customer_type === 'interno' && data.customer_room) {
            roomItem.style.display = 'flex';
            document.getElementById('edit-room').textContent = data.customer_room;
        } else {
            roomItem.style.display = 'none';
        }

        // Date
        document.getElementById('edit-date').textContent = formatDate(data.reservation_date || data.start_date);

        // Furniture
        const furnitureList = data.furniture || [];
        let furnitureText = '-';
        if (furnitureList.length > 0) {
            furnitureText = furnitureList.map(f => {
                const name = f.number || f.furniture_type || '';
                const zone = f.zone_name ? ` (${f.zone_name})` : '';
                return name + zone;
            }).join(', ');
        }
        document.getElementById('edit-furniture').textContent = furnitureText;

        // Editable fields
        document.getElementById('edit-num-people').value = data.num_people || 1;
        document.getElementById('edit-paid').checked = data.paid == 1;
        updatePaidLabel();
        document.getElementById('edit-notes').value = data.notes || data.observations || '';
        document.getElementById('edit-price').textContent = `€${(data.final_price || 0).toFixed(2)}`;

        // Payment details
        document.getElementById('edit-payment-ticket').value = data.payment_ticket_number || '';
        document.getElementById('edit-payment-method').value = data.payment_method || '';

        // Load and render characteristics
        await loadAllCharacteristics();
        renderCharacteristicsChips(data.reservation_characteristics || []);

        // Load and render tags
        await loadAllTags();
        renderTagChips(data.tags || []);

        // Select current state
        document.querySelectorAll('#quickEditModal .state-chip').forEach(chip => {
            chip.classList.remove('selected');
            if (chip.dataset.stateName === data.current_state) {
                chip.classList.add('selected');
            }
        });

        quickEditModal.show();
    } catch (error) {
        console.error(error);
        if (typeof showToast === 'function') {
            showToast('Error al cargar la reserva', 'error');
        } else {
            alert('Error al cargar la reserva');
        }
    }
}

function adjustPeople(delta) {
    const input = document.getElementById('edit-num-people');
    let value = parseInt(input.value) || 1;
    value = Math.max(1, Math.min(20, value + delta));
    input.value = value;
}

function updatePaidLabel() {
    const checkbox = document.getElementById('edit-paid');
    const label = document.getElementById('paid-label');
    if (checkbox.checked) {
        label.textContent = 'Pagado';
        label.classList.add('paid');
    } else {
        label.textContent = 'Pendiente';
        label.classList.remove('paid');
    }
}

function _getCSRFToken() {
    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    return '';
}

async function saveQuickEdit() {
    const reservationId = document.getElementById('edit-reservation-id').value;
    const selectedState = document.querySelector('#quickEditModal .state-chip.selected');

    const updates = {
        num_people: parseInt(document.getElementById('edit-num-people').value),
        paid: document.getElementById('edit-paid').checked ? 1 : 0,
        observations: document.getElementById('edit-notes').value,
        payment_ticket_number: document.getElementById('edit-payment-ticket').value.trim() || null,
        payment_method: document.getElementById('edit-payment-method').value || null
    };

    // Collect selected characteristics
    const selectedChars = Array.from(
        document.querySelectorAll('#edit-characteristics-chips .char-chip.selected')
    ).map(chip => chip.dataset.code);
    updates.preferences = selectedChars.join(',');

    // Collect selected tags
    const selectedTagIds = Array.from(
        document.querySelectorAll('#edit-tag-chips .tag-chip.selected')
    ).map(chip => parseInt(chip.dataset.tagId));
    updates.tag_ids = selectedTagIds;

    // Add state if changed
    if (selectedState && selectedState.dataset.stateName !== currentReservation.current_state) {
        updates.state_id = parseInt(selectedState.dataset.stateId);
    }

    try {
        const response = await fetch(`/beach/api/map/reservations/${reservationId}/update`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': _getCSRFToken()
            },
            body: JSON.stringify(updates)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al guardar');
        }

        quickEditModal.hide();
        location.reload();
    } catch (error) {
        console.error(error);
        if (typeof showToast === 'function') {
            showToast('Error al guardar: ' + error.message, 'error');
        } else {
            alert('Error al guardar: ' + error.message);
        }
    }
}
