/**
 * Map Editor - Main Entry Point
 * Composes all mixins into the final MapEditor class
 *
 * Beach Map Editor Controller
 * Architectural-style visual editor for designing beach map layout
 */

import { MapEditorBase } from './editor-core.js';
import { ViewportMixin } from './viewport.js';
import { CanvasMixin } from './canvas.js';
import { FurnitureRendererMixin } from './furniture-renderer.js';
import { SelectionMixin } from './selection.js';
import { MarqueeMixin } from './marquee.js';
import { OperationsMixin } from './operations.js';
import { DragDropMixin } from './drag-drop.js';
import { PersistenceMixin } from './persistence.js';

/**
 * Compose all mixins into the final MapEditor class
 * Order matters: each mixin may depend on methods from previous mixins
 */
const MapEditor = PersistenceMixin(
    DragDropMixin(
        OperationsMixin(
            MarqueeMixin(
                SelectionMixin(
                    FurnitureRendererMixin(
                        CanvasMixin(
                            ViewportMixin(
                                MapEditorBase
                            )
                        )
                    )
                )
            )
        )
    )
);

// Export for ES modules
export { MapEditor };

// Also expose on window for legacy compatibility (non-module scripts)
window.MapEditor = MapEditor;
