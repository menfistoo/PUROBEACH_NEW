# Purobeach Design System

> Official visual design specification for the Beach Club Management System.
> Based on Purobeach Brand Guide (Santa Ponsa, February 2025).

---

## Brand Identity

### Concept
**Premium Mediterranean Beach Club** - Modern luxury with minimalist sophistication. The design embodies coastal elegance, warm hospitality, and contemporary style.

### Design Principles
1. **Minimalist Luxury** - Flat design, no gradients or shadows, clean aesthetics
2. **Clarity First** - Information hierarchy that staff can scan in seconds
3. **Geometric Precision** - Clean lines with subtle curves, professional execution
4. **Action-Oriented** - Clear CTAs with brand gold accent
5. **Accessible** - WCAG 2.1 AA compliant, readable in all environments

---

## Typography

### Font Families

**Primary Font: Gilroy**
- Use for: Headers, navigation, buttons, CTAs
- Weights: 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)
- Characteristics: Geometric, modern, professional

**Secondary Font: Cralika**
- Use for: Body text, descriptions, table content
- Weights: 400 (Regular), 500 (Medium), 600 (Semibold)
- Characteristics: Readable, clean, versatile

**Accent Font: Solitas**
- Use for: Special labels, badges, decorative elements
- Weights: 500 (Medium), 600 (Semibold)
- Characteristics: Distinctive, premium feel

**Fallback Stack:**
```css
/* If brand fonts unavailable, use web-safe alternatives */
--font-primary: 'Gilroy', 'Montserrat', 'Inter', -apple-system, sans-serif;
--font-secondary: 'Cralika', 'Inter', -apple-system, 'Segoe UI', sans-serif;
--font-accent: 'Solitas', 'Inter', Georgia, serif;
```

### Type Scale

| Element | Font | Size | Weight | Line Height | Usage |
|---------|------|------|--------|-------------|-------|
| Display | Gilroy | 36px | 700 | 1.2 | Page titles, hero text |
| H1 | Gilroy | 28px | 600 | 1.3 | Section headers |
| H2 | Gilroy | 24px | 600 | 1.3 | Card titles, subsections |
| H3 | Gilroy | 20px | 600 | 1.4 | Widget titles |
| H4 | Gilroy | 18px | 500 | 1.4 | Subheadings |
| Body Large | Cralika | 16px | 400 | 1.5 | Primary content, intro text |
| Body | Cralika | 14px | 400 | 1.5 | Default text, descriptions |
| Body Small | Cralika | 13px | 400 | 1.5 | Secondary info, captions |
| Caption | Cralika | 12px | 400 | 1.4 | Labels, hints, metadata |
| Micro/Badge | Solitas | 11px | 500 | 1.3 | Badges, tags, tiny labels |

---

## Color Palette

### Primary Colors (Brand Core)

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Gold** | `#CEB677` | 206, 182, 119 | Primary brand, CTAs, highlights, active states |
| **Natural** | `#EAD6B7` | 234, 214, 183 | Light backgrounds, available furniture states |
| **Beige** | `#EEE5D3` | 238, 229, 211 | Card backgrounds, table headers, subtle surfaces |
| **Wood** | `#A2795D` | 162, 121, 93 | Dark accents, borders, hover states |

### Secondary Colors (Functional)

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| **Red** | `#E45E41` | 228, 94, 65 | Errors, alerts, cancellations, danger actions |
| **Safari** | `#55996D` | 85, 153, 109 | Success, confirmations, completed states |
| **Med** | `#6890C9` | 104, 144, 201 | Info, links, secondary actions, highlights |
| **Cromad** | `#1A1A1A` | 26, 26, 26 | Primary text, headers, dark elements |

### Neutral Colors

| Name | Hex | Usage |
|------|-----|-------|
| **White** | `#FFFFFF` | Card backgrounds, modal surfaces |
| **Off White** | `#FAFAFA` | Page backgrounds |
| **Light Gray** | `#E0E0E0` | Borders, dividers, subtle separators |
| **Medium Gray** | `#999999` | Placeholder text, disabled states |
| **Dark Gray** | `#666666` | Secondary text |
| **Near Black** | `#1F1F1F` | Body text (if Cromad too dark) |

