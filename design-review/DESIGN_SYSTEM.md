# Beach Club Design System

> Complete visual design specification for the Beach Club Management System.
> Luxury beach club aesthetic with professional hospitality UX.

---

## Brand Identity

### Concept
**Luxury Mediterranean Beach Club** - Elegant, warm, and professional. The design evokes sandy beaches, golden sunsets, and premium hospitality service.

### Design Principles
1. **Clarity First** - Information hierarchy that staff can scan in seconds
2. **Warm Professionalism** - Luxury feel without being cold or corporate
3. **Action-Oriented** - Clear CTAs, obvious next steps
4. **Responsive** - Works on reception desk monitors and handheld tablets
5. **Accessible** - WCAG 2.1 AA compliant, readable in bright environments

---

## Color Palette

### Primary Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Sand Gold** | `#D4AF37` | 212, 175, 55 | Primary brand, CTAs, highlights |
| **Deep Ocean** | `#1A3A5C` | 26, 58, 92 | Headers, primary text, navigation |
| **Warm Sand** | `#F5E6D3` | 245, 230, 211 | Backgrounds, cards, available state |

### Secondary Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Sunset Coral** | `#E07B54` | 224, 123, 84 | Warnings, attention items |
| **Sea Foam** | `#7FB5B5` | 127, 181, 181 | Secondary actions, info states |
| **Driftwood** | `#8B7355` | 139, 115, 85 | Borders, subtle elements |

### Functional Colors

| Name | Hex | Usage |
|------|-----|-------|
| **Success Green** | `#4A7C59` | Confirmations, completed states |
| **Error Red** | `#C1444F` | Errors, cancellations, alerts |
| **Warning Amber** | `#E5A33D` | Warnings, pending actions |
| **Info Blue** | `#4A90A4` | Information, help text |

### Neutral Colors

| Name | Hex | Usage |
|------|-----|-------|
| **White** | `#FFFFFF` | Card backgrounds, modals |
| **Off White** | `#FAFAFA` | Page backgrounds |
| **Light Gray** | `#E8E8E8` | Borders, dividers |
| **Medium Gray** | `#9CA3AF` | Placeholder text, disabled |
| **Dark Gray** | `#4B5563` | Secondary text |
| **Near Black** | `#1F2937` | Primary text |

### State Colors (Reservations)

| State | Background | Border | Text |
|-------|------------|--------|------|
| Pendiente | `#FEF3C7` | `#F59E0B` | `#92400E` |
| Confirmada | `#DBEAFE` | `#3B82F6` | `#1E40AF` |
| Check-in | `#D1FAE5` | `#10B981` | `#065F46` |
| Activa | `#DCFCE7` | `#22C55E` | `#166534` |
| Completada | `#F3F4F6` | `#9CA3AF` | `#4B5563` |
| Cancelada | `#FEE2E2` | `#EF4444` | `#991B1B` |
| No-Show | `#FCE7F3` | `#EC4899` | `#9D174D` |

### Map Colors (Furniture States)

| State | Fill | Stroke | Opacity |
|-------|------|--------|---------|
| Available | `#F5E6D3` | `#D4AF37` | 100% |
| Occupied | `#90EE90` | `#228B22` | 100% |
| Selected | `#D4AF37` | `#8B6914` | 100% |
| Maintenance | `#9CA3AF` | `#6B7280` | 70% |
| Temporary | `#E0F2FE` | `#0EA5E9` | 100% |

---

## Typography

### Font Stack

```css
/* Primary Font - Headers & UI */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Alternative for Spanish Characters */
font-family: 'Source Sans Pro', 'Inter', sans-serif;
```

### Type Scale

| Name | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Display | 36px | 700 | 1.2 | Page titles |
| H1 | 28px | 600 | 1.3 | Section headers |
| H2 | 24px | 600 | 1.3 | Card titles |
| H3 | 20px | 600 | 1.4 | Subsections |
| H4 | 18px | 500 | 1.4 | Widget titles |
| Body Large | 16px | 400 | 1.5 | Primary content |
| Body | 14px | 400 | 1.5 | Default text |
| Body Small | 13px | 400 | 1.5 | Secondary info |
| Caption | 12px | 400 | 1.4 | Labels, hints |
| Micro | 11px | 500 | 1.3 | Badges, tags |

