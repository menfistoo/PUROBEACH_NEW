/**
 * Map Renderer Module
 * Handles SVG creation and rendering of zones, furniture, and decorative elements
 */

import { darkenColor, getContrastColor } from './utils.js';

/**
 * SVG namespace for creating elements
 */
const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Create the main SVG element with layers
 * @param {HTMLElement} container - Container element
 * @param {Object} colors - Color configuration
 * @returns {Object} SVG element and layer references
 */
export function createSVG(container, colors) {
    container.innerHTML = '';

    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('id', 'beach-map');
    svg.setAttribute('class', 'beach-map-svg');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    // Create defs for patterns and filters
    const defs = document.createElementNS(SVG_NS, 'defs');
    defs.innerHTML = `
        <filter id="selected-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge>
                <feMergeNode in="blur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        <pattern id="zone-pattern" patternUnits="userSpaceOnUse" width="20" height="20">
            <rect width="20" height="20" fill="rgba(245, 230, 211, 0.3)"/>
            <circle cx="10" cy="10" r="1" fill="rgba(212, 175, 55, 0.2)"/>
        </pattern>
        <pattern id="pool-pattern" patternUnits="userSpaceOnUse" width="10" height="10">
            <rect width="10" height="10" fill="${colors.poolPrimary}"/>
            <rect x="0" y="0" width="5" height="5" fill="${colors.poolSecondary}" opacity="0.3"/>
            <rect x="5" y="5" width="5" height="5" fill="${colors.poolSecondary}" opacity="0.3"/>
        </pattern>
        <pattern id="blocked-stripes" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
            <rect width="4" height="8" fill="rgba(0,0,0,0.15)"/>
        </pattern>
    `;
    svg.appendChild(defs);

    // Create layers (order matters: zones -> decorative -> furniture -> selection)
    const zonesLayer = document.createElementNS(SVG_NS, 'g');
    zonesLayer.setAttribute('id', 'zones-layer');

    const decorativeLayer = document.createElementNS(SVG_NS, 'g');
    decorativeLayer.setAttribute('id', 'decorative-layer');

    const furnitureLayer = document.createElementNS(SVG_NS, 'g');
    furnitureLayer.setAttribute('id', 'furniture-layer');

    const selectionLayer = document.createElementNS(SVG_NS, 'g');
    selectionLayer.setAttribute('id', 'selection-layer');

    svg.appendChild(zonesLayer);
    svg.appendChild(decorativeLayer);
    svg.appendChild(furnitureLayer);
    svg.appendChild(selectionLayer);

    container.appendChild(svg);

    return {
        svg,
        zonesLayer,
        decorativeLayer,
        furnitureLayer,
        selectionLayer
    };
}

/**
 * Render zone backgrounds and labels
 * @param {SVGGElement} layer - Zones layer
 * @param {Object} data - Map data with zones and zone_bounds
 * @param {Object} colors - Color configuration
 */
export function renderZones(layer, data, colors) {
    layer.innerHTML = '';

    if (!data.zones || !data.zone_bounds) return;

    data.zones.forEach(zone => {
        const bounds = data.zone_bounds[zone.id];
        if (!bounds) return;

        const group = document.createElementNS(SVG_NS, 'g');
        group.setAttribute('class', 'zone-group');
        group.setAttribute('data-zone-id', zone.id);

        // Zone background
        const rect = document.createElementNS(SVG_NS, 'rect');
        rect.setAttribute('x', bounds.x);
        rect.setAttribute('y', bounds.y);
        rect.setAttribute('width', bounds.width);
        rect.setAttribute('height', bounds.height);
        rect.setAttribute('fill', 'url(#zone-pattern)');
        rect.setAttribute('stroke', zone.color || '#D4AF37');
        rect.setAttribute('stroke-width', '2');
        rect.setAttribute('stroke-dasharray', '8 4');
        rect.setAttribute('rx', '8');

        // Zone label
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', bounds.x + 15);
        label.setAttribute('y', bounds.y + 25);
        label.setAttribute('class', 'zone-label');
        label.setAttribute('fill', colors.zoneLabel);
        label.setAttribute('font-size', '14');
        label.setAttribute('font-weight', '600');
        label.textContent = zone.name;

        group.appendChild(rect);
        group.appendChild(label);
        layer.appendChild(group);
    });
}

