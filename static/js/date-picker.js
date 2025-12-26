/**
 * DatePicker - Shared multi-day date picker component
 *
 * Provides a calendar-based date picker with multi-day selection support.
 * Used by both the reservation form and the map quick reservation modal.
 *
 * Usage:
 *   const picker = new DatePicker({
 *       container: document.getElementById('my-container'),
 *       onDateChange: (dates) => { console.log(dates); },
 *       initialDates: ['2025-01-15']
 *   });
 */

class DatePicker {
    constructor(options = {}) {
        // Required elements
        this.container = options.container;

        // Callbacks
        this.onDateChange = options.onDateChange || (() => {});

        // Configuration
        this.initialDates = options.initialDates || [];
        this.minDate = options.minDate || null;

        // Occupancy configuration
        this.fetchOccupancy = options.fetchOccupancy !== false; // Default true
        this.occupancyApiUrl = options.occupancyApiUrl || '/beach/api/reservations/availability-map';

        // Spanish month and day names
        this.monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        this.dayNames = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];

        // State
        this.selectedDates = new Set(this.initialDates);
        this.calendarMonth = new Date().getMonth();
        this.calendarYear = new Date().getFullYear();
        this.calendarOpen = false;
        this.calendarInteracting = false;

        // Occupancy state
        this.occupancyData = {};       // {date: {total, available, occupied, occupancy_rate}}
        this.occupancyLoading = false;
        this.occupancyLoadedMonth = null; // Track which month is loaded