### Font Weights
- **Regular (400):** Body text, descriptions
- **Medium (500):** Labels, table headers
- **Semibold (600):** Headings, buttons
- **Bold (700):** Display, emphasis

---

## Spacing System

### Base Unit: 4px

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight spacing, icon gaps |
| `space-2` | 8px | Related elements |
| `space-3` | 12px | Form field gaps |
| `space-4` | 16px | Card padding, section gaps |
| `space-5` | 20px | Component separation |
| `space-6` | 24px | Section padding |
| `space-8` | 32px | Major sections |
| `space-10` | 40px | Page sections |
| `space-12` | 48px | Hero spacing |

### Layout Grid
- **Max Width:** 1440px
- **Columns:** 12
- **Gutter:** 24px
- **Margin:** 32px (desktop), 16px (mobile)

---

## Components

### Buttons

#### Primary Button
```css
.btn-primary {
    background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%);
    color: #FFFFFF;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    border: none;
    box-shadow: 0 2px 4px rgba(212, 175, 55, 0.3);
    transition: all 0.2s ease;
}
.btn-primary:hover {
    background: linear-gradient(135deg, #E5C04A 0%, #C9A71D 100%);
    box-shadow: 0 4px 8px rgba(212, 175, 55, 0.4);
    transform: translateY(-1px);
}
```

#### Secondary Button
```css
.btn-secondary {
    background: #FFFFFF;
    color: #1A3A5C;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
    border: 2px solid #D4AF37;
    transition: all 0.2s ease;
}
.btn-secondary:hover {
    background: #FDF8E8;
    border-color: #B8960C;
}
```

#### Danger Button
```css
.btn-danger {
    background: #C1444F;
    color: #FFFFFF;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    border: none;
}
.btn-danger:hover {
    background: #A93842;
}
```

#### Button Sizes
- **Small:** padding: 8px 16px; font-size: 13px;
- **Medium:** padding: 12px 24px; font-size: 14px;
- **Large:** padding: 16px 32px; font-size: 16px;

### Cards

```css
.card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08),
                0 4px 12px rgba(0, 0, 0, 0.05);
    border: 1px solid #E8E8E8;
}
.card-header {
    border-bottom: 1px solid #E8E8E8;
    padding-bottom: 16px;
    margin-bottom: 16px;
}
.card-title {
    font-size: 18px;
    font-weight: 600;
    color: #1A3A5C;
}
```

### Form Inputs

```css
.form-input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #E8E8E8;
    border-radius: 8px;
    font-size: 14px;
    color: #1F2937;
    background: #FFFFFF;
    transition: all 0.2s ease;
}
.form-input:focus {
    border-color: #D4AF37;
    outline: none;
    box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.15);
}
.form-input::placeholder {
    color: #9CA3AF;
}
.form-input.error {
    border-color: #C1444F;
}
.form-label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: #4B5563;
    margin-bottom: 6px;
}
```

### Select Dropdown

```css
.form-select {
    appearance: none;
    background-image: url("data:image/svg+xml,..."); /* chevron icon */
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 40px;
}
```

### Tables

```css
.table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
}
.table th {
    background: #F5E6D3;
    color: #1A3A5C;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 16px;
    text-align: left;
    border-bottom: 2px solid #D4AF37;
}
.table td {
    padding: 14px 16px;
    border-bottom: 1px solid #E8E8E8;
    font-size: 14px;
    color: #1F2937;
}
.table tr:hover {
    background: #FAFAFA;
}
```

### Badges & Tags

```css
.badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
}
.badge-gold {
    background: #FEF3C7;
    color: #92400E;
}
.badge-success {
    background: #D1FAE5;
    color: #065F46;
}
.badge-danger {
    background: #FEE2E2;
    color: #991B1B;
}
.badge-info {
    background: #DBEAFE;
    color: #1E40AF;
}
```

