---
allowed-tools: Grep, Read, Edit, Write, Glob, Bash
description: Guidelines for creating or modifying UI components following the project design system
---

You are implementing frontend UI. Follow these design guidelines strictly.

## Before Starting

**IMPORTANT:** Before implementing any UI, ensure you have:
1. Read the project's DESIGN_SYSTEM.md (if it exists)
2. Understood the color palette and typography
3. Reviewed existing component patterns

## Core Principles

### Language Convention (if applicable)
- **Code (English):** Variables, functions, classes, CSS classes, IDs
- **UI Text (localized):** Labels, buttons, messages, errors, tooltips

### Color Usage
- Define colors as CSS variables
- Never use magic hex values inline
- Follow the design system palette

### Typography
- Use the project's font stack
- Follow the established type scale
- Maintain consistent line heights

## Component Patterns

### Buttons
```css
/* Primary action - prominent */
.btn-primary {
    /* Use design system primary color */
}

/* Secondary action - less prominent */
.btn-secondary {
    /* Use design system secondary color */
}
```

### Cards
- White/light background
- Consistent border-radius
- Subtle shadow for elevation

### Forms
- Clear labels above inputs
- Visible focus states
- Validation feedback

### Tables
- Header styling distinct from body
- Alternating row colors or hover states
- Responsive considerations

## Spacing System

Use a consistent spacing scale (e.g., 4px base):
- Small gaps: 4px, 8px
- Medium gaps: 12px, 16px
- Large gaps: 24px, 32px

## Accessibility Requirements

1. **Color Contrast**: Minimum 4.5:1 for text
2. **Focus States**: Visible on all interactive elements
3. **Form Labels**: Every input must have a label
4. **Alt Text**: All images need descriptions
5. **ARIA**: Use for icon-only buttons

```html
<!-- Icon button with ARIA -->
<button aria-label="Edit item">
    <i class="icon-edit"></i>
</button>
```

## Checklist Before Implementing

- [ ] Colors match design system
- [ ] Typography uses correct fonts/sizes
- [ ] Components follow established patterns
- [ ] Forms have proper labels
- [ ] Interactive elements have hover/focus states
- [ ] Accessibility requirements met
- [ ] Responsive breakpoints considered

## Instructions

When implementing UI:
1. First read any existing design system documentation
2. Review similar existing components for patterns
3. Follow the color palette exactly
4. Ensure accessibility compliance
5. Test at multiple screen sizes

If no design system exists, establish consistent patterns and document them.
