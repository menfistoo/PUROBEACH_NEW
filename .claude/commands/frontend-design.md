---
allowed-tools: Grep, Read, Edit, Write, Glob, Bash, TodoWrite
description: Guidelines for creating or modifying UI components following the Beach Club design system (project)
---

You are implementing frontend UI for the Beach Club Management System. Follow these design guidelines strictly.

## CRITICAL RULES

### Language Convention
- **Code (English):** Variables, functions, classes, CSS classes, IDs, data attributes
- **UI (Spanish):** Labels, buttons, messages, errors, tooltips, placeholders, table headers

```html
<!-- CORRECT -->
<button class="btn-primary" id="create-reservation-btn">Crear Reserva</button>
<label for="customer-name">Nombre del Cliente</label>
<span class="error-message">El campo es obligatorio</span>

<!-- INCORRECT -->
<button class="boton-primario">Create Reservation</button>
```

---

## COLOR PALETTE

### Primary Colors (MUST USE)
| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| Sand Gold | `#D4AF37` | `--color-primary` | CTAs, highlights, active states |
| Deep Ocean | `#1A3A5C` | `--color-secondary` | Headers, text, navigation |
| Warm Sand | `#F5E6D3` | `--color-accent` | Backgrounds, cards, available state |

### Functional Colors
| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| Success | `#4A7C59` | `--color-success` | Confirmations, completed |
| Error | `#C1444F` | `--color-error` | Errors, cancellations |
| Warning | `#E5A33D` | `--color-warning` | Warnings, pending |
| Info | `#4A90A4` | `--color-info` | Information, help |

### Neutrals
| Hex | Usage |
|-----|-------|
| `#FFFFFF` | Card backgrounds, modals |
| `#FAFAFA` | Page backgrounds |
| `#E8E8E8` | Borders, dividers |
| `#9CA3AF` | Placeholder text, disabled |
| `#4B5563` | Secondary text |
| `#1F2937` | Primary text |

### Reservation State Colors
```css
/* Pendiente */    background: #FEF3C7; border-color: #F59E0B; color: #92400E;
/* Confirmada */   background: #DBEAFE; border-color: #3B82F6; color: #1E40AF;
/* Check-in */     background: #D1FAE5; border-color: #10B981; color: #065F46;
/* Activa */       background: #DCFCE7; border-color: #22C55E; color: #166534;
/* Completada */   background: #F3F4F6; border-color: #9CA3AF; color: #4B5563;
/* Cancelada */    background: #FEE2E2; border-color: #EF4444; color: #991B1B;
/* No-Show */      background: #FCE7F3; border-color: #EC4899; color: #9D174D;
```

### Map Furniture States
```css
/* Available */    fill: #F5E6D3; stroke: #D4AF37;
/* Occupied */     fill: #90EE90; stroke: #228B22;
/* Selected */     fill: #D4AF37; stroke: #8B6914;
/* Maintenance */  fill: #9CA3AF; stroke: #6B7280; opacity: 0.7;
/* Temporary */    fill: #E0F2FE; stroke: #0EA5E9;
```

---

## TYPOGRAPHY

### Font Stack
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

### Type Scale
| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| Display | 36px | 700 | 1.2 |
| H1 | 28px | 600 | 1.3 |
| H2 | 24px | 600 | 1.3 |
| H3 | 20px | 600 | 1.4 |
| H4 | 18px | 500 | 1.4 |
| Body Large | 16px | 400 | 1.5 |
| Body | 14px | 400 | 1.5 |
| Body Small | 13px | 400 | 1.5 |
| Caption | 12px | 400 | 1.4 |
| Micro/Badge | 11px | 500 | 1.3 |

---

## SPACING SYSTEM (Base: 4px)

| Token | Value | Usage |
|-------|-------|-------|
| space-1 | 4px | Icon gaps |
| space-2 | 8px | Related elements |
| space-3 | 12px | Form field gaps |
| space-4 | 16px | Card padding |
| space-6 | 24px | Section padding |
| space-8 | 32px | Major sections |

---

## COMPONENT PATTERNS

### Buttons

```html
<!-- Primary Button (Gold Gradient) -->
<button class="btn btn-primary">
    <i class="fas fa-plus me-2"></i>Nueva Reserva
</button>

<!-- Secondary Button (White with Gold Border) -->
<button class="btn btn-outline-primary">Cancelar</button>

<!-- Danger Button -->
<button class="btn btn-danger">Eliminar</button>
```

**CSS Pattern:**
```css
.btn-primary {
    background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 600;
    box-shadow: 0 2px 4px rgba(212, 175, 55, 0.3);
}
.btn-primary:hover {
    background: linear-gradient(135deg, #E5C04A 0%, #C9A71D 100%);
    transform: translateY(-1px);
}
```

### Cards

```html
<div class="card">
    <div class="card-header">
        <h5 class="card-title mb-0">Titulo de la Tarjeta</h5>
    </div>
    <div class="card-body">
        <!-- content -->
    </div>
</div>
```

**CSS Pattern:**
```css
.card {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E8E8E8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.05);
}
.card-header {
    background: transparent;
    border-bottom: 1px solid #E8E8E8;
    padding: 16px 24px;
}
.card-title {
    color: #1A3A5C;
    font-weight: 600;
}
```

### Forms

```html
<div class="mb-3">
    <label for="customer-name" class="form-label">Nombre del Cliente</label>
    <input type="text" class="form-control" id="customer-name"
           placeholder="Ingrese el nombre...">
    <div class="form-text">Texto de ayuda opcional</div>
</div>
```

**CSS Pattern:**
```css
.form-control {
    border: 2px solid #E8E8E8;
    border-radius: 8px;
    padding: 12px 16px;
}
.form-control:focus {
    border-color: #D4AF37;
    box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.15);
}
.form-label {
    font-size: 13px;
    font-weight: 500;
    color: #4B5563;
}
```

