# Brand UI Facelift - Implementation Plan

**Date:** 2026-02-05
**Objective:** Complete UI redesign to align with official Purobeach Brand Guide
**Duration:** Est. 15-21 hours
**Branch:** `feature/brand-ui-facelift`

---

## Executive Summary

Redesign the Beach Club Management System UI to match the official Purobeach Brand Guide (Santa Ponsa, February 2025). This is a **strictly visual facelift** with zero functionality changes.

### Key Changes
- **Colors:** Gold `#CEB677`, Natural `#EAD6B7`, Beige `#EEE5D3`, Wood `#A2795D`
- **Typography:** Gilroy (headers), Cralika (body), Solitas (accent)
- **Design Style:** Flat, minimalist (remove all gradients and shadows)
- **Logo:** Use official white/gold/black variants
- **Navigation:** Dark sidebar with Cromad `#1A1A1A`

---

## Phase 1: Foundation (2-3 hours)

### Objectives
- Update CSS variables with brand colors
- Integrate brand fonts
- Copy logo files
- Update Bootstrap overrides

### Tasks

#### 1.1 Update CSS Variables
**File:** `static/css/main.css` (lines 8-110)

Replace all color variables:
```css
:root {
    /* Brand Colors */
    --color-gold: #CEB677;
    --color-natural: #EAD6B7;
    --color-beige: #EEE5D3;
    --color-wood: #A2795D;

    --color-red: #E45E41;
    --color-safari: #55996D;
    --color-med: #6890C9;
    --color-cromad: #1A1A1A;

    /* Semantic */
    --color-primary: var(--color-gold);
    --color-secondary: var(--color-med);
    --color-success: var(--color-safari);
    --color-error: var(--color-red);

    /* Typography */
    --font-primary: 'Gilroy', 'Montserrat', 'Inter', sans-serif;
    --font-secondary: 'Cralika', 'Inter', sans-serif;
    --font-accent: 'Solitas', 'Inter', serif;
}
```

#### 1.2 Add Font Links
**File:** `templates/base.html` (after line 12)

```html
<!-- Brand Fonts -->
<link href="https://fonts.cdnfonts.com/css/gilroy-bold" rel="stylesheet">
<!-- Note: If Gilroy/Cralika unavailable, fallback to Montserrat/Inter -->
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
```

#### 1.3 Copy Logo Files
```bash
# Copy from Brand Guide to static/images/
cp "examples/Brand Guide/.svg/Logo_PBSP_Blanco.svg" static/images/
cp "examples/Brand Guide/.svg/Logo_PBSP_Dorado.svg" static/images/
cp "examples/Brand Guide/.svg/Logo_PBSP_DoradoNew.svg" static/images/
cp "examples/Brand Guide/.svg/Logo_PBSP_Negro.svg" static/images/
```

#### 1.4 Update Bootstrap Overrides
**File:** `static/css/main.css` (lines 112-155)

Update all `.btn-primary`, `.bg-primary`, `.text-primary` to use brand gold.

### Verification
- [ ] CSS variables updated with brand colors
- [ ] Fonts loading in browser inspector
- [ ] Logos copied to `static/images/`
- [ ] Bootstrap utilities reflect brand colors
- [ ] No console errors

---

## Phase 2: Components (3-4 hours)

### Objectives
- Remove gradients from buttons
- Remove shadows from cards
- Update form focus states
- Update table headers
- Update badges

### Tasks

#### 2.1 Buttons
**File:** `static/css/main.css`

```css
.btn-primary {
    background: #CEB677;  /* Flat, no gradient */
    border: none;
    /* REMOVE: box-shadow, transform */
}
.btn-primary:hover {
    background: #B8A166;  /* Darker gold */
}
```

#### 2.2 Cards
```css
.card {
    border: 1px solid #E0E0E0;
    /* REMOVE: box-shadow */
}
.card-header {
    background: #EEE5D3;  /* Beige */
}
```