### Modals

```css
.modal-overlay {
    background: rgba(26, 58, 92, 0.6);
    backdrop-filter: blur(4px);
}
.modal {
    background: #FFFFFF;
    border-radius: 16px;
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow: hidden;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}
.modal-header {
    background: linear-gradient(135deg, #1A3A5C 0%, #2A4A6C 100%);
    color: #FFFFFF;
    padding: 20px 24px;
}
.modal-body {
    padding: 24px;
    overflow-y: auto;
}
.modal-footer {
    background: #FAFAFA;
    padding: 16px 24px;
    border-top: 1px solid #E8E8E8;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
}
```

### Toast Notifications

```css
.toast {
    padding: 16px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    gap: 12px;
    max-width: 400px;
}
.toast-success {
    background: #D1FAE5;
    border-left: 4px solid #10B981;
    color: #065F46;
}
.toast-error {
    background: #FEE2E2;
    border-left: 4px solid #EF4444;
    color: #991B1B;
}
.toast-warning {
    background: #FEF3C7;
    border-left: 4px solid #F59E0B;
    color: #92400E;
}
.toast-info {
    background: #DBEAFE;
    border-left: 4px solid #3B82F6;
    color: #1E40AF;
}
```

---

## Navigation

### Sidebar

```css
.sidebar {
    width: 260px;
    background: linear-gradient(180deg, #1A3A5C 0%, #0F2744 100%);
    color: #FFFFFF;
    min-height: 100vh;
}
.sidebar-logo {
    padding: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.sidebar-logo img {
    height: 40px;
}
.sidebar-nav {
    padding: 16px 0;
}
.nav-item {
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
}
.nav-item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #FFFFFF;
}
.nav-item.active {
    background: rgba(212, 175, 55, 0.15);
    color: #D4AF37;
    border-left-color: #D4AF37;
}
.nav-item i {
    width: 20px;
    text-align: center;
}
.nav-section-title {
    padding: 16px 24px 8px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255, 255, 255, 0.4);
}
```

### Top Bar

```css
.topbar {
    height: 64px;
    background: #FFFFFF;
    border-bottom: 1px solid #E8E8E8;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
}
.topbar-title {
    font-size: 20px;
    font-weight: 600;
    color: #1A3A5C;
}
.topbar-actions {
    display: flex;
    align-items: center;
    gap: 16px;
}
.user-menu {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
}
.user-menu:hover {
    background: #F5E6D3;
}
.user-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #D4AF37;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
}
```

---

## Beach Map Specific

### Furniture Elements

```css
/* Hamaca (Lounger) */
.furniture-hamaca {
    width: 60px;
    height: 30px;
    rx: 4px;
}

/* Balinesa (Day Bed) */
.furniture-balinesa {
    width: 80px;
    height: 80px;
    rx: 8px;
}

/* Sombrilla (Umbrella) */
.furniture-sombrilla {
    r: 25px; /* circle */
}

/* Furniture Number Label */
.furniture-label {
    font-size: 12px;
    font-weight: 600;
    fill: #1A3A5C;
    text-anchor: middle;
    dominant-baseline: middle;
}

/* Selection Indicator */
.furniture-selected {
    stroke: #D4AF37;
    stroke-width: 3px;
    filter: drop-shadow(0 0 8px rgba(212, 175, 55, 0.5));
}
```

### Zone Rendering

```css
.zone {
    fill: rgba(245, 230, 211, 0.3);
    stroke: #D4AF37;
    stroke-width: 2px;
    stroke-dasharray: 8 4;
}
.zone-label {
    font-size: 14px;
    font-weight: 600;
    fill: #1A3A5C;
    text-transform: uppercase;
    letter-spacing: 1px;
}
```

### Map Controls

```css
.map-controls {
    position: absolute;
    top: 16px;
    right: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.map-control-btn {
    width: 40px;
    height: 40px;
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
}
.map-control-btn:hover {
    background: #F5E6D3;
    border-color: #D4AF37;
}
```

