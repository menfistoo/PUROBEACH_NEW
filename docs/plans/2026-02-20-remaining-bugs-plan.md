# Remaining Bugs Fix Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 6 remaining bugs from GitHub issues #34, #35, and #36, plus Phase 3 roadmap items.

**Architecture:** All fixes are isolated, independent changes to existing JS/CSS files. Each task touches 1-2 source files plus their corresponding bundle files.

**Tech Stack:** JavaScript ES6+, CSS3

**Worktree:** `C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/production-readiness`

---

## Task 1: XSS — Escape furniture number in chip rendering (#35)

**Files:**
- Modify: `static/js/map/reservation-panel/panel-core.js:575`
- Modify: `static/js/map-panels-bundle.js` (corresponding line)

**Step 1: Fix source file**

In `panel-core.js`, inside `renderFurnitureChips()`, change line 575 from:
```javascript
                ${f.number}
```
to:
```javascript
                ${escapeHtml(String(f.number))}
```

`escapeHtml` is already globally available in the bundle context.

**Step 2: Fix bundle file**

Apply the same change in `map-panels-bundle.js` at the corresponding location (search for `renderFurnitureChips` or `furniture-chip`).

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel/panel-core.js static/js/map-panels-bundle.js
git commit -m "fix: escape furniture number in chip rendering (XSS #35)"
```

---

## Task 2: z-index stacking conflicts (#34)

**Files:**
- Modify: `static/css/map-blocks.css:18` (CSS variable)
- Modify: `static/css/move-mode.css:57`
- Modify: `static/css/map-page.css:882`

**Step 1: Establish z-index hierarchy**

Target stacking order (bottom to top):
- `#moveModePanel`: **1040** (full panel, below context menus)
- `.context-menu` (map-page.css): **1055** (above move panel)
- `.furniture-context-menu` (via `--z-context-menu`): **1060** (topmost interactive)
- Safeguard modal (9998/9999): stays as-is (emergency overlay)

**Step 2: Fix map-blocks.css line 18**

Change:
```css
    --z-context-menu: 1050;
```
to:
```css
    --z-context-menu: 1060;
```

**Step 3: Fix move-mode.css line 57**

Change:
```css
    z-index: 1050;
```
to:
```css
    z-index: 1040;
```

**Step 4: Fix map-page.css line 882**

Change:
```css
    z-index: 1050;
```
to:
```css
    z-index: 1055;
```

**Step 5: Fix bundle CSS**

Apply the same z-index changes in `static/css/map-bundle.css` if it contains copies of these rules.

**Step 6: Commit**

```bash
git add static/css/map-blocks.css static/css/move-mode.css static/css/map-page.css static/css/map-bundle.css
git commit -m "fix: resolve z-index stacking conflicts between context menu and move panel (#34)"
```

---

## Task 3: Toolbar overflow on mobile (#34)

**Files:**
- Modify: `static/css/map-page.css` (mobile breakpoint section)
- Modify: `static/css/map-bundle.css` (corresponding rules)

**Step 1: Add flex-wrap and overflow handling**

In `map-page.css`, find the `.map-toolbar` rule and add `flex-wrap: wrap` and `gap`. At the mobile breakpoint (`@media (max-width: 576px)`), hide secondary controls and show only essentials.

Add after existing `.map-toolbar` rules:

```css
.map-toolbar {
    flex-wrap: wrap;
    gap: 4px;
}

@media (max-width: 576px) {
    .map-toolbar {
        gap: 2px;
    }

    /* Hide secondary controls on small screens */
    .map-filter-dropdowns,
    #btn-add-temp-furniture,
    #sync-button {
        display: none;
    }
}
```

**Step 2: Update bundle CSS**

Apply same changes to `map-bundle.css`.

**Step 3: Commit**

```bash
git add static/css/map-page.css static/css/map-bundle.css
git commit -m "fix: add toolbar flex-wrap and hide secondary controls on mobile (#34)"
```

---

## Task 4: Context menu positioning before visible (#36)

**Files:**
- Modify: `static/js/map/context-menu.js` (positionMenu + positionEmptySpaceMenu)
- Modify: `static/js/map-core-bundle.js` (corresponding code)

**Step 1: Fix positionMenu() — use estimated dimensions**

Instead of relying on `getBoundingClientRect()` on a hidden element, use CSS-known dimensions. In `context-menu.js`, replace `positionMenu()` (around line 443):

