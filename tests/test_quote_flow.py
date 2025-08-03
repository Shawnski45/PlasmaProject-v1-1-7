import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
from app import create_app
import json

class QuoteFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()

    @patch("app.routes.main.get_db")
    def test_parse_dxf_upload(self, mock_get_db):
        # Mock DB and insert_one
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.cart.insert_one.return_value.inserted_id = "fake_id"

        # Simulate DXF file upload
        data = {
            'file': (BytesIO(b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nENDSEC\n0\nEOF\n"), 'test.dxf')
        }
        response = self.client.post('/parse_dxf', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertIn('success', resp_json)
        self.assertTrue(resp_json['success'])
        self.assertIn('preview', resp_json)

    @patch("app.routes.main.get_db")
    def test_cart_items_flow(self, mock_get_db):
        # Mock DB find
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.cart.find.return_value = [
            {"_id": "fake_id", "name": "Test Part", "quantity": 1, "material": "Steel", "thickness": "0.125", "price": 10.0}
        ]
        response = self.client.get('/cart_items')
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertIn('items', resp_json)
        self.assertIsInstance(resp_json['items'], list)
        self.assertEqual(resp_json['items'][0]['name'], "Test Part")

    @patch("app.routes.main.get_db")
    def test_calculate_flow(self, mock_get_db):
        # Mock DB and cart update
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.cart.find.return_value = [
            {"_id": "fake_id", "name": "Test Part", "quantity": 2, "material": "Steel", "thickness": "0.125", "price": 10.0}
        ]
        mock_db.cart.update_one.return_value.modified_count = 1
        response = self.client.post('/calculate', json={})
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertIn('total', resp_json)
        self.assertGreaterEqual(resp_json['total'], 0)

    @patch("app.routes.main.get_db")
    def test_remove_item(self, mock_get_db):
        # Mock DB delete_one
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.cart.delete_one.return_value.deleted_count = 1
        response = self.client.post('/remove', json={"cart_uid": "fake_id"})
        self.assertEqual(response.status_code, 200)
        resp_json = response.get_json()
        self.assertIn('success', resp_json)
        self.assertTrue(resp_json['success'])

    @patch("app.routes.main.get_db")
    def test_remove_item_not_found(self, mock_get_db):
        # Simulate item not found
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.cart.delete_one.return_value.deleted_count = 0
        response = self.client.post('/remove', json={"cart_uid": "nonexistent_id"})
        self.assertEqual(response.status_code, 404)
        resp_json = response.get_json()
        self.assertIn('success', resp_json)
        self.assertFalse(resp_json['success'])

if __name__ == "__main__":
    unittest.main()