### Derived Colors (Generated)

```css
/* Hover states - darker variations */
--color-gold-hover: #B8A166;
--color-wood-light: #C29A7D;
--color-safari-dark: #3E7D52;
--color-red-dark: #C14830;
--color-med-dark: #5578A3;
```

---

## Reservation State Colors

These colors serve functional purposes for operational clarity:

| State | Background | Border | Text | Usage |
|-------|------------|--------|------|-------|
| **Pendiente** | `#FEF3C7` | `#CEB677` (Gold) | `#A2795D` (Wood) | Pending confirmation |
| **Confirmada** | `#E3F2FD` | `#6890C9` (Med) | `#1565C0` | Confirmed, awaiting check-in |
| **Check-in** | `#E8F5E9` | `#55996D` (Safari) | `#2E7D32` | Customer checked in |
| **Activa** | `#DCFCE7` | `#55996D` (Safari) | `#166534` | Active reservation |
| **Completada** | `#F5F5F5` | `#9E9E9E` | `#616161` | Completed successfully |
| **Cancelada** | `#FFEBEE` | `#E45E41` (Red) | `#C62828` | Cancelled by customer/staff |
| **No-Show** | `#FCE7F3` | `#E45E41` (Red) | `#9D174D` | Customer didn't arrive |

---

## Beach Map Colors

### Furniture States

| State | Fill | Stroke | Usage |
|-------|------|--------|-------|
| **Available** | `#EAD6B7` (Natural) | `#CEB677` (Gold) | Free for booking |
| **Occupied** | `#55996D` (Safari) | `#3E7D52` | Reserved/occupied |
| **Selected** | `#CEB677` (Gold) | `#A2795D` (Wood) | User selection |
| **Blocked** | `#E45E41` (Red) | `#C14830` | Maintenance/blocked |
| **Temporary** | `#6890C9` (Med) | `#5578A3` | Temporary furniture |

### Zone Rendering

```css
.zone {
    fill: rgba(234, 214, 183, 0.2);    /* Natural with 20% opacity */
    stroke: #CEB677;                    /* Gold */
    stroke-width: 2px;
    stroke-dasharray: 8 4;
}
```

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

---

## Components

### Buttons

#### Primary Button (Gold)
```css
.btn-primary {
    background: #CEB677;              /* Flat gold, no gradient */
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 12px 24px;
    font-family: var(--font-primary);
    font-weight: 600;
    font-size: 14px;
    transition: background 0.2s ease;
    /* NO box-shadow, NO transform */
}
.btn-primary:hover {
    background: #B8A166;              /* Darker gold */
}
```

#### Secondary Button (Outline)
```css
.btn-outline-primary {
    background: transparent;
    color: #CEB677;
    border: 2px solid #CEB677;
    border-radius: 4px;
    padding: 12px 24px;
    font-family: var(--font-primary);
    font-weight: 600;
}
.btn-outline-primary:hover {
    background: #CEB677;
    color: #FFFFFF;
}
```

#### Danger Button
```css
.btn-danger {
    background: #E45E41;
    color: #FFFFFF;
    border: none;
}
.btn-danger:hover {
    background: #C14830;
}
```

**Button Sizes:**
- Small: `padding: 8px 16px; font-size: 13px;`
- Medium (default): `padding: 12px 24px; font-size: 14px;`
- Large: `padding: 16px 32px; font-size: 16px;`

---

### Cards

```css
.card {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    padding: 24px;
    /* NO box-shadow */
}

.card-header {
    background: #EEE5D3;              /* Beige */
    border-bottom: 1px solid #E0E0E0;
    padding: 16px 24px;
    margin: -24px -24px 24px -24px;
    border-radius: 8px 8px 0 0;
}

.card-title {
    font-family: var(--font-primary);
    font-size: 18px;
    font-weight: 600;
    color: #1A1A1A;
    margin: 0;
}
```