        // Initialize if container is provided
        if (this.container) {
            this._init();
        }
    }

    _init() {
        // Build the date picker structure
        this._buildStructure();

        // Set initial month/year based on initial dates or today
        if (this.initialDates.length > 0) {
            const firstDate = new Date(this.initialDates[0] + 'T12:00:00');
            this.calendarMonth = firstDate.getMonth();
            this.calendarYear = firstDate.getFullYear();
        }

        // Update preview text
        this._updatePreviewText();

        // Close calendar on outside click
        document.addEventListener('click', (e) => {
            if (this.calendarOpen && !this.calendarInteracting &&
                !e.target.closest('.dp-container')) {
                this.toggleCalendar(false);
            }
        });
    }

    _buildStructure() {
        this.container.innerHTML = `
            <div class="dp-container">
                <div class="dp-collapsed">
                    <div class="dp-preview">
                        <i class="fas fa-calendar-alt text-primary me-2"></i>
                        <span class="dp-preview-text">Seleccionar fechas...</span>
                    </div>
                    <i class="fas fa-chevron-down text-muted dp-chevron"></i>
                </div>
                <div class="dp-expanded" style="display:none;">
                    <div class="dp-calendar"></div>
                    <div class="dp-footer">
                        <div class="dp-selected-tags"></div>
                        <small class="text-muted mt-2 d-block">
                            <span class="dp-count">0</span> dias seleccionados
                        </small>
                    </div>
                </div>
            </div>
        `;

        // Cache DOM references
        this.collapsedEl = this.container.querySelector('.dp-collapsed');
        this.expandedEl = this.container.querySelector('.dp-expanded');
        this.calendarEl = this.container.querySelector('.dp-calendar');
        this.previewTextEl = this.container.querySelector('.dp-preview-text');
        this.chevronEl = this.container.querySelector('.dp-chevron');
        this.tagsEl = this.container.querySelector('.dp-selected-tags');
        this.countEl = this.container.querySelector('.dp-count');

        // Bind click handler for collapsed view
        this.collapsedEl.addEventListener('click', () => this.toggleCalendar(true));
    }

    toggleCalendar(open) {
        this.calendarOpen = open;
        if (open) {
            this.expandedEl.style.display = 'block';
            this.chevronEl.classList.replace('fa-chevron-down', 'fa-chevron-up');
            this._renderCalendar();
            // Auto-fetch occupancy if enabled
            if (this.fetchOccupancy) {
                this._fetchMonthAvailability();
            }
        } else {
            this.expandedEl.style.display = 'none';
            this.chevronEl.classList.replace('fa-chevron-up', 'fa-chevron-down');
            this._updatePreviewText();
            // Notify of date change
            this.onDateChange(this.getSelectedDates());
        }
    }

    /**
     * Fetch occupancy data for the current month
     */
    async _fetchMonthAvailability() {
        const monthKey = `${this.calendarYear}-${this.calendarMonth}`;

        // Skip if already loaded for this month
        if (this.occupancyLoadedMonth === monthKey) {
            return;
        }

        const firstDay = new Date(this.calendarYear, this.calendarMonth, 1);
        const lastDay = new Date(this.calendarYear, this.calendarMonth + 1, 0);
        const dateFrom = this._formatDateISO(firstDay);
        const dateTo = this._formatDateISO(lastDay);

        this.occupancyLoading = true;
        this._showLoadingIndicator(true);

        try {
            const response = await fetch(
                `${this.occupancyApiUrl}?date_from=${dateFrom}&date_to=${dateTo}`
            );
            const data = await response.json();

            if (data.summary) {
                this.occupancyData = { ...this.occupancyData, ...data.summary };
                this.occupancyLoadedMonth = monthKey;
                // Re-render to show occupancy
                this._renderCalendar();
            }
        } catch (error) {
            console.warn('Failed to fetch occupancy data:', error);
        } finally {
            this.occupancyLoading = false;
            this._showLoadingIndicator(false);
        }
    }

    /**
     * Show/hide loading indicator on calendar
     */
    _showLoadingIndicator(show) {
        if (!this.calendarEl) return;

        let loader = this.calendarEl.querySelector('.dp-loading');
        if (show && !loader) {
            loader = document.createElement('div');
            loader.className = 'dp-loading';
            loader.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.calendarEl.appendChild(loader);
        } else if (!show && loader) {
            loader.remove();
        }
    }

    _renderCalendar() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const firstDay = new Date(this.calendarYear, this.calendarMonth, 1);
        const lastDay = new Date(this.calendarYear, this.calendarMonth + 1, 0);
        let startDay = firstDay.getDay();
        startDay = startDay === 0 ? 6 : startDay - 1;

        let html = `
            <div class="cal-header">
                <button type="button" class="dp-prev-month">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="cal-title">${this.monthNames[this.calendarMonth]} ${this.calendarYear}</span>
                <button type="button" class="dp-next-month">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            <div class="cal-weekdays">
                ${this.dayNames.map(d => `<div>${d}</div>`).join('')}
            </div>
            <div class="cal-days">
        `;

        // Previous month days (disabled)
        for (let i = 0; i < startDay; i++) {
            const prevMonth = new Date(this.calendarYear, this.calendarMonth, 0 - startDay + i + 1);
            html += `<div class="cal-day other-month disabled">${prevMonth.getDate()}</div>`;
        }

        // Current month days
        for (let d = 1; d <= lastDay.getDate(); d++) {
            const date = new Date(this.calendarYear, this.calendarMonth, d);
            const dateStr = this._formatDateISO(date);
            const isToday = date.getTime() === today.getTime();
            const isPast = date < today;
            const isSelected = this.selectedDates.has(dateStr);

            // Get occupancy data for this date
            const occupancy = this.occupancyData[dateStr];
            const occupancyRate = occupancy?.occupancy_rate || 0;
            const isFullyBooked = occupancyRate >= 100;

            let classes = ['cal-day'];
            if (isToday) classes.push('today');
            if (isPast || isFullyBooked) classes.push('disabled');
            if (isSelected) classes.push('selected');

            // Add occupancy level classes
            if (occupancy && !isPast) {
                if (occupancyRate >= 100) {
                    classes.push('occupancy-full');
                } else if (occupancyRate >= 80) {
                    classes.push('occupancy-high');
                } else if (occupancyRate >= 50) {
                    classes.push('occupancy-medium');
                }
            }

            // Build day HTML with optional tooltip for fully booked days
            const tooltip = isFullyBooked ? ' title="Sin disponibilidad"' : '';
            html += `<div class="${classes.join(' ')}" data-date="${dateStr}"${tooltip}>${d}</div>`;
        }

        html += `</div>`;
        this.calendarEl.innerHTML = html;

        // Bind event handlers
        this.calendarEl.querySelector('.dp-prev-month').addEventListener('click', (e) => {
            e.stopPropagation();
            this._changeMonth(-1);
        });
        this.calendarEl.querySelector('.dp-next-month').addEventListener('click', (e) => {
            e.stopPropagation();
            this._changeMonth(1);
        });
        this.calendarEl.querySelectorAll('.cal-day:not(.disabled):not(.other-month)').forEach(dayEl => {
            dayEl.addEventListener('click', (e) => {
                e.stopPropagation();
                this._toggleDate(dayEl.dataset.date);
            });
        });

        this._updateSelectedDisplay();
    }

    _changeMonth(delta) {
        this.calendarInteracting = true;
        this.calendarMonth += delta;
        if (this.calendarMonth > 11) {
            this.calendarMonth = 0;
            this.calendarYear++;
        }
        if (this.calendarMonth < 0) {
            this.calendarMonth = 11;
            this.calendarYear--;
        }
        this._renderCalendar();
        // Fetch occupancy for new month if enabled
        if (this.fetchOccupancy) {
            this._fetchMonthAvailability();
        }
        setTimeout(() => { this.calendarInteracting = false; }, 50);
    }

    _toggleDate(dateStr) {
        this.calendarInteracting = true;
        if (this.selectedDates.has(dateStr)) {
            this.selectedDates.delete(dateStr);
        } else {
            this.selectedDates.add(dateStr);
        }
        this._renderCalendar();
        setTimeout(() => { this.calendarInteracting = false; }, 50);
    }

    _removeDate(dateStr, e) {
        if (e) e.stopPropagation();
        this.selectedDates.delete(dateStr);
        this._renderCalendar();
        this._updatePreviewText();
    }

    _updateSelectedDisplay() {
        const count = this.selectedDates.size;
        this.countEl.textContent = count;

        const sorted = this.getSelectedDates();
        this.tagsEl.innerHTML = sorted.map(d =>
            `<span class="date-tag">
                ${this._formatDate(d)}
                <span class="remove" data-date="${d}">&times;</span>
            </span>`
        ).join('');

        // Bind remove handlers
        this.tagsEl.querySelectorAll('.remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this._removeDate(btn.dataset.date);
            });
        });
    }

    _updatePreviewText() {
        const sorted = this.getSelectedDates();
        const count = sorted.length;

        if (count === 0) {
            this.previewTextEl.textContent = 'Seleccionar fechas...';
        } else if (count === 1) {
            this.previewTextEl.textContent = this._formatDate(sorted[0]);
        } else {
            const preview = sorted.slice(0, 3).map(d => this._formatDate(d)).join(', ');
            this.previewTextEl.innerHTML = `<strong>${count} dias:</strong> ${preview}${count > 3 ? ' ...' : ''}`;
        }
    }

    _formatDate(dateStr) {
        if (!dateStr) return '';
        const parts = dateStr.split('-');
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }

    _formatDateISO(date) {
        // Format date as YYYY-MM-DD in local timezone (avoids UTC conversion issues)
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // Public methods
    getSelectedDates() {
        return Array.from(this.selectedDates).sort();
    }

    setSelectedDates(dates) {
        this.selectedDates = new Set(dates);
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
    }

    addDate(dateStr) {
        this.selectedDates.add(dateStr);
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
    }

    /**
     * Remove a specific date from selection
     * @param {string} dateStr - Date to remove (YYYY-MM-DD)
     */
    removeDate(dateStr) {
        this.selectedDates.delete(dateStr);
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
        // Notify of change
        this.onDateChange(this.getSelectedDates());
    }

    clearDates() {
        this.selectedDates.clear();
        this._updatePreviewText();
        if (this.calendarOpen) {
            this._renderCalendar();
        }
    }

    getFirstDate() {
        const sorted = this.getSelectedDates();
        return sorted.length > 0 ? sorted[0] : null;
    }

    isMultiday() {
        return this.selectedDates.size > 1;
    }

    destroy() {
        this.container.innerHTML = '';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatePicker;
}