#### 2.3 Forms
```css
.form-control:focus {
    border-color: #CEB677;
    /* REMOVE: box-shadow */
}
.form-label {
    font-family: var(--font-primary);
    font-weight: 600;
    text-transform: uppercase;
}
```

#### 2.4 Tables
```css
.table th {
    background: #EEE5D3;  /* Beige */
    border-bottom: 2px solid #CEB677;  /* Gold */
}
.table tbody tr:hover {
    background: #EAD6B7;  /* Natural */
}
```

#### 2.5 Badges
Update all badge classes to use brand colors:
- `.badge-gold` → `#CEB677`
- `.badge-safari` → `#55996D`
- `.badge-red` → `#E45E41`
- `.badge-med` → `#6890C9`

### Verification
- [ ] Primary buttons flat (no gradient)
- [ ] Cards have no shadow
- [ ] Form focus uses gold outline
- [ ] Table headers beige background
- [ ] Badges use brand colors

---

## Phase 3: Navigation (1-2 hours)

### Objectives
- Update sidebar to dark Cromad
- Integrate white logo
- Update active states with gold
- Update topbar styling

### Tasks

#### 3.1 Sidebar
**File:** `static/css/main.css`

```css
.sidebar {
    background: #1A1A1A;  /* Cromad */
}
.nav-item.active {
    background: rgba(206, 182, 119, 0.15);
    color: #CEB677;
    border-left-color: #CEB677;
}
```

#### 3.2 Logo Integration
**File:** `templates/components/_sidebar.html`

```html
<div class="sidebar-logo">
    <img src="{{ url_for('static', filename='images/Logo_PBSP_Blanco.svg') }}"
         alt="PuroBeach"
         style="height: 40px;">
</div>
```

#### 3.3 User Avatar
```css
.user-avatar {
    background: #CEB677;  /* Gold */
}
.user-menu:hover {
    background: #EAD6B7;  /* Natural */
}
```

### Verification
- [ ] Sidebar dark (#1A1A1A)
- [ ] White logo displays correctly
- [ ] Active nav items show gold
- [ ] User avatar gold background

---

## Phase 4: Pages (4-5 hours)

### Objectives
- Update login page
- Update all beach management pages
- Update admin pages
- Update configuration pages

### Tasks

#### 4.1 Login Page
**File:** `templates/auth/login.html`

- Add gold logo (Logo_PBSP_Dorado.svg)
- Update form styling
- Update primary button
- Test login flow

#### 4.2 Reservations Pages
**Files:** `templates/beach/reservations.html`, `templates/beach/reservation_detail.html`

- Update state badge colors (use brand colors where appropriate)
- Update table styling
- Update action buttons

#### 4.3 Customer Pages
**Files:** `templates/beach/customers.html`, `templates/beach/customer_detail.html`

- Update cards
- Update forms
- Update tables

#### 4.4 Configuration Pages
**Files:** `templates/beach/config/*.html`

- Update tabbed navigation (use brand colors)
- Update forms
- Update lists

#### 4.5 Admin Pages
**Files:** `templates/admin/*.html`

- Update user management
- Update role permissions
- Update audit logs

### Verification
- [ ] Login page displays gold logo
- [ ] All pages use brand color palette
- [ ] No gradients or shadows visible
- [ ] Forms use brand styling
- [ ] Tables use beige headers

---

## Phase 5: Beach Map (3-4 hours)

### Objectives
- Update furniture state colors
- Update zone rendering
- Update map controls
- Update reservation panel
- Update date navigator

### Tasks

#### 5.1 Map Colors
**File:** `static/js/map/map-core.js` or map config

```javascript
const MAP_COLORS = {
    available: { fill: '#EAD6B7', stroke: '#CEB677' },
    occupied: { fill: '#55996D', stroke: '#3E7D52' },
    selected: { fill: '#CEB677', stroke: '#A2795D' },
    blocked: { fill: '#E45E41', stroke: '#C14830' },
    temporary: { fill: '#6890C9', stroke: '#5578A3' }
};
```

#### 5.2 Reservation Panel
**File:** `static/css/reservation-panel.css`

- Update header colors
- Update button styling
- Update form fields
- Update state badges

#### 5.3 Date Navigator
**File:** `static/css/map-page.css`

```css
.date-navigator {
    border: 1px solid #CEB677;
}
.date-nav-btn {
    background: #EAD6B7;
}
.date-nav-btn:hover {
    background: #CEB677;
}
```

### Verification
- [ ] Available furniture shows Natural fill
- [ ] Selected furniture shows Gold
- [ ] Occupied furniture shows Safari green
- [ ] Date navigator uses brand colors
- [ ] Reservation panel styled correctly

---

## Phase 6: Testing & Polish (2-3 hours)

### Objectives
- Cross-browser testing
- Mobile responsiveness
- Accessibility audit
- Visual consistency check

### Tasks

#### 6.1 Browser Testing
Test in:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)
- [ ] Safari (if available)

