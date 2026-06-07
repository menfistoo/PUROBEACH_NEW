/**
 * Waitlist Renderers
 * Entry card rendering and list display
 */

import { formatDateShort, formatTimeAgo, getStatusLabel, getTimePreferenceLabel, escapeHtml } from './utils.js';

/**
 * Render a single entry card
 * @param {Object} entry - Entry data
 * @param {number|null} position - Position in list (null for history)
 * @param {boolean} isHistory - Whether this is a history entry
 * @returns {string} HTML string
 */
export function renderEntryCard(entry, position, isHistory) {
    const statusClass = `status-${entry.status}`;
    const statusLabel = getStatusLabel(entry.status);
    const timeAgo = formatTimeAgo(entry.created_at);
    const historyClass = isHistory ? 'history-entry' : '';
    const convertedClass = entry.status === 'converted' ? 'converted' : '';

    // Build preferences chips
    let prefsHtml = '';
    if (entry.zone_name) {
        prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-map-marker-alt"></i> ${escapeHtml(entry.zone_name)}</span>`;
    }
    if (entry.furniture_type_name) {
        prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-umbrella-beach"></i> ${escapeHtml(entry.furniture_type_name)}</span>`;
    }
    if (entry.time_preference) {
        const timeLabel = getTimePreferenceLabel(entry.time_preference);
        prefsHtml += `<span class="waitlist-pref-chip"><i class="fas fa-clock"></i> ${timeLabel}</span>`;
    }

    // Build actions (only for pending entries)
    let actionsHtml = '';
    if (!isHistory && (entry.status === 'waiting' || entry.status === 'contacted' || entry.status === 'no_answer')) {
        actionsHtml = `
            <div class="waitlist-entry-actions">
                <button type="button" class="btn-action btn-edit" data-action="edit" data-id="${entry.id}">
                    <i class="fas fa-edit"></i> Editar
                </button>
                <button type="button" class="btn-action btn-convert" data-action="convert" data-id="${entry.id}">
                    <i class="fas fa-check"></i> Convertir
                </button>
                <button type="button" class="btn-action btn-danger" data-action="declined" data-id="${entry.id}">
                    <i class="fas fa-times"></i> Cancelar
                </button>
            </div>
        `;
    }

    return `
        <div class="waitlist-entry ${historyClass} ${convertedClass}" data-entry-id="${entry.id}">
            <div class="waitlist-entry-header">
                ${position ? `<div class="waitlist-entry-priority">${position}</div>` : ''}
                <div class="waitlist-entry-customer">
                    <div class="waitlist-entry-name">${escapeHtml(entry.customer_name || 'Sin nombre')}</div>
                    <div class="waitlist-entry-meta">
                        ${entry.room_number ? `<i class="fas fa-door-open"></i> Hab. ${escapeHtml(entry.room_number)}` : ''}
                        ${entry.phone ? `<i class="fas fa-phone"></i> ${escapeHtml(entry.phone)}` : ''}
                        <span title="${entry.created_at}">${timeAgo}</span>
                    </div>
                </div>
                <span class="waitlist-entry-status ${statusClass}">${statusLabel}</span>
            </div>
            <div class="waitlist-entry-body">
                <div class="waitlist-entry-details">
                    <span class="waitlist-entry-detail">
                        <i class="fas fa-users"></i> ${entry.num_people} personas
                    </span>
                    <span class="waitlist-entry-detail">
                        <i class="fas fa-calendar"></i> ${formatDateShort(entry.requested_date)}
                    </span>
                    ${entry.package_name ? `
                        <span class="waitlist-entry-detail">
                            <i class="fas fa-gift"></i> ${escapeHtml(entry.package_name)}
                        </span>
                    ` : ''}
                </div>
                ${prefsHtml ? `<div class="waitlist-entry-preferences">${prefsHtml}</div>` : ''}
                ${entry.notes ? `<div class="waitlist-entry-notes">${escapeHtml(entry.notes)}</div>` : ''}
                ${actionsHtml}
            </div>
        </div>
    `;
}

/**
 * Render pending entries list
 * @param {Object} elements - DOM elements cache
 * @param {Array} entries - Entry data array
 * @param {Function} onActionClick - Callback for action button clicks
 */
export function renderPendingEntries(elements, entries, onActionClick) {
    if (!elements.entriesPending) return;

    if (entries.length === 0) {
        elements.entriesPending.innerHTML = '';
        elements.emptyPending.style.display = 'flex';
        return;
    }

    elements.emptyPending.style.display = 'none';

    const html = entries.map((entry, index) => renderEntryCard(entry, index + 1, false)).join('');
    elements.entriesPending.innerHTML = html;

    // Attach action listeners
    attachEntryListeners(elements.entriesPending, onActionClick);
}

/**
 * Render history entries list
 * @param {Object} elements - DOM elements cache
 * @param {Array} entries - Entry data array
 */
export function renderHistoryEntries(elements, entries) {
    if (!elements.entriesHistory) return;

    if (entries.length === 0) {
        elements.entriesHistory.innerHTML = '';
        elements.emptyHistory.style.display = 'flex';
        return;
    }

    elements.emptyHistory.style.display = 'none';

    const html = entries.map((entry) => renderEntryCard(entry, null, true)).join('');
    elements.entriesHistory.innerHTML = html;
}

/**
 * Attach click listeners to entry action buttons
 * @param {HTMLElement} container - Container element
 * @param {Function} onActionClick - Callback (entryId, action)
 */
export function attachEntryListeners(container, onActionClick) {
    container.querySelectorAll('.btn-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            const entryId = parseInt(btn.dataset.id);
            if (onActionClick) {
                onActionClick(entryId, action);
            }
        });
    });
}

