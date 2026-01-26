/**
 * Move Mode Panel Component
 * Displays the pool of reservations waiting to be assigned during move mode
 */

import { formatDateDisplay, showToast } from './utils.js';

/**
 * Move Mode Panel Class
 * Renders and manages the side panel showing unassigned reservations
 */
export class MoveModePanel {
    // Interaction timing constants
    static DOUBLE_CLICK_THRESHOLD = 300;  // ms between clicks for double-click
    static LONG_PRESS_DELAY = 500;        // ms to trigger long-press
    static MOVE_THRESHOLD = 10;           // px movement to cancel long-press
    static TOOLTIP_AUTO_DISMISS = 3000;   // ms before mobile tooltip auto-hides

    constructor(containerId, moveMode) {
        this.container = document.getElementById(containerId);
        this.moveMode = moveMode;

        // Filter state
        this.filters = {
            type: 'all',  // all, interno, externo
            vip: false,
            hasPreferences: false
        };

        // Create panel structure if container exists
        if (this.container) {
            this.createPanelStructure();
            this.setupEventListeners();
        } else {
            console.warn(`MoveModePanel: Container #${containerId} not found`);
        }
    }

    /**
     * Create the panel HTML structure
     */
    createPanelStructure() {
        this.container.innerHTML = `
            <!-- Collapsed bar - always visible in the 48px strip when collapsed -->
            <div class="collapsed-bar">
                <button type="button" class="collapse-toggle" id="moveModeCollapseBtn" title="Colapsar panel">
                    <i class="fas fa-chevron-right"></i>
                </button>
                <div class="collapsed-thumbnails" id="collapsedThumbnails"></div>
            </div>
            <div class="move-mode-panel">
                <div class="move-mode-panel-header">
                    <h5>
                        <i class="fas fa-exchange-alt"></i>
                        Modo Mover
                        <span class="badge" id="moveModePoolCount">0</span>
                    </h5>
                    <div class="header-actions">
                        <button type="button" class="btn collapse-btn" id="moveModeCollapseBtnHeader" title="Colapsar panel" aria-label="Colapsar panel">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                        <button type="button" class="btn" id="moveModeExitBtn" title="Cerrar" aria-label="Cerrar panel">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>

                <div class="move-mode-filters" id="moveModeFilters">
                    <div class="filter-group">
                        <button type="button" class="filter-btn active" data-filter="type" data-value="all">Todos</button>
                        <button type="button" class="filter-btn" data-filter="type" data-value="interno">Interno</button>
                        <button type="button" class="filter-btn" data-filter="type" data-value="externo">Externo</button>
                    </div>
                    <div class="filter-toggles">
                        <label class="filter-toggle" title="Solo VIP">
                            <input type="checkbox" id="filterVip"> <i class="fas fa-star"></i>
                        </label>
                        <label class="filter-toggle" title="Con preferencias">
                            <input type="checkbox" id="filterPrefs"> <i class="fas fa-heart"></i>
                        </label>
                    </div>
                </div>

                <div class="move-mode-panel-body" id="moveModePoolList">
                    <div class="move-mode-empty-state">
                        <i class="fas fa-hand-pointer fa-2x text-muted mb-2"></i>
                        <p class="text-muted mb-0">Toca mobiliario ocupado para liberarlo</p>
                        <p class="text-muted small mb-0">Mantén presionado para liberar todo</p>
                    </div>
                </div>

                <!-- Keyboard shortcuts - desktop only -->
                <div class="move-mode-shortcuts">
                    <span><kbd>Clic</kbd> 1 item</span>
                    <span><kbd>Ctrl+Clic</kbd> Todos</span>
                    <span><kbd>Ctrl+Z</kbd> Deshacer</span>
                </div>

                <!-- Footer with action buttons -->
                <div class="move-mode-panel-footer">
                    <button type="button" class="move-mode-footer-btn btn-exit" id="moveModeExitFooterBtn">
                        Salir
                    </button>
                    <button type="button" class="move-mode-footer-btn btn-undo" id="moveModeUndoBtn" disabled>
                        <i class="fas fa-undo"></i>
                        <span>Deshacer</span>
                        <span class="undo-count" id="moveModeUndoCount"></span>
                    </button>
                </div>

                <div class="move-mode-legend" id="moveModeLegend" style="display: none;">
                    <div class="legend-header">Buscando:</div>
                    <div class="legend-items" id="moveModeLegendItems"></div>
                </div>
            </div>
        `;

        // Cache elements
        this.poolCount = document.getElementById('moveModePoolCount');
        this.poolList = document.getElementById('moveModePoolList');
        this.exitBtn = document.getElementById('moveModeExitBtn');
        this.exitFooterBtn = document.getElementById('moveModeExitFooterBtn');
        this.undoBtn = document.getElementById('moveModeUndoBtn');
        this.undoCount = document.getElementById('moveModeUndoCount');
        this.legend = document.getElementById('moveModeLegend');
        this.legendItems = document.getElementById('moveModeLegendItems');
        this.collapseBtn = document.getElementById('moveModeCollapseBtn');
        this.collapseBtnHeader = document.getElementById('moveModeCollapseBtnHeader');
        this.collapsedThumbnails = document.getElementById('collapsedThumbnails');
        this.filterVip = document.getElementById('filterVip');
        this.filterPrefs = document.getElementById('filterPrefs');
        this.filterBtns = document.querySelectorAll('.filter-btn[data-filter="type"]');

        // Swipe gesture state
        this.swipeState = {
            startX: 0,
            currentX: 0,
            isDragging: false
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Exit button (header)
        this.exitBtn?.addEventListener('click', () => {
            this.moveMode.deactivate();
        });

        // Exit button (footer)
        this.exitFooterBtn?.addEventListener('click', () => {
            this.moveMode.deactivate();
        });

        // Undo button
        this.undoBtn?.addEventListener('click', () => {
            this.moveMode.undo();
        });

        // Collapse button (in collapsed bar)
        this.collapseBtn?.addEventListener('click', () => {
            this.toggleCollapse();
        });

        // Collapse button (in header - visible when expanded)
        this.collapseBtnHeader?.addEventListener('click', () => {
            this.toggleCollapse();
        });

        // Filter type buttons
        this.filterBtns?.forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.filters.type = btn.dataset.value;
                this.renderPool(this.moveMode.getPool());
            });
        });

        // Filter VIP checkbox
        this.filterVip?.addEventListener('change', () => {
            this.filters.vip = this.filterVip.checked;
            this.renderPool(this.moveMode.getPool());
        });

        // Filter preferences checkbox
        this.filterPrefs?.addEventListener('change', () => {
            this.filters.hasPreferences = this.filterPrefs.checked;
            this.renderPool(this.moveMode.getPool());
        });

        // Setup swipe-to-close gesture
        this.setupSwipeGesture();

        // MoveMode events
        this.moveMode.on('onPoolUpdate', (data) => this.renderPool(data.pool));
        this.moveMode.on('onSelectionChange', (data) => this.updateSelection(data.reservation));
        this.moveMode.on('onFurnitureHighlight', (data) => this.updateLegend(data.preferences));
        this.moveMode.on('onActivate', () => this.show());
        this.moveMode.on('onDeactivate', () => this.hide());
        this.moveMode.on('onUndo', () => this.updateUndoState());
    }

    /**
     * Setup swipe-to-close gesture for mobile
     */
    setupSwipeGesture() {
        if (!this.container) return;

        const panel = this.container;

        panel.addEventListener('touchstart', (e) => {
            // Only initiate from left edge (first 50px)
            if (e.touches[0].clientX < 50) {
                this.swipeState.startX = e.touches[0].clientX;
                this.swipeState.isDragging = true;
                panel.classList.add('dragging');
            }
        }, { passive: true });

        panel.addEventListener('touchmove', (e) => {
            if (!this.swipeState.isDragging) return;
            this.swipeState.currentX = e.touches[0].clientX;
            const deltaX = this.swipeState.currentX - this.swipeState.startX;

            // Only allow swipe right (to close)
            if (deltaX > 0) {
                panel.style.transform = `translateX(${deltaX}px)`;
            }
        }, { passive: true });

        panel.addEventListener('touchend', () => {
            if (!this.swipeState.isDragging) return;
            this.swipeState.isDragging = false;
            panel.classList.remove('dragging');

            const deltaX = this.swipeState.currentX - this.swipeState.startX;
            if (deltaX > 100) { // Threshold to close
                this.moveMode.deactivate();
            } else {
                panel.style.transform = '';
            }
            this.swipeState.startX = 0;
            this.swipeState.currentX = 0;
        });

        panel.addEventListener('touchcancel', () => {
            this.swipeState.isDragging = false;
            panel.classList.remove('dragging');
            panel.style.transform = '';
            this.swipeState.startX = 0;
            this.swipeState.currentX = 0;
        });
    }

    /**
     * Show the panel
     */
    show() {
        this.container?.classList.add('visible');
        this.updateUndoState();
    }

    /**
     * Hide the panel
     */
    hide() {
        this.container?.classList.remove('visible');
        this.container?.classList.remove('collapsed');
        this._hideThumbnailTooltip();
    }

    /**
     * Toggle panel collapsed state
     */
    toggleCollapse() {
        this.container?.classList.toggle('collapsed');
    }

    /**
     * Check if reservation has VIP status
     * @private
     * @param {Object} res - Reservation object
     * @returns {boolean} True if VIP
     */
    _isVip(res) {
        if (res.is_vip) return true;
        return res.tags?.some(t =>
            t.name?.toLowerCase().includes('vip') ||
            t.code?.toLowerCase().includes('vip')
        ) || false;
    }

    /**
     * Apply filters to pool
     * @param {Array} pool - Full pool
     * @returns {Array} Filtered pool
     */
    applyFilters(pool) {
        return pool.filter(res => {
            if (this.filters.type !== 'all' && res.customer_type !== this.filters.type) {
                return false;
            }
            if (this.filters.vip && !this._isVip(res)) {
                return false;
            }
            if (this.filters.hasPreferences && (!res.preferences || res.preferences.length === 0)) {
                return false;
            }
            return true;
        });
    }

    /**
     * Render the pool of reservations
     * @param {Array} pool - Pool reservations
     */
    renderPool(pool) {
        if (!this.poolList) return;

        // Apply filters
        const filteredPool = this.applyFilters(pool);

        // Update count badge (show filtered/total)
        this.poolCount.textContent = filteredPool.length === pool.length
            ? pool.length
            : `${filteredPool.length}/${pool.length}`;

        if (pool.length === 0) {
            this.poolList.innerHTML = `
                <div class="move-mode-empty-state">
                    <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
                    <p class="text-muted mb-0">Todas las reservas asignadas</p>
                </div>
            `;
            // Clear collapsed thumbnails when pool is empty
            this.renderCollapsedThumbnails(pool);
            return;
        }

        if (filteredPool.length === 0) {
            this.poolList.innerHTML = `
                <div class="move-mode-empty-state">
                    <i class="fas fa-filter fa-2x text-muted mb-2"></i>
                    <p class="text-muted mb-0">Sin resultados con estos filtros</p>
                </div>
            `;
            // Still show collapsed thumbnails for full pool (unfiltered)
            this.renderCollapsedThumbnails(pool);
            return;
        }

        this.poolList.innerHTML = filteredPool.map(res => this.renderReservationCard(res)).join('');

        // Add click handlers to cards
        this.poolList.querySelectorAll('.move-mode-card').forEach(card => {
            card.addEventListener('click', () => {
                const resId = parseInt(card.dataset.reservationId);
                this.moveMode.selectReservation(resId);
            });
        });

        // Add restore handlers
        this.poolList.querySelectorAll('.restore-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const card = btn.closest('.move-mode-card');
                const resId = parseInt(card.dataset.reservationId);
                const res = this.moveMode.pool.find(r => r.reservation_id === resId);

                // If triggered by conflict, cancel and return to conflict view - Issue #7
                if (this.moveMode.triggeredByConflict) {
                    const result = this.moveMode.cancelToConflict();
                    if (result.conflictContext) {
                        document.dispatchEvent(new CustomEvent('moveMode:returnToConflict', {
                            detail: result.conflictContext
                        }));
                    }
                    return;
                }

                // Normal restore: assign back to original furniture
                // Use initialFurniture (what it had when first entering pool)
                if (!res || !res.initialFurniture?.length) {
                    showToast('No hay posición original para restaurar', 'warning');
                    return;
                }

                // Get original furniture IDs (furniture_id is the actual furniture, id is the assignment record)
                const originalIds = res.initialFurniture.map(f => f.furniture_id || f.id);

                // Assign back to original furniture
                const result = await this.moveMode.assignFurniture(resId, originalIds);
                if (result.success) {
                    showToast('Posición original restaurada', 'success');
                }
            });
        });

        // Edit button handlers - Issue #8
        this.poolList.querySelectorAll('.edit-reservation-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const resId = parseInt(btn.dataset.reservationId);

                // Dispatch event to open edit modal
                document.dispatchEvent(new CustomEvent('moveMode:editReservation', {
                    detail: { reservationId: resId }
                }));
            });
        });

        this.updateUndoState();

        // Also update collapsed thumbnails
        this.renderCollapsedThumbnails(pool);
    }

    /**
     * Render mini-cards for collapsed state
     * @param {Array} pool - Pool reservations
     */
    renderCollapsedThumbnails(pool) {
        if (!this.collapsedThumbnails) return;

        if (pool.length === 0) {
            this.collapsedThumbnails.innerHTML = '';
            return;
        }

        const maxThumbnails = 4;
        const visiblePool = pool.slice(0, maxThumbnails);
        const remainingCount = pool.length - maxThumbnails;

        let html = visiblePool.map(res => {
            const isVip = this._isVip(res);
            const isSelected = res.reservation_id === this.moveMode.selectedReservationId;
            const isComplete = res.isComplete || res.assignedCount >= res.totalNeeded;
            const vipClass = isVip ? 'is-vip' : '';
            const selectedClass = isSelected ? 'selected' : '';
            const completeClass = isComplete ? 'is-complete' : '';
            const vipStar = isVip ? '<i class="fas fa-star vip-star"></i>' : '';

            // Mini progress dots (max 4 dots for space)
            const totalDots = Math.min(res.totalNeeded, 4);
            const filledDots = Math.min(res.assignedCount, totalDots);
            let progressHtml = '';
            for (let i = 0; i < totalDots; i++) {
                const filled = i < filledDots ? 'filled' : '';
                progressHtml += `<span class="mini-dot ${filled}"></span>`;
            }

            return `
                <div class="collapsed-thumbnail ${vipClass} ${selectedClass} ${completeClass}"
                     data-reservation-id="${res.reservation_id}"
                     data-customer-name="${res.customer_name || ''}"
                     data-room="${res.room_number || ''}">
                    ${vipStar}
                    <span class="person-count">${isComplete ? '✓' : res.num_people}</span>
                    <div class="mini-progress">${progressHtml}</div>
                    ${isSelected ? `<div class="selected-info">
                        <span class="selected-name">${res.customer_name?.split(' ')[0] || ''}</span>
                        ${res.room_number ? `<span class="selected-room">${res.room_number}</span>` : ''}
                    </div>` : ''}
                </div>
            `;
        }).join('');

        // Add "+N" badge if there are more reservations
        if (remainingCount > 0) {
            html += `
                <div class="collapsed-thumbnail more-badge">
                    +${remainingCount}
                </div>
            `;
        }

        this.collapsedThumbnails.innerHTML = html;

        // Setup interaction handlers (click, double-click, hover, touch)
        this._setupThumbnailInteractions(pool);
    }

    /**
     * Setup thumbnail interaction handlers (click, double-click, hover, touch)
     * @private
     * @param {Array} pool - Pool reservations
     */
    _setupThumbnailInteractions(pool) {
        const thumbnails = this.collapsedThumbnails.querySelectorAll(
            '.collapsed-thumbnail[data-reservation-id]'
        );

        thumbnails.forEach(thumb => {
            const resId = parseInt(thumb.dataset.reservationId);
            const reservation = pool.find(r => r.reservation_id === resId);
            if (!reservation) return;

            // Track click timing for double-click detection
            let lastClickTime = 0;

            // Click handler: select without expand, double-click expands
            thumb.addEventListener('click', () => {
                const now = Date.now();
                if (now - lastClickTime < MoveModePanel.DOUBLE_CLICK_THRESHOLD) {
                    // Double-click: expand + select
                    this.container?.classList.remove('collapsed');
                    this.moveMode.selectReservation(resId);
                } else {
                    // Single click: select only (no expand)
                    this.moveMode.selectReservation(resId);
                }
                lastClickTime = now;
            });

            // Hover handlers (desktop only)
            if (window.matchMedia('(hover: hover)').matches) {
                thumb.addEventListener('mouseenter', () => {
                    this._showThumbnailTooltip(thumb, reservation);
                });
                thumb.addEventListener('mouseleave', () => {
                    this._hideThumbnailTooltip();
                });
            }

            // Touch handlers (mobile)
            this._setupThumbnailTouchHandlers(thumb, reservation);
        });

        // "+N" badge just expands panel
        const moreBadge = this.collapsedThumbnails.querySelector('.more-badge');
        moreBadge?.addEventListener('click', () => {
            this.container?.classList.remove('collapsed');
        });
    }

    /**
     * Setup touch handlers for long-press tooltip on mobile
     * @private
     * @param {HTMLElement} thumb - Thumbnail element
     * @param {Object} reservation - Reservation data
     */
    _setupThumbnailTouchHandlers(thumb, reservation) {
        let longPressTimer = null;
        let touchStartX = 0;
        let touchStartY = 0;

        thumb.addEventListener('touchstart', (e) => {
            if (e.touches.length !== 1) return;

            const touch = e.touches[0];
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;

            longPressTimer = setTimeout(() => {
                // Haptic feedback
                if (navigator.vibrate) {
                    navigator.vibrate(50);
                }
                this._showThumbnailTooltip(thumb, reservation, true);
            }, MoveModePanel.LONG_PRESS_DELAY);
        }, { passive: true });

        thumb.addEventListener('touchmove', (e) => {
            if (!longPressTimer) return;

            const touch = e.touches[0];
            const deltaX = Math.abs(touch.clientX - touchStartX);
            const deltaY = Math.abs(touch.clientY - touchStartY);

            if (deltaX > MoveModePanel.MOVE_THRESHOLD || deltaY > MoveModePanel.MOVE_THRESHOLD) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        }, { passive: true });

        thumb.addEventListener('touchend', () => {
            if (longPressTimer) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        });

        thumb.addEventListener('touchcancel', () => {
            if (longPressTimer) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        });
    }

    /**
     * Create the tooltip element if not exists
     * @private
     */
    _createThumbnailTooltip() {
        if (this.thumbnailTooltip) return;

        this.thumbnailTooltip = document.createElement('div');
        this.thumbnailTooltip.className = 'collapsed-bar-tooltip';
        document.body.appendChild(this.thumbnailTooltip);
    }

    /**
     * Show tooltip for a thumbnail
     * @private
     * @param {HTMLElement} thumb - Thumbnail element
     * @param {Object} reservation - Reservation data
     * @param {boolean} isMobile - Whether triggered from mobile long-press
     */
    _showThumbnailTooltip(thumb, reservation, isMobile = false) {
        this._createThumbnailTooltip();

        // Build tooltip content
        let content = `<div class="tooltip-name">${reservation.customer_name}</div>`;

        if (reservation.room_number) {
            content += `<div class="tooltip-room">Hab. ${reservation.room_number}</div>`;
        }

        // Progress info
        content += `<div class="tooltip-progress">${reservation.assignedCount} de ${reservation.totalNeeded} asignados</div>`;

        // Render preferences (max 6 icons)
        if (reservation.preferences && reservation.preferences.length > 0) {
            const maxPrefs = 6;
            const visiblePrefs = reservation.preferences.slice(0, maxPrefs);
            const prefIcons = visiblePrefs.map(p => {
                const icon = this._normalizeIconClass(p.icon);
                return `<div class="tooltip-pref-icon" title="${p.name}"><i class="${icon}"></i></div>`;
            }).join('');
            content += `<div class="tooltip-preferences">${prefIcons}</div>`;

            if (reservation.preferences.length > maxPrefs) {
                content += `<div class="tooltip-room">+${reservation.preferences.length - maxPrefs} más</div>`;
            }
        }

        if (isMobile) {
            content += `<div class="tooltip-dismiss-hint">Toca para cerrar</div>`;
        }

        this.thumbnailTooltip.innerHTML = content;
        this.thumbnailTooltip.style.display = 'block';
        this.thumbnailTooltip.classList.remove('above'); // Reset position modifier

        // Position tooltip to the left of the thumbnail
        const thumbRect = thumb.getBoundingClientRect();
        const tooltipRect = this.thumbnailTooltip.getBoundingClientRect();

        let left = thumbRect.left - tooltipRect.width - 16; // 16px gap + arrow
        let top = thumbRect.top + (thumbRect.height / 2) - (tooltipRect.height / 2);

        // Keep within viewport
        if (top < 10) top = 10;
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = window.innerHeight - tooltipRect.height - 10;
        }
        if (left < 10) {
            // If not enough space on left, position above the thumbnail
            left = thumbRect.left - tooltipRect.width / 2;
            top = thumbRect.top - tooltipRect.height - 10;
            this.thumbnailTooltip.classList.add('above'); // Arrow points down
        }

        this.thumbnailTooltip.style.left = `${left}px`;
        this.thumbnailTooltip.style.top = `${top}px`;

        // Auto-dismiss on mobile
        if (isMobile) {
            this._clearTooltipDismissTimer();
            this.tooltipDismissTimer = setTimeout(() => {
                this._hideThumbnailTooltip();
            }, MoveModePanel.TOOLTIP_AUTO_DISMISS);

            // Also dismiss on next tap anywhere
            const dismissOnTap = () => {
                this._hideThumbnailTooltip();
                document.removeEventListener('touchstart', dismissOnTap);
            };
            setTimeout(() => {
                document.addEventListener('touchstart', dismissOnTap, { once: true });
            }, 100);
        }
    }

    /**
     * Hide the thumbnail tooltip
     * @private
     */
    _hideThumbnailTooltip() {
        if (this.thumbnailTooltip) {
            this.thumbnailTooltip.style.display = 'none';
        }
        this._clearTooltipDismissTimer();
    }

    /**
     * Clear the tooltip auto-dismiss timer
     * @private
     */
    _clearTooltipDismissTimer() {
        if (this.tooltipDismissTimer) {
            clearTimeout(this.tooltipDismissTimer);
            this.tooltipDismissTimer = null;
        }
    }

    /**
     * Normalize icon class to ensure proper FontAwesome prefix
     * @private
     * @param {string} icon - Icon class string
     * @returns {string} Normalized icon class
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

    /**
     * Update selected class on collapsed thumbnails
     * @private
     * @param {number|null} selectedId - Selected reservation ID
     */
    _updateCollapsedThumbnailSelection(selectedId) {
        if (!this.collapsedThumbnails) return;

        this.collapsedThumbnails.querySelectorAll('.collapsed-thumbnail[data-reservation-id]')
            .forEach(thumb => {
                const resId = parseInt(thumb.dataset.reservationId);
                if (resId === selectedId) {
                    thumb.classList.add('selected');
                } else {
                    thumb.classList.remove('selected');
                }
            });
    }

    /**
     * Get furniture numbers display string
     * @private
     * @param {Object} res - Reservation data
     * @returns {string} Comma-separated furniture numbers or '-'
     */
    _getFurnitureDisplay(res) {
        const furniture = res.initialFurniture?.length > 0
            ? res.initialFurniture
            : res.original_furniture;
        if (!furniture || furniture.length === 0) return '-';
        return furniture.map(f => f.number || f.furniture_number).join(', ');
    }

    /**
     * Render a single reservation card
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderReservationCard(res) {
        const isSelected = res.reservation_id === this.moveMode.selectedReservationId;
        const selectedClass = isSelected ? 'selected' : '';
        const progressDots = this.renderProgressDots(res.assignedCount, res.totalNeeded);
        const prefDots = this.renderPreferenceDots(res.preferences?.length || 0);
        const multidayBadge = res.is_multiday
            ? `<span class="badge bg-info ms-1" title="${res.total_days} días">📅${res.total_days}</span>`
            : '';
        const roomDisplay = res.room_number
            ? `<span class="badge bg-primary me-1"><i class="fas fa-door-open me-1"></i>${res.room_number}</span>`
            : '';

        return `
            <div class="move-mode-card ${selectedClass}" data-reservation-id="${res.reservation_id}">
                <div class="card-header">
                    ${roomDisplay}
                    <span class="customer-name">${res.customer_name}</span>
                    ${multidayBadge}
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span><i class="fas fa-users me-1"></i>${res.num_people} personas</span>
                        <span class="preference-dots">${prefDots}</span>
                    </div>
                    <div class="text-muted small">
                        <i class="fas fa-map-marker-alt me-1"></i>Era: ${this._getFurnitureDisplay(res)}
                    </div>
                    <div class="progress-indicator mt-2">
                        ${progressDots}
                        <span class="progress-text">${res.assignedCount} de ${res.totalNeeded}</span>
                    </div>
                </div>
                ${isSelected ? this.renderExpandedContent(res) : ''}
            </div>
        `;
    }

    /**
     * Render expanded content for selected reservation
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderExpandedContent(res) {
        const preferences = res.preferences?.map(p =>
            `<div class="preference-item"><span class="pref-icon">${p.icon || '⭐'}</span> ${p.name}</div>`
        ).join('') || '<span class="text-muted">Sin preferencias</span>';

        const notes = res.notes
            ? `<div class="notes-section"><i class="fas fa-sticky-note me-1"></i>${res.notes}</div>`
            : '';

        const dayAssignments = res.is_multiday && res.day_assignments
            ? this.renderDayAssignments(res)
            : '';

        // Dynamic button text based on conflict context - Issue #7
        const restoreButtonText = this.moveMode.triggeredByConflict
            ? 'Cancelar y volver'
            : 'Restaurar';
        const restoreButtonIcon = this.moveMode.triggeredByConflict
            ? 'fa-arrow-left'
            : 'fa-undo';

        return `
            <div class="card-expanded">
                <div class="preferences-section">
                    <strong>Preferencias:</strong>
                    ${preferences}
                </div>
                ${notes}
                ${dayAssignments}
                <div class="expanded-actions mt-2">
                    <button type="button" class="btn btn-sm btn-outline-primary edit-reservation-btn"
                            data-reservation-id="${res.reservation_id}">
                        <i class="fas fa-edit me-1"></i>Editar
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary restore-btn">
                        <i class="fas ${restoreButtonIcon} me-1"></i>${restoreButtonText}
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render day assignments for multi-day reservations
     * @param {Object} res - Reservation data
     * @returns {string} HTML string
     */
    renderDayAssignments(res) {
        const days = Object.entries(res.day_assignments || {}).map(([date, furniture]) => {
            const isToday = date === res.target_date;
            const todayBadge = isToday ? ' <span class="badge bg-warning">hoy</span>' : '';
            return `<div class="day-assignment ${isToday ? 'today' : ''}">${formatDateDisplay(date)}${todayBadge}: ${furniture}</div>`;
        }).join('');

        return `
            <div class="days-section mt-2">
                <strong>Días de reserva:</strong>
                ${days}
            </div>
        `;
    }

    /**
     * Render progress dots
     * @param {number} assigned - Number assigned
     * @param {number} total - Total needed
     * @returns {string} HTML string
     */
    renderProgressDots(assigned, total) {
        const dots = [];
        for (let i = 0; i < total; i++) {
            const filled = i < assigned ? 'filled' : '';
            dots.push(`<span class="progress-dot ${filled}"></span>`);
        }
        return dots.join('');
    }

    /**
     * Render preference dots indicator
     * @param {number} count - Preference count
     * @returns {string} HTML string
     */
    renderPreferenceDots(count) {
        if (count === 0) return '';
        const filled = '●'.repeat(Math.min(count, 3));
        const empty = '○'.repeat(Math.max(0, 3 - count));
        return `<span title="${count} preferencias">${filled}${empty}</span>`;
    }

    /**
     * Update selection state
     * @param {Object|null} reservation - Selected reservation or null
     */
    updateSelection(reservation) {
        // Re-render to update selection state (for expanded cards)
        this.renderPool(this.moveMode.getPool());

        // Update collapsed thumbnail selection state directly (faster, no full re-render)
        this._updateCollapsedThumbnailSelection(reservation?.reservation_id);

        // Legend is hidden - furniture highlighting on map shows matches instead
        if (this.legend) {
            this.legend.style.display = 'none';
        }
    }

    /**
     * Update the preference legend
     * @param {Array} preferences - Preferences to display
     */
    updateLegend(preferences) {
        // Legend is hidden - furniture highlighting on map shows matches instead
        if (this.legend) {
            this.legend.style.display = 'none';
        }
    }

    /**
     * Update undo button state
     */
    updateUndoState() {
        const canUndo = this.moveMode.canUndo();
        const undoCount = this.moveMode.getUndoCount();

        if (this.undoBtn) {
            this.undoBtn.disabled = !canUndo;
        }

        if (this.undoCount) {
            this.undoCount.textContent = canUndo ? `(${undoCount})` : '';
        }
    }
}
