import os
import logging
import requests
from requests.sessions import Session

# Configure logging for the test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# --- CONFIGURATION ---
BASE_URL = 'http://127.0.0.1:5000'  # Change if your Flask app runs elsewhere
TEST_DXF_PATH = os.path.join(
    os.path.dirname(__file__), '../Inputs/primary_validation/Zz343-batman-wall-decor.dxf'
)

# --- TEST PARAMETERS ---
MATERIAL = 'A36 Steel'
THICKNESS = '0.25'
QUANTITY = '1'


def test_database_flow():
    """
    Simulate uploading a DXF, setting material/thickness/quantity, and pressing Calculate.
    Log all steps and responses for validation.
    """
    session = Session()
    session.headers.update({'User-Agent': 'DatabaseValidationTest/1.0'})

    # 1. Upload DXF file
    logging.info('Uploading DXF file: %s', TEST_DXF_PATH)
    with open(TEST_DXF_PATH, 'rb') as f:
        files = {'file': (os.path.basename(TEST_DXF_PATH), f, 'application/dxf')}
        response = session.post(f'{BASE_URL}/parse_dxf', files=files)
    logging.info('Upload response: %s', response.text)
    assert response.ok, f"Upload failed: {response.text}"
    data = response.json()
    assert 'items' in data and len(data['items']) > 0, 'No items returned after upload.'
    cart_uid = data['items'][0]['cart_uid']

    # 2. Set material, thickness, quantity
    # Update cart item fields individually as required by /cart_items endpoint
    for field_type, value in [
        ("material", MATERIAL),
        ("thickness", THICKNESS),
        ("quantity", QUANTITY),
    ]:
        update_data = {
            "cart_uid": cart_uid,
            field_type: value,
        }
        logging.info(f'Setting {field_type} for cart_uid={cart_uid} to {value}')
        resp = session.post(f'{BASE_URL}/cart_items', data=update_data)
        logging.info('Cart update response: %s', resp.text)
        assert resp.ok, f"Cart update failed: {resp.text}"

    # 3. Simulate pressing Calculate (POST to /calculate)
    cart_form = {
        f'material_{cart_uid}': MATERIAL,
        f'thickness_{cart_uid}': THICKNESS,
        f'quantity_{cart_uid}': QUANTITY,
    }
    logging.info('Simulating Calculate button for cart_uid=%s', cart_uid)
    resp = session.post(f'{BASE_URL}/calculate', data=cart_form)
    logging.info('Calculate response: %s', resp.text)
    assert resp.ok, f"Calculate failed: {resp.text}"
    calc_data = resp.json()
    assert 'total_sell_price' in calc_data, 'No total_sell_price in calculate response.'
    assert 'detailed_breakdown' in calc_data, 'No detailed_breakdown in calculate response.'
    logging.info('Test PASSED: Database/flow is working for DXF file.')


if __name__ == '__main__':
    test_database_flow()