/**
 * Populate zones dropdown
 * @param {HTMLSelectElement} selectEl - Select element
 * @param {Array} zones - Zone data array
 */
export function populateZonesDropdown(selectEl, zones) {
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Sin preferencia</option>';
    zones.forEach(zone => {
        const option = document.createElement('option');
        option.value = zone.id;
        option.textContent = zone.name;
        selectEl.appendChild(option);
    });
}

/**
 * Populate furniture types dropdown
 * @param {HTMLSelectElement} selectEl - Select element
 * @param {Array} furnitureTypes - Furniture type data array
 */
export function populateFurnitureTypesDropdown(selectEl, furnitureTypes) {
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Sin preferencia</option>';
    furnitureTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.textContent = type.display_name || type.name;
        selectEl.appendChild(option);
    });
}

/**
 * Populate packages dropdown
 * @param {HTMLSelectElement} selectEl - Select element
 * @param {Array} packages - Package data array
 */
export function populatePackagesDropdown(selectEl, packages) {
    if (!selectEl) return;

    selectEl.innerHTML = '<option value="">Seleccionar paquete...</option>';
    packages.forEach(pkg => {
        const option = document.createElement('option');
        option.value = pkg.id;
        option.textContent = `${pkg.package_name} - ${pkg.base_price}`;
        selectEl.appendChild(option);
    });
}

/**
 * Render room search results
 * @param {HTMLElement} resultsEl - Results container
 * @param {Array} guests - Guest data array
 * @param {Function} onSelect - Callback when guest selected
 */
export function renderRoomResults(resultsEl, results, onSelect) {
    if (!resultsEl) return;

    if (!results || results.length === 0) {
        resultsEl.innerHTML = '<div class="p-3 text-muted">No se encontraron resultados</div>';
        resultsEl.classList.add('show');
        return;
    }

    // Same badges as the new-reservation search.
    const badges = (r) => {
        let b = '';
        if (r.vip_status || r.vip_code) b += '<span class="cs-badge cs-vip">VIP</span>';
        if (r.is_main_guest) b += '<span class="cs-badge cs-main">Principal</span>';
        if (r.is_checkin_today) b += '<span class="cs-badge cs-checkin">Check-in</span>';
        if (r.is_checkout_today) b += '<span class="cs-badge cs-checkout">Check-out</span>';
        return b;
    };

    const html = results.map(r => {
        const phone = r.phone || '';
        if (r.source === 'hotel_guest') {
            const guestName = r.guest_name || `${r.first_name || ''} ${r.last_name || ''}`.trim();
            const guestCount = r.room_guest_count || r.guest_count || 1;
            const countDisplay = guestCount > 1 ? ` - x${guestCount}` : '';
            return `
                <div class="cs-item" data-source="hotel_guest" data-guest-id="${r.id}" data-guest-name="${escapeHtml(guestName)}" data-room="${escapeHtml(r.room_number || '')}" data-phone="${escapeHtml(phone)}" data-guest-count="${guestCount}">
                    <div class="cs-info">
                        <div class="cs-name">Hab. ${escapeHtml(r.room_number || '')} - ${escapeHtml(guestName)}${countDisplay} ${badges(r)}</div>
                        <div class="cs-details">${phone ? `<i class="fas fa-phone"></i> ${escapeHtml(phone)}` : ''}</div>
                    </div>
                </div>
            `;
        }
        // Existing beach customer
        const name = r.display_name || `${r.first_name || ''} ${r.last_name || ''}`.trim();
        const roomInfo = r.room_number ? `Hab. ${escapeHtml(r.room_number)}` : (r.customer_type === 'externo' ? 'Externo' : '');
        return `
            <div class="cs-item" data-source="customer" data-customer-id="${r.id}" data-customer-name="${escapeHtml(name)}" data-room="${escapeHtml(r.room_number || '')}" data-phone="${escapeHtml(phone)}">
                <div class="cs-info">
                    <div class="cs-name">${escapeHtml(name)} ${badges(r)}</div>
                    <div class="cs-details">${roomInfo}${phone ? ` <i class="fas fa-phone"></i> ${escapeHtml(phone)}` : ''}</div>
                </div>
            </div>
        `;
    }).join('');

    resultsEl.innerHTML = html;
    resultsEl.classList.add('show');

    // Attach click listeners
    resultsEl.querySelectorAll('.cs-item').forEach(item => {
        item.addEventListener('click', () => onSelect(item));
    });
}

/**
 * Render customer search results
 * @param {HTMLElement} resultsEl - Results container
 * @param {Array} customers - Customer data array
 * @param {Function} onSelect - Callback when customer selected
 */
export function renderCustomerResults(resultsEl, customers, onSelect) {
    if (!resultsEl) return;

    if (customers.length === 0) {
        resultsEl.innerHTML = '<div class="p-3 text-muted">No se encontraron clientes</div>';
        resultsEl.classList.add('show');
        return;
    }

    const html = customers.map(customer => {
        const name = customer.display_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim();
        return `
            <div class="cs-item" data-customer-id="${customer.id}" data-customer-name="${escapeHtml(name)}" data-phone="${escapeHtml(customer.phone || '')}">
                <div class="cs-info">
                    <div class="cs-name">${escapeHtml(name)}</div>
                    <div class="cs-details">${customer.phone ? `<i class="fas fa-phone"></i> ${escapeHtml(customer.phone)}` : ''}</div>
                </div>
            </div>
        `;
    }).join('');

    resultsEl.innerHTML = html;
    resultsEl.classList.add('show');

    // Attach click listeners
    resultsEl.querySelectorAll('.cs-item').forEach(item => {
        item.addEventListener('click', () => onSelect(item));
    });
}
