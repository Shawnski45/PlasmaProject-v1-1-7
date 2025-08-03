import stripe
from flask import Blueprint, request, jsonify, current_app, session, redirect, render_template
from bson.objectid import ObjectId
from app import db
import logging
import datetime

payments_bp = Blueprint('payments', __name__)

# Move Stripe configuration to a function or app context
def configure_stripe(app):
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

orders_collection = db['orders']

@payments_bp.before_app_request
def setup_stripe():
    with current_app.app_context():
        configure_stripe(current_app)

@payments_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    logging.info(f"[Stripe DIAG] Incoming /create-checkout-session | method={request.method} | url={request.url} | session={dict(session)} | timestamp={datetime.datetime.now().isoformat()}")
    try:
        order_id = session.get('order_id')
        if not order_id:
            logging.error("No order_id in session")
            return jsonify({"error": "No active order session"}), 400

        # Accept both ObjectId and UUID order_id
        try:
            mongo_id = ObjectId(order_id)
            order = orders_collection.find_one({'_id': mongo_id})
        except Exception:
            order = orders_collection.find_one({'_id': order_id})
        if not order:
            logging.error(f"Order not found: {order_id}")
            return jsonify({"error": "Order not found"}), 404

        if order.get('total', 0) <= 0:
            logging.error(f"Invalid order total: {order.get('total')}")
            return jsonify({"error": "Invalid order total"}), 400

        logging.info(f"[Stripe DIAG] Creating Stripe Checkout Session | order_id={order_id} | total={order.get('total')} | BASE_URL={current_app.config['BASE_URL']} | timestamp={datetime.datetime.now().isoformat()}")
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Plasma Cutting Order',
                        },
                        'unit_amount': int(order['total'] * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=f"{current_app.config['BASE_URL']}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{current_app.config['BASE_URL']}/",
            metadata={'order_id': str(order_id)},
        )
        logging.info(f"[Stripe DIAG] Stripe Session Created | session_id={checkout_session.id} | order_id={order_id} | response={checkout_session} | timestamp={datetime.datetime.now().isoformat()}")
        logging.info(f"[Stripe DIAG] Created Checkout Session | session_id={checkout_session.id} | order_id={order_id} | BASE_URL={current_app.config['BASE_URL']} | success_url={current_app.config['BASE_URL']}/success?session_id={{CHECKOUT_SESSION_ID}} | cancel_url={current_app.config['BASE_URL']}/ | timestamp={datetime.datetime.now().isoformat()}")
        # Accept both ObjectId and UUID order_id for update
        # Accept both ObjectId and UUID order_id for update
        try:
            mongo_id = ObjectId(order_id)
            orders_collection.update_one(
                {'_id': mongo_id},
                {'$set': {'stripe_session_id': checkout_session.id}}
            )
        except Exception:
            orders_collection.update_one(
                {'_id': order_id},
                {'$set': {'stripe_session_id': checkout_session.id}}
            )
        # Already logged above with more detail
        logging.info(f"[Stripe DIAG] Returning session_id to frontend | session_id={checkout_session.id} | order_id={order_id} | timestamp={datetime.datetime.now().isoformat()}")
        return jsonify({'session_id': checkout_session.id})
    except Exception as e:
        logging.error(f"[Stripe DIAG] Error creating Stripe Checkout session: {str(e)} | session={dict(session)} | url={request.url} | timestamp={datetime.datetime.now().isoformat()}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    logging.info(f"[Stripe DIAG] Incoming /webhook | method={request.method} | url={request.url} | headers={dict(request.headers)} | timestamp={datetime.datetime.now().isoformat()}")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    try:
        logging.info(f"[Stripe DIAG] Webhook payload: {payload} | sig_header={sig_header}")
        webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logging.error(f"Invalid webhook payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Webhook signature verification failed: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400

    logging.info(f"[Stripe DIAG] Webhook event received | type={event['type']} | event={event}")
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        order_id = session_data['metadata'].get('order_id')
        session_id = session_data.get('id')
        logging.info(f"[Stripe DIAG] Webhook checkout.session.completed | session_id={session_id} | order_id={order_id} | timestamp={datetime.datetime.now().isoformat()}")
        # Accept both ObjectId and UUID order_id for update
        try:
            mongo_id = ObjectId(order_id)
            orders_collection.update_one(
                {'_id': mongo_id},
                {'$set': {'status': 'paid', 'payment_details': session_data}}
            )
        except Exception:
            orders_collection.update_one(
                {'_id': order_id},
                {'$set': {'status': 'paid', 'payment_details': session_data}}
            )
        logging.info(f"Order {order_id} marked as paid via webhook")
    else:
        logging.info(f"Unhandled webhook event: {event['type']}")

    logging.info(f"[Stripe DIAG] Webhook processing complete | status=success | timestamp={datetime.datetime.now().isoformat()}")
    return jsonify({'status': 'success'}), 200

@payments_bp.route('/success')
def success():
    logging.info(f"[Stripe DIAG] Incoming /success | method={request.method} | url={request.url} | args={request.args} | timestamp={datetime.datetime.now().isoformat()}")
    session_id = request.args.get('session_id')
    if not session_id:
        logging.error("No session_id in success route")
        return render_template('error.html', message="Invalid session ID"), 400
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        logging.info(f"[Stripe DIAG] Stripe Session Retrieved in /success | session_id={session_id} | session={checkout_session} | timestamp={datetime.datetime.now().isoformat()}")
        order_id = checkout_session['metadata'].get('order_id')
        logging.info(f"[Stripe DIAG] /success hit | session_id={session_id} | order_id={order_id} | timestamp={datetime.datetime.now().isoformat()}")
        # Accept both ObjectId and UUID order_id
        try:
            order = orders_collection.find_one({'_id': ObjectId(order_id)})
        except Exception:
            order = orders_collection.find_one({'_id': order_id})
        if not order:
            logging.error(f"Order not found in success route: {order_id}")
            return render_template('error.html', message="Order not found"), 404
        if order.get('status') == 'paid':
            return redirect(f"/contact-info?order_id={order_id}")
        else:
            # Render a pending payment success page
            return render_template('success.html', order=order, pending=True)
    except Exception as e:
        logging.error(f"[Stripe DIAG] Error in /success route: {str(e)} | session_id={request.args.get('session_id')} | url={request.url} | timestamp={datetime.datetime.now().isoformat()}", exc_info=True)
        return render_template('error.html', message=str(e)), 500

@payments_bp.route('/contact-info', methods=['GET', 'POST'])
def contact_info():
    order_id = request.args.get('order_id') if request.method == 'GET' else request.form.get('order_id')
    if not order_id:
        flash('Invalid order ID', 'error')
        return redirect('/')
    # Accept both ObjectId and UUID order_id
    try:
        mongo_id = ObjectId(order_id)
        order = orders_collection.find_one({'_id': mongo_id})
    except Exception:
        order = orders_collection.find_one({'_id': order_id})
    if not order:
        flash('Order not found', 'error')
        return redirect('/')
    if order.get('status') != 'paid':
        flash('Order not paid yet', 'error')
        return redirect('/')
    if request.method == 'POST':
        # Validate and update contact info
        contact = {
            'company_name': request.form.get('company_name', ''),
            'first_name': request.form.get('first_name', ''),
            'last_name': request.form.get('last_name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
        }
        if not contact['first_name'] or not contact['last_name'] or not contact['email'] or not contact['phone']:
            flash('All fields except company name are required', 'error')
            return render_template('contact_info.html', order_id=order_id, contact=contact)
        # Accept both ObjectId and UUID order_id for update
        try:
            mongo_id = ObjectId(order_id)
            orders_collection.update_one(
                {'_id': mongo_id},
                {'$set': {'contact_info': contact}}
            )
        except Exception:
            orders_collection.update_one(
                {'_id': order_id},
                {'$set': {'contact_info': contact}}
            )
        flash('Thank you! Your contact info has been received.', 'success')
        return redirect('/')
    else:
        contact = order.get('contact_info')
        return render_template('contact_info.html', order_id=order_id, contact=contact)