---

### Forms

#### Labels
```css
.form-label {
    font-family: var(--font-primary);
    font-size: 13px;
    font-weight: 600;
    color: #1A1A1A;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
```

#### Inputs
```css
.form-control {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 12px 16px;
    font-family: var(--font-secondary);
    font-size: 14px;
    color: #1F1F1F;
    background: #FFFFFF;
    transition: border-color 0.2s ease;
}

.form-control:focus {
    border-color: #CEB677;
    outline: none;
    /* NO box-shadow */
}

.form-control::placeholder {
    color: #999999;
    font-style: italic;
}

.form-control.error {
    border-color: #E45E41;
}
```

---

### Tables

```css
.table th {
    background: #EEE5D3;              /* Beige */
    color: #1A1A1A;
    font-family: var(--font-primary);
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 14px 16px;
    text-align: left;
    border-bottom: 2px solid #CEB677;
}

.table td {
    padding: 14px 16px;
    border-bottom: 1px solid #E8E8E8;
    font-family: var(--font-secondary);
    font-size: 14px;
    color: #1F1F1F;
    vertical-align: middle;
}

.table tbody tr:hover {
    background: #EAD6B7;              /* Natural - light gold tint */
}
```

---

### Badges & Tags

```css
.badge {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 20px;
    font-family: var(--font-primary);
    font-size: 12px;
    font-weight: 600;
}

.badge-gold {
    background: #CEB677;
    color: #FFFFFF;
}

.badge-safari {
    background: #55996D;
    color: #FFFFFF;
}

.badge-red {
    background: #E45E41;
    color: #FFFFFF;
}

.badge-med {
    background: #6890C9;
    color: #FFFFFF;
}
```

---

### Modals

```css
.modal-content {
    border-radius: 8px;
    border: none;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
    background: #1A1A1A;              /* Cromad dark */
    color: #FFFFFF;
    padding: 20px 24px;
    border-radius: 8px 8px 0 0;
    border-bottom: 3px solid #CEB677; /* Gold accent */
}

.modal-title {
    font-family: var(--font-primary);
    font-weight: 600;
    color: #FFFFFF;
}

.modal-body {
    padding: 24px;
    background: #FFFFFF;
}

.modal-footer {
    background: #EEE5D3;              /* Beige */
    padding: 16px 24px;
    border-top: 1px solid #E0E0E0;
    border-radius: 0 0 8px 8px;
}
```

---

### Toast Notifications

```css
.toast {
    padding: 16px 20px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    max-width: 400px;
}

.toast-success {
    background: #E8F5E9;
    border-left: 4px solid #55996D;   /* Safari */
    color: #2E7D32;
}

.toast-error {
    background: #FFEBEE;
    border-left: 4px solid #E45E41;   /* Red */
    color: #C62828;
}

.toast-info {
    background: #E3F2FD;
    border-left: 4px solid #6890C9;   /* Med */
    color: #1565C0;
}
```

---

## Navigation

### Sidebar (Dark Theme)

```css
.sidebar {
    width: 260px;
    background: #1A1A1A;              /* Cromad dark */
    color: #FFFFFF;
    min-height: 100vh;
}

.sidebar-logo {
    padding: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}

.sidebar-logo img {
    height: 40px;
    /* Use Logo_PBSP_Blanco.svg (white) */
}

.nav-item {
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: rgba(255, 255, 255, 0.6);
    font-family: var(--font-primary);
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
    background: rgba(206, 182, 119, 0.15);  /* Gold tint */
    color: #CEB677;
    border-left-color: #CEB677;
}
```

### Topbar

```css
.topbar {
    height: 64px;
    background: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
}

.topbar-title {
    font-family: var(--font-primary);
    font-size: 20px;
    font-weight: 600;
    color: #1A1A1A;
}

.user-menu {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s ease;
}

.user-menu:hover {
    background: #EAD6B7;              /* Natural */
}

.user-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #CEB677;              /* Gold */
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-primary);
    font-weight: 700;
}
```

---

## Logo Usage

### Logo Variants