### Tables

```html
<table class="table">
    <thead>
        <tr>
            <th>Nombre</th>
            <th>Estado</th>
            <th>Acciones</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Juan Perez</td>
            <td><span class="badge badge-confirmada">Confirmada</span></td>
            <td>
                <button class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    </tbody>
</table>
```

**CSS Pattern:**
```css
.table th {
    background: #F5E6D3;
    color: #1A3A5C;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid #D4AF37;
}
.table td {
    border-bottom: 1px solid #E8E8E8;
    vertical-align: middle;
}
.table tbody tr:hover {
    background: #FAFAFA;
}
```

### Badges

```html
<span class="badge badge-pendiente">Pendiente</span>
<span class="badge badge-confirmada">Confirmada</span>
<span class="badge badge-success">Completada</span>
<span class="badge badge-danger">Cancelada</span>
```

### Modals

```html
<div class="modal fade" id="example-modal">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Titulo del Modal</h5>
                <button type="button" class="btn-close btn-close-white"
                        data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- content -->
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline-secondary" data-bs-dismiss="modal">
                    Cancelar
                </button>
                <button class="btn btn-primary">Guardar</button>
            </div>
        </div>
    </div>
</div>
```

**CSS Pattern:**
```css
.modal-header {
    background: linear-gradient(135deg, #1A3A5C 0%, #2A4A6C 100%);
    color: #FFFFFF;
    border-radius: 16px 16px 0 0;
}
.modal-content {
    border-radius: 16px;
    border: none;
}
.modal-footer {
    background: #FAFAFA;
    border-top: 1px solid #E8E8E8;
}
```

### Toast Notifications

```html
<div class="toast toast-success">
    <i class="fas fa-check-circle"></i>
    <span>Reserva creada exitosamente</span>
</div>
```

**CSS Pattern:**
```css
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
```

---

## NAVIGATION

### Sidebar (Dark Theme)
```css
.sidebar {
    background: linear-gradient(180deg, #1A3A5C 0%, #0F2744 100%);
    color: #FFFFFF;
    width: 260px;
}
.nav-item.active {
    background: rgba(212, 175, 55, 0.15);
    color: #D4AF37;
    border-left: 3px solid #D4AF37;
}
```

---

## ICONS (Font Awesome 6)

| Action | Icon |
|--------|------|
| Add | `fa-plus` |
| Edit | `fa-pen` |
| Delete | `fa-trash` |
| View | `fa-eye` |
| Search | `fa-magnifying-glass` |
| Filter | `fa-filter` |
| Export | `fa-download` |
| Calendar | `fa-calendar` |
| Map | `fa-map` |
| User | `fa-user` |
| Settings | `fa-gear` |
| Check | `fa-check` |
| Close | `fa-xmark` |
| Warning | `fa-triangle-exclamation` |

---

## ANIMATIONS

```css
/* Standard transition */
transition: all 0.2s ease;

/* Hover lift effect */
.hover-lift:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Gold glow effect */
.hover-glow:hover {
    box-shadow: 0 0 20px rgba(212, 175, 55, 0.3);
}

/* Loading spinner */
.spinner {
    border: 3px solid #E8E8E8;
    border-top-color: #D4AF37;
    animation: spin 0.8s linear infinite;
}
```

---

## ACCESSIBILITY REQUIREMENTS

1. **Color Contrast:** Minimum 4.5:1 ratio for text
2. **Focus States:** Visible focus indicator on all interactive elements
3. **Form Labels:** Every input MUST have an associated label
4. **Alt Text:** All images must have descriptive alt text
5. **ARIA:** Use appropriate ARIA labels for icons-only buttons
6. **Keyboard:** All interactions must be keyboard accessible

```html
<!-- Icon-only button with ARIA -->
<button class="btn btn-sm" aria-label="Editar reserva">
    <i class="fas fa-pen"></i>
</button>

<!-- Form with proper labels -->
<label for="phone" class="form-label">Telefono</label>
<input type="tel" id="phone" class="form-control">
```

---

## CSS VARIABLES REFERENCE

```css
:root {
    --color-primary: #D4AF37;
    --color-primary-dark: #B8960C;
    --color-secondary: #1A3A5C;
    --color-accent: #F5E6D3;
    --color-success: #4A7C59;
    --color-error: #C1444F;
    --color-warning: #E5A33D;
    --color-text: #1F2937;
    --color-text-secondary: #4B5563;
    --color-border: #E8E8E8;
    --color-background: #FAFAFA;
    --border-radius-sm: 4px;
    --border-radius-md: 8px;
    --border-radius-lg: 12px;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
    --transition-normal: 0.2s ease;
}
```

---

## BOOTSTRAP 5 INTEGRATION

This project uses Bootstrap 5. Override Bootstrap variables to match the design system:

```scss
$primary: #D4AF37;
$secondary: #1A3A5C;
$success: #4A7C59;
$danger: #C1444F;
$warning: #E5A33D;
$info: #4A90A4;
$body-bg: #FAFAFA;
$body-color: #1F2937;
$border-radius: 0.5rem;
```

Use Bootstrap classes where appropriate, but customize with project styles for the Beach Club luxury aesthetic.

---

## CHECKLIST BEFORE IMPLEMENTING

- [ ] All UI text is in Spanish
- [ ] All code (classes, IDs, variables) is in English
- [ ] Colors match the design system palette
- [ ] Typography uses Inter font and correct scale
- [ ] Components follow established patterns
- [ ] Forms have proper labels and validation messages
- [ ] Interactive elements have hover/focus states
- [ ] Accessibility requirements are met
- [ ] Responsive breakpoints are considered