/**
 * Render decorative items (pools, umbrellas, etc.)
 * @param {SVGGElement} layer - Decorative layer
 * @param {Object} data - Map data
 * @param {Object} colors - Color configuration
 * @param {SVGSVGElement} svg - Main SVG element for pattern creation
 */
export function renderDecorativeItems(layer, data, colors, svg) {
    layer.innerHTML = '';

    if (!data.furniture) return;

    const decorativeItems = data.furniture.filter(item => {
        const typeConfig = data.furniture_types[item.furniture_type] || {};
        return typeConfig.is_decorative === 1;
    });

    decorativeItems.forEach(item => {
        const group = createDecorativeElement(item, data, colors, svg);
        layer.appendChild(group);
    });
}

/**
 * Create a single decorative element
 */
function createDecorativeElement(item, data, colors, svg) {
    const group = document.createElementNS(SVG_NS, 'g');
    group.setAttribute('class', 'decorative-item');
    group.setAttribute('data-furniture-id', item.id);
    group.setAttribute('data-furniture-type', item.furniture_type);

    const posX = item.position_x ?? 0;
    const posY = item.position_y ?? 0;
    const rotation = item.rotation ?? 0;
    group.setAttribute('transform', `translate(${posX}, ${posY}) rotate(${rotation})`);

    const typeConfig = data.furniture_types[item.furniture_type] || {};
    const width = item.width || typeConfig.default_width || 100;
    const height = item.height || typeConfig.default_height || 60;

    let fillColor, strokeColor, fillPattern;

    if (item.furniture_type === 'piscina') {
        const poolFill = typeConfig.fill_color || colors.poolPrimary;
        const poolStroke = typeConfig.stroke_color || colors.poolSecondary;
        fillPattern = getPoolPattern(svg, item.id, poolFill, poolStroke);
        strokeColor = poolStroke;
    } else {
        fillColor = item.fill_color || typeConfig.fill_color || '#E8E8E8';
        strokeColor = typeConfig.stroke_color || '#CCCCCC';
    }

    const shape = createShape(typeConfig.map_shape || 'rounded_rect', width, height,
        fillPattern || fillColor, strokeColor);
    shape.setAttribute('stroke-width', '3');
    shape.setAttribute('opacity', '0.9');
    group.appendChild(shape);

    // Add label for non-pool decorative items
    if (item.furniture_type !== 'piscina') {
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', width / 2);
        label.setAttribute('y', height / 2);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('dominant-baseline', 'middle');
        label.setAttribute('fill', '#666666');
        label.setAttribute('font-size', '11');
        label.setAttribute('font-style', 'italic');
        label.setAttribute('pointer-events', 'none');
        label.textContent = item.number;
        group.appendChild(label);
    }

    return group;
}

/**
 * Render reservable furniture items
 * @param {SVGGElement} layer - Furniture layer
 * @param {Object} data - Map data
 * @param {Set} selectedFurniture - Set of selected furniture IDs
 * @param {Object} colors - Color configuration
 * @param {Function} onFurnitureClick - Click handler
 * @param {Object} tooltipManager - Tooltip manager instance
 * @param {Function} onFurnitureContextMenu - Right-click context menu handler
 */
export function renderFurniture(layer, data, selectedFurniture, colors, onFurnitureClick, tooltipManager, onFurnitureContextMenu) {
    layer.innerHTML = '';

    if (!data.furniture) return;

    const reservableFurniture = data.furniture.filter(item => {
        const typeConfig = data.furniture_types[item.furniture_type] || {};
        return typeConfig.is_decorative !== 1;
    });

    reservableFurniture.forEach(item => {
        const group = createFurnitureElement(item, data, selectedFurniture, colors, onFurnitureClick, tooltipManager, onFurnitureContextMenu);
        layer.appendChild(group);
    });
}

