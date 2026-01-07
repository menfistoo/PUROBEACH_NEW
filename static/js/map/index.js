/**
 * Beach Map Module Index
 * Exports all map components and sets up global access
 */

// Re-export all modules
export { loadCSSVariables, darkenColor, getContrastColor, getCSRFToken, showToast, formatDateDisplay } from './utils.js';
export { TooltipManager } from './tooltips.js';
export { SelectionManager } from './selection.js';
export { NavigationManager } from './navigation.js';
export { InteractionManager } from './interaction.js';
export { SearchManager } from './SearchManager.js';
export { createSVG, renderZones, renderDecorativeItems, renderFurniture, createShape, updateLegend } from './renderer.js';
export { BeachMap } from './BeachMap.js';

// Import main class for global assignment
import { BeachMap } from './BeachMap.js';

// Make BeachMap available globally for non-module usage
window.BeachMap = BeachMap;