### Date Navigator

```css
.date-navigator {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #FFFFFF;
    padding: 12px 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.date-nav-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #F5E6D3;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}
.date-nav-btn:hover {
    background: #D4AF37;
    color: #FFFFFF;
}
.date-display {
    font-size: 18px;
    font-weight: 600;
    color: #1A3A5C;
    min-width: 200px;
    text-align: center;
}
.date-today-badge {
    background: #D4AF37;
    color: #FFFFFF;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 8px;
}
```

---

## Dashboard Widgets

### Stats Card

```css
.stats-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #E8E8E8;
}
.stats-card-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    margin-bottom: 12px;
}
.stats-card-icon.gold {
    background: #FEF3C7;
    color: #D4AF37;
}
.stats-card-icon.blue {
    background: #DBEAFE;
    color: #3B82F6;
}
.stats-card-icon.green {
    background: #D1FAE5;
    color: #10B981;
}
.stats-card-value {
    font-size: 32px;
    font-weight: 700;
    color: #1A3A5C;
    line-height: 1;
}
.stats-card-label {
    font-size: 14px;
    color: #6B7280;
    margin-top: 4px;
}
.stats-card-trend {
    font-size: 13px;
    margin-top: 8px;
}
.stats-card-trend.up {
    color: #10B981;
}
.stats-card-trend.down {
    color: #EF4444;
}
```

### Quick Actions

```css
.quick-actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
}
.quick-action-btn {
    background: #FFFFFF;
    border: 2px solid #E8E8E8;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
}
.quick-action-btn:hover {
    border-color: #D4AF37;
    background: #FDF8E8;
    transform: translateY(-2px);
}
.quick-action-icon {
    font-size: 24px;
    color: #D4AF37;
    margin-bottom: 8px;
}
.quick-action-label {
    font-size: 14px;
    font-weight: 500;
    color: #1A3A5C;
}
```

---

## Responsive Breakpoints

```css
/* Mobile First */
/* Small phones */
@media (min-width: 320px) { }

/* Large phones */
@media (min-width: 480px) { }

/* Tablets */
@media (min-width: 768px) { }

/* Laptops */
@media (min-width: 1024px) { }

/* Desktops */
@media (min-width: 1280px) { }

/* Large screens */
@media (min-width: 1440px) { }
```

### Mobile Adaptations
- Sidebar becomes bottom navigation or hamburger menu
- Tables become cards on mobile
- Modal becomes full-screen on mobile
- Touch-friendly tap targets (min 44px)

---

## Icons

### Icon Library
Use **Font Awesome 6** (Free) for consistency.

### Common Icons

| Action | Icon | Class |
|--------|------|-------|
| Add/Create | Plus | `fa-plus` |
| Edit | Pencil | `fa-pen` |
| Delete | Trash | `fa-trash` |
| View | Eye | `fa-eye` |
| Search | Magnifying glass | `fa-magnifying-glass` |
| Filter | Filter | `fa-filter` |
| Export | Download | `fa-download` |
| Import | Upload | `fa-upload` |
| Settings | Gear | `fa-gear` |
| User | User | `fa-user` |
| Calendar | Calendar | `fa-calendar` |
| Map | Map | `fa-map` |
| Reservation | Calendar check | `fa-calendar-check` |
| Customer | Users | `fa-users` |
| Furniture | Umbrella beach | `fa-umbrella-beach` |
| Zone | Layer group | `fa-layer-group` |
| Reports | Chart | `fa-chart-bar` |
| Hotel | Hotel | `fa-hotel` |
| Check | Check | `fa-check` |
| Close | Xmark | `fa-xmark` |
| Warning | Triangle exclamation | `fa-triangle-exclamation` |
| Info | Circle info | `fa-circle-info` |
| Success | Circle check | `fa-circle-check` |

---

## Animation & Transitions

### Standard Transitions