/**
 * Create a single furniture element
 */
function createFurnitureElement(item, data, selectedFurniture, colors, onFurnitureClick, tooltipManager, onFurnitureContextMenu) {
    const group = document.createElementNS(SVG_NS, 'g');
    group.setAttribute('class', 'furniture-item');
    group.setAttribute('data-furniture-id', item.id);

    const posX = item.position_x ?? 0;
    const posY = item.position_y ?? 0;
    const rotation = item.rotation ?? 0;
    group.setAttribute('transform', `translate(${posX}, ${posY}) rotate(${rotation})`);
    group.style.cursor = 'pointer';

    const typeConfig = data.furniture_types[item.furniture_type] || {};
    const availability = data.availability[item.id];
    const isAvailable = !availability || availability.available;
    const state = availability ? availability.state : null;

    let fillColor, strokeColor;
    if (isAvailable) {
        fillColor = colors.availableFill;
        strokeColor = colors.availableStroke;
    } else if (state && data.state_colors[state]) {
        fillColor = data.state_colors[state];
        strokeColor = darkenColor(fillColor, 30);
    } else {
        fillColor = typeConfig.fill_color || '#A0522D';
        strokeColor = typeConfig.stroke_color || '#654321';
    }

    // Check if blocked
    const blockInfo = data.blocks && data.blocks[item.id];
    if (blockInfo) {
        fillColor = blockInfo.color || '#9CA3AF';
        strokeColor = darkenColor(fillColor, 30);
        group.classList.add('blocked');
        group.setAttribute('data-block-type', blockInfo.block_type);
        group.style.cursor = 'not-allowed';
    }

    // Check if temporary furniture
    if (item.is_temporary) {
        group.classList.add('temporary');
        group.setAttribute('data-temp-start', item.temp_start_date || '');
        group.setAttribute('data-temp-end', item.temp_end_date || '');
        // Use sky blue fill for available temp furniture (not reserved, not blocked)
        if (isAvailable && !blockInfo) {
            fillColor = '#E0F2FE';
            strokeColor = '#0EA5E9';
        }
    }

    // Check if selected (selection overrides blocked visual for highlighting)
    if (selectedFurniture.has(item.id)) {
        fillColor = colors.selectedFill;
        strokeColor = colors.selectedStroke;
        group.setAttribute('filter', 'url(#selected-glow)');
    }

    // Create shape
    const width = item.width || typeConfig.default_width || 60;
    const height = item.height || typeConfig.default_height || 40;
    const shape = createShape(typeConfig.map_shape || 'rounded_rect', width, height, fillColor, strokeColor);
    group.appendChild(shape);

    // Add stripes overlay for blocked furniture
    if (blockInfo && !selectedFurniture.has(item.id)) {
        const stripesOverlay = document.createElementNS(SVG_NS, 'rect');
        stripesOverlay.setAttribute('x', '2');
        stripesOverlay.setAttribute('y', '2');
        stripesOverlay.setAttribute('width', width - 4);
        stripesOverlay.setAttribute('height', height - 4);
        stripesOverlay.setAttribute('fill', 'url(#blocked-stripes)');
        stripesOverlay.setAttribute('rx', '5');
        stripesOverlay.setAttribute('ry', '5');
        stripesOverlay.setAttribute('pointer-events', 'none');
        group.appendChild(stripesOverlay);
    }

    // Add labels
    if (blockInfo) {
        // Blocked furniture: show icon + furniture number
        const blockIcons = {
            'maintenance': '🔧',
            'vip_hold': '⭐',
            'event': '📅',
            'other': '🚫'
        };
        const icon = blockIcons[blockInfo.block_type] || '🚫';

        const iconLabel = document.createElementNS(SVG_NS, 'text');
        iconLabel.setAttribute('x', width / 2);
        iconLabel.setAttribute('y', height / 2 - 4);
        iconLabel.setAttribute('text-anchor', 'middle');
        iconLabel.setAttribute('dominant-baseline', 'middle');
        iconLabel.setAttribute('font-size', '12');
        iconLabel.setAttribute('pointer-events', 'none');
        iconLabel.textContent = icon;
        group.appendChild(iconLabel);

        const numberLabel = document.createElementNS(SVG_NS, 'text');
        numberLabel.setAttribute('x', width / 2);
        numberLabel.setAttribute('y', height / 2 + 10);
        numberLabel.setAttribute('text-anchor', 'middle');
        numberLabel.setAttribute('dominant-baseline', 'middle');
        numberLabel.setAttribute('fill', getContrastColor(fillColor, colors));
        numberLabel.setAttribute('font-size', '9');
        numberLabel.setAttribute('font-weight', '600');
        numberLabel.setAttribute('pointer-events', 'none');
        numberLabel.textContent = item.number;
        group.appendChild(numberLabel);
    } else if (!isAvailable && availability) {
        const customerLabel = tooltipManager.getCustomerLabel(availability);

        const primaryLabel = document.createElementNS(SVG_NS, 'text');
        primaryLabel.setAttribute('x', width / 2);
        primaryLabel.setAttribute('y', height / 2 - 4);
        primaryLabel.setAttribute('text-anchor', 'middle');
        primaryLabel.setAttribute('dominant-baseline', 'middle');
        primaryLabel.setAttribute('fill', getContrastColor(fillColor, colors));
        primaryLabel.setAttribute('font-size', '11');
        primaryLabel.setAttribute('font-weight', '600');
        primaryLabel.setAttribute('pointer-events', 'none');
        primaryLabel.textContent = customerLabel;
        group.appendChild(primaryLabel);

        const secondaryLabel = document.createElementNS(SVG_NS, 'text');
        secondaryLabel.setAttribute('x', width / 2);
        secondaryLabel.setAttribute('y', height / 2 + 8);
        secondaryLabel.setAttribute('text-anchor', 'middle');
        secondaryLabel.setAttribute('dominant-baseline', 'middle');
        secondaryLabel.setAttribute('fill', getContrastColor(fillColor, colors));
        secondaryLabel.setAttribute('font-size', '8');
        secondaryLabel.setAttribute('font-weight', '400');
        secondaryLabel.setAttribute('pointer-events', 'none');
        secondaryLabel.setAttribute('opacity', '0.8');
        secondaryLabel.textContent = item.number;
        group.appendChild(secondaryLabel);
    } else {
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('x', width / 2);
        label.setAttribute('y', height / 2);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('dominant-baseline', 'middle');
        label.setAttribute('fill', getContrastColor(fillColor, colors));
        label.setAttribute('font-size', '12');
        label.setAttribute('font-weight', '600');
        label.setAttribute('pointer-events', 'none');
        label.textContent = item.number;
        group.appendChild(label);
    }

    // Event listeners
    group.addEventListener('click', (e) => onFurnitureClick(e, item));

    // Right-click context menu
    if (onFurnitureContextMenu) {
        group.addEventListener('contextmenu', (e) => onFurnitureContextMenu(e, item));
    }

    // Hover handlers for tooltip
    if (blockInfo) {
        // Show block info on hover
        group.addEventListener('mouseenter', (e) => tooltipManager.showBlock(e, blockInfo, item.number));
        group.addEventListener('mouseleave', () => tooltipManager.hide());
        group.addEventListener('mousemove', (e) => tooltipManager.move(e));
    } else if (!isAvailable && availability && availability.customer_name) {
        group.addEventListener('mouseenter', (e) => tooltipManager.show(e, availability));
        group.addEventListener('mouseleave', () => tooltipManager.hide());
        group.addEventListener('mousemove', (e) => tooltipManager.move(e));
    }

    return group;
}