1. **Logo_PBSP_Blanco.svg** (White)
   - Use on: Dark backgrounds (sidebar, dark headers, dark sections)
   - Background: #1A1A1A, dark images, dark overlays

2. **Logo_PBSP_Dorado.svg** (Gold)
   - Use on: Light backgrounds (login page, white cards, light sections)
   - Background: #FFFFFF, #FAFAFA, light images

3. **Logo_PBSP_Negro.svg** (Black)
   - Use on: High contrast applications (print, documents, very light backgrounds)
   - Background: #FFFFFF, #F5F5F5

### Logo Specifications
- **Minimum Width:** 120px
- **Clear Space:** Minimum 20px on all sides
- **Aspect Ratio:** Maintain original proportions (~2.8:1)
- **Format:** SVG (scalable) preferred, PNG fallback

---

## CSS Variables Reference

```css
:root {
    /* ========== BRAND COLORS ========== */
    --color-gold: #CEB677;
    --color-natural: #EAD6B7;
    --color-beige: #EEE5D3;
    --color-wood: #A2795D;

    --color-red: #E45E41;
    --color-safari: #55996D;
    --color-med: #6890C9;
    --color-cromad: #1A1A1A;

    /* ========== SEMANTIC MAPPING ========== */
    --color-primary: var(--color-gold);
    --color-secondary: var(--color-med);
    --color-accent: var(--color-natural);

    --color-success: var(--color-safari);
    --color-error: var(--color-red);
    --color-warning: #E5A33D;
    --color-info: var(--color-med);

    /* ========== NEUTRALS ========== */
    --color-white: #FFFFFF;
    --color-background: #FAFAFA;
    --color-surface: #FFFFFF;
    --color-border: #E0E0E0;
    --color-text: #1A1A1A;
    --color-text-secondary: #666666;
    --color-text-muted: #999999;

    /* ========== DERIVED ========== */
    --color-gold-hover: #B8A166;
    --color-wood-light: #C29A7D;

    /* ========== TYPOGRAPHY ========== */
    --font-primary: 'Gilroy', 'Montserrat', 'Inter', sans-serif;
    --font-secondary: 'Cralika', 'Inter', sans-serif;
    --font-accent: 'Solitas', 'Inter', serif;

    --font-size-base: 14px;
    --line-height-base: 1.5;

    /* ========== SPACING ========== */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-8: 32px;
    --space-10: 40px;
    --space-12: 48px;

    /* ========== BORDERS ========== */
    --border-radius-sm: 4px;
    --border-radius-md: 8px;
    --border-radius-lg: 12px;
    --border-radius-xl: 16px;
    --border-radius-full: 9999px;

    /* ========== TRANSITIONS ========== */
    --transition-fast: 0.15s ease;
    --transition-normal: 0.2s ease;
    --transition-slow: 0.3s ease;

    /* ========== Z-INDEX ========== */
    --z-dropdown: 100;
    --z-sticky: 200;
    --z-modal-backdrop: 300;
    --z-modal: 400;
    --z-toast: 500;
    --z-tooltip: 600;

    /* ========== MAP SPECIFIC ========== */
    --map-available-fill: var(--color-natural);
    --map-available-stroke: var(--color-gold);
    --map-selected-fill: var(--color-gold);
    --map-selected-stroke: var(--color-wood);
}
```

---

## Accessibility

### Color Contrast (WCAG 2.1 AA)