#### 6.2 Responsive Testing
Test breakpoints:
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

#### 6.3 Accessibility Audit
- [ ] Color contrast ratios meet WCAG 2.1 AA
- [ ] Focus indicators visible
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility (basic test)

#### 6.4 Visual Consistency
- [ ] All buttons use brand styling
- [ ] All cards have no shadows
- [ ] All tables use beige headers
- [ ] All forms use gold focus states
- [ ] No gradients remain anywhere

#### 6.5 Functionality Testing
- [ ] Login/logout works
- [ ] Create reservation works
- [ ] Edit customer works
- [ ] Map interactions work
- [ ] Reports generate correctly

---

## Rollback Plan

If issues arise:

```bash
# Revert to previous state
git checkout main -- static/css/main.css
git checkout main -- templates/base.html
git checkout main -- design-review/DESIGN_SYSTEM.md

# Or revert entire branch
git checkout main
git branch -D feature/brand-ui-facelift
```

---

## Success Criteria

### Visual
- ✅ All pages use Purobeach brand color palette
- ✅ Gilroy font applied to headers/navigation
- ✅ NO gradients visible anywhere
- ✅ NO box-shadows on components
- ✅ Flat, minimalist design throughout
- ✅ Logos display correctly (white/gold/black)

### Functional
- ✅ All existing functionality works
- ✅ No JavaScript errors
- ✅ No CSS layout breaks
- ✅ Forms submit correctly
- ✅ Map interactions work

### Accessibility
- ✅ WCAG 2.1 AA compliance
- ✅ Keyboard navigation functional
- ✅ Focus states visible

---

## Post-Implementation

### Documentation
- [x] Updated CLAUDE.md with brand specs
- [x] Updated DESIGN_SYSTEM.md
- [x] Created this implementation plan
- [ ] Update DEMO_ROADMAP.md if needed
- [ ] Create GitHub issue for any discovered issues

### Demo/Stakeholder Review
- [ ] Schedule demo with stakeholders
- [ ] Gather feedback
- [ ] Make minor adjustments if needed
- [ ] Merge to main when approved

---

## Notes

### Font Availability
If Gilroy/Cralika/Solitas are not available via CDN:
1. Use Montserrat as Gilroy alternative (similar geometric sans-serif)
2. Use Inter as Cralika alternative (excellent readability)
3. Update CSS variables accordingly

### Browser Compatibility
- CSS variables supported in all modern browsers
- CSS Grid and Flexbox used extensively
- Fallbacks in place for older browsers

### Performance
- Logo SVGs are small and efficient
- Font loading optimized with display=swap
- No performance impact expected

---

**Plan Created:** 2026-02-05
**Author:** Claude (Sonnet 4.5)
**Status:** Ready for implementation