/**
 * Create an SVG shape element
 * @param {string} shapeType - Shape type (circle, ellipse, rectangle, rounded_rect)
 * @param {number} width - Shape width
 * @param {number} height - Shape height
 * @param {string} fillColor - Fill color or pattern URL
 * @param {string} strokeColor - Stroke color
 * @returns {SVGElement} Shape element
 */
export function createShape(shapeType, width, height, fillColor, strokeColor) {
    const strokeWidth = 2;
    let shape;

    switch (shapeType) {
        case 'circle':
            shape = document.createElementNS(SVG_NS, 'circle');
            const radius = Math.min(width, height) / 2 - strokeWidth;
            shape.setAttribute('cx', width / 2);
            shape.setAttribute('cy', height / 2);
            shape.setAttribute('r', radius);
            break;

        case 'ellipse':
            shape = document.createElementNS(SVG_NS, 'ellipse');
            shape.setAttribute('cx', width / 2);
            shape.setAttribute('cy', height / 2);
            shape.setAttribute('rx', width / 2 - strokeWidth);
            shape.setAttribute('ry', height / 2 - strokeWidth);
            break;

        case 'rectangle':
        case 'rounded_rect':
        default:
            shape = document.createElementNS(SVG_NS, 'rect');
            shape.setAttribute('x', strokeWidth);
            shape.setAttribute('y', strokeWidth);
            shape.setAttribute('width', width - 2 * strokeWidth);
            shape.setAttribute('height', height - 2 * strokeWidth);
            if (shapeType === 'rounded_rect') {
                shape.setAttribute('rx', '5');
                shape.setAttribute('ry', '5');
            }
            break;
    }

    shape.setAttribute('fill', fillColor);
    shape.setAttribute('stroke', strokeColor);
    shape.setAttribute('stroke-width', strokeWidth);

    return shape;
}

