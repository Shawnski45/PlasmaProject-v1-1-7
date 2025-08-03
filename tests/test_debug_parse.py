import requests
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "http://localhost:5000"
TEST_FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_files"))
MATERIALS = ["A36 Steel", "Stainless 304", "Aluminum 6061"]
THICKNESSES = [0.25, 0.5, 1.0]

def test_dxf_parse_and_cost():
    if not os.path.exists(TEST_FILES_DIR):
        os.makedirs(TEST_FILES_DIR)
        logging.warning(f"Created test_files directory: {TEST_FILES_DIR}")

    dxf_files = [f for f in os.listdir(TEST_FILES_DIR) if f.lower().endswith('.dxf')]
    if not dxf_files:
        logging.error(f"No .dxf files found in {TEST_FILES_DIR}")
        return

    for dxf_file in dxf_files:
        file_path = os.path.join(TEST_FILES_DIR, dxf_file)
        logging.info(f"Testing file: {file_path}")
        if not os.path.exists(file_path):
            logging.error(f"DXF file not found: {file_path}")
            continue

        with open(file_path, "rb") as f:
            for material in MATERIALS:
                for thickness in THICKNESSES:
                    url = f"{BASE_URL}/debug_parse"
                    files = {"file": (dxf_file, f, "application/dxf")}
                    data = {"material": material, "thickness": str(thickness)}
                    logging.info(f"Uploading {dxf_file} with material={material}, thickness={thickness}...")
                    try:
                        resp = requests.post(url, files=files, data=data, timeout=10)
                        logging.info(f"Status code: {resp.status_code}")
                        if resp.status_code == 200:
                            try:
                                resp_json = resp.json()
                                parse_result = resp_json.get("parse_result", {})
                                cost_result = resp_json.get("cost_result", {})
                                logging.info(f"--- Parse Result for {dxf_file} (Material: {material}, Thickness: {thickness}) ---")
                                logging.info(f"Total Cut Length: {parse_result.get('total_length', 0):.2f} in")
                                logging.info(f"Total Gross Area: {parse_result.get('gross_area_sqin', 0):.2f} sqin")
                                logging.info(f"Total Sell Price: ${cost_result.get('total_sell_price', 0):.2f}")
                            except json.JSONDecodeError as e:
                                logging.error(f"Failed to parse JSON response: {e}")
                                logging.error(f"Response text: {resp.text}")
                            except Exception as e:
                                logging.error(f"Unexpected error processing response: {e}")
                        elif resp.status_code == 500:
                            logging.error(f"Server error: {resp.status_code} - {resp.text}")
                        else:
                            logging.error(f"Request failed: {resp.status_code} - {resp.text}")
                    except requests.RequestException as e:
                        logging.error(f"Network error: {e}")
                    finally:
                        f.seek(0)

if __name__ == "__main__":
    test_dxf_parse_and_cost()