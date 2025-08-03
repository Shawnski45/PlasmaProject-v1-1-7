# PlasmaProject v1-1-7 MVP Fixes - 7/10/2025
## Critical (MVP Blockers)
1. **Infinite Bounds in `dxf_parser.py`**
   - File: `app/utils/dxf_parser.py` (lines 602–609)
   - Issue: Infinite `gross_area_sqin` (e.g., `307-003_PL01.dxf`) breaks pricing.
   - Fix: Validate bounds (<1e6), return error preview.
   - Test: Update `test_dxf_parse_batch.py` to assert finite bounds.
2. **Blank Previews in `customer_index.html`**
   - File: `templates/customer_index.html` (lines 364–470)
   - Issue: Empty `preview` data causes blank canvases, breaking UX.
   - Fix: Ensure `uploadFiles` calls `renderPreviews`; validate `preview` in `dxf_parser.py`.
   - Test: Update `test_ui_mimicry.py` to check non-empty canvases.
3. **Pricing Errors in `costing.py`**
   - File: `app/utils/costing.py` (lines 35–53)
   - Issue: Zero division risks (`cut_speed=0`, `material_efficiency=0`).
   - Fix: Add validation, update `inputs.csv` for all thicknesses.
   - Test: Create `test_costing.py` for edge cases.

## High Priority (UX/Polish)
1. **Missing Visual Cues in `customer_index.html`**
   - File: `templates/customer_index.html` (lines 140–150)
   - Issue: No red asterisks, dynamic `calculateButton` color, or gray `buyButton`.
   - Fix: Add CSS for asterisks, update `calculatePrices` for button color.
   - Test: Update `test_ui_mimicry.py` to verify cues.

## Medium Priority (Production Readiness)
1. **Database Context in `conftest.py`**
   - File: `tests/conftest.py` (lines 25–34)
   - Issue: `RuntimeError: Working outside of application context`.
   - Fix: Wrap schema check in `app.app_context()`.
   - Test: Run `pytest` to confirm no context errors.

## Low Priority (Optimization)
1. **Verbose Logging in `dxf_parser.py`, `costing.py`**
   - File: `app/utils/dxf_parser.py` (lines 326, 448), `app/utils/costing.py` (line 92)
   - Issue: Slows parsing/pricing for large DXFs.
   - Fix: Toggle with `VERBOSE_LOGGING=0`.
   - Test: Check `error.log` size after processing 10 DXFs.