import requests
import os

BASE_URL = "http://localhost:5000"
STATIC_ASSETS = [
    "react-build/assets/index-CE39g0lV.js",
    "react-build/assets/index-SES_qBDA.css",
]

DXF_PATH = "Inputs/primary_validation/10x10 Square.dxf"

session = requests.Session()

def test_asset_serving():
    print("Checking React asset serving...")
    for asset in STATIC_ASSETS:
        url = f"{BASE_URL}/static/{asset}"
        resp = session.get(url)
        print(f"{url}: {resp.status_code}")
        assert resp.status_code == 200

def test_upload_dxf():
    print("Uploading DXF file...")
    with open(DXF_PATH, "rb") as f:
        files = {'file': (os.path.basename(DXF_PATH), f, 'application/dxf')}
        resp = session.post(f"{BASE_URL}/parse_dxf", files=files)
        print(f"Upload response: {resp.status_code}")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data and data["status"] == "success"
        assert "items" in data

def get_cart_items():
    resp = session.get(f"{BASE_URL}/cart_items")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    return data["items"]

def test_calculate():
    print("Calculating quote...")
    cart_items = get_cart_items()
    if not cart_items:
        print("No items in cart to calculate.")
        return
    cart_uid = cart_items[0]["cart_uid"]
    payload = {
        f"material_{cart_uid}": "A36 Steel",
        f"thickness_{cart_uid}": 0.25,
        f"quantity_{cart_uid}": 1,
    }
    resp = session.post(f"{BASE_URL}/calculate", data=payload)
    print(f"Calculate response: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sell_price" in data or "total" in data

def test_remove():
    print("Removing item from cart...")
    cart_items = get_cart_items()
    if not cart_items:
        print("No items to remove.")
        return
    cart_uid = cart_items[0]["cart_uid"]
    resp = session.post(f"{BASE_URL}/remove", data={"cart_uid": cart_uid})
    print(f"Remove response: {resp.status_code}")
    assert resp.status_code == 200

def test_clear():
    print("Clearing cart via /api/clear...")
    resp = session.post(f"{BASE_URL}/api/clear")
    print(f"Clear response: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True

if __name__ == "__main__":
    test_asset_serving()
    test_upload_dxf()
    test_calculate()
    test_remove()
    test_clear()
    print("All tests passed!")
