# Beach Club Package Configuration Mockups

Interactive HTML mockups for the Payment & Pricing System - Package Configuration feature.

## 📁 Files

```
mockups/
├── css/
│   └── beach-club-design.css     # Design system styles
├── packages/
│   ├── package-list.html         # Package list/table view
│   ├── package-form.html         # Package create/edit form
│   └── screenshots/              # Screenshots directory (empty)
└── README.md                     # This file
```

---

## 🎨 Design System

### Colors Used

| Color | Hex | Usage |
|-------|-----|-------|
| Primary Gold | `#D4AF37` | Primary buttons, highlights, active states |
| Deep Ocean | `#1A3A5C` | Headers, navigation, text |
| Warm Sand | `#F5E6D3` | Card headers, backgrounds |
| Success | `#4A7C59` | Active badges, success messages |
| Error | `#C1444F` | Error messages, required fields |
| Warning | `#E5A33D` | Warning badges, alerts |

### Typography
- **Font:** Inter (Google Fonts)
- **Headings:** Deep Ocean (#1A3A5C), 600 weight
- **Body:** Gray 800 (#1F2937)

### Components
- **Buttons:** Gold gradient primary, white with gold border secondary
- **Cards:** White background, 12px border-radius, subtle shadow
- **Tables:** Sand header, gold bottom border, hover states
- **Forms:** 2px borders, gold focus states, inline validation

---

## 📄 Mockup Pages

### 1. Package List (`package-list.html`)

**Features:**
- ✅ Responsive table with 5 sample packages
- ✅ Color-coded badges (Active/Inactive, Customer Type)
- ✅ Filter controls (Search, Customer Type, Status)
- ✅ Action buttons (Edit, Toggle Active)
- ✅ Pagination controls
- ✅ Success alert (auto-dismisses after 5 seconds)
- ✅ Help card with package information

**Sample Data:**
1. Paquete Premium (Active, Per Person, €89.00, 2-4 pax, Externo)
2. Día de Playa Familiar (Active, Per Package, €250.00, 1-6 pax, Ambos)
3. Paquete Balinesa VIP (Active, Per Person, €150.00, 2-2 pax, Externo)
4. Paquete Temporada Baja (Inactive, Per Person, €45.00, 1-4 pax, Externo)
5. Paquete Huéspedes Premium (Active, Per Package, €25.00, 1-2 pax, Interno)

**Interactive Elements:**
- Toggle package status (confirmation dialog)
- Auto-dismiss alerts
- Hover effects on table rows
- Click edit to navigate to form

---

### 2. Package Form (`package-form.html`)

**Features:**
- ✅ Organized into 5 sections with dividers
- ✅ Real-time validation (capacity constraints)
- ✅ Live price calculation preview
- ✅ Custom styled form controls
- ✅ Required field indicators (*)
- ✅ Help text for each field
- ✅ Responsive layout

**Sections:**

#### 1. Información General
- Package Name (required)
- Description (textarea)
- Display Order

#### 2. Precio y Capacidad
- Base Price (required, €)
- Price Type (radio: Per Package / Per Person)
- Capacity (min/standard/max with validation)
- **Live Price Preview** - Updates as you type

#### 3. Aplicabilidad
- Customer Type (dropdown: Interno/Externo/Ambos)
- Zone restriction (optional)
- Furniture types included (checkboxes)

#### 4. Vigencia
- Valid From (date picker)
- Valid Until (date picker)
- Info alert about seasonal packages

#### 5. Estado
- Active toggle switch

**Validation:**
- ✅ Capacity constraint: `min ≤ standard ≤ max`
- ✅ Required fields marked with *
- ✅ Real-time error feedback
- ✅ Form submission validation

**Interactive Features:**
- Real-time price calculation
- Capacity validation with visual feedback
- Preview button (shows alert in mockup)
- Save button with success simulation

---

## 🚀 How to Use

### View Mockups Locally

1. **Open in browser:**
   ```bash
   cd /home/user/PUROBEACH_NEW/mockups/packages

   # Open in your default browser (Linux)
   xdg-open package-list.html

   # Or just drag files into browser
   ```

2. **Or use a local server (recommended):**
   ```bash
   # Python 3
   cd /home/user/PUROBEACH_NEW/mockups
   python3 -m http.server 8000

   # Then open: http://localhost:8000/packages/package-list.html
   ```

### Navigation

- **Package List** → Click "Nuevo Paquete" or any "Edit" button → **Package Form**
- **Package Form** → Click "Volver a Lista" or "Cancelar" → **Package List**

### Test Scenarios

#### Test 1: Create Package (Per Person)
1. Open `package-form.html`
2. Fill: Name = "Test Package", Price = €50.00
3. Select "Por Persona"
4. Set capacity: Min=1, Standard=2, Max=4
5. Watch price preview update automatically
6. Click "Guardar Paquete"

#### Test 2: Capacity Validation
1. Open `package-form.html`
2. Set: Min=4, Standard=2, Max=1 (invalid)
3. See red borders and error message
4. Fix: Min=1, Standard=2, Max=4 (valid)
5. Error clears automatically

#### Test 3: Toggle Package Status
1. Open `package-list.html`
2. Click toggle button on any package
3. See confirmation dialog
4. Click OK to simulate status change

---

## 📸 Screenshots

To take screenshots for documentation:

1. Open mockup in browser
2. Use browser dev tools (F12) → Device Toolbar
3. Test responsive views:
   - Desktop: 1920×1080
   - Tablet: 768×1024
   - Mobile: 375×667

Screenshots should be saved in `mockups/packages/screenshots/`:
- `package-list-desktop.png`
- `package-list-mobile.png`
- `package-form-section1.png`
- `package-form-section2.png`
- `package-form-validation.png`

---

## 🔧 Customization

### Modify Colors

Edit `mockups/css/beach-club-design.css`:

```css
:root {
    --primary-gold: #D4AF37;       /* Change primary color */
    --deep-ocean: #1A3A5C;         /* Change header color */
    /* ... */
}
```

### Add More Sample Packages

Edit `package-list.html`, add rows in `<tbody>`:

```html
<tr>
    <td>6</td>
    <td><strong>Your Package Name</strong></td>
    <!-- ... -->
</tr>
```

### Modify Form Fields

Edit `package-form.html`, add fields in appropriate section:

```html
<div class="col-md-6">
    <label for="newField" class="form-label">New Field</label>
    <input type="text" class="form-control" id="newField">
</div>
```

---

## ✅ Validation & Features

### Client-Side Validation Implemented

- ✅ Required field checking
- ✅ Capacity constraint validation (`min ≤ standard ≤ max`)
- ✅ Real-time validation feedback
- ✅ Number field min/max constraints
- ✅ Date field formatting

### Interactive Features

- ✅ Live price calculation preview
- ✅ Form field dependencies (price type affects preview)
- ✅ Toggle package active/inactive
- ✅ Confirmation dialogs
- ✅ Success message auto-dismiss
- ✅ Responsive sidebar navigation

---

## 📝 Notes

### What This Mockup Shows

✅ **UI/UX Design** - Visual design and layout
✅ **User Flow** - Navigation between list and form
✅ **Form Validation** - Real-time validation logic
✅ **Price Calculation** - Preview calculation examples
✅ **Responsive Design** - Bootstrap 5 grid system

### What This Mockup Does NOT Include

❌ **Backend Integration** - No real API calls
❌ **Database** - Sample data is hardcoded
❌ **Authentication** - No login/session handling
❌ **Server-Side Validation** - Only client-side
❌ **Image Uploads** - No file handling

### For Production Implementation

When implementing these designs in the actual Beach Club system:

1. **Use existing templates structure** from `/templates/beach/config/`
2. **Integrate with Flask routes** from `/blueprints/beach/routes/config/packages.py`
3. **Connect to models** from `/models/package.py`
4. **Add server-side validation** in route handlers
5. **Implement AJAX** for real-time price calculation
6. **Add CSRF tokens** to all forms
7. **Apply permissions** checks (`@permission_required('beach.config.packages.create')`)

---

## 🎯 Next Steps

After reviewing mockups:

1. **Get feedback** from stakeholders on UI/UX
2. **Refine design** based on feedback
3. **Start Phase 1** implementation (database & models)
4. **Implement Phase 2** (configuration UI based on these mockups)
5. **Test integration** with existing beach club system

---

## 📞 Support

Questions or suggestions about these mockups?
- Review the design specs in `/docs/DEVELOPMENT_PLAN.md`
- Check the design system in `DESIGN_SYSTEM.md`
- Refer to Bootstrap 5 documentation for components

---

**Created:** 2025-12-25
**Version:** 1.0
**Status:** Ready for Review
