# Offline Functionality Design

**Date:** 2026-01-09
**Status:** Approved
**Feature:** Funcionalidad Offline - Daily offline plan for beach club operations

---

## Overview

Enable staff to view today's map and reservations when internet connection fails, ensuring service continuity.

### Scope

- **View-only** access when offline (no create/edit)
- **Map + Reservations** data cached (furniture, zones, availability, reservation details with customer name)
- **Automatic + Manual** sync (background caching + "Descargar Día" button)
- **Prominent banner** + disabled action buttons when offline
- **Auto-refresh with toast** when connection restored
- **Persistent storage** via IndexedDB (survives browser restart)

---

## User Experience Flow

```
Normal operation (online):
┌─────────────────────────────────────────┐
│  Map view works normally                │
│  Background auto-sync every 5 min       │
│  "Descargar Día" button shows ✓ synced  │
└─────────────────────────────────────────┘

Connection lost:
┌─────────────────────────────────────────┐
│ ⚠ Modo Offline - Datos de las 10:35    │
├─────────────────────────────────────────┤
│  Map displays cached data               │
│  Create/Edit buttons greyed out         │
│  Staff can view but not modify          │
└─────────────────────────────────────────┘

Connection restored:
┌─────────────────────────────────────────┐
│  Auto-refresh happens                   │
│  Toast: "Datos actualizados"            │
│  Full functionality restored            │
└─────────────────────────────────────────┘
```

---

## Technical Architecture

### Storage Layer - IndexedDB

```
Database: "purobeach_offline"
├── Store: "map_data"
│   └── Key: date (YYYY-MM-DD)
│   └── Value: { zones, furniture, availability, lastSync }
│
├── Store: "reservations"
│   └── Key: date (YYYY-MM-DD)
│   └── Value: [ {id, customer_name, furniture_ids, state, time_slot, notes, num_people} ]
│
└── Store: "sync_meta"
    └── Key: "current"
    └── Value: { lastSyncDate, lastSyncTime, version }
```

**Why IndexedDB (not localStorage):**
- Larger storage limit (~50MB vs 5MB)
- Async API doesn't block UI
- Structured data with indexes
- Better for complex objects like map data

### Caching Strategy

- Cache **today's date only** (single day focus)
- Auto-sync triggers: page load, every 5 minutes while online
- Manual sync: "Descargar Día" button
- Data expires: automatically cleared when date changes (next day)

### What Gets Cached

```javascript
{
  zones: [...],           // Zone boundaries and names
  furniture: [...],       // Position, type, capacity, number
  availability: {...},    // furniture_id → state (available/occupied)
  reservations: [...]     // Reservation details with customer name
}
```

---

## UI Components

### 1. Offline Banner

```css
.offline-banner {
    position: fixed;
    top: 0;
    left: var(--sidebar-width);
    right: 0;
    background: linear-gradient(135deg, var(--color-warning) 0%, #CC8C2E 100%);
    color: var(--color-white);
    padding: var(--space-3) var(--space-6);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    font-weight: 600;
    font-size: 14px;
    z-index: var(--z-sticky);
    box-shadow: var(--shadow-md);
}
```

- Uses `--color-warning` (#E5A33D) with gradient
- Respects sidebar width
- Icon: `fa-wifi-slash`
- Text: "Modo Offline - Datos de las HH:MM"

### 2. Sync Button (map toolbar)

| State | Display | Style |
|-------|---------|-------|
| Synced | ✓ Sincronizado 10:35 | badge-success |
| Syncing | ↻ Sincronizando... | btn-primary with spinner |
| Stale | ⬇ Descargar Día | btn-secondary (gold border) |
| Offline | ✗ Sin conexión | disabled, opacity 0.5 |

- Uses existing `.btn-sm` sizing
- Tooltip on hover shows full sync timestamp

### 3. Disabled State for Actions

```css
.offline-disabled {
    opacity: 0.5;
    pointer-events: none;
    cursor: not-allowed;
}
```

- Applied to: "Nueva Reserva" button, furniture click handlers, save/edit buttons
- Click attempt shows toast: "Función no disponible en modo offline"

---

## Connectivity Detection & Sync Logic

### Online/Offline Detection

```javascript
// Uses Navigator API + periodic health check
class ConnectivityManager {
    // 1. Browser events (instant but not always reliable)
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());

    // 2. Health check ping every 30s (confirms actual connectivity)
    async checkConnectivity() {
        try {
            await fetch('/api/health', { timeout: 5000 });
            return true;
        } catch {
            return false;
        }
    }
}
```

### Sync Triggers

| Event | Action |
|-------|--------|
| Page load | Sync if data older than 5 min |
| Every 5 min (online) | Background auto-sync |
| "Descargar Día" click | Force sync now |
| Connection restored | Auto-sync + toast |
| Date changes to new day | Clear old data, sync new |

### Sync Flow

```
1. Check connectivity
2. Fetch /beach/api/map/data?date=YYYY-MM-DD
3. Fetch /beach/api/map/reservations?date=YYYY-MM-DD
4. Store in IndexedDB with timestamp
5. Update UI (sync button, last sync time)
```

### Data Expiration

- On app load, check if stored date ≠ today → clear old data
- No manual cleanup needed

---

## Implementation Files

### New Files to Create

| File | Purpose | ~Lines |
|------|---------|--------|
| `static/js/offline/index.js` | Module exports | ~10 |
| `static/js/offline/offline-manager.js` | Main orchestrator | ~150 |
| `static/js/offline/connectivity.js` | Network detection | ~60 |
| `static/js/offline/storage.js` | IndexedDB operations | ~120 |
| `static/css/offline.css` | Offline UI styles | ~80 |

### Existing Files to Modify

| File | Changes |
|------|---------|
| `static/js/map/BeachMap.js` | Initialize OfflineManager, use cached data when offline |
| `templates/beach/map.html` | Add offline banner HTML, sync button in toolbar |
| `blueprints/beach/routes/api/map_data.py` | Add `/api/health` endpoint |

### File Structure

```
static/js/offline/
├── index.js              # Module exports
├── offline-manager.js    # Main orchestrator (~150 lines)
├── connectivity.js       # Network detection (~60 lines)
└── storage.js            # IndexedDB operations (~120 lines)

static/css/
└── offline.css           # Offline UI styles (~80 lines)
```

### No Service Worker Needed

Since this is view-only with manual/auto sync, a simple IndexedDB approach is sufficient. Service Workers add complexity without benefit for this use case.

---

## Implementation Order

1. **Storage layer** - IndexedDB wrapper with stores
2. **Connectivity detection** - Online/offline events + health check
3. **Offline manager** - Orchestrates sync and state
4. **UI components** - Banner, sync button, disabled states
5. **BeachMap integration** - Use cached data when offline
6. **Testing** - Simulate offline scenarios

---

## Out of Scope

- Creating/editing reservations offline (requires complex sync)
- Multi-day caching (only today's data)
- Customer creation offline
- Conflict resolution (view-only eliminates conflicts)
