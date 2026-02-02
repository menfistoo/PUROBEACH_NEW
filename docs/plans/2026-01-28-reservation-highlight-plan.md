# Reservation Furniture Highlight - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Highlight furniture belonging to a reservation on the live map with a pulsing gold glow when the reservation panel opens.

**Architecture:** The infrastructure already exists — `furniture-mixin.js` has highlight/unhighlight methods and `map-page.css` has the `.highlighted` class with gold pulse animation. We just need to: (1) fix the CSS class used, (2) add date filtering, (3) wire into panel lifecycle.

**Branch:** `feature/reservation-highlight` (worktree at `.worktrees/reservation-highlight`)

---

## Task 1: Fix highlight methods in furniture-mixin.js

**Modify:** `static/js/map/reservation-panel-v2/furniture-mixin.js:130-155`

Change `highlightReservationFurniture()` to:
- Use `.highlighted` class (gold pulse from map-page.css) instead of `.furniture-editing` (red aura)
- Filter furniture by `this.state.currentDate` (only highlight today's assignments)

Change `unhighlightReservationFurniture()` to:
- Remove `.highlighted` class instead of `.furniture-editing`

```javascript
highlightReservationFurniture() {
    // Clear any previous highlights first
    this.unhighlightReservationFurniture();

    if (!this.state.data?.furniture) return;

    const currentDate = this.state.currentDate;

    // Filter furniture for current date
    const todayFurniture = this.state.data.furniture.filter(f => {
        const assignDate = parseDateToYMD(f.assignment_date);
        return assignDate === currentDate;
    });

    // Highlight each furniture element on the map
    todayFurniture.forEach(f => {
        const id = f.id || f.furniture_id;
        const furnitureEl = document.querySelector(`[data-furniture-id="${id}"]`);
        if (furnitureEl) {
            furnitureEl.classList.add('highlighted');
        }
    });
}

unhighlightReservationFurniture() {
    const highlightedElements = document.querySelectorAll('.furniture-item.highlighted');
    highlightedElements.forEach(el => {
        el.classList.remove('highlighted');
    });
}
```

**Verify:** No syntax errors. `parseDateToYMD` is already imported at line 11.

---

## Task 2: Wire highlight into panel lifecycle

**Modify:** `static/js/map/reservation-panel-v2/panel-lifecycle.js`

In `open()` (line 37): Call `this.highlightReservationFurniture()` is NOT needed here — data isn't loaded yet. Instead, call it at the end of `loadReservation()` after `renderContent()`.

In `loadReservation()` (line 201): Add highlight call after `this.renderContent(result)` at line 219.

In `close()` (line 95): Add `this.unhighlightReservationFurniture()` early in the method.

```javascript
// In loadReservation(), after line 219:
this.highlightReservationFurniture();

// In close(), after line 96 (the isOpen check):
this.unhighlightReservationFurniture();
```

**Verify:** Open map, click a reservation → furniture glows gold. Close panel → glow disappears. Open different reservation → previous glow clears, new one appears.

---

## Task 3: Commit

```bash
git add static/js/map/reservation-panel-v2/furniture-mixin.js static/js/map/reservation-panel-v2/panel-lifecycle.js
git commit -m "feat(map): highlight reservation furniture with gold glow on panel open

Fixes #2"
```

---

## Verification Checklist

- [ ] Open reservation panel → furniture items pulse gold
- [ ] Close panel → glow disappears
- [ ] Open different reservation → previous glow clears, new glow appears
- [ ] Multi-day reservation → only today's furniture highlighted
- [ ] No console errors
- [ ] `python -m pytest tests/ -x -q` passes
