import os
import io
import json
import pytest
from app import create_app, db
from app.models import OrderItem

PRIMARY_VALIDATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Inputs/primary_validation'))

def print_metric_row(row_dict):
    # print removed: "| {filename:35} | {total_length:12.2f} | {entity_counts:20} | {net_area:10.2f} | {gross_area:10.2f} | {preview_types:18} | {contour_count:13} | {preview_count:13} | {warnings:40} |".format(**row_dict))
    pass
@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_cart_parsing_report(client):
    # print removed: "TEST IS RUNNING", flush=True)

    with client.application.app_context():
        dxf_files = [f for f in os.listdir(PRIMARY_VALIDATION_DIR) if f.lower().endswith('.dxf')]
        # print removed: f"DXF files found: {dxf_files}", flush=True)
        assert dxf_files, f"No DXF files found in {PRIMARY_VALIDATION_DIR}"
        files = []
        for dxf_file in dxf_files:
            with open(os.path.join(PRIMARY_VALIDATION_DIR, dxf_file), 'rb') as f:
                files.append((io.BytesIO(f.read()), dxf_file))
        data = {
            'material': 'A36 Steel',
            'thickness': 0.25
        }
        multi_file_data = []
        for file_obj, filename in files:
            multi_file_data.append(('files[]', (file_obj, filename)))
        from werkzeug.datastructures import MultiDict
        post_data = MultiDict(list(data.items()) + multi_file_data)
        response = client.post('/', data=post_data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200, f"Failed to upload files: status {response.status_code}"

        # print removed: "\n| {0:35} | {1:12} | {2:20} | {3:10} | {4:10} | {5:18} | {6:13} | {7:13} | {8:40} |".format(
        # print removed: "|" + "-"*35 + "|" + "-"*12 + "|" + "-"*20 + "|" + "-"*10 + "|" + "-"*10 + "|" + "-"*18 + "|" + "-"*13 + "|" + "-"*13 + "|" + "-"*40 + "|")

        def diagnose_preview_issue(preview, warnings, entity_counts, total_length, net_area, gross_area):
            diag = []
            if not preview:
                diag.append("Preview is empty.")
            else:
                # Show up to 2 preview objects
                diag.append(f"Sample preview object(s): {str(preview[:2])[:200]}")
                # Check for error/warning objects
                errors = [p for p in preview if p.get('type') in ('error','warning')]
                if errors:
                    diag.append(f"Errors/warnings in preview: {errors}")
                # Accept both 'geometry' and 'points' as valid for preview
                for obj in preview[:2]:
                    if 'geometry' in obj and not obj['geometry']:
                        diag.append(f"Preview object has empty geometry: {obj}")
                    elif 'points' in obj and not obj['points']:
                        diag.append(f"Preview object has empty points: {obj}")
                    elif 'geometry' not in obj and 'points' not in obj:
                        diag.append(f"Preview object missing geometry/points: {obj}")
            if entity_counts in (0, "0", "?"):
                diag.append("Entity count is zero or missing.")
            if total_length == 0:
                diag.append("Total cut length is zero.")
            if net_area == 0:
                diag.append("Net area is zero.")
            if gross_area == 0:
                diag.append("Gross area is zero.")
            if warnings:
                diag.append(f"Other warnings: {'; '.join(warnings)}")
            return " | ".join(diag)

        for dxf_file in dxf_files:
            warnings = []
            item = OrderItem.query.filter_by(part_number=dxf_file).first()
            if item is None:
                row = dict(filename=dxf_file, total_length=0, entity_counts="N/A", net_area=0, gross_area=0, preview_types="Not uploaded", contour_count="-", preview_count=0, warnings="OrderItem not created!")
                print_metric_row(row)
                continue
            try:
                preview = json.loads(item.preview) if item.preview else []
            except Exception:
                preview = []
                warnings.append("Preview JSON decode error")
            # Accept both 'polyline' and 'spline' as valid preview types for SPLINEs
            preview_types = set(p.get('type', 'unknown') for p in preview) if preview else set()
            if 'polyline' in preview_types and all('points' in p for p in preview if p.get('type') == 'polyline'):
                preview_types.add('spline')  # Treat 'polyline' with points as valid SPLINE preview
            entity_counts = getattr(item, 'entity_count', "?")
            if isinstance(entity_counts, dict):
                entity_counts = json.dumps(entity_counts)
            total_length = getattr(item, 'length', 0)
            net_area = getattr(item, 'net_area_sqin', 0)
            gross_area = getattr(item, 'gross_area_sqin', 0)
            preview_count = len(preview)
            contour_count = getattr(item, 'pierce_count', '-')
            if preview_count == 0:
                warnings.append("Preview empty")
                diag = diagnose_preview_issue(preview, warnings, entity_counts, total_length, net_area, gross_area)
                raise AssertionError(f"Preview missing/empty for {filename}: {diag}")
            if not preview_types or preview_types == {"error"} or preview_types == {"warning"}:
                warnings.append(f"Preview types: {', '.join(preview_types) if preview_types else 'None'}")
                diag = diagnose_preview_issue(preview, warnings, entity_counts, total_length, net_area, gross_area)
                raise AssertionError(f"Preview error/warning for {filename}: {diag}")
            if total_length == 0:
                warnings.append("Total length is zero")
            if net_area == 0:
                warnings.append("Net area is zero")
            if gross_area == 0:
                warnings.append("Gross area is zero")
            row = dict(
                filename=dxf_file,
                total_length=total_length,
                entity_counts=entity_counts,
                net_area=net_area,
                gross_area=gross_area,
                preview_types=", ".join(preview_types) if preview_types else "None",
                contour_count=contour_count,
                preview_count=preview_count,
                warnings="; ".join(warnings) if warnings else ""
            )
            print_metric_row(row)
            # Print detailed diagnosis for preview failures
            if preview_count == 0 or not preview_types or preview_types == {"error"} or preview_types == {"warning"} or total_length == 0 or net_area == 0 or gross_area == 0:
                # print removed: f"  >> DIAGNOSE: {diagnose_preview_issue(preview, warnings, entity_counts, total_length, net_area, gross_area)}\n")
                # Enhanced debug logging for failing previews
                # Print raw preview JSON (truncated)
                preview_json_str = json.dumps(preview)
                # print removed: f"  >> DEBUG: Raw preview JSON (truncated): {preview_json_str[:500]}{' ...' if len(preview_json_str) > 500 else ''}")
                # Per-entity diagnostics
                for idx, obj in enumerate(preview):
                    entity_type = obj.get('type', 'UNKNOWN')
                    geometry = obj.get('geometry')
                    # print removed: f"    Preview[{idx}]: type={entity_type}, geometry={'PRESENT' if geometry else 'MISSING'}")
                    if not geometry:
                        # print removed: f"      >> MISSING GEOMETRY for entity type {entity_type} in preview[{idx}]")
                        pass
                    # print removed: f"  >> Entity counts by type: {entity_counts}"
                pass
if __name__ == "__main__":
    import pytest
    import sys
    sys.exit(pytest.main([__file__]))
