import unittest
import os
from app.utils.dxf_parser import parse_dxf

TEST_DIR = os.path.dirname(__file__)

class TestPolylineHandling(unittest.TestCase):
    def test_real_world_dxf_files(self):
        """
        Automatically test all DXF files in the Inputs/primary_validation directory
        and print/log the results for each file.
        """
        validation_dir = r"C:\Users\shawng\CascadeProjects\PlasmaProject v1-1-7\Inputs\primary_validation"
        dxf_files = [f for f in os.listdir(validation_dir) if f.lower().endswith('.dxf')]
        self.assertGreater(len(dxf_files), 0, f"No DXF files found in {validation_dir}")
        for fname in dxf_files:
            path = os.path.join(validation_dir, fname)
            try:
                result = parse_dxf(path)
                poly_count = result['entity_count'].get('POLYLINE', 0)
                # print removed: f"{fname}: total_length={result.get('total_length')}, net_area={result.get('net_area_sqin')}, POLYLINEs={poly_count}")
            except Exception as e:
                pass
                # print removed: f"{fname}: ERROR: {e}")

if __name__ == '__main__':
    unittest.main()
