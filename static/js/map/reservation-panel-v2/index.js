/**
 * ReservationPanel - Main Entry Point
 * Composes all mixins into the final ReservationPanel class
 */

import { ReservationPanelBase } from './panel-base.js';
import { PanelLifecycleMixin } from './panel-lifecycle.js';
import { EditModeMixin } from './edit-mode-mixin.js';
import { CustomerMixin } from './customer-mixin.js';
import { PreferencesMixin } from './preferences-mixin.js';
import { StateMixin } from './state-mixin.js';
import { FurnitureMixin } from './furniture-mixin.js';
import { PricingMixin } from './pricing-mixin.js';
import { DetailsMixin } from './details-mixin.js';
import { SaveMixin } from './save-mixin.js';

/**
 * Compose all mixins into the final ReservationPanel class
 * Order matters: each mixin may depend on methods from previous mixins
 */
const ReservationPanel = SaveMixin(
    DetailsMixin(
        PricingMixin(
            FurnitureMixin(
                StateMixin(
                    PreferencesMixin(
                        CustomerMixin(
                            EditModeMixin(
                                PanelLifecycleMixin(
                                    ReservationPanelBase
                                )
                            )
                        )
                    )
                )
            )
        )
    )
);

// Export for ES modules
export { ReservationPanel };

// Also expose on window for legacy compatibility
window.ReservationPanel = ReservationPanel;