/**
 * Get or create a pool pattern for a specific item
 * @param {SVGSVGElement} svg - Main SVG element
 * @param {number} itemId - Furniture item ID
 * @param {string} fillColor - Primary pool color
 * @param {string} strokeColor - Secondary pool color
 * @returns {string} Pattern URL reference
 */
export function getPoolPattern(svg, itemId, fillColor, strokeColor) {
    const patternId = `pool-pattern-${itemId}`;

    let pattern = svg.querySelector(`#${patternId}`);
    if (!pattern) {
        const defs = svg.querySelector('defs');
        pattern = document.createElementNS(SVG_NS, 'pattern');
        pattern.setAttribute('id', patternId);
        pattern.setAttribute('patternUnits', 'userSpaceOnUse');
        pattern.setAttribute('width', '10');
        pattern.setAttribute('height', '10');
        pattern.innerHTML = `
            <rect width="10" height="10" fill="${fillColor}"/>
            <rect x="0" y="0" width="5" height="5" fill="${strokeColor}" opacity="0.3"/>
            <rect x="5" y="5" width="5" height="5" fill="${strokeColor}" opacity="0.3"/>
        `;
        defs.appendChild(pattern);
    }
    return `url(#${patternId})`;
}

/**
 * Update the legend with state colors
 * @param {Object} data - Map data with states
 * @param {Object} colors - Color configuration
 */
export function updateLegend(data, colors) {
    const legend = document.getElementById('map-legend');
    if (!legend || !data.states) return;

    let html = '<div class="legend-items d-flex flex-wrap gap-2">';

    // Available state
    html += `
        <div class="legend-item d-flex align-items-center">
            <span class="legend-color" style="background-color: ${colors.availableFill}; border: 2px solid ${colors.availableStroke};"></span>
            <span class="ms-1">Disponible</span>
        </div>
    `;

    // State colors from database
    data.states.forEach(state => {
        if (state.active) {
            html += `
                <div class="legend-item d-flex align-items-center">
                    <span class="legend-color" style="background-color: ${state.color};"></span>
                    <span class="ms-1">${state.name}</span>
                </div>
            `;
        }
    });

    html += '</div>';
    legend.innerHTML = html;
}