```css
/* Quick interactions */
transition: all 0.15s ease;

/* Normal transitions */
transition: all 0.2s ease;

/* Smooth transitions */
transition: all 0.3s ease;

/* Emphasis */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

### Hover Effects

```css
/* Lift effect */
.hover-lift:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Scale effect */
.hover-scale:hover {
    transform: scale(1.02);
}

/* Glow effect (gold) */
.hover-glow:hover {
    box-shadow: 0 0 20px rgba(212, 175, 55, 0.3);
}
```

### Loading States

```css
/* Skeleton loading */
.skeleton {
    background: linear-gradient(90deg, #E8E8E8 25%, #F5F5F5 50%, #E8E8E8 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
}
@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Spinner */
.spinner {
    width: 24px;
    height: 24px;
    border: 3px solid #E8E8E8;
    border-top-color: #D4AF37;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}
```

---

## CSS Variables (Root)

```css
:root {
    /* Colors */
    --color-primary: #D4AF37;
    --color-primary-dark: #B8960C;
    --color-primary-light: #E5C04A;
    --color-secondary: #1A3A5C;
    --color-accent: #F5E6D3;

    --color-success: #4A7C59;
    --color-error: #C1444F;
    --color-warning: #E5A33D;
    --color-info: #4A90A4;

    --color-text: #1F2937;
    --color-text-secondary: #4B5563;
    --color-text-muted: #9CA3AF;

    --color-background: #FAFAFA;
    --color-surface: #FFFFFF;
    --color-border: #E8E8E8;

    /* Typography */
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-size-base: 14px;
    --line-height-base: 1.5;

    /* Spacing */
    --space-unit: 4px;
    --space-1: calc(var(--space-unit) * 1);
    --space-2: calc(var(--space-unit) * 2);
    --space-3: calc(var(--space-unit) * 3);
    --space-4: calc(var(--space-unit) * 4);
    --space-6: calc(var(--space-unit) * 6);
    --space-8: calc(var(--space-unit) * 8);

    /* Borders */
    --border-radius-sm: 4px;
    --border-radius-md: 8px;
    --border-radius-lg: 12px;
    --border-radius-xl: 16px;
    --border-radius-full: 9999px;

    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
    --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15);

    /* Transitions */
    --transition-fast: 0.15s ease;
    --transition-normal: 0.2s ease;
    --transition-slow: 0.3s ease;

    /* Z-index */
    --z-dropdown: 100;
    --z-sticky: 200;
    --z-modal-backdrop: 300;
    --z-modal: 400;
    --z-toast: 500;
    --z-tooltip: 600;
}
```

---

## Implementation Notes

### Bootstrap 5 Integration
This design system is meant to work **with** Bootstrap 5, not replace it. Override Bootstrap's variables:

```scss
// _variables.scss
$primary: #D4AF37;
$secondary: #1A3A5C;
$success: #4A7C59;
$danger: #C1444F;
$warning: #E5A33D;
$info: #4A90A4;

$body-bg: #FAFAFA;
$body-color: #1F2937;

$font-family-base: 'Inter', sans-serif;
$font-size-base: 0.875rem;

$border-radius: 0.5rem;
$border-radius-lg: 0.75rem;

$box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
$box-shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
```

### File Organization

```
static/
├── css/
│   ├── variables.css       # CSS custom properties
│   ├── base.css            # Reset, typography, utilities
│   ├── components/
│   │   ├── buttons.css
│   │   ├── cards.css
│   │   ├── forms.css
│   │   ├── tables.css
│   │   ├── modals.css
│   │   └── navigation.css
│   ├── pages/
│   │   ├── dashboard.css
│   │   ├── map.css
│   │   ├── reservations.css
│   │   └── customers.css
│   └── main.css            # Import all
```

---

## Quick Reference: Color Codes

```
Primary Gold:     #D4AF37
Deep Ocean:       #1A3A5C
Warm Sand:        #F5E6D3
Success:          #4A7C59
Error:            #C1444F
Warning:          #E5A33D
Text Primary:     #1F2937
Text Secondary:   #4B5563
Border:           #E8E8E8
Background:       #FAFAFA
```
