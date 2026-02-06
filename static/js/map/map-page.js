/**
 * Map Page Initialization
 *
 * Main initialization logic for the beach map page (/beach/map)
 * Extracted from templates/beach/map.html for maintainability
 *
 * Dependencies (loaded via script tags in map.html):
 * - BeachMap, WaitlistManager, ReservationPanel, NewReservationPanel
 * - TouchHandler (global)
 *
 * ES Module imports:
 * - SearchManager, BlockManager, TempFurnitureManager
 * - MoveMode, MoveModePanel, PinchZoomHandler
 */

import { SearchManager } from '/static/js/map/SearchManager.js';
import { BlockManager } from '/static/js/map/block-manager.js';
import { TempFurnitureManager } from '/static/js/map/temp-furniture-manager.js';
import { MoveMode } from '/static/js/map/MoveMode.js';
import { MoveModePanel } from '/static/js/map/MoveModePanel.js';
import { PinchZoomHandler } from '/static/js/map/pinch-zoom.js';

document.addEventListener('DOMContentLoaded', function () {
    // ==========================================================================
    // INITIALIZE MAP
    // ==========================================================================
    const map = new BeachMap('map-container', {
        apiUrl: '/beach/api/map/data',
        initialDate: new Date().toISOString().split('T')[0],
        enableZoom: true
    });

    // Expose map globally for panel access
    window.beachMap = map;

    // ==========================================================================
    // BLOCK MANAGER (Furniture blocking functionality)
    // ==========================================================================
    const blockManager = new BlockManager({
        getCurrentDate: () => map.getCurrentDate(),
        onBlockSuccess: () => {
            map.clearSelection();
            map.refreshAvailability();
        },
        onUnblockSuccess: () => {
            map.clearSelection();
            map.refreshAvailability();
        },
        getBlockInfo: (furnitureId) => {
            const data = map.getData();
            return data?.blocks?.[furnitureId] || null;
        }
    });

    // Wire up BeachMap block/unblock callbacks
    map.on('onBlockRequest', (furnitureIds, furnitureNumbers) => {
        blockManager.showBlockModal(furnitureIds, furnitureNumbers);
    });

    map.on('onUnblockRequest', (furnitureId, furnitureNumber) => {
        const data = map.getData();
        const blockInfo = data?.blocks?.[furnitureId] || null;
        blockManager.showUnblockModal(furnitureId, furnitureNumber, blockInfo);
    });

    // ==========================================================================
    // TEMP FURNITURE MANAGER (Add/delete temporary furniture)
    // ==========================================================================
    const tempFurnitureManager = new TempFurnitureManager({
        getCurrentDate: () => map.getCurrentDate(),
        getZones: () => map.getData()?.zones || [],
        getFurnitureTypes: () => map.getData()?.furniture_types || {},
        onCreateSuccess: () => map.refreshAvailability(),
        onDeleteSuccess: () => {
            map.clearSelection();
            map.refreshAvailability();
        }
    });

    // Wire up temp furniture callbacks
    map.on('onAddTemporaryRequest', (x, y, zoneId) => {
        tempFurnitureManager.showCreateModal(x, y, zoneId);
    });

    map.on('onDeleteTemporaryRequest', (furnitureId, furnitureNumber) => {
        tempFurnitureManager.showDeleteModal(furnitureId, furnitureNumber);
    });

    // Toolbar button handler
    const addTempBtn = document.getElementById('btn-add-temp-furniture');
    if (addTempBtn) {
        addTempBtn.addEventListener('click', () => {
            // Open modal with default position (will be in first zone)
            const zones = map.getData()?.zones || [];
            const firstZoneId = zones.length > 0 ? zones[0].id : null;
            tempFurnitureManager.showCreateModal(100, 100, firstZoneId);
        });
    }

    // ==========================================================================
    // MOVE MODE MANAGER (Furniture reassignment)
    // ==========================================================================
    const moveMode = new MoveMode({
        apiBaseUrl: '/beach/api/move-mode'
    });

    const moveModePanel = new MoveModePanel('moveModePanel', moveMode);

    // Store global unassigned data for tooltip and navigation
    let globalUnassignedData = null;

    // Move mode button handler
    const moveModeBtn = document.getElementById('btn-move-mode');
    if (moveModeBtn) {
        moveModeBtn.addEventListener('click', async () => {
            if (moveMode.isActive()) {
                moveMode.deactivate();
                moveModeBtn.classList.remove('active');
                document.querySelector('.beach-map-container')?.classList.remove('move-mode-active');
            } else {
                // If there are unassigned reservations, navigate to first problematic date
                let targetDate = map.getCurrentDate();
                if (globalUnassignedData && globalUnassignedData.first_date) {
                    targetDate = globalUnassignedData.first_date;
                    // Navigate map to that date if different from current
                    if (targetDate !== map.getCurrentDate()) {
                        await map.goToDate(targetDate);
                    }
                }

                moveMode.activate(targetDate);
                moveModeBtn.classList.add('active');
                document.querySelector('.beach-map-container')?.classList.add('move-mode-active');

                // Show onboarding toast on first use (mobile-focused)
                showMoveModeOnboarding();
            }
        });
    }

    // Note: moveMode.currentDate is updated from the main onDateChange handler

    // Wire up move mode deactivate to update button state
    moveMode.on('onDeactivate', () => {
        moveModeBtn?.classList.remove('active');
        document.querySelector('.beach-map-container')?.classList.remove('move-mode-active');
        map.clearPreferenceHighlights();
        map.refreshAvailability();
        // Refresh global badge after move mode - assignments may have changed
        checkUnassignedReservationsGlobal();
    });

    // Handle edit reservation from move mode - Issue #8, #14
    document.addEventListener('moveMode:editReservation', (e) => {
        const { reservationId } = e.detail;

        // Force exit move mode to avoid panel overlap - Issue #14
        // Use forceDeactivate() to skip the "assign all reservations" check
        if (moveMode.isActive()) {
            moveMode.forceDeactivate();
        }

        // Open the reservation edit modal
        if (typeof openReservationPanel === 'function') {
            openReservationPanel(reservationId, 'edit');
        } else {
            // Fallback: dispatch to reservation details handler
            document.dispatchEvent(new CustomEvent('furniture:showReservation', {
                detail: { reservationId }
            }));
        }
    });

    // Handle return to conflict from move mode - Issue #7
    document.addEventListener('moveMode:returnToConflict', (e) => {
        const conflictContext = e.detail;

        if (conflictContext) {
            // Re-dispatch the cancelled event to restore the conflict modal
            // The ConflictResolutionModal listens for this event and restores itself
            document.dispatchEvent(new CustomEvent('conflictResolution:cancelled'));
        }
    });

    // Badge element for unassigned reservations
    const unassignedBadge = document.getElementById('moveModeUnassignedBadge');

    // Function to update the badge visibility and tooltip
    function updateUnassignedBadge(count, data = null) {
        if (unassignedBadge) {
            unassignedBadge.style.display = count > 0 ? 'flex' : 'none';

            // Update tooltip with dates info
            if (data && data.dates && data.dates.length > 0) {
                const dateLabels = data.dates.slice(0, 3).map(d => {
                    const date = new Date(d + 'T12:00:00');
                    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
                }).join(', ');
                const suffix = data.dates.length > 3 ? ` +${data.dates.length - 3} más` : '';
                moveModeBtn.title = `${count} reserva(s) sin asignar (${dateLabels}${suffix})`;
            } else if (count > 0) {
                moveModeBtn.title = `${count} reserva(s) sin asignar`;
            } else {
                moveModeBtn.title = 'Modo Mover - Reorganizar mobiliario';
            }
        }
    }

    // Wire up pool update to refresh map and update warning badge
    moveMode.on('onPoolUpdate', (data) => {
        map.refreshAvailability();

        // Update badge based on unassigned reservations in pool
        const unassignedCount = (data.pool || []).filter(r => r.assignedCount < r.totalNeeded).length;
        updateUnassignedBadge(unassignedCount);
    });

    /**
     * Show onboarding toast for move mode on first use
     * Explains touch gestures for mobile/tablet users
     */
    function showMoveModeOnboarding() {
        const storageKey = 'moveMode_onboarding_shown';

        // Only show once
        if (localStorage.getItem(storageKey)) {
            return;
        }

        // Mark as shown
        localStorage.setItem(storageKey, 'true');

        // Check if touch device (more likely to need gesture explanation)
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

        const message = isTouchDevice
            ? 'Toca mobiliario para liberar. Mantén presionado para liberar todo.'
            : 'Clic para liberar mobiliario. Ctrl+Clic para liberar todo.';

        if (window.PuroBeach && window.PuroBeach.showToast) {
            window.PuroBeach.showToast(message, 'info', 5000);
        }
    }

    // Check for unassigned reservations GLOBALLY (next 7 days) and update warning badge
    async function checkUnassignedReservationsGlobal() {
        try {
            const response = await fetch('/beach/api/move-mode/unassigned-global', {
                headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' }
            });
            if (response.ok) {
                const data = await response.json();
                globalUnassignedData = data;
                console.log('[MoveMode] Global unassigned check:', data.count, 'reservations', data.dates);
                updateUnassignedBadge(data.count || 0, data);
            }
        } catch (error) {
            console.error('Error checking unassigned reservations:', error);
        }
    }

    // Check on page load (global - next 7 days)
    checkUnassignedReservationsGlobal();

    // Wire up furniture highlighting for preference matches (tiered)
    moveMode.on('onFurnitureHighlight', (data) => {
        const furniture = data.furniture || [];
        // Full match: 100% of preferences matched
        const fullMatchIds = furniture
            .filter(f => f.match_score === 1)
            .map(f => f.id || f.furniture_id);
        // Partial match: some but not all preferences matched
        const partialMatchIds = furniture
            .filter(f => f.match_score > 0 && f.match_score < 1)
            .map(f => f.id || f.furniture_id);
        map.applyPreferenceHighlights(fullMatchIds, partialMatchIds);
    });

    // Wire up lock blocked event to show warning toast
    moveMode.on('onLockBlocked', (data) => {
        // Show toast message only
        showToast('Mobiliario bloqueado - no se puede mover', 'warning');
    });

    // Expose moveMode to BeachMap for furniture click handling
    window.moveMode = moveMode;

    // Keyboard shortcuts for move mode
    document.addEventListener('keydown', (event) => {
        if (moveMode.isActive()) {
            moveMode.handleKeyboard(event);
        }
    });

    // ==========================================================================
    // WAITLIST MANAGER (Waitlist panel functionality)
    // ==========================================================================
    // Track pending waitlist conversion entry
    let pendingWaitlistEntry = null;

    // Helper to normalize date to ISO format (YYYY-MM-DD)
    function normalizeToISO(dateStr) {
        if (!dateStr) return null;
        // Already ISO format
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
        // Try to parse and convert
        try {
            const d = new Date(dateStr);
            if (!isNaN(d.getTime())) {
                return d.toISOString().split('T')[0];
            }
        } catch (e) {}
        return null;
    }

    const waitlistManager = new WaitlistManager({
        currentDate: map.getCurrentDate(),
        onConvert: (entry) => {
            // Store the waitlist entry for pre-filling after furniture selection
            // Normalize dates to ISO format for consistency
            if (entry.requested_date) {
                entry.requested_date = normalizeToISO(entry.requested_date);
            }
            pendingWaitlistEntry = entry;

            // Show toast to guide user
            if (window.PuroBeach && window.PuroBeach.showToast) {
                window.PuroBeach.showToast('Selecciona mobiliario en el mapa para crear la reserva', 'info', 5000);
            }

            // Set the date to the requested date if available
            if (entry.requested_date) {
                map.goToDate(entry.requested_date);
            }

            // Dispatch event to notify other components
            document.dispatchEvent(new CustomEvent('waitlist:convertToReservation', {
                detail: { entry }
            }));
        }
    });

    // Toolbar button click handler
    document.getElementById('waitlistToolbarBtn')?.addEventListener('click', () => {
        waitlistManager.open();
    });

    // Function to update waitlist badge
    function updateWaitlistBadge() {
        waitlistManager.setDate(map.getCurrentDate());
        const badge = document.getElementById('waitlistToolbarBadge');
        if (badge) {
            // Fetch current count from API
            fetch(`/beach/api/waitlist/count?date=${map.getCurrentDate()}`)
                .then(response => response.json())
                .then(data => {
                    const count = data.count || 0;
                    badge.textContent = count > 0 ? count : '';
                    badge.dataset.count = count;
                })
                .catch(err => console.error('Error fetching waitlist count:', err));
        }
    }

    // Listen for waitlist count updates
    window.addEventListener('waitlist:countUpdate', updateWaitlistBadge);

    // Note: updateWaitlistBadge is called from the main onDateChange handler

    // Initial badge update after short delay for map to load
    setTimeout(updateWaitlistBadge, 500);

    // ==========================================================================
    // SEARCH MANAGER (Enhanced with filters and grouped results)
    // ==========================================================================
    const searchManager = new SearchManager();

    // Load search reservations when map renders
    map.on('onRender', (data) => {
        const zoneId = document.getElementById('zone-select')?.value || null;
        searchManager.loadReservations(map.getCurrentDate(), zoneId ? parseInt(zoneId) : null);
    });

    // Also load initial data after a short delay
    setTimeout(() => {
        const zoneId = document.getElementById('zone-select')?.value || null;
        searchManager.loadReservations(map.getCurrentDate(), zoneId ? parseInt(zoneId) : null);
    }, 500);

    // Handle search result selection (active reservations)
    searchManager.on('onSelect', (result) => {
        // Highlight ALL furniture for this reservation
        if (result.furnitureIds && result.furnitureIds.length > 0) {
            // Highlight first furniture and pan to it
            map.highlightAndPanToFurniture(result.furnitureIds[0]);
            // Highlight additional furniture items
            result.furnitureIds.slice(1).forEach(id => {
                const el = document.querySelector(`[data-furniture-id="${id}"]`);
                if (el) el.classList.add('search-highlight');
            });
        }

        // Open reservation panel
        if (result.reservationId) {
            openReservationPanel(result.reservationId, 'view');
        }
    });

    // Handle navigation for released reservations
    searchManager.on('onNavigate', (reservationId) => {
        window.location.href = `/beach/reservations/${reservationId}`;
    });

    // Filter event listeners
    const filterStateSelect = document.getElementById('search-filter-state');
    const filterTypeSelect = document.getElementById('search-filter-type');
    const filterPaidSelect = document.getElementById('search-filter-paid');
    const filterClearBtn = document.getElementById('filter-clear-btn');

    // Function to update filter dropdown active states and clear button visibility
    function updateFilterUI() {
        const hasFilters = filterStateSelect?.value || filterTypeSelect?.value || filterPaidSelect?.value;

        // Toggle active class on dropdowns
        filterStateSelect?.classList.toggle('active', !!filterStateSelect.value);
        filterTypeSelect?.classList.toggle('active', !!filterTypeSelect.value);
        filterPaidSelect?.classList.toggle('active', !!filterPaidSelect.value);

        // Show/hide clear button
        if (filterClearBtn) {
            filterClearBtn.style.display = hasFilters ? 'flex' : 'none';
        }
    }

    if (filterStateSelect) {
        filterStateSelect.addEventListener('change', (e) => {
            searchManager.setFilter('state', e.target.value || null);
            updateFilterUI();
        });
    }
    if (filterTypeSelect) {
        filterTypeSelect.addEventListener('change', (e) => {
            searchManager.setFilter('customerType', e.target.value || null);
            updateFilterUI();
        });
    }
    if (filterPaidSelect) {
        filterPaidSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            searchManager.setFilter('paid', val === '' ? null : val === '1');
            updateFilterUI();
        });
    }
    if (filterClearBtn) {
        filterClearBtn.addEventListener('click', () => {
            searchManager.clearFilters();
            // Reset dropdown values
            if (filterStateSelect) filterStateSelect.value = '';
            if (filterTypeSelect) filterTypeSelect.value = '';
            if (filterPaidSelect) filterPaidSelect.value = '';
            updateFilterUI();
        });
    }

    // Reload search data when zone changes
    document.getElementById('zone-select')?.addEventListener('change', () => {
        const zoneId = document.getElementById('zone-select')?.value || null;
        searchManager.loadReservations(map.getCurrentDate(), zoneId ? parseInt(zoneId) : null);
    });

    // Add global keyboard listener for search shortcut (Ctrl+F or /)
    document.addEventListener('keydown', (e) => {
        const isInputField = ['input', 'textarea', 'select'].includes(e.target.tagName.toLowerCase());
        if (!isInputField) {
            if ((e.ctrlKey && e.key === 'f') || e.key === '/') {
                e.preventDefault();
                searchManager.focus();
            }
        }
    });

    // ==========================================================================
    // RESERVATION PANEL (Slide-in for editing)
    // ==========================================================================
    const reservationPanel = new ReservationPanel({
        apiBaseUrl: '/beach/api',
        onClose: () => {
            // Refresh map when panel closes
            map.refreshAvailability();
            updateStats(currentZoneId);
        },
        onStateChange: (reservationId, newState) => {
            // Refresh map after state change
            map.refreshAvailability();
            updateStats(currentZoneId);
        },
        onSave: (reservationId, updates) => {
            // Refresh map after save
            map.refreshAvailability();
            updateStats(currentZoneId);
        },
        onCustomerChange: (reservationId, customer) => {
            // Refresh map after customer change
            map.refreshAvailability();
        }
    });

    // Function to open the reservation panel
    function openReservationPanel(reservationId, mode = 'view') {
        const currentDate = map.getCurrentDate();
        reservationPanel.setMapData(map.getData());
        reservationPanel.open(reservationId, currentDate, mode);
    }

    // ==========================================================================
    // NEW RESERVATION PANEL (Slide-in for creating)
    // ==========================================================================
    const newReservationPanel = new NewReservationPanel({
        apiBaseUrl: '/beach/api',
        onSave: (reservation) => {
            // Refresh map after creating reservation
            map.refreshAvailability();
            map.clearSelection();
            updateSelectionBar();
            updateStats(currentZoneId);
        },
        onCancel: () => {
            // Keep selection on cancel so user can try again
            // Clear any pending waitlist entry if panel cancelled
            pendingWaitlistEntry = null;
        }
    });

    // Function to open the new reservation panel
    function openNewReservationPanel() {
        const selected = map.getSelectedFurnitureData();
        if (selected.length === 0) {
            if (window.PuroBeach && window.PuroBeach.showToast) {
                window.PuroBeach.showToast('Selecciona mobiliario primero', 'warning');
            }
            return;
        }
        const currentDate = map.getCurrentDate();
        newReservationPanel.open(selected, currentDate);

        // If there's a pending waitlist entry, pre-fill the form
        if (pendingWaitlistEntry) {
            newReservationPanel.prefillFromWaitlist(pendingWaitlistEntry);
            pendingWaitlistEntry = null; // Clear after use
        }
    }

    // ==========================================================================
    // ADD MORE FURNITURE MODE (from capacity warning in new reservation panel)
    // ==========================================================================
    let addMoreFurnitureContext = null;

    // Listen for request to add more furniture
    document.addEventListener('reservation:addMoreFurniture', (e) => {
        const { currentFurniture, neededCapacity, currentDate } = e.detail;

        // Store context for when user confirms selection
        addMoreFurnitureContext = {
            currentFurniture: currentFurniture,
            neededCapacity: neededCapacity,
            date: currentDate
        };

        // Clear any existing selection
        map.clearSelection();

        // Pre-select the furniture that was already selected in the panel
        currentFurniture.forEach(id => {
            map.selectFurniture(id, true);
        });

        updateSelectionBar();

        // Show toast with instructions
        if (window.PuroBeach && window.PuroBeach.showToast) {
            window.PuroBeach.showToast(`Selecciona ${neededCapacity} mobiliario(s) adicional(es) y pulsa "Reservar"`, 'info', 5000);
        }
    });

    // Override the openNewReservationPanel to handle add furniture mode
    const originalOpenNewReservationPanel = openNewReservationPanel;
    openNewReservationPanel = function() {
        if (addMoreFurnitureContext) {
            // In add furniture mode - send selected furniture back to panel
            const selected = map.getSelectedFurnitureData();
            const newFurniture = selected.filter(f => !addMoreFurnitureContext.currentFurniture.includes(f.id));

            if (newFurniture.length > 0) {
                // Add the new furniture to the reservation panel
                newReservationPanel.addFurniture(newFurniture);
            } else {
                // Just restore the panel
                newReservationPanel.panel.classList.remove('minimized');
                newReservationPanel.backdrop.classList.add('show');
            }

            // Clear the context but keep furniture selected on map
            addMoreFurnitureContext = null;

            // Update map selection to show all furniture in the panel
            const allPanelFurniture = newReservationPanel.state.selectedFurniture.map(f => f.id);
            map.clearSelection();
            allPanelFurniture.forEach(id => {
                map.selectFurniture(id, true);
            });
            updateSelectionBar();
        } else {
            // Normal behavior
            originalOpenNewReservationPanel();
        }
    };

    // ==========================================================================
    // CONFLICT RESOLUTION - Alternative selection from map
    // ==========================================================================
    let conflictResolutionContext = null;

    // Listen for request to select alternative furniture
    document.addEventListener('conflictResolution:selectAlternative', (e) => {
        const { date, conflicts, currentSelection, originalCount, conflictingLabels } = e.detail;

        // Store context for when user confirms selection
        // requiredCount = total furniture originally selected (for contiguity)
        conflictResolutionContext = {
            date: date,
            conflicts: conflicts,
            originalSelection: currentSelection,
            requiredCount: originalCount || currentSelection.length,
            conflictingLabels: conflictingLabels
        };

        // Hide the panel backdrop to ensure map is fully interactive
        const backdrop = document.getElementById('newReservationPanelBackdrop');
        if (backdrop) {
            backdrop.classList.remove('show');
        }

        // Clear any existing selection so user starts fresh
        map.clearSelection();
        updateSelectionBar();

        // Navigate map to the conflict date
        if (date !== map.getCurrentDate()) {
            map.goToDate(date).then(() => {
                // Ensure selection is cleared after map loads
                map.clearSelection();
                updateSelectionBar();

                // Highlight after map loads
                highlightConflictingFurniture(conflicts);
                updateConflictSelectionCounter();
            });
        } else {
            highlightConflictingFurniture(conflicts);
        }

        // Update selection bar to show conflict resolution mode
        updateSelectionBarForConflict();

        // Show instruction panel with conflicting furniture labels
        showConflictInstructions(conflicts, conflictResolutionContext.requiredCount, conflictingLabels);
    });

    // Highlight conflicting furniture on the map
    function highlightConflictingFurniture(conflicts) {
        // Clear any existing highlights first
        clearConflictHighlights();

        // Apply highlight to each conflicting furniture
        conflicts.forEach(conflict => {
            const el = document.querySelector(
                `.furniture-item[data-furniture-id="${conflict.furniture_id}"]`
            );
            if (el) {
                el.classList.add('conflict-blocked');
            }
        });
    }

    // Clear conflict highlights
    function clearConflictHighlights() {
        document.querySelectorAll('.furniture-item.conflict-blocked').forEach(el => {
            el.classList.remove('conflict-blocked');
        });
    }

    // Show conflict instruction panel
    function showConflictInstructions(conflicts, requiredCount, conflictingLabels) {
        const panel = document.getElementById('conflictInstructionPanel');

        // Get conflicting furniture labels
        const labels = conflictingLabels ||
            conflicts.map(c => c.furniture_number || `#${c.furniture_id}`).join(', ');

        // Update counters
        document.getElementById('conflictRequiredCount').textContent = requiredCount;
        document.getElementById('conflictSelectedCount').textContent = map.getSelectedFurniture().length;

        // Check if all conflicts are resolved
        if (!conflicts || conflicts.length === 0) {
            document.getElementById('conflictInstructionText').innerHTML =
                `<i class="fas fa-check-circle text-success"></i> Conflicto resuelto<br>` +
                `Selecciona ${requiredCount} hamaca(s)`;
            document.getElementById('conflictReplacingList').innerHTML =
                `<small>La hamaca original ya está disponible</small>`;
        } else {
            // Build detailed conflict info
            let conflictDetails = '';
            conflicts.forEach(c => {
                const blockerInfo = c.room_number
                    ? `Hab. ${c.room_number} (${c.customer_name})`
                    : c.customer_name;

                conflictDetails += `<div class="mb-1">
                    <strong>${c.furniture_number || '#' + c.furniture_id}</strong>: 
                    <span class="text-danger">${blockerInfo}</span>
                </div>`;
            });

            // Update instruction text to show which furniture has conflict
            document.getElementById('conflictInstructionText').innerHTML =
                `<div class="mb-2">${conflictDetails}</div>` +
                `Selecciona ${requiredCount} hamaca(s) alternativa(s)`;

            // Show tip about clicking conflicting furniture
            document.getElementById('conflictReplacingList').innerHTML =
                `<small><i class="fas fa-lightbulb text-warning"></i> ` +
                `Haz clic en la hamaca ocupada para moverla</small>`;
        }

        panel.style.display = 'block';
    }

    // Hide conflict instruction panel
    function hideConflictInstructions() {
        const panel = document.getElementById('conflictInstructionPanel');
        if (panel) {
            panel.style.display = 'none';
        }
    }

    // Update selection counter for conflict resolution
    function updateConflictSelectionCounter() {
        if (!conflictResolutionContext) return;
        const selectedCount = map.getSelectedFurniture().length;
        const counterEl = document.getElementById('conflictSelectedCount');
        if (counterEl) {
            counterEl.textContent = selectedCount;
        }
        updateSelectionBarForConflict();
    }

    // Listen for reservation highlight events from panel
    document.addEventListener('reservation:highlightFurniture', (e) => {
        const { furnitureIds } = e.detail;
        if (furnitureIds && furnitureIds.length > 0) {
            map.setHighlightedFurniture(furnitureIds);
        }
    });
    document.addEventListener('reservation:clearHighlight', () => {
        map.clearHighlightedFurniture();
    });

    // Listen for request to open existing reservation (from safeguard duplicate check)
    document.addEventListener('reservation:openExisting', async (e) => {
        const { reservationId } = e.detail;
        if (reservationId) {
            openReservationPanel(reservationId, 'view');

            // Also select the reservation's furniture on the map with visual highlight
            try {
                const currentDate = map.getCurrentDate();
                const response = await fetch(`/beach/api/map/reservations/${reservationId}/details?date=${currentDate}`);
                if (response.ok) {
                    const data = await response.json();
                    const furniture = data.reservation?.furniture || [];

                    // Filter furniture for current date
                    const todayFurniture = furniture.filter(f => {
                        if (!f.assignment_date) return true;
                        // Parse date properly (handles both ISO and RFC formats)
                        const dateObj = new Date(f.assignment_date);
                        const assignDate = dateObj.toISOString().split('T')[0];
                        return assignDate === currentDate;
                    });

                    // Select furniture on map and add highlight
                    if (todayFurniture.length > 0) {
                        // Clear any existing highlights first
                        document.querySelectorAll('.existing-reservation-highlight').forEach(el => {
                            el.classList.remove('existing-reservation-highlight');
                        });

                        // Get furniture IDs
                        const furnitureIds = todayFurniture.map(f => f.furniture_id || f.id);

                        // Select furniture on map
                        map.clearSelection();
                        furnitureIds.forEach(id => {
                            map.selectFurniture(id, true);
                        });
                        updateSelectionBar();

                        // Wait for map to re-render, then add highlight class
                        requestAnimationFrame(() => {
                            setTimeout(() => {
                                furnitureIds.forEach(id => {
                                    const furnitureEl = document.querySelector(`g.furniture-item[data-furniture-id="${id}"]`);
                                    if (furnitureEl) {
                                        furnitureEl.classList.add('existing-reservation-highlight');
                                    }
                                });

                                // Remove highlight after 5 seconds
                                setTimeout(() => {
                                    document.querySelectorAll('.existing-reservation-highlight').forEach(el => {
                                        el.classList.remove('existing-reservation-highlight');
                                    });
                                }, 5000);
                            }, 200);
                        });
                    }
                }
            } catch (error) {
                console.error('Error selecting reservation furniture on map:', error);
            }
        }
    });

    // Update selection bar for conflict resolution mode
    function updateSelectionBarForConflict() {
        if (!conflictResolutionContext) return;

        const actionsContainer = document.getElementById('selection-actions');
        if (!actionsContainer) return;

        // Hide the clear button during conflict resolution (it looks like cancel)
        const clearBtn = document.getElementById('btn-clear-selection');
        if (clearBtn) {
            clearBtn.style.display = 'none';
        }

        // Hide the block button during conflict resolution
        const blockBtn = document.getElementById('btn-block-selection');
        if (blockBtn) {
            blockBtn.style.display = 'none';
        }

        // Remove any existing action buttons (reserve, view-reservation, mixed, etc.)
        const existingActionBtns = actionsContainer.querySelectorAll(
            '.btn-reserve, .btn-view-reservation, .btn-mixed, .btn-success, .btn-secondary, .btn-conflict-confirm, .btn-conflict-cancel'
        );
        existingActionBtns.forEach(btn => btn.remove());

        // Capture current selection NOW - prevents race conditions
        const capturedSelection = [...map.getSelectedFurniture()];
        const selectedCount = capturedSelection.length;

        // Create "Cancelar" button (outline style per design system)
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn-conflict-cancel';
        cancelBtn.style.cssText = 'background: transparent; color: #1A3A5C; padding: 10px 16px; border: 2px solid #E8E8E8; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s ease;';
        cancelBtn.innerHTML = '<i class="fas fa-arrow-left"></i> Volver';
        cancelBtn.onmouseenter = () => { cancelBtn.style.borderColor = '#D4AF37'; cancelBtn.style.background = 'rgba(212,175,55,0.1)'; };
        cancelBtn.onmouseleave = () => { cancelBtn.style.borderColor = '#E8E8E8'; cancelBtn.style.background = 'transparent'; };
        cancelBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            exitConflictResolutionMode();
        };

        // Create "Confirmar" button (success style per design system)
        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.className = 'btn-conflict-confirm';

        if (selectedCount !== conflictResolutionContext.requiredCount) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = `<i class="fas fa-check"></i> Confirmar (${selectedCount}/${conflictResolutionContext.requiredCount})`;
            confirmBtn.style.cssText = 'background: #9CA3AF; color: white; padding: 10px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: not-allowed; display: flex; align-items: center; gap: 6px;';
        } else {
            confirmBtn.innerHTML = '<i class="fas fa-check"></i> Confirmar';
            confirmBtn.style.cssText = 'background: linear-gradient(135deg, #4A7C59 0%, #3d6b4a 100%); color: white; padding: 10px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 4px rgba(74,124,89,0.3); transition: all 0.2s ease;';
            confirmBtn.onmouseenter = () => { confirmBtn.style.transform = 'translateY(-1px)'; };
            confirmBtn.onmouseleave = () => { confirmBtn.style.transform = 'translateY(0)'; };
        }

        confirmBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            confirmAlternativeSelection(capturedSelection);
        };

        // Add buttons to container (cancel first, then confirm)
        actionsContainer.appendChild(cancelBtn);
        actionsContainer.appendChild(confirmBtn);
    }

    // Exit conflict resolution mode and return to modal
    function exitConflictResolutionMode() {
        // Clear context
        conflictResolutionContext = null;

        // Restore clear button visibility
        const clearBtn = document.getElementById('btn-clear-selection');
        if (clearBtn) {
            clearBtn.style.display = '';
        }

        // Restore block button visibility
        const blockBtn = document.getElementById('btn-block-selection');
        if (blockBtn) {
            blockBtn.style.display = '';
        }

        // Clear selection
        map.clearSelection();

        // Hide conflict instruction panel
        const instructionPanel = document.getElementById('conflictInstructionPanel');
        if (instructionPanel) {
            instructionPanel.style.display = 'none';
        }

        // Update selection bar to restore normal buttons
        updateSelectionBar();

        // Show the conflict resolution modal again
        document.dispatchEvent(new CustomEvent('conflictResolution:cancelled'));
    }

    // Confirm the alternative furniture selection
    // capturedSelection is passed from updateSelectionBarForConflict to avoid race conditions
    function confirmAlternativeSelection(capturedSelection) {
        if (!conflictResolutionContext) return;

        // Use the captured selection passed from the button click handler
        // This prevents issues where selection might be cleared between click and execution
        const selectedIds = capturedSelection || map.getSelectedFurniture();
        const requiredCount = parseInt(conflictResolutionContext.requiredCount);

        console.log('[Map] Confirming selection:', {
            selectedIds: selectedIds,
            count: selectedIds ? selectedIds.length : 'null',
            required: requiredCount,
            capturedFromButton: !!capturedSelection
        });

        // Validate exact count match
        if (selectedIds.length != requiredCount) {
            if (window.PuroBeach && window.PuroBeach.showToast) {
                window.PuroBeach.showToast(
                    `Debes seleccionar exactamente ${requiredCount} hamaca(s)`,
                    'warning'
                );
            }
            return;
        }

        // Dispatch event to notify the conflict modal
        // The modal will show again after this
        // Capture date BEFORE clearing context (setTimeout runs after context is nulled)
        const capturedDate = conflictResolutionContext.date;
        console.log('[Map] Dispatching alternativeSelected event:', capturedDate, selectedIds);

        // Small delay to ensure UI updates have processed
        setTimeout(() => {
            document.dispatchEvent(new CustomEvent('conflictResolution:alternativeSelected', {
                detail: {
                    date: capturedDate,
                    furnitureIds: selectedIds
                }
            }));
        }, 50);

        // Clear map state but keep context for potential further edits
        clearConflictHighlights();
        hideConflictInstructions();
        map.clearSelection();

        // Clear context - the modal now manages the flow
        conflictResolutionContext = null;

        // Restore clear button visibility
        const clearBtn = document.getElementById('btn-clear-selection');
        if (clearBtn) {
            clearBtn.style.display = '';
        }

        // Restore block button visibility
        const blockBtn = document.getElementById('btn-block-selection');
        if (blockBtn) {
            blockBtn.style.display = '';
        }

        updateSelectionBar();

        // Brief toast - the modal will show immediately after
        if (window.PuroBeach && window.PuroBeach.showToast) {
            window.PuroBeach.showToast('Alternativa guardada', 'success');
        }
    }

    // ==========================================================================
    // QUICK SWAP - Move blocking reservations to free up furniture
    // ==========================================================================
    let quickSwapContext = null;

    const quickSwapModal = document.getElementById('quickSwapModal');
    const quickSwapCancelBtn = document.getElementById('quickSwapCancelBtn');
    const quickSwapStartBtn = document.getElementById('quickSwapStartBtn');
    const quickSwapBackdrop = quickSwapModal.querySelector('.quick-swap-backdrop');

    // Show quick swap modal when clicking on a conflicting furniture
    function showQuickSwapModal(furnitureId, reservationId, customerName, furnitureLabel) {
        quickSwapContext = {
            fromFurnitureId: furnitureId,
            reservationId: reservationId,
            customerName: customerName,
            furnitureLabel: furnitureLabel,
            date: conflictResolutionContext ? conflictResolutionContext.date : map.getCurrentDate()
        };

        document.getElementById('quickSwapCustomerName').textContent = customerName || 'Cliente';
        document.getElementById('quickSwapFurnitureLabel').textContent = furnitureLabel || `#${furnitureId}`;
        document.getElementById('quickSwapSelectPrompt').style.display = 'none';

        quickSwapModal.style.display = 'flex';
        quickSwapModal.classList.remove('selecting-destination');
    }

    function hideQuickSwapModal() {
        quickSwapModal.style.display = 'none';
        quickSwapModal.classList.remove('selecting-destination');
        clearSwapSourceHighlight();
        quickSwapContext = null;
    }

    function enterSwapDestinationMode() {
        // Hide the modal - we'll use the instruction panel instead
        quickSwapModal.style.display = 'none';
        quickSwapModal.classList.add('selecting-destination');

        // Highlight the source furniture
        const sourceEl = document.querySelector(
            `.furniture-item[data-furniture-id="${quickSwapContext.fromFurnitureId}"]`
        );
        if (sourceEl) {
            sourceEl.classList.add('swap-source');
        }

        // Update the conflict instruction panel to show swap mode
        const instrPanel = document.getElementById('conflictInstructionPanel');
        if (instrPanel) {
            document.getElementById('conflictInstructionText').innerHTML =
                `<i class="fas fa-exchange-alt text-warning"></i> Moviendo <strong>${quickSwapContext.furnitureLabel}</strong><br>` +
                `Selecciona la hamaca de destino`;
            document.getElementById('conflictReplacingList').innerHTML =
                `<small><button type="button" class="btn btn-sm btn-outline-secondary" id="cancelSwapBtn">` +
                `<i class="fas fa-times"></i> Cancelar</button></small>`;

            // Bind cancel button
            document.getElementById('cancelSwapBtn').addEventListener('click', () => {
                hideQuickSwapModal();
                // Restore original instruction
                if (conflictResolutionContext) {
                    showConflictInstructions(
                        conflictResolutionContext.conflicts,
                        conflictResolutionContext.requiredCount,
                        conflictResolutionContext.conflictingLabels
                    );
                }
            });

            instrPanel.style.display = 'block';
        }
    }

    function clearSwapSourceHighlight() {
        document.querySelectorAll('.furniture-item.swap-source').forEach(el => {
            el.classList.remove('swap-source');
        });
    }

    // Perform the quick swap via API
    async function performQuickSwap(toFurnitureId) {
        if (!quickSwapContext) return;

        try {
            const response = await fetch('/beach/api/map/move-reservation-furniture', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
                },
                body: JSON.stringify({
                    reservation_id: quickSwapContext.reservationId,
                    date: quickSwapContext.date,
                    from_furniture_id: quickSwapContext.fromFurnitureId,
                    to_furniture_id: toFurnitureId
                })
            });

            const result = await response.json();

            if (result.success) {
                if (window.PuroBeach && window.PuroBeach.showToast) {
                    window.PuroBeach.showToast(result.message || 'Reserva movida exitosamente', 'success');
                }

                // Refresh the map to show updated availability
                await map.refreshAvailability();

                // The conflicting furniture is now free
                if (conflictResolutionContext) {
                    // Remove the moved furniture from conflicts list
                    conflictResolutionContext.conflicts = conflictResolutionContext.conflicts.filter(
                        c => c.furniture_id !== quickSwapContext.fromFurnitureId
                    );

                    // Update conflicting labels
                    conflictResolutionContext.conflictingLabels =
                        conflictResolutionContext.conflicts.map(c => c.furniture_number).join(', ');

                    // Update highlights
                    clearConflictHighlights();
                    if (conflictResolutionContext.conflicts.length > 0) {
                        highlightConflictingFurniture(conflictResolutionContext.conflicts);
                    }

                    // Restore the instruction panel with updated info
                    showConflictInstructions(
                        conflictResolutionContext.conflicts,
                        conflictResolutionContext.requiredCount,
                        conflictResolutionContext.conflictingLabels
                    );

                    // If no more conflicts, notify user they can now select
                    if (conflictResolutionContext.conflicts.length === 0) {
                        document.getElementById('conflictInstructionText').innerHTML =
                            `<i class="fas fa-check-circle text-success"></i> Conflicto resuelto<br>` +
                            `Selecciona ${conflictResolutionContext.requiredCount} hamaca(s)`;
                    }
                }

                hideQuickSwapModal();
            } else {
                if (window.PuroBeach && window.PuroBeach.showToast) {
                    window.PuroBeach.showToast(result.error || 'Error al mover la reserva', 'error');
                }
            }
        } catch (error) {
            console.error('Quick swap error:', error);
            if (window.PuroBeach && window.PuroBeach.showToast) {
                window.PuroBeach.showToast('Error de conexión', 'error');
            }
        }
    }

    // Bind quick swap modal events
    quickSwapCancelBtn.addEventListener('click', hideQuickSwapModal);
    quickSwapBackdrop.addEventListener('click', hideQuickSwapModal);
    quickSwapStartBtn.addEventListener('click', enterSwapDestinationMode);

    // ==========================================================================
    // TOUCH HANDLER FOR RESERVATION DETAILS
    // ==========================================================================
    const mapContainer = document.getElementById('map-container');

    // Initialize touch handler for long-press detection
    const touchHandler = new TouchHandler(mapContainer, {
        longPressDelay: 500,
        vibrate: true
    });

    touchHandler.onLongPress(async (event) => {
        const { furnitureId, clientX, clientY, target } = event;

        // Check if furniture is occupied
        const data = map.getData();
        const availability = data.availability[furnitureId];

        // Handle move mode - long-press releases ALL furniture from reservation
        if (moveMode.isActive()) {
            if (availability && !availability.available && availability.reservation_id) {
                // Add visual feedback during long-press
                if (target) {
                    target.classList.add('long-press-active');
                    setTimeout(() => target.classList.remove('long-press-active'), 500);
                }

                // Get ALL furniture for this reservation
                const allFurnitureForReservation = Object.entries(data.availability)
                    .filter(([id, av]) => av.reservation_id === availability.reservation_id)
                    .map(([id, av]) => {
                        const furnitureItem = data.furniture.find(f => f.id === parseInt(id));
                        return {
                            furniture_id: parseInt(id),
                            number: furnitureItem?.number || av.furniture_number,
                            capacity: furnitureItem?.capacity || 1
                        };
                    });

                // Release ALL furniture for this reservation
                const furnitureIds = allFurnitureForReservation.map(f => f.furniture_id);
                const result = await moveMode.unassignFurniture(
                    availability.reservation_id,
                    furnitureIds,
                    false,
                    allFurnitureForReservation
                );

                if (result.success) {
                    map.refreshAvailability();
                    if (window.PuroBeach && window.PuroBeach.showToast) {
                        window.PuroBeach.showToast(`${furnitureIds.length} mueble(s) liberado(s)`, 'success');
                    }
                }
            }
            return; // Exit early - don't open panel in move mode
        }

        // Outside move mode: Show context menu (Block/Unblock/Temporary)
        // Get furniture item from map data (reuse 'data' from above)
        const furnitureItem = data.furniture?.find(f => f.id === furnitureId);

        if (furnitureItem) {
            // Create a synthetic event with the touch coordinates for positioning
            const syntheticEvent = {
                preventDefault: () => {},
                stopPropagation: () => {},
                clientX: clientX,
                clientY: clientY
            };

            // Use BeachMap's context menu (Block/Unblock/Delete Temporary)
            map.handleFurnitureContextMenu(syntheticEvent, furnitureItem);
        }
    });

    // ==========================================================================
    // DATE NAVIGATION
    // ==========================================================================
    const dateDisplay = document.getElementById('date-display');
    const datePicker = document.getElementById('date-picker');
    const btnPrevDay = document.getElementById('btn-prev-day');
    const btnNextDay = document.getElementById('btn-next-day');

    // Format date for display (compact for mobile)
    function formatDateCompact(dateStr) {
        const date = new Date(dateStr + 'T12:00:00');
        const day = date.getDate();
        const month = date.toLocaleDateString('es-ES', { month: 'short' });
        return `${day} ${month.charAt(0).toUpperCase() + month.slice(1)}`;
    }

    map.on('onDateChange', function (dateStr) {
        // Update UI elements
        dateDisplay.textContent = formatDateCompact(dateStr);
        datePicker.value = dateStr;
        updateStats(currentZoneId);
        populateZoneSelector();
        // Update waitlist badge
        updateWaitlistBadge();
        // Update move mode date if active - refresh pool for new date
        if (moveMode.isActive()) {
            moveMode.setDate(dateStr);
        }
        // Note: Global unassigned badge is NOT refreshed on date change
        // It only refreshes on page load and after assignments
    });

    btnPrevDay.addEventListener('click', async () => {
        btnPrevDay.disabled = true;
        await map.goToPreviousDay();
        btnPrevDay.disabled = false;
    });

    btnNextDay.addEventListener('click', async () => {
        btnNextDay.disabled = true;
        await map.goToNextDay();
        btnNextDay.disabled = false;
    });

    // Click on date to open picker
    dateDisplay.addEventListener('click', () => {
        datePicker.classList.toggle('show');
        if (datePicker.classList.contains('show')) {
            datePicker.focus();
            datePicker.showPicker && datePicker.showPicker();
        }
    });

    datePicker.addEventListener('change', async (e) => {
        await map.goToDate(e.target.value);
        datePicker.classList.remove('show');
    });

    datePicker.addEventListener('blur', () => {
        setTimeout(() => datePicker.classList.remove('show'), 200);
    });

    // Swipe date navigation on mobile
    let touchStartX = 0;
    dateDisplay.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
    }, { passive: true });

    dateDisplay.addEventListener('touchend', (e) => {
        const diff = e.changedTouches[0].clientX - touchStartX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) map.goToPreviousDay();
            else map.goToNextDay();
        }
    }, { passive: true });

    // Set initial date
    datePicker.value = map.getCurrentDate();
    setTimeout(() => {
        dateDisplay.textContent = formatDateCompact(map.getCurrentDate());
        updateStats();
        populateZoneSelector();
    }, 500);

    // ==========================================================================
    // ZONE SELECTOR
    // ==========================================================================
    const zoneSelect = document.getElementById('zone-select');
    let currentZoneId = null;

    function populateZoneSelector() {
        const data = map.getData();
        if (!data || !data.zones || data.zones.length === 0) return;

        const currentValue = zoneSelect.value;
        zoneSelect.innerHTML = '';

        data.zones.forEach(zone => {
            const option = document.createElement('option');
            option.value = zone.id;
            option.textContent = zone.name;
            zoneSelect.appendChild(option);
        });

        if (currentValue && data.zones.some(z => z.id == currentValue)) {
            zoneSelect.value = currentValue;
        } else {
            zoneSelect.value = data.zones[0].id;
        }

        currentZoneId = parseInt(zoneSelect.value);
        applyZoneView(currentZoneId);
    }

    zoneSelect.addEventListener('change', () => {
        currentZoneId = parseInt(zoneSelect.value);
        applyZoneView(currentZoneId);
    });

    function applyZoneView(zoneId) {
        const data = map.getData();
        if (!data) return;

        // Show only furniture in selected zone
        document.querySelectorAll('.furniture-item').forEach(item => {
            const furnitureId = parseInt(item.dataset.furnitureId);
            const furniture = data.furniture?.find(f => f.id === furnitureId);
            if (!furniture) return;
            item.style.display = furniture.zone_id === zoneId ? '' : 'none';
        });

        // Show only decorative items in selected zone
        document.querySelectorAll('.decorative-item').forEach(item => {
            const furnitureId = parseInt(item.dataset.furnitureId);
            const furniture = data.furniture?.find(f => f.id === furnitureId);
            if (!furniture) return;
            item.style.display = furniture.zone_id === zoneId ? '' : 'none';
        });

        updateStats(zoneId);
        adjustViewBoxForZone(zoneId);
    }

    function adjustViewBoxForZone(zoneId) {
        const data = map.getData();
        if (!data) return;

        const svg = document.getElementById('beach-map');
        if (!svg) return;

        // Get zone's canvas dimensions (more accurate than map_dimensions)
        const zone = data.zones?.find(z => z.id === zoneId);
        const canvasWidth = zone?.canvas_width || data.map_dimensions?.width || 1200;
        const canvasHeight = zone?.canvas_height || data.map_dimensions?.height || 800;

        // Use the zone's full canvas dimensions (matches map editor)
        svg.setAttribute('viewBox', `0 0 ${canvasWidth} ${canvasHeight}`);
    }

    // ==========================================================================
    // STATS
    // ==========================================================================
    function updateStats(zoneId = null) {
        const data = map.getData();
        if (!data || !data.furniture) return;

        // Filter out decorative items
        let furniture = data.furniture.filter(f => {
            const typeConfig = data.furniture_types[f.furniture_type] || {};
            return typeConfig.is_decorative !== 1;
        });

        if (zoneId !== null) {
            furniture = furniture.filter(f => f.zone_id === zoneId);
        }

        const total = furniture.length;
        let available = 0;
        let occupied = 0;

        furniture.forEach(f => {
            const avail = data.availability[f.id];
            if (!avail || avail.available) {
                available++;
            } else {
                occupied++;
            }
        });

        const rate = total > 0 ? Math.round((occupied / total) * 100) : 0;

        document.getElementById('stat-total').textContent = total;
        document.getElementById('stat-available').textContent = available;
        document.getElementById('stat-occupied').textContent = occupied;
        document.getElementById('stat-rate').textContent = `${rate}%`;
    }

    // ==========================================================================
    // CANVAS INFO BAR
    // ==========================================================================
    const canvasDimensions = document.getElementById('canvas-dimensions');
    const cursorPos = document.getElementById('cursor-pos');
    const furnitureCount = document.getElementById('furniture-count');
    const zoomLevel = document.getElementById('zoom-level');

    function updateCanvasInfo() {
        const data = map.getData();
        if (!data) return;

        // Get zone's canvas dimensions
        const zone = data.zones?.find(z => z.id === currentZoneId);
        const width = zone?.canvas_width || data.map_dimensions?.width || 1200;
        const height = zone?.canvas_height || data.map_dimensions?.height || 800;

        canvasDimensions.textContent = `${width} x ${height}`;

        // Count visible furniture (in current zone, non-decorative)
        const visibleCount = data.furniture?.filter(f => {
            if (f.zone_id !== currentZoneId) return false;
            const typeConfig = data.furniture_types[f.furniture_type] || {};
            return typeConfig.is_decorative !== 1;
        }).length || 0;

        furnitureCount.textContent = visibleCount;

        // Update zoom level
        updateZoomDisplay();
    }

    function updateZoomDisplay() {
        const zoom = map.getZoom ? map.getZoom() : 1;
        zoomLevel.textContent = `${Math.round(zoom * 100)}%`;
    }

    // Track cursor position over canvas
    const mapCanvas = document.querySelector('.map-canvas');
    mapCanvas?.addEventListener('mousemove', (e) => {
        const svg = document.getElementById('beach-map');
        if (!svg) return;

        const rect = svg.getBoundingClientRect();
        const viewBox = svg.getAttribute('viewBox')?.split(' ').map(Number) || [0, 0, 1200, 800];

        // Convert screen coords to SVG coords
        const scaleX = viewBox[2] / rect.width;
        const scaleY = viewBox[3] / rect.height;

        const x = Math.round((e.clientX - rect.left) * scaleX);
        const y = Math.round((e.clientY - rect.top) * scaleY);

        cursorPos.textContent = `${x}, ${y}`;
    });

    mapCanvas?.addEventListener('mouseleave', () => {
        cursorPos.textContent = '-';
    });

    // Update info after render
    map.on('onRender', () => {
        updateCanvasInfo();
    });

    // ==========================================================================
    // ZOOM CONTROLS
    // ==========================================================================
    document.getElementById('btn-zoom-in').addEventListener('click', () => { map.zoomIn(); updateZoomDisplay(); });
    document.getElementById('btn-zoom-out').addEventListener('click', () => { map.zoomOut(); updateZoomDisplay(); });

    // Info bar zoom controls
    document.getElementById('btn-zoom-in-bar')?.addEventListener('click', () => { map.zoomIn(); updateZoomDisplay(); });
    document.getElementById('btn-zoom-out-bar')?.addEventListener('click', () => { map.zoomOut(); updateZoomDisplay(); });
    document.getElementById('btn-zoom-reset')?.addEventListener('click', () => { resetToSavedView(); });
    document.getElementById('btn-save-view')?.addEventListener('click', () => { saveCurrentView(); });

    // ==========================================================================
    // SAVE/RESTORE VIEW
    // ==========================================================================
    const VIEW_STORAGE_KEY = 'beachMap_savedView';
    let savedView = null;

    // Load saved view on init
    function loadSavedView() {
        try {
            const saved = localStorage.getItem(VIEW_STORAGE_KEY);
            if (saved) {
                savedView = JSON.parse(saved);
            }
        } catch (e) {
            console.warn('Could not load saved view:', e);
        }
    }

    // Save current view (zoom + scroll position)
    function saveCurrentView() {
        const view = {
            zoom: map.getZoom ? map.getZoom() : 1,
            scrollLeft: mapWrapper.scrollLeft,
            scrollTop: mapWrapper.scrollTop,
            zoneId: currentZoneId
        };

        savedView = view;

        try {
            localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify(view));
            // Visual feedback
            const btn = document.getElementById('btn-save-view');
            btn.innerHTML = '<i class="fas fa-check"></i>';
            btn.style.color = 'var(--color-success)';
            setTimeout(() => {
                btn.innerHTML = '<i class="fas fa-save"></i>';
                btn.style.color = '';
            }, 1500);
        } catch (e) {
            console.warn('Could not save view:', e);
        }
    }

    // Reset to saved view or default
    function resetToSavedView() {
        if (savedView) {
            // Restore zoom
            map.setZoom(savedView.zoom || 1);
            updateZoomDisplay();

            // Restore scroll position after a short delay (for zoom to apply)
            setTimeout(() => {
                mapWrapper.scrollLeft = savedView.scrollLeft || 0;
                mapWrapper.scrollTop = savedView.scrollTop || 0;
            }, 50);

            // Restore zone if different
            if (savedView.zoneId && savedView.zoneId !== currentZoneId) {
                zoneSelect.value = savedView.zoneId;
                currentZoneId = savedView.zoneId;
                applyZoneView(currentZoneId);
            }
        } else {
            // Default: zoom 100%, scroll to origin
            map.setZoom(1);
            updateZoomDisplay();
            mapWrapper.scrollLeft = 0;
            mapWrapper.scrollTop = 0;
        }
    }

    // Load saved view on page load
    loadSavedView();

    // ==========================================================================
    // MAP EDITOR STYLE NAVIGATION (Ctrl+Wheel Zoom, Space+Drag Pan)
    // ==========================================================================
    const mapWrapper = document.querySelector('.map-canvas-wrapper');
    let spaceDown = false;
    let isPanning = false;
    let panStart = { x: 0, y: 0 };
    let scrollStart = { x: 0, y: 0 };

    // Shift+Wheel Zoom (zoom to mouse position)
    // Using Shift instead of Ctrl to avoid conflict with browser zoom
    document.addEventListener('wheel', (e) => {
        // Only handle if Shift is pressed and mouse is over the map
        if (!e.shiftKey) return;

        // Check if event is within map wrapper
        if (!mapWrapper.contains(e.target)) return;

        // Prevent default scroll behavior
        e.preventDefault();
        e.stopPropagation();

        const svg = document.getElementById('beach-map');
        if (!svg) return;

        // Get current zoom
        const currentZoom = map.getZoom ? map.getZoom() : 1;

        // Use percentage-based zoom for smoother experience at all zoom levels
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;  // 10% change
        const minZoom = 0.1;
        const maxZoom = 3;
        const newZoom = Math.max(minZoom, Math.min(currentZoom * zoomFactor, maxZoom));

        // Skip if zoom didn't change (hit min/max)
        if (Math.abs(newZoom - currentZoom) < 0.001) return;

        // Get wrapper dimensions
        const wrapperRect = mapWrapper.getBoundingClientRect();
        const wrapperWidth = mapWrapper.clientWidth;
        const wrapperHeight = mapWrapper.clientHeight;

        // Get SVG rect
        const svgRect = svg.getBoundingClientRect();

        // Mouse position relative to wrapper viewport
        const mouseXInWrapper = e.clientX - wrapperRect.left;
        const mouseYInWrapper = e.clientY - wrapperRect.top;

        // Calculate mouse position relative to SVG (clamp to SVG bounds)
        const mouseXInSvg = Math.max(0, Math.min(e.clientX - svgRect.left, svgRect.width));
        const mouseYInSvg = Math.max(0, Math.min(e.clientY - svgRect.top, svgRect.height));

        // Convert to canvas coordinates (the actual viewBox coordinates)
        const canvasX = mouseXInSvg / currentZoom;
        const canvasY = mouseYInSvg / currentZoom;

        // Get current SVG dimensions
        const currentSvgWidth = svgRect.width;
        const currentSvgHeight = svgRect.height;

        // Calculate new SVG dimensions after zoom
        const zoomRatio = newZoom / currentZoom;
        const newSvgWidth = currentSvgWidth * zoomRatio;
        const newSvgHeight = currentSvgHeight * zoomRatio;

        // Calculate centering offset after zoom
        const padding = 10;
        const availableWidth = wrapperWidth - padding * 2;
        const availableHeight = wrapperHeight - padding * 2;
        const newCenterOffsetX = Math.max(0, (availableWidth - newSvgWidth) / 2);
        const newCenterOffsetY = Math.max(0, (availableHeight - newSvgHeight) / 2);

        // Apply zoom
        map.setZoom(newZoom);
        updateZoomDisplay();

        // Calculate new scroll position
        requestAnimationFrame(() => {
            // The canvas point position in the new SVG
            const newPointXInSvg = canvasX * newZoom;
            const newPointYInSvg = canvasY * newZoom;

            // Target scroll: position the point under the mouse
            const targetScrollX = padding + newCenterOffsetX + newPointXInSvg - mouseXInWrapper;
            const targetScrollY = padding + newCenterOffsetY + newPointYInSvg - mouseYInWrapper;

            mapWrapper.scrollLeft = Math.max(0, targetScrollX);
            mapWrapper.scrollTop = Math.max(0, targetScrollY);
        });
    }, { passive: false, capture: true });

    // Track space key for pan mode
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !spaceDown && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            spaceDown = true;
            mapWrapper.style.cursor = 'grab';
        }
    });

    document.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            spaceDown = false;
            if (!isPanning) {
                mapWrapper.style.cursor = '';
            }
        }
    });

    // Space+Drag or Middle Mouse Button Pan
    mapWrapper.addEventListener('mousedown', (e) => {
        // Middle mouse button (1) or space + left click (0)
        if (e.button === 1 || (e.button === 0 && spaceDown)) {
            e.preventDefault();
            isPanning = true;
            panStart = { x: e.clientX, y: e.clientY };
            scrollStart = { x: mapWrapper.scrollLeft, y: mapWrapper.scrollTop };
            mapWrapper.style.cursor = 'grabbing';
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        const dx = e.clientX - panStart.x;
        const dy = e.clientY - panStart.y;
        mapWrapper.scrollLeft = scrollStart.x - dx;
        mapWrapper.scrollTop = scrollStart.y - dy;
    });

    document.addEventListener('mouseup', (e) => {
        if (isPanning) {
            isPanning = false;
            mapWrapper.style.cursor = spaceDown ? 'grab' : '';
        }
    });

    // Prevent default middle click behavior
    mapWrapper.addEventListener('auxclick', (e) => {
        if (e.button === 1) e.preventDefault();
    });

    // ==========================================================================
    // KEYBOARD SHORTCUTS (Map Editor Style)
    // ==========================================================================
    document.addEventListener('keydown', (e) => {
        const isInputFocused = document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA';
        const hasSelection = map.getSelectedFurniture && map.getSelectedFurniture().length > 0;

        switch (e.key) {
            case 'Escape':
                // Close new reservation panel if open
                if (newReservationPanel.isOpen()) {
                    newReservationPanel.close();
                } else {
                    // Deselect all
                    map.clearSelection();
                    updateSelectionBar();
                }
                break;

            case 'a':
            case 'A':
                // Ctrl+A: Select all visible furniture
                if ((e.ctrlKey || e.metaKey) && !isInputFocused) {
                    e.preventDefault();
                    selectAllVisibleFurniture();
                }
                break;

            case '+':
            case '=':
                // Ctrl++: Zoom in
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    map.zoomIn();
                    updateZoomDisplay();
                }
                break;

            case '-':
                // Ctrl+-: Zoom out
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    map.zoomOut();
                    updateZoomDisplay();
                }
                break;

            case '0':
                // Ctrl+0: Reset to saved view
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    resetToSavedView();
                }
                break;

            case 'ArrowLeft':
                // Navigate to previous day
                if (!isInputFocused && !hasSelection) {
                    e.preventDefault();
                    map.goToPreviousDay();
                }
                break;

            case 'ArrowRight':
                // Navigate to next day
                if (!isInputFocused && !hasSelection) {
                    e.preventDefault();
                    map.goToNextDay();
                }
                break;

            case 'r':
            case 'R':
                // R: Refresh
                if (!e.ctrlKey && !e.metaKey && !isInputFocused) {
                    e.preventDefault();
                    btnRefresh.click();
                }
                break;

            case 's':
            case 'S':
                // Ctrl+S: Save view
                if ((e.ctrlKey || e.metaKey) && !isInputFocused) {
                    e.preventDefault();
                    saveCurrentView();
                }
                break;
        }
    });

    // Select all visible furniture in current zone
    function selectAllVisibleFurniture() {
        const data = map.getData();
        if (!data || !data.furniture) return;

        // Get visible furniture (in current zone, not decorative)
        const visibleFurniture = data.furniture.filter(f => {
            if (f.zone_id !== currentZoneId) return false;
            const typeConfig = data.furniture_types[f.furniture_type] || {};
            return typeConfig.is_decorative !== 1;
        });

        visibleFurniture.forEach(f => {
            map.selectFurniture(f.id, true); // true = add to selection
        });

        updateSelectionBar();
    }

    // ==========================================================================
    // REFRESH
    // ==========================================================================
    const btnRefresh = document.getElementById('btn-refresh');
    btnRefresh.addEventListener('click', async () => {
        btnRefresh.querySelector('i').classList.add('fa-spin');
        await map.refreshAvailability();
        updateStats(currentZoneId);
        setTimeout(() => btnRefresh.querySelector('i').classList.remove('fa-spin'), 500);
    });

    map.startAutoRefresh(30000);

    // ==========================================================================
    // PINCH ZOOM FOR TOUCH DEVICES
    // ==========================================================================
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        const pinchZoom = new PinchZoomHandler(
            document.querySelector('.map-canvas-wrapper'),
            {
                minZoom: 0.1,
                maxZoom: 3,
                getZoom: () => map.getZoom(),
                setZoom: (z) => { map.setZoom(z); updateZoomDisplay(); },
                getMapWrapper: () => document.querySelector('.map-canvas-wrapper'),
                getSvg: () => document.getElementById('beach-map')
            }
        );
    }

    // ==========================================================================
    // SELECTION & BOTTOM ACTION BAR
    // ==========================================================================
    const selectionBar = document.getElementById('selection-bar');
    const selectedBadges = document.getElementById('selected-badges');
    const totalCapacity = document.getElementById('total-capacity');

    function updateSelectionBar() {
        const selected = map.getSelectedFurnitureData();

        if (selected.length === 0) {
            selectionBar.classList.remove('show');
            return;
        }

        selectionBar.classList.add('show');

        // Check availability status of selected furniture
        const data = map.getData();
        const availability = data.availability || {};

        let occupiedFurniture = [];
        let availableFurniture = [];
        let reservationIds = new Set();

        selected.forEach(f => {
            const avail = availability[f.id];
            if (avail && !avail.available) {
                occupiedFurniture.push({ ...f, reservation_id: avail.reservation_id });
                if (avail.reservation_id) {
                    reservationIds.add(avail.reservation_id);
                }
            } else {
                availableFurniture.push(f);
            }
        });

        // Build chips with visual indicator for occupied
        selectedBadges.innerHTML = selected.map(f => {
            const avail = availability[f.id];
            const isOccupied = avail && !avail.available;
            const chipStyle = isOccupied ?
                'background: rgba(220, 53, 69, 0.15); border-color: #dc3545;' : '';

            return `
            <span class="selection-chip" data-id="${f.id}" style="${chipStyle}">
                ${f.number}
                ${isOccupied ? '<i class="fas fa-user" style="font-size: 8px; margin-left: 2px; opacity: 0.7;"></i>' : ''}
                <span class="remove-chip" data-id="${f.id}"><i class="fas fa-times"></i></span>
            </span>
        `;
        }).join('');

        // Add remove handlers
        selectedBadges.querySelectorAll('.remove-chip').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                map.deselectFurniture(id);
                updateSelectionBar();
            });
        });

        // Calculate total capacity
        const capacity = selected.reduce((sum, f) => sum + (f.capacity || 2), 0);
        totalCapacity.textContent = capacity;

        // Update action button based on selection type
        updateSelectionActions(availableFurniture, occupiedFurniture, reservationIds);

        // If in conflict resolution mode, override the button
        if (conflictResolutionContext) {
            updateSelectionBarForConflict();
        }
    }

    function updateSelectionActions(availableFurniture, occupiedFurniture, reservationIds) {
        const actionsContainer = document.getElementById('selection-actions');
        const clearBtn = document.getElementById('btn-clear-selection');

        // Determine the action type
        const allAvailable = occupiedFurniture.length === 0;
        const allOccupied = availableFurniture.length === 0;
        const singleReservation = reservationIds.size === 1;

        // Clear existing action button (keep clear button)
        // Include btn-success and btn-secondary which are set by updateSelectionBarForConflict
        const existingActionBtn = actionsContainer.querySelector('.btn-reserve, .btn-view-reservation, .btn-mixed, .btn-success, .btn-secondary');
        if (existingActionBtn) {
            existingActionBtn.remove();
        }

        let actionBtn;

        if (allAvailable) {
            // All available - show "Reservar" button
            actionBtn = document.createElement('button');
            actionBtn.type = 'button';
            actionBtn.className = 'btn-reserve';
            actionBtn.id = 'btn-new-reservation';
            actionBtn.innerHTML = '<i class="fas fa-calendar-plus"></i> <span>Reservar</span>';
            actionBtn.addEventListener('click', openNewReservationPanel);

        } else if (allOccupied && singleReservation) {
            // All from same reservation - show "Ver Reserva" button
            const reservationId = Array.from(reservationIds)[0];
            actionBtn = document.createElement('button');
            actionBtn.type = 'button';
            actionBtn.className = 'btn-view-reservation';
            actionBtn.style.cssText = 'background: linear-gradient(135deg, #1A3A5C 0%, #2d5a87 100%); color: white; padding: 10px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px;';
            actionBtn.innerHTML = '<i class="fas fa-eye"></i> <span>Ver Reserva</span>';
            actionBtn.addEventListener('click', () => {
                openReservationPanel(reservationId, 'view');
            });

        } else if (allOccupied) {
            // Multiple reservations selected
            actionBtn = document.createElement('button');
            actionBtn.type = 'button';
            actionBtn.className = 'btn-view-reservation';
            actionBtn.style.cssText = 'background: #6c757d; color: white; padding: 10px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px;';
            actionBtn.innerHTML = `<i class="fas fa-layer-group"></i> <span>${reservationIds.size} Reservas</span>`;
            actionBtn.addEventListener('click', () => {
                alert(`Hay ${reservationIds.size} reservas diferentes seleccionadas. Seleccione mobiliario de una sola reserva para ver detalles.`);
            });

        } else {
            // Mixed selection (some available, some occupied)
            actionBtn = document.createElement('button');
            actionBtn.type = 'button';
            actionBtn.className = 'btn-mixed';
            actionBtn.style.cssText = 'background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%); color: white; padding: 10px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px;';
            actionBtn.innerHTML = `<i class="fas fa-calendar-plus"></i> <span>Reservar ${availableFurniture.length}</span>`;
            actionBtn.title = `Reservar solo los ${availableFurniture.length} mobiliarios disponibles`;
            actionBtn.addEventListener('click', () => {
                // Deselect occupied furniture and open reservation sheet
                occupiedFurniture.forEach(f => map.deselectFurniture(f.id));
                updateSelectionBar();
                openNewReservationPanel();
            });
        }

        actionsContainer.appendChild(actionBtn);
    }

    // Override map selection callback - handle occupied furniture clicks
    map.on('onFurnitureClick', async (item, selectedFurniture) => {
        try {
            const data = map.getData();
            const availability = data.availability[item.id];

            // Handle move mode - furniture reassignment
            if (moveMode.isActive()) {
                map.deselectFurniture(item.id); // Don't select during move mode

                const selectedRes = moveMode.getSelectedReservation();

                if (availability && !availability.available && availability.reservation_id) {
                    // Get ALL furniture for this reservation before unassigning
                    // This is needed for proper totalNeeded calculation in move mode pool
                    const allFurnitureForReservation = Object.entries(data.availability)
                        .filter(([id, av]) => av.reservation_id === availability.reservation_id)
                        .map(([id, av]) => {
                            const furnitureItem = data.furniture.find(f => f.id === parseInt(id));
                            return {
                                furniture_id: parseInt(id),
                                number: furnitureItem?.number || av.furniture_number,
                                capacity: furnitureItem?.capacity || 1  // Include capacity for proper counting
                            };
                        });

                    // Occupied furniture - unassign from its reservation
                    // Ctrl+click releases ALL furniture, normal click releases just one
                    const furnitureToUnassign = event?.ctrlKey
                        ? allFurnitureForReservation.map(f => f.furniture_id)
                        : [item.id];

                    const result = await moveMode.unassignFurniture(
                        availability.reservation_id,
                        furnitureToUnassign,
                        false,
                        allFurnitureForReservation  // Pass all furniture for correct totalNeeded
                    );
                    if (result.success) {
                        map.refreshAvailability();
                    }
                } else if (selectedRes && availability?.available) {
                    // Available furniture with reservation selected - assign
                    const result = await moveMode.assignFurniture(
                        selectedRes.reservation_id,
                        [item.id]
                    );
                    if (result.success) {
                        map.refreshAvailability();
                    }
                } else if (!selectedRes) {
                    // No reservation selected
                    if (window.PuroBeach && window.PuroBeach.showToast) {
                        window.PuroBeach.showToast('Selecciona una reserva del panel primero', 'info');
                    }
                }
                return;
            }

            // Handle quick swap destination selection
            if (quickSwapContext && quickSwapModal.classList.contains('selecting-destination')) {
                map.deselectFurniture(item.id); // Don't select during swap

                if (availability && availability.available) {
                    // Available furniture - perform the swap
                    performQuickSwap(item.id);
                } else {
                    // Can't swap to occupied furniture
                    if (window.PuroBeach && window.PuroBeach.showToast) {
                        window.PuroBeach.showToast('Selecciona una hamaca disponible', 'warning');
                    }
                }
                return;
            }

            // Handle conflict resolution mode - show quick swap for occupied furniture
            if (conflictResolutionContext && availability && !availability.available) {
                map.deselectFurniture(item.id); // Don't select occupied furniture

                // Check if this is one of the conflicting furniture items
                const isConflicting = conflictResolutionContext.conflicts.some(
                    c => c.furniture_id === item.id
                );

                if (isConflicting) {
                    // Get conflict details for quick swap
                    const conflict = conflictResolutionContext.conflicts.find(
                        c => c.furniture_id === item.id
                    );
                    const furnitureData = data.furniture.find(f => f.id === item.id);

                    showQuickSwapModal(
                        item.id,
                        availability.reservation_id,
                        conflict.customer_name || availability.customer_name,
                        furnitureData?.number || conflict.furniture_number
                    );
                } else {
                    // Occupied but not conflicting - just show message
                    if (window.PuroBeach && window.PuroBeach.showToast) {
                        window.PuroBeach.showToast('Esta hamaca está ocupada', 'info');
                    }
                }
                updateConflictSelectionCounter();
                return;
            }

            // Normal mode - check if clicked furniture is occupied
            if (availability && !availability.available && availability.reservation_id) {
                // Occupied furniture - deselect it and open reservation panel
                map.deselectFurniture(item.id);
                openReservationPanel(availability.reservation_id, 'view');
            }
            updateSelectionBar();
            updateConflictSelectionCounter();
        } catch (error) {
            console.error('Error in onFurnitureClick callback:', error);
            updateSelectionBar();
            updateConflictSelectionCounter();
        }
    });

    document.getElementById('btn-clear-selection').addEventListener('click', () => {
        map.clearSelection();
        updateSelectionBar();
        updateConflictSelectionCounter();
    });

    // ==========================================================================
    // NEW RESERVATION BUTTON
    // ==========================================================================
    const btnNewReservation = document.getElementById('btn-new-reservation');
    btnNewReservation.addEventListener('click', openNewReservationPanel);

    // ==========================================================================
    // BLOCK SELECTED BUTTON
    // ==========================================================================
    const btnBlockSelection = document.getElementById('btn-block-selection');
    if (btnBlockSelection) {
        btnBlockSelection.addEventListener('click', () => {
            const selected = map.getSelectedFurnitureData();
            if (selected.length === 0) {
                window.PuroBeach.showToast('Selecciona mobiliario primero', 'warning');
                return;
            }
            const ids = selected.map(f => f.id);
            const numbers = selected.map(f => f.number);
            blockManager.showBlockModal(ids, numbers);
        });
    }

    // ==========================================================================
    // CONTEXT MENU
    // ==========================================================================
    const contextMenu = document.getElementById('contextMenu');
    const contextMenuHeader = document.getElementById('context-menu-header');
    const contextMenuAvailable = document.getElementById('context-menu-available');
    const contextMenuOccupied = document.getElementById('context-menu-occupied');
    let contextFurnitureId = null;
    let contextReservationId = null;

    document.addEventListener('click', () => contextMenu.classList.add('d-none'));
    document.addEventListener('contextmenu', (e) => {
        if (!e.target.closest('.furniture-item') && !e.target.closest('.context-menu')) {
            contextMenu.classList.add('d-none');
        }
    });

    async function showContextMenu(furnitureId, event) {
        event.preventDefault();
        event.stopPropagation();

        try {
            const response = await fetch(`/beach/api/map/furniture/${furnitureId}/details?date=${map.getCurrentDate()}`);
            const data = await response.json();

            if (!data.success) return;

            contextFurnitureId = furnitureId;
            contextReservationId = data.reservation?.id || null;

            contextMenuHeader.textContent = `${data.furniture.type_name} #${data.furniture.number}`;

            contextMenuAvailable.classList.add('d-none');
            contextMenuOccupied.classList.add('d-none');

            if (data.reservation) {
                contextMenuOccupied.classList.remove('d-none');
            } else {
                contextMenuAvailable.classList.remove('d-none');
            }

            // Position menu
            let left = event.clientX;
            let top = event.clientY;

            if (left + 180 > window.innerWidth - 10) {
                left = window.innerWidth - 190;
            }
            if (top + 200 > window.innerHeight - 10) {
                top = window.innerHeight - 210;
            }

            contextMenu.style.left = `${left}px`;
            contextMenu.style.top = `${top}px`;
            contextMenu.classList.remove('d-none');

        } catch (error) {
            console.error('Error showing context menu:', error);
        }
    }

    document.getElementById('map-container').addEventListener('contextmenu', (e) => {
        const furnitureItem = e.target.closest('.furniture-item');
        if (furnitureItem) {
            const furnitureId = parseInt(furnitureItem.dataset.furnitureId);
            if (furnitureId) showContextMenu(furnitureId, e);
        }
    });

    contextMenu.addEventListener('click', async (e) => {
        const menuItem = e.target.closest('.context-menu-item');
        if (!menuItem) return;

        const action = menuItem.dataset.action;
        contextMenu.classList.add('d-none');

        switch (action) {
            case 'view-details':
                // TODO: Show details modal
                break;
            case 'select':
                if (contextFurnitureId) {
                    map.selectFurniture(contextFurnitureId, true);
                    updateSelectionBar();
                }
                break;
            case 'new-reservation':
                if (contextFurnitureId) {
                    map.clearSelection();
                    map.selectFurniture(contextFurnitureId);
                    updateSelectionBar();
                    openNewReservationPanel();
                }
                break;
            case 'view-reservation':
                if (contextReservationId) {
                    window.location.href = `/beach/reservations/${contextReservationId}`;
                }
                break;
            case 'edit-reservation':
                if (contextReservationId) {
                    window.location.href = `/beach/reservations/${contextReservationId}/edit`;
                }
                break;
            case 'cancel-reservation':
                if (contextReservationId) {
                    const confirmed = await PuroBeach.confirmAction({
                        title: 'Cancelar reserva',
                        message: '¿Cancelar esta reserva?',
                        confirmText: 'Cancelar reserva',
                        confirmClass: 'btn-warning',
                        iconClass: 'fa-ban'
                    });
                    if (confirmed) {
                        try {
                            const response = await fetch(`/beach/api/reservations/${contextReservationId}/toggle-state`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                                },
                                body: JSON.stringify({ state: 'Cancelada', action: 'set' })
                            });
                            const data = await response.json();
                            if (data.success) {
                                await map.refreshAvailability();
                                updateStats(currentZoneId);
                            } else {
                                alert(data.error || 'Error al cancelar');
                            }
                        } catch (error) {
                            console.error('Error canceling:', error);
                        }
                    }
                }
                break;
            case 'block':
                if (contextFurnitureId) {
                    const today = map.getCurrentDate();
                    const blockConfirmed = await PuroBeach.confirmAction({
                        title: 'Bloquear mobiliario',
                        message: `¿Bloquear mobiliario para ${formatDateCompact(today)}?`,
                        confirmText: 'Bloquear',
                        confirmClass: 'btn-warning',
                        iconClass: 'fa-lock'
                    });
                    if (blockConfirmed) {
                        try {
                            const response = await fetch(`/beach/api/map/furniture/${contextFurnitureId}/block`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                                },
                                body: JSON.stringify({
                                    start_date: today,
                                    end_date: today,
                                    block_type: 'maintenance',
                                    reason: 'Bloqueado desde mapa'
                                })
                            });
                            const data = await response.json();
                            if (data.success) {
                                await map.refreshAvailability();
                                updateStats(currentZoneId);
                            }
                        } catch (error) {
                            console.error('Error blocking:', error);
                        }
                    }
                }
                break;
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            contextMenu.classList.add('d-none');
            if (newReservationPanel.isOpen()) {
                newReservationPanel.close();
            }
        }
    });

    // Apply zone view after every render
    map.on('onRender', () => {
        if (currentZoneId) {
            applyZoneView(currentZoneId);
        } else {
            populateZoneSelector();
        }
    });

});

