## Status: ALL COMPLETED

---

### Issue 1: Guest type label [DONE]
**Problem:** Guest of the Hotel (but not yet client of the beachclub) is appearing with the label Externo - should be interno.

**Solution:** Added `source: 'hotel_guest'` and `customer_type: 'interno'` to the `/hotel-guests/lookup` API endpoint response. This ensures that when switching between guests in the room selector, the correct type is displayed.

**Files changed:**
- `blueprints/beach/routes/api/customers.py`

---

### Issue 2: Guest information presentation [DONE]
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
- `static/js/map/new-reservation-panel.js

---

---

### Issue 4: Unify modals [DONE]
**Problem:** When I make a reservation for a guest of the hotel that is not a costumer of the beachclub I have a modal but when I make a reservation for a BeachClub costumer I have another. I want to delete the modal for the beaclub costumer, the first one should be universal.

**Solution:**
- Unified the experience: Beach club customers (interno) now get the same treatment as hotel guests
- When selecting an internal customer with a room number, the system fetches room guests
- Shows the guest selector if multiple guests in the room
- Displays check-in/check-out dates in the proper UI (not in notes)
- Can change the selected guest just like with hotel guests

**Files changed:**
- `static/js/map/new-reservation-panel.js` (modified `autoFillCustomerData` to be async and unified)

---

### Issue 5: Inline customer creation [DONE]
**Problem:** When I search for a guest and there are no results I want the option to create a new costumer right at the modal (exactly same workflow as in new reservation - try to reuse as much code as possible)

**Solution:**
- Added inline customer creation form that appears when search has no results
- Form includes: Name, Surname, Phone, Email, Language, Number of guests
- Pre-fills name from search query if it looks like a name
- Creates external customer via API and automatically selects them
- Sets num_people from the form

**Files changed:**
- `static/js/customer-search.js`
- `static/css/customer-search.css`
- `static/js/map/new-reservation-panel.js`

---

## Summary of All Changes

### Backend Changes
- `blueprints/beach/routes/api/customers.py`: Added source/customer_type to hotel-guests/lookup

### Frontend Changes
- `templates/beach/_new_reservation_panel.html`: Compact customer display layout
- `static/css/new-reservation-panel.css`: New styles for compact layout, capacity warning
- `static/css/customer-search.css`: Inline creation form styles
- `static/js/map/new-reservation-panel.js`:
  - Unified customer/hotel guest experience
  - Auto-update guest count
  - Capacity warning with add furniture flow
  - Handle new customer creation
- `static/js/customer-search.js`: Inline customer creation form
