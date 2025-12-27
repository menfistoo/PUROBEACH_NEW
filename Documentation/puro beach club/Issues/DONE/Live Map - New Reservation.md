# Live Map - New Reservation Issues

## Status: DONE

All issues have been resolved and approved.

---

### Issue 1: Guest type label [DONE] aproved
**Problem:** Guest of the Hotel (but not yet client of the beachclub) is appearing with the label Externo - should be interno.

**Solution:** Added `source: 'hotel_guest'` and `customer_type: 'interno'` to the `/hotel-guests/lookup` API endpoint response.

**Files changed:**
- `blueprints/beach/routes/api/customers.py`

---

### Issue 2: Guest information presentation [DONE] aproved
**Problem:** The information of the guests is not really well presented (contrast; I have the inicials - i don't really need that; and I have a lot of space saying 3 guests in the room but then the actual name of the guests are cuted)

**Solution:**
- Removed the avatar with initials (no longer needed)
- Created a compact inline layout for customer details (room, check-in, check-out)
- Improved text contrast with darker colors
- Names now have full width and won't be truncated
- Guest selector is now more compact

**Files changed:**
- `templates/beach/_new_reservation_panel.html`
- `static/css/new-reservation-panel.css`
- `static/js/map/new-reservation-panel.js`

---

### Issue 3: Auto-update customer count [DONE]
**Problem:** The number of costumers is not being automatically updated. So, I selected two sunbeds to make a reservation (room number 120). This room has three guests. So the program should update the number of guests to three and inform me I have to select three sunbeds.

**Solution:**
- Number of people now auto-updates to match room guest count
- Added capacity warning when guest count exceeds furniture capacity
- Added "Agregar mobiliario" button to allow selecting more furniture
- Panel minimizes AND backdrop hides to allow map interaction

**UPDATE FIX [25/12/25]:** Fixed the issue where the map turned gray when adding furniture. Now the backdrop is hidden when the panel is minimized, allowing proper map interaction.

**UPDATE FIX [25/12/25 17:00]:** Fixed add furniture flow:
- Added event listener in `map.html` to handle `reservation:addMoreFurniture` event
- Pre-selects current furniture when entering add furniture mode
- Overrides "Reservar" button to detect add furniture context
- When additional furniture is selected, calls `newReservationPanel.addFurniture()` to update panel
- Panel correctly restores with updated furniture selection

**UPDATE FIX [25/12/25 17:15]:** Fixed map selection persistence:
- After returning to panel, all furniture in reservation remains selected on map
- Gets furniture IDs from panel state and re-selects them on map

**Files changed:**
- `static/js/map/new-reservation-panel.js`
- `static/css/new-reservation-panel.css`
- `templates/beach/map.html`

---

### Issue 4: Unify modals [DONE]
**Problem:** When I make a reservation for a guest of the hotel that is not a costumer of the beachclub I have a modal but when I make a reservation for a BeachClub costumer I have another. I want to delete the modal for the beaclub costumer, the first one should be universal.

**Solution:**
- Unified the experience: Beach club customers (interno) now get the same treatment as hotel guests
- When selecting an internal customer with a room number, the system fetches room guests
- Shows the guest selector if multiple guests in the room
- Displays check-in/check-out dates in the proper UI (not in notes)
- Can change the selected guest just like with hotel guests

**UPDATE FIX [25/12/25]:** Added filter to remove date patterns (Check-in/Check-out/Entrada/Salida) from notes when displaying internal customers, since dates are now shown in the UI.

**UPDATE FIX [25/12/25 17:00]:** Enhanced date pattern filter to catch Spanish format "Huesped hotel (llegada: YYYY-MM-DD, salida: YYYY-MM-DD)":
- Added regex pattern `/huesped\s+hotel\s*\([^)]*llegada[^)]*salida[^)]*\)/gi`
- Updated existing patterns to handle YYYY-MM-DD date format
- Added explicit "llegada:" pattern match

**Files changed:**
- `static/js/map/new-reservation-panel.js`

---

### Issue 5: Inline customer creation [DONE]
**Problem:** When I search for a guest and there are no results I want the option to create a new costumer right at the modal (exactly same workflow as in new reservation - try to reuse as much code as possible)

**Solution (Updated):**
- When no search results found, a "Crear nuevo cliente externo" button appears
- Clicking the button shows an inline form (same style as /reservations/create)
- Form includes: Nombre, Apellido, Telefono, Email, Idioma
- Pre-fills name from search query if it looks like a name
- Creates customer via API and automatically selects them
- Cleaner UX: button first, then form (not automatic form display)

**Files changed:**
- `static/js/customer-search.js`
- `static/css/customer-search.css`
- `static/js/map/new-reservation-panel.js`
- `templates/beach/_new_reservation_panel.html`

---

## Summary of All Changes

### Backend Changes
- `blueprints/beach/routes/api/customers.py`: Added source/customer_type to hotel-guests/lookup

### Frontend Changes
- `templates/beach/_new_reservation_panel.html`:
  - Compact customer display layout
  - Added inline create customer form
- `static/css/new-reservation-panel.css`:
  - New styles for compact layout
  - Capacity warning styles
  - Inline create form styles
- `static/css/customer-search.css`:
  - Create button styles (divider + button)
- `static/js/map/new-reservation-panel.js`:
  - Unified customer/hotel guest experience
  - Auto-update guest count
  - Capacity warning with add furniture flow (backdrop now hides)
  - Handle new customer creation
  - Filter dates from notes for internal customers
  - Inline create customer form handling
- `static/js/customer-search.js`:
  - "Crear nuevo cliente externo" button when no results
  - onShowCreateForm callback

---

## Testing Checklist

- [x] Select a hotel guest and verify it shows "Interno" badge
- [x] Check the compact customer display layout (no initials, good contrast)
- [x] Select a room with 3+ guests when only 2 sunbeds are selected - verify capacity warning appears
- [x] Click "Agregar mobiliario" and verify map is interactive (not grayed out)
- [x] Select additional furniture and click "Reservar" - verify panel restores with updated furniture and selection remains on map 
- [x] Select an existing beach club customer with a room - verify guest selector appears and dates show in UI (not notes) *(RE-TEST: Fixed date pattern filter)*
- [x] Search for a non-existent customer - verify "Crear nuevo cliente externo" button appears
- [x] Click the button and fill out the form - verify customer is created and selected