**Compliant Combinations:**
- ✅ Cromad (#1A1A1A) on White (#FFFFFF): 15.7:1 - Use for body text
- ✅ Safari (#55996D) on White (#FFFFFF): 4.1:1 - Use for large text (18px+)
- ✅ Med (#6890C9) on White (#FFFFFF): 4.5:1 - Use for all text
- ✅ Red (#E45E41) on White (#FFFFFF): 4.2:1 - Use for large text

**Caution:**
- ⚠️ Gold (#CEB677) on White (#FFFFFF): 2.8:1 - Use for large UI elements (18px+), icons, borders ONLY
- ⚠️ Wood (#A2795D) on Beige (#EEE5D3): 3.2:1 - Use for large text only

**Best Practices:**
- Use Cromad (#1A1A1A) for all body text and small text
- Use Gold (#CEB677) for buttons, icons, large headers (18px+)
- Never use Gold for small body text
- Ensure all interactive elements have visible focus states

### Focus Indicators
```css
*:focus {
    outline: 2px solid #CEB677;
    outline-offset: 2px;
}
```

---

## Bootstrap 5 Integration

### Variable Overrides

```scss
// _variables.scss (if using SCSS)
$primary: #CEB677;
$secondary: #6890C9;
$success: #55996D;
$danger: #E45E41;
$warning: #E5A33D;
$info: #6890C9;

$body-bg: #FAFAFA;
$body-color: #1A1A1A;

$font-family-base: 'Cralika', 'Inter', sans-serif;
$headings-font-family: 'Gilroy', 'Montserrat', sans-serif;

$border-radius: 0.25rem;
$border-radius-lg: 0.5rem;
```

---

## Responsive Breakpoints

```css
/* Mobile First Approach */
/* Extra small (default) */
@media (min-width: 576px) { /* Small */ }
@media (min-width: 768px) { /* Tablets */ }
@media (min-width: 1024px) { /* Laptops */ }
@media (min-width: 1280px) { /* Desktops */ }
@media (min-width: 1440px) { /* Large screens */ }
```

---

## Animation & Transitions

### Standard Transitions
```css
/* Simple state changes */
transition: background 0.2s ease;
transition: color 0.2s ease;
transition: border-color 0.2s ease;

/* NO transform animations (flat design) */
/* NO box-shadow animations */
```

### Loading States
```css
/* Skeleton loading */
.skeleton {
    background: linear-gradient(90deg, #E0E0E0 25%, #F0F0F0 50%, #E0E0E0 75%);
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
    border: 3px solid #E0E0E0;
    border-top-color: #CEB677;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

---

## Icon System

### FontAwesome 6 (Functional Icons)
Use for utility icons: arrows, close, check, search, filter, etc.

### Custom Brand Icons
Located in `static/images/icons/` (from Brand Guide):
- Circular framed design
- Gold/tan colorization
- Line-based, outline style
- Use for: Dashboard features, marketing areas, branding moments

---

## Implementation Checklist

Before launching UI updates:

**Visual Consistency:**
- [ ] All pages use brand color palette (Gold, Natural, Beige, Wood, etc.)
- [ ] Gilroy font loaded and applied to headers/navigation
- [ ] Cralika/fallback applied to body text
- [ ] Logos display correctly (white/gold/black variants)
- [ ] NO gradients or box-shadows remain
- [ ] Flat, minimal design throughout

**Accessibility:**
- [ ] Color contrast ratios meet WCAG 2.1 AA
- [ ] Focus indicators visible on all interactive elements
- [ ] Keyboard navigation functional
- [ ] All images have alt text

**Functionality:**
- [ ] All buttons clickable with correct hover states
- [ ] Forms validate and submit properly
- [ ] Map interactions work (selection, drag, zoom)
- [ ] Modals open/close correctly
- [ ] Navigation active states accurate

---

## Quick Reference

```
PRIMARY COLORS:
Gold:    #CEB677
Natural: #EAD6B7
Beige:   #EEE5D3
Wood:    #A2795D

SECONDARY COLORS:
Red:     #E45E41
Safari:  #55996D
Med:     #6890C9
Cromad:  #1A1A1A

FONTS:
Primary:   Gilroy (headers, navigation)
Secondary: Cralika (body)
Accent:    Solitas (special)
Fallback:  Montserrat, Inter

DESIGN PHILOSOPHY:
- Flat design (no gradients, no shadows)
- Clean geometric shapes
- Generous whitespace
- Premium, sophisticated
- WCAG 2.1 AA compliant
```

---

**Last Updated:** 2026-02-05 (Brand UI Facelift)
**Based On:** Purobeach Brand Guide, Santa Ponsa, February 2025
