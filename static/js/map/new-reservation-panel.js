/**
 * NewReservationPanel - Side panel for creating new reservations
 * Uses shared CustomerSearch and DatePicker components
 *
 * REFACTORED: This file now re-exports the modular implementation.
 * See reservation-panel/ directory for the split modules.
 *
 * Module Architecture:
 * - panel-core.js: Main coordinator (471 lines)
 * - customer-handler.js: Customer selection, creation, display (609 lines)
 * - date-availability.js: Date picker, availability checks (246 lines)
 * - pricing-calculator.js: Pricing fetch, display, editing (361 lines)
 * - conflict-resolver.js: Conflict modal, per-day selections (244 lines)
 * - safeguard-checks.js: All validation checks SG-01 to SG-07 (326 lines)
 *
 * Total: ~2257 lines split into 6 focused modules (was 2239 lines in single file)
 */

export { NewReservationPanel } from './reservation-panel/panel-core.js';

// For backward compatibility with non-ES6 module usage
if (typeof window !== 'undefined') {
    import('./reservation-panel/panel-core.js').then(module => {
        window.NewReservationPanel = module.NewReservationPanel;
    });
}
