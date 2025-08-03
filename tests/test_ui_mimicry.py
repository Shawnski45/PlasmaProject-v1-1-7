import requests
import os


# App URL
base_url = "http://127.0.0.1:5000"

# Test data
import os
from bs4 import BeautifulSoup

dxf_file_path = os.path.abspath("Inputs/primary_validation/10x10 Square.dxf")
part_number = "10x10_Square.dxf"

try:
    if not os.path.exists(dxf_file_path):
        # logging removed: error(f"DXF file not found: {dxf_file_path}")
        raise FileNotFoundError(f"DXF file not found: {dxf_file_path}")
    # logging removed: info(f"DXF file absolute path: {dxf_file_path}")
    session = requests.Session()

    # Step 0: Clear the cart (simulate by resetting session cookies)
    # logging removed: info("Starting new session and clearing cart by resetting session cookies.")
    session.cookies.clear()
    # logging removed: info(f"Session cookies after clear: {session.cookies.get_dict()}")

    # Step 1: Drop DXF File
    # logging removed: info(f"Uploading DXF file from {dxf_file_path}")
    with open(dxf_file_path, 'rb') as f:
        files = {'files[]': f}
        data = {'material_10x10_Square.dxf': 'A36 Steel', 'thickness_10x10_Square.dxf': '0.25'}
        # logging removed: info(f"POST / form data: {data}")
        response = session.post(f"{base_url}/", files=files, data=data)
    # logging removed: info(f"Upload response: {response.status_code}")
    # logging removed: debug(f"Upload response text: {response.text[:500]}")
    # logging removed: info(f"Session cookies after upload: {session.cookies.get_dict()}")
    # Fetch cart page after upload
    cart_response = session.get(f"{base_url}/")
    # logging removed: info(f"Cart page after upload: {cart_response.status_code}")
    # logging removed: debug(f"Cart HTML after upload: {cart_response.text[:500]}")

    # Step 2: Change Material/Thickness/Quantity
    # logging removed: info(f"Updating {part_number} to material=A36 Steel, thickness=0.5, quantity=2")
    update_data = {
        "part_number": part_number,
        "material": "A36 Steel",
        "thickness": 0.5,
        "quantity": 2
    }
    # logging removed: info(f"POST /update_price json: {update_data}")
    response = session.post(f"{base_url}/update_price", json=update_data)
    # logging removed: info(f"Update response: {response.status_code}")
    # logging removed: debug(f"Update response text: {response.text[:500]}")
    # logging removed: info(f"Session cookies after update: {session.cookies.get_dict()}")
    # Fetch cart page after update
    cart_response = session.get(f"{base_url}/")
    # logging removed: info(f"Cart page after update: {cart_response.status_code}")
    # logging removed: debug(f"Cart HTML after update: {cart_response.text[:500]}")

    # Step 3: Press Calculate
    calc_data = {'update_only': 'true', f'quantity_{part_number}': '2'}
    # logging removed: info(f"POST / form data: {calc_data}")
    response = session.post(f"{base_url}/", data=calc_data)
    # logging removed: info(f"Calculate response: {response.status_code}")
    # logging removed: debug(f"Calculate response text: {response.text[:500]}")
    # logging removed: info(f"Session cookies after calculate: {session.cookies.get_dict()}")
    # Fetch cart page after calculate
    cart_response = session.get(f"{base_url}/")
    # logging removed: info(f"Cart page after calculate: {cart_response.status_code}")
    # logging removed: debug(f"Cart HTML after calculate: {cart_response.text[:500]}")
    # Parse quantity from HTML
    soup = BeautifulSoup(cart_response.text, 'html.parser')
    qty_input = soup.find('input', {'name': f'quantity_{part_number}'})
    qty_val = qty_input['value'] if qty_input else 'NOT FOUND'
    # logging removed: info(f"Parsed quantity input value after calculate: {qty_val}")

    # Step 4: Verify Price (from HTML or API)
    # Optionally parse price from HTML as well
    price_span = soup.find('span', {'class': 'total-price'})
    price_val = price_span.text if price_span else 'NOT FOUND'
    # logging removed: info(f"Parsed total price after calculate: {price_val}")
    if response.status_code == 200:
        pass  # Placeholder for future success handling
        # logging removed: info("Test completed successfully")
    else:
        pass  # Placeholder for future error handling
        # logging removed: error(f"Test failed with status {response.status_code}: {response.text}")
except Exception as e:
    pass
    # logging removed: error(f"Exception during UI mimicry test: {e}")

if __name__ == "__main__":
    pass
    
