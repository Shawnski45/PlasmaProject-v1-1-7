"""
Test script for validating Stripe Elements integration in the PlasmaProject e-commerce MVP.
This script uses Flask's test client and unittest.mock to simulate the payment flow.
It does NOT make real Stripe API calls; it mocks them for safe, repeatable local testing.
"""
import unittest
from unittest.mock import patch, MagicMock
from bson import ObjectId
from app import create_app, db
import os

class TestStripeElementsIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.order_id = str(ObjectId())
        # Insert a test order into MongoDB
        db['orders'].insert_one({
            '_id': ObjectId(self.order_id),
            'total': 123.45,
            'status': 'pending',
        })

    def tearDown(self):
        db['orders'].delete_one({'_id': ObjectId(self.order_id)})

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent(self, mock_create):
        mock_create.return_value = MagicMock(id='pi_test', client_secret='cs_test')
        resp = self.client.post('/create-payment-intent', json={'order_id': self.order_id})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('clientSecret', data)
        self.assertEqual(data['clientSecret'], 'cs_test')

    @patch('stripe.PaymentIntent.retrieve')
    def test_confirm_payment_success(self, mock_retrieve):
        # Simulate a successful payment intent
        mock_intent = MagicMock(status='succeeded', id='pi_test')
        mock_retrieve.return_value = mock_intent
        resp = self.client.post('/confirm-payment', json={'payment_intent_id': 'pi_test', 'order_id': self.order_id})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'success')
        # Check DB status
        order = db['orders'].find_one({'_id': ObjectId(self.order_id)})
        self.assertEqual(order['status'], 'paid')

    @patch('stripe.PaymentIntent.retrieve')
    def test_confirm_payment_fail(self, mock_retrieve):
        # Simulate a failed payment intent
        mock_intent = MagicMock(status='requires_payment_method', id='pi_test')
        mock_retrieve.return_value = mock_intent
        resp = self.client.post('/confirm-payment', json={'payment_intent_id': 'pi_test', 'order_id': self.order_id})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('status', data)
        self.assertNotEqual(data['status'], 'success')

if __name__ == '__main__':
    unittest.main()
