/**
 * NewReservationPanel - Side panel for creating new reservations
 * Uses shared CustomerSearch and DatePicker components
 *
 * REFACTORED: This file is now a loading stub.
 * The actual implementation is in reservation-panel/ directory split into focused modules.
 *
 * Module Architecture:
 * - panel-core.js: Main coordinator (510 lines)
 * - customer-handler.js: Customer selection, creation, display (671 lines)
 * - date-availability.js: Date picker, availability checks (249 lines)
 * - pricing-calculator.js: Pricing fetch, display, editing (376 lines)
 * - conflict-resolver.js: Conflict modal, per-day selections (240 lines)
 * - safeguard-checks.js: All validation checks SG-01 to SG-07 (329 lines)
 *
 * IMPORTANT: All module files must be loaded BEFORE this file in the HTML:
 * 1. static/js/map/reservation-panel/customer-handler.js
 * 2. static/js/map/reservation-panel/date-availability.js
 * 3. static/js/map/reservation-panel/pricing-calculator.js
 * 4. static/js/map/reservation-panel/conflict-resolver.js
 * 5. static/js/map/reservation-panel/safeguard-checks.js
 * 6. static/js/map/reservation-panel/panel-core.js
 *
 * See map.html for the correct loading order.
 */

// NewReservationPanel class is defined in reservation-panel/panel-core.js
// This file exists only to maintain the expected script loading location
