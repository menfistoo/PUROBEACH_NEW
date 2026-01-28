/**
 * Map Editor - Feature Utilities
 * Standalone utility for parsing and toggling furniture features.
 */

/**
 * Parse features from multiple storage formats into a string array.
 * Handles: Array, JSON-encoded array string, comma-separated string.
 * @param {*} rawFeatures - Features in any supported format
 * @returns {string[]} Array of feature codes
 */
export function parseFeatures(rawFeatures) {
    if (!rawFeatures) return [];
    if (Array.isArray(rawFeatures)) return [...rawFeatures];
    if (typeof rawFeatures === 'string') {
        try {
            const parsed = JSON.parse(rawFeatures);
            return Array.isArray(parsed) ? [...parsed] : [rawFeatures];
        } catch {
            return rawFeatures.split(',').map(f => f.trim()).filter(f => f);
        }
    }
    return [];
}

/**
 * Toggle a feature code in a features array.
 * @param {string[]} currentFeatures - Current feature codes
 * @param {string} code - Feature code to toggle
 * @returns {{ features: string[], added: boolean }}
 */
export function toggleFeature(currentFeatures, code) {
    if (currentFeatures.includes(code)) {
        return { features: currentFeatures.filter(f => f !== code), added: false };
    }
    return { features: [...currentFeatures, code], added: true };
}