```javascript
positionMenu(x, y) {
    const menu = this.menuElement;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Use offsetWidth/Height after temporarily making visible for measurement
    menu.style.visibility = 'hidden';
    menu.classList.add('visible');
    const menuWidth = menu.offsetWidth || 180;
    const menuHeight = menu.offsetHeight || 200;
    menu.classList.remove('visible');
    menu.style.visibility = '';

    // Adjust position to stay within viewport
    if (x + menuWidth > viewportWidth) {
        x = viewportWidth - menuWidth - 10;
    }
    if (y + menuHeight > viewportHeight) {
        y = viewportHeight - menuHeight - 10;
    }
    if (x < 10) x = 10;
    if (y < 10) y = 10;

    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;
}
```

**Step 2: Fix positionEmptySpaceMenu() — same approach**

Apply the same pattern to `positionEmptySpaceMenu()` (around line 407).

**Step 3: Update bundle**

Apply same changes to `map-core-bundle.js`.

**Step 4: Commit**

```bash
git add static/js/map/context-menu.js static/js/map-core-bundle.js
git commit -m "fix: measure context menu dimensions correctly before positioning (#36)"
```

---

## Task 5: Null-checks on primary zoom buttons (#36)

**Files:**
- Modify: `static/js/map/map-page.js:1519-1520`
- Modify: `static/js/map-bundle.js` (corresponding lines)

**Step 1: Add optional chaining**

In `map-page.js`, change lines 1519-1520 from:
```javascript
document.getElementById('btn-zoom-in').addEventListener('click', () => { map.zoomIn(); updateZoomDisplay(); });
document.getElementById('btn-zoom-out').addEventListener('click', () => { map.zoomOut(); updateZoomDisplay(); });
```
to:
```javascript
document.getElementById('btn-zoom-in')?.addEventListener('click', () => { map.zoomIn(); updateZoomDisplay(); });
document.getElementById('btn-zoom-out')?.addEventListener('click', () => { map.zoomOut(); updateZoomDisplay(); });
```

**Step 2: Update bundle**

Apply same change in `map-bundle.js`.

**Step 3: Commit**

```bash
git add static/js/map/map-page.js static/js/map-bundle.js
git commit -m "fix: add null-checks on primary zoom button listeners (#36)"
```

---

## Task 6: Conflict retry payload missing payment fields (#36)

**Files:**
- Modify: `static/js/map/reservation-panel/conflict-resolver.js:185-195`
- Modify: `static/js/map-panels-bundle.js` (corresponding code)

**Step 1: Add payment field reads and include in payload**

In `conflict-resolver.js`, before the payload construction (around line 183), add payment field reads:

```javascript
// Read payment fields (same as panel-core.js createReservation)
const paymentTicketEl = document.getElementById('newPanelPaymentTicket');
const paymentMethodEl = document.getElementById('newPanelPaymentMethod');
const paymentTicketValue = paymentTicketEl ? paymentTicketEl.value.trim() : '';
const paymentMethodValue = paymentMethodEl ? paymentMethodEl.value.trim() : '';
```

Then update the payload to include:
```javascript
const payload = {
    customer_id: finalCustomerId,
    dates: selectedDates,
    furniture_by_date: furnitureByDate,
    num_people: numPeople,
    time_slot: 'all_day',
    notes: notes,
    preferences: preferences,
    charge_to_room: chargeToRoom,
    tag_ids: tagIds,
    payment_ticket_number: paymentTicketValue,
    payment_method: paymentMethodValue,
    paid: (paymentTicketValue || paymentMethodValue) ? 1 : 0
};
```

**Step 2: Update bundle**

Apply same changes to `map-panels-bundle.js`.

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel/conflict-resolver.js static/js/map-panels-bundle.js
git commit -m "fix: include payment fields in conflict retry payload (#36)"
```

---

## Task 7: Run tests and verify

**Step 1: Run full test suite**

```bash
cd /c/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/production-readiness
python -m pytest tests/ -x --tb=short -q
```

Expected: 303+ tests passing, 0 failures.

**Step 2: Final commit if any adjustments needed**

---

## Summary

| Task | Issue | Fix | Risk |
|------|-------|-----|------|
| 1 | #35 | Escape `f.number` in chip innerHTML | Low - one-line |
| 2 | #34 | Differentiate z-index values | Low - CSS only |
| 3 | #34 | Toolbar flex-wrap + hide on mobile | Low - CSS only |
| 4 | #36 | Measure context menu while temporarily visible | Medium - behavior change |
| 5 | #36 | Add `?.` to zoom button listeners | Low - one-char |
| 6 | #36 | Add payment fields to conflict retry | Low - additive |
| 7 | - | Run tests | - |
