# 🔔 Beach Club Notification System — Project Plan

**Goal:** Real-time notifications for valets and staff when reservation states change, new reservations are created, or actions are needed.

**Timeline:** Feb 2 → Mar 12 (hotel opening)
**Status:** Planning

---

## Phase 1: Backend Foundation (Week 1: Feb 3-9)

### 1.1 Event System
- Create `models/notification.py` — notification model with:
  - `id` (UUID), `type`, `title`, `body`, `created_at`
  - `target_role` (valet, admin, reception, all)
  - `reservation_id` (FK, nullable)
  - `furniture_id` (FK, nullable)
  - `is_read` (per-user tracking)
  - `priority` (info, warning, urgent)
- DB migration for `notifications` + `notification_reads` tables

### 1.2 Event Triggers
Emit notifications on:
- ✅ New reservation created
- 🔄 Reservation state changed (e.g., confirmed → checked-in)
- 🪑 Furniture reassigned
- ❌ Reservation cancelled
- ⏰ Upcoming check-in (30 min before)
- 🧹 Checkout needed (state → needs cleanup)

### 1.3 SSE Endpoint
- `GET /api/notifications/stream` — Server-Sent Events endpoint
- Authenticated per user/role
- Sends JSON events with notification data
- Heartbeat every 30s to keep connection alive

---

## Phase 2: Frontend Integration (Week 2: Feb 10-16)

### 2.1 Notification Client (JS)
- `static/js/notifications/NotificationClient.js`
  - Connect to SSE stream
  - Track seen notification IDs (dedup in Set, max 200)
  - Show toast + optional sound for urgent
  - Badge counter in nav bar

### 2.2 Notification Bell UI
- Bell icon in navbar with unread count badge
- Dropdown panel with recent notifications
- Click → navigate to relevant reservation/furniture
- Mark as read on click, "mark all read" button

### 2.3 Valet View
- Simplified notification panel for valets
- Only shows notifications targeted at `valet` role
- Large, touch-friendly cards for mobile/tablet use
- Audio alert for new check-ins and urgent items

---

## Phase 3: Smart Notifications (Week 3: Feb 17-23)

### 3.1 Anti-Duplicate Logic
- Each event gets a unique `event_key` = `{type}:{reservation_id}:{state}:{timestamp_minute}`
- Client tracks last 200 event_keys in localStorage
- Server deduplicates within 60s window
- If same reservation changes state 3x in 1 minute → only latest notification sent

### 3.2 Role-Based Filtering
- **Admin/Reception:** All notifications
- **Valet:** Only assigned zone notifications + new check-ins + cleanup needed
- **Manager:** Summary notifications (hourly digest option)

### 3.3 Quiet Hours / Priority
- `info`: Silent, badge only
- `warning`: Toast notification
- `urgent`: Toast + sound + persistent until acknowledged

---

## Phase 4: Testing & Polish (Week 4: Feb 24-Mar 2)

### 4.1 Testing
- Unit tests for notification model
- Integration tests for SSE endpoint
- Manual testing: create reservation → verify valet receives notification
- Load test: 50 concurrent SSE connections
- Mobile browser testing (iOS Safari, Android Chrome)

### 4.2 Polish
- Notification preferences page (per user)
- Sound selection
- Browser notification permission (Push API fallback for when tab not focused)
- Connection recovery (auto-reconnect SSE on disconnect)

---

## Phase 5: Production Deploy (Week 5: Mar 3-9)

### 5.1 Staging Test
- Deploy to test server (beachclubinterno.duckdns.org)
- Staff training session
- Collect feedback

### 5.2 Production
- Deploy to production server (192.145.37.218)
- Monitor performance
- Fine-tune notification frequency based on real usage

---

## Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Transport | SSE (not WebSocket) | Simpler, works through proxies, one-way is enough |
| Dedup | Client-side + server-side | Belt and suspenders |
| Storage | SQLite (same DB) | No need for Redis/separate DB |
| Sound | Web Audio API | No external dependencies |
| Mobile | Responsive CSS + PWA | No native app needed |

## Files to Create/Modify

### New Files
- `models/notification.py`
- `blueprints/beach/routes/api/notifications.py`
- `static/js/notifications/NotificationClient.js`
- `static/js/notifications/NotificationUI.js`
- `static/js/notifications/sounds/` (alert sounds)
- `templates/beach/components/notification-bell.html`
- `database/migrations/notifications.py`

### Modified Files
- `models/reservation.py` — emit events on state change
- `blueprints/beach/routes/api/map_res_create.py` — emit on create
- `blueprints/beach/routes/api/map_res_edit_fields.py` — emit on edit
- `templates/beach/base.html` — add notification bell
- `static/js/map/BeachMap.js` — integrate notification refresh
- `database/schema.py` — add notification tables

---

## Success Criteria

- [ ] Valet receives notification within 3 seconds of state change
- [ ] No duplicate notifications for same event
- [ ] Works on mobile (tablet at pool)
- [ ] Survives connection drops (auto-reconnect)
- [ ] Does not degrade map performance
- [ ] Zero notifications missed during 8-hour shift
