import os
import csv
import sys
import sys
import os
# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from app.utils import dxf_parser

# Directory containing DXF files
DXF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Inputs', 'secondary_test_samples')

# Output CSV file
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), 'dxf_entity_inventory.csv')

def main():
    files = [f for f in os.listdir(DXF_DIR) if f.lower().endswith('.dxf')]
    if not files:
        print(f"No DXF files found in {DXF_DIR}")
        return

    # Collect all possible entity types from dxf_parser
    entity_types = ["LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE", "INSERT", "SPLINE", "ELLIPSE", "HATCH", "OTHER"]
    results = []

    for fname in files:
        path = os.path.join(DXF_DIR, fname)
        try:
            # Only need entity_count from parse_dxf
            result = dxf_parser.parse_dxf(path)
            entity_count = result.get('entity_count') if isinstance(result, dict) else None
            if entity_count is None:
                print(f"Warning: {fname} did not return entity_count.")
                entity_count = {k: 'ERR' for k in entity_types}
        except Exception as e:
            print(f"Error parsing {fname}: {e}")
            entity_count = {k: 'ERR' for k in entity_types}
        row = {'file': fname}
        for etype in entity_types:
            row[etype] = entity_count.get(etype, 0)
        results.append(row)

    # Write CSV
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['file'] + entity_types)
        writer.writeheader()
        writer.writerows(results)
    print(f"Inventory complete. Results written to {OUTPUT_CSV}")
    # Also print a summary table
    print("\nSummary:")
    print(f"{'File':40} " + " ".join([f"{t:8}" for t in entity_types]))
    for row in results:
        print(f"{row['file'][:40]:40} " + " ".join([f"{str(row[t]):8}" for t in entity_types]))

if __name__ == '__main__':
    main()
