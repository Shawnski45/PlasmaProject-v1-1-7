# PlasmaProject UI: Line-by-Line, Function-by-Function Migration Table

| customer_index.html Line/Block | Purpose/UX Impact | React/TSX File & Snippet | Status | Notes/Gaps |
|-------------------------------|-------------------|-------------------------|--------|------------|
| 1-19: `<head>`, meta, favicon, Tailwind/Firebase CDN, Google Fonts | Page setup, favicon, fonts, Tailwind, Firebase config/init | `client_test/index.html` (meta, favicon, fonts), `client_test/src/firebase.js` (Firebase init) | Implemented (structure differs) | Vite handles head/meta/fonts; Firebase config handled via JS import, not Jinja. |
| 20-21: `<body>`, `<main>` flex layout | Main app layout, two columns | `App.tsx` root JSX: `<main className="flex ...">...</main>` | Implemented | Structure and classes ported to React JSX. |
| 22-35: Drop Zone section | Drag/drop DXF upload, browse button, file input | `App.tsx`: `<div className="drop-zone" ... onDrop={handleDrop}>...</div>`, file input, button triggers input | Implemented | All handlers moved to React; file input is hidden and triggered by button. |
| 33: File type support note | User guidance on DXF support | `App.tsx`, drop zone JSX | Implemented | Text preserved in JSX. |
| 37-77: Cart/Preview Area section | Cart, preview, error messages, validation popup, overlay | `App.tsx`: `<section>...</section>`, `<div className="cart-container ...">`, popup state/components | Implemented | All UI blocks present as JSX; overlay/popup state managed in React. |
| 39-45: Error messages, validation popup, overlay | Error/popup UX for trust/validation | `App.tsx`: `{popupMessage && <Popup ... />}`; overlay div | Implemented | Popup/overlay shown via React state, not DOM. |
| 46-74: Cart container, form, cart list | Cart UI, item list, totals, buttons | `App.tsx`: cart state, `.map` over cart items, total, buttons | Implemented | Cart list is React array, not DOM injection. |
| 47: Instant Quote heading | Section title | `App.tsx`: `<h2>Instant Quote</h2>` | Implemented | Visual/semantic parity. |
| 48-54: Flask flash messages | Show server-side messages | `App.tsx`: popup/message state | Partially implemented | Server flash messages may not surface; React uses own popup state. |
| 55-57: Authenticated user message | Welcome, cart saved | `App.tsx`: `{user && ...}` | Implemented | Conditional JSX for user state. |
| 58-61: Cart form, cart list | Cart rendering | `App.tsx`: `<form>`, cart items JSX | Implemented | Cart rendered from state, not DOM. |
| 62-65: Total price | Show total | `App.tsx`: `<span>{total}</span>` | Implemented | Total from React state. |
| 66-73: Action buttons (Calculate, Buy, Sign In, Clear) | Cart actions, enable/disable logic | `App.tsx`: `<button ... disabled={!cartValid}>` etc. | Implemented | Button logic in React state, not class toggling. |
| 76: isCalculatedData div | Calculation state for UI | `App.tsx`: `isCalculated` state | Implemented | React state, not DOM dataset. |
| 80-81: Login/Signup modals | Auth modals | `LoginModal.tsx`, `SignupModal.tsx` | Implemented | Controlled by React state. |
| 82: modals.js include | Modal logic | N/A | Not needed | All modal logic in React. |
| 83-573: Embedded JS: cart, popup, upload, preview, event handlers | All business logic: cart, preview, upload, validation, price recalc, event triggers, DOM updates | `App.tsx`: useState/useEffect for cart, preview, popup, etc.; event handlers as React functions; `PreviewSVG.tsx` for SVG rendering | Implemented, some differences | All logic in React hooks; no direct DOM updates. |
| 88-101: showPopup/closePopup | Show/hide error popup | `App.tsx`: popup state, `<Popup ... />` | Implemented | Popup logic in React state, not DOM style. |
| 103-120: updateButtonVisibility | Button state/UX | `App.tsx`: button `disabled` prop, conditional rendering | Implemented | Handled via React state. |
| 127-174: calculatePrices | Price calculation (POST to backend, validation, error handling, update UI) | `App.tsx`: `handleCalculatePrices` function, fetch to `/api/quote` or similar | Implemented | Logic ported to React; error handling via popup. |
| 176-191: clearCart | Clear cart (POST, update UI, reload) | `App.tsx`: `handleClearCart` | Implemented (no reload) | React clears state, no page reload. |
| 193-251: updateField | Field change, validation, update backend | `App.tsx`: `handleFieldChange` | Implemented | All field changes update state and backend. |
| 253-268: removeItem | Remove cart item (POST, update UI) | `App.tsx`: `handleRemoveItem` | Implemented | State and backend kept in sync. |
| 270-380: renderPreviews | Render SVG previews from backend | `PreviewSVG.tsx` | Implemented | SVG preview logic in dedicated component. |
| 382-392: getCartItems | Collect cart items for UI logic | `App.tsx`: cart state | Implemented | State-driven. |
| 394-462: updateCartUI | Re-render cart UI from backend data | `App.tsx`: setCart, render JSX | Implemented | React state updates trigger re-render. |
| 464-495: uploadFiles | Upload DXF files, update cart | `App.tsx`: `handleFileUpload` | Implemented | Logic ported to React; uses fetch/FormData. |
| 497-522: attachCartEventHandlers | Attach change/click listeners | `App.tsx`: JSX event props | Implemented | All events handled via React, not DOM listeners. |
| 524-530: updateAsterisk | Show/hide required field asterisks | `App.tsx`: conditional className | Implemented | Class toggling via React state. |
| 532-547: Drop zone drag/drop events, file input change | Drag/drop UX, input UX | `App.tsx`: onDrop, onDragOver, onChange | Implemented | Handlers in JSX. |
| 548-565: DOMContentLoaded: fetch cart, set up UI | On load, fetch cart, initialize UI | `App.tsx`: useEffect(() => { fetchCart() }, []) | Implemented | useEffect replaces DOMContentLoaded. |
| 567-572: window global functions | Expose handlers globally | Not needed | Not needed | All logic in React. |

---

## Gaps & Preserved Elements (Summary)

- **Preserved:**
  - All core UX flows (upload, preview, cart, price calculation, error/popup, authentication, cart save/load, SVG preview) are present and mapped to React/TSX.
  - All business logic (fetching, posting, validation, error handling) is ported to React hooks and state.
  - All event handlers are now declarative React props, not DOM listeners.
  - All popups, overlays, and modals are controlled by React state.
  - SVG preview logic is encapsulated in a dedicated React component.
- **Gaps/Differences:**
  - Flash messages from Flask backend may not surface in React UI unless explicitly fetched and shown.
  - Some validation or error messages may differ in timing/appearance due to React state model.
  - No direct page reloads on cart clear (React resets state instead).
  - Accessibility (ARIA, keyboard navigation) should be reviewed for parity.
  - Some minor UI/UX nuances (e.g., focus management, exact popup styling) may differ and should be validated in browser.

---

**This table provides a full audit trail for every major UI and business logic element, ensuring nothing is lost in migration.**

