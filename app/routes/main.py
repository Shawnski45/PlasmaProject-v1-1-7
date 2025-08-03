from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
import os
import json
import pytz
from datetime import datetime
import uuid
import secrets
from shutil import copyfile
from werkzeug.utils import secure_filename
import math
import stripe
import logging
from flask_cors import cross_origin  # For React dev mode

from app import db
from app.models.order import create_order, get_user_orders
from app.models.upload import create_upload, get_user_uploads
from app.models.user import create_user, get_user
from app.utils import dxf_parser, costing
from app.utils.email import send_receipt_email
from app import mail, login_manager

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')

stripe.api_key = STRIPE_SECRET_KEY

main_bp = Blueprint('main', __name__)

# Serve the login page (Firebase handles authentication in the template)
@main_bp.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# --- Constants and Utility Functions ---
UNIT_CONVERSIONS = {
    "hour": {"min": 60}, "min": {"min": 1}, "sec": {"min": 1 / 60},
    "$/hour": {"$/min": 1 / 60}, "$/min": {"$/min": 1}, "in/min": {"in/min": 1},
    "in": {"in": 1}, "$/lb": {"$/lb": 1}, "unitless": {"unitless": 1}
}
REQUIRED_INPUTS = [
    "direct_labor_rate", "machine_rate_per_min", "cut_speed_0.375", "cut_speed_0.75", "cut_speed_1.0",
    "order_setup_time", "thickness_changeover_time", "plate_change_time",
    "cleanup_assembly_time_thick", "cleanup_assembly_time_thin", "steel_cost_per_lb",
    "kerf_thickness", "skeleton_thickness", "margin", "pierce_time", "travel_speed",
    "material_efficiency"
]
AVAILABLE_THICKNESSES = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
AVAILABLE_MATERIALS = ["A36 Steel", "Stainless 304", "Stainless 316", "Aluminum 3003", "Aluminum 6061"]

def load_inputs():
    """Load input parameters from inputs.csv, providing safe defaults if file is missing."""
    inputs = {}
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    inputs_file = os.path.join(project_root, 'inputs.csv')
    resolved_path = os.path.abspath(inputs_file)
    logging.info(f"Attempting to load inputs.csv from: {resolved_path}")
    if os.path.exists(resolved_path):
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                logging.info(f"inputs.csv content: {lines}")
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        parts = [x.strip() for x in line.split(',')]
                        if len(parts) < 3:
                            logging.warning(f"Skipping invalid line in inputs.csv: {line.strip()}")
                            continue
                        key, value, unit = parts[:3]
                        if key in REQUIRED_INPUTS:
                            try:
                                inputs[key] = {"value": float(value), "unit": unit}
                            except ValueError:
                                logging.warning(f"Invalid value for {key} in inputs.csv: {value}")
                                inputs[key] = {"value": 0.0, "unit": unit}
                logging.info(f"Loaded inputs: {inputs}")
        except Exception as e:
            logging.error(f"Failed to parse inputs.csv: {e}")
            for key in REQUIRED_INPUTS:
                inputs[key] = {"value": 0.0, "unit": "unitless"}
    else:
        logging.warning(f"Could not load inputs.csv from {resolved_path}. Using safe defaults.")
        for key in REQUIRED_INPUTS:
            inputs[key] = {"value": 0.0, "unit": "unitless"}
    return inputs

@main_bp.route('/preview_data')
@cross_origin()
def preview_data():
    order_id = session.get('order_id')
    if not order_id:
        order_id = str(uuid.uuid4())
        session['order_id'] = order_id
    cart_items = list(db.order_items.find({"order_id": order_id}))
    previews = []
    error_count = 0
    for item in cart_items:
        preview_data = []
        if item.get('preview'):
            try:
                preview_data = json.loads(item['preview'])
            except Exception as e:
                preview_data = [{"type": "error", "message": f"Failed to load preview: {e}"}]
                error_count += 1
                logging.error(f"[DIAG] /preview_data: Failed to load preview for cart_uid={item['cart_uid']}: {e}, raw preview: {repr(item.get('preview'))}")
        previews.append({
            "id": f"preview_{item['cart_uid']}",
            "data": preview_data,
            "minX": item.get('gross_min_x'),
            "maxX": item.get('gross_max_x'),
            "minY": item.get('gross_min_y'),
            "maxY": item.get('gross_max_y')
        })
    # Patch: ensure all preview values are serializable
    for preview in previews:
        for key in ["minX", "maxX", "minY", "maxY"]:
            if preview[key] is None or str(preview[key]).lower() == "undefined":
                preview[key] = 0
    return jsonify({"previews": previews})

@main_bp.route('/cart_items', methods=['GET', 'POST'])
@cross_origin()
def cart_items():
    order_id = session.get('order_id')
    if not order_id:
        order_id = str(uuid.uuid4())
        session['order_id'] = order_id
    if request.method == 'POST':
        cart_uid = request.form.get('cart_uid')
        field_type = next((key for key in request.form.keys() if key in ['material', 'thickness', 'quantity']), None)
        value = request.form.get(field_type)
        if not cart_uid or not field_type:
            return jsonify({"error": "Missing cart_uid or field_type"}), 400
        # Update the order_items collection
        db.order_items.update_one(
            {"cart_uid": cart_uid, "order_id": order_id},
            {"$set": {field_type: value}}
        )
    cart_items = list(db.order_items.find({"order_id": order_id}))
    items = [{
        "cart_uid": item['cart_uid'],
        "part_number": item['part_number'],
        "material": item.get('material', None),
        "thickness": item.get('thickness', None),
        "quantity": item.get('quantity', 1)
    } for item in cart_items]
    # Patch: ensure all cart item values are serializable
    for item in items:
        for key in ["material", "part_number"]:
            if item.get(key) is None or str(item.get(key)).lower() == "undefined":
                item[key] = ''
        for key in ["thickness", "quantity"]:
            if item.get(key) is None or str(item.get(key)).lower() == "undefined":
                item[key] = 0
    return jsonify({"items": items})

@main_bp.route('/parse_dxf', methods=['POST'])
@cross_origin()
def parse_dxf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    files = request.files.getlist('file')
    logging.info(f"parse_dxf received files: {[file.filename for file in files]}")
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No file selected for uploading"}), 400

    order_id = session.get('order_id')
    if not order_id:
        order_id = str(uuid.uuid4())
        session['order_id'] = order_id
    
    # Update existing items with form data
    existing_items = list(db.order_items.find({"order_id": order_id}))
    for item in existing_items:
        material_key = f"material_{item['cart_uid']}"
        thickness_key = f"thickness_{item['cart_uid']}"
        quantity_key = f"quantity_{item['cart_uid']}"
        if material_key in request.form:
            item['material'] = request.form[material_key] or item.get('material', None)
            db.order_items.update_one({"cart_uid": item['cart_uid']}, {"$set": {"material": item['material']}})
        if thickness_key in request.form:
            item['thickness'] = float(request.form[thickness_key]) if request.form[thickness_key] else item.get('thickness', None)
            db.order_items.update_one({"cart_uid": item['cart_uid']}, {"$set": {"thickness": item['thickness']}})
        if quantity_key in request.form:
            item['quantity'] = int(request.form[quantity_key]) if request.form[quantity_key] else item.get('quantity', 1)
            db.order_items.update_one({"cart_uid": item['cart_uid']}, {"$set": {"quantity": item['quantity']}})
        logging.info(f"Updating item {item['cart_uid']}: material={item.get('material', None)}, thickness={item.get('thickness', None)}, quantity={item.get('quantity', 1)}")

    results = []
    partial_warnings = []
    for file in files:
        if file.filename == '':
            continue
        if not file.filename.lower().endswith('.dxf'):
            return jsonify({"error": f'Invalid file type: {file.filename}. Please upload a .dxf file'}), 400
        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        logging.info(f"Uploaded file saved to {save_path}")
        
        try:
            parse_result = dxf_parser.parse_dxf(save_path)
            # Accept if at least one valid geometry entity is present (total_length or net_area_sqin > 0)
            has_valid_geometry = (
                parse_result.get('total_length', 0) > 0 or
                parse_result.get('net_area_sqin', 0) > 0
            )
            # Log partial warnings if any errors in preview
            if any(p.get('type') == 'error' for p in parse_result.get('preview', [])):
                partial_warnings.append(f"Partial parse for {filename}: {parse_result.get('preview')}")
                logging.warning(f"Partial parse for {filename}: {parse_result.get('preview')}")
            if parse_result.get('gross_area_sqin') == float('inf'):
                logging.error(f"Invalid gross area for {filename}: infinite value")
                return jsonify({"error": "Invalid geometry (infinite bounds)"}), 400
            if not has_valid_geometry:
                return jsonify({"error": "No valid geometry found"}), 400
            cart_uid = str(uuid.uuid4())
            order_item = {
                'cart_uid': cart_uid,
                'order_id': order_id,
                'part_number': filename,
                'preview': json.dumps(parse_result.get('preview', [])),
                'gross_min_x': parse_result.get('gross_min_x', 0),
                'gross_max_x': parse_result.get('gross_max_x', 0),
                'gross_min_y': parse_result.get('gross_min_y', 0),
                'gross_max_y': parse_result.get('gross_max_y', 0),
                'net_area_sqin': parse_result.get('net_area_sqin', 0),
                'total_length': parse_result.get('total_length', 0),
                'pierce_count': parse_result.get('entity_count', {}).get('PIERCE', 0),
                'material': None,
                'thickness': None,
                'quantity': 1
            }
            db.order_items.insert_one(order_item)  # MongoDB insert
            results.append(order_item)
        except Exception as e:
            logging.error(f"Error parsing DXF {filename}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    if results:
        cart_items = list(db.order_items.find({"order_id": order_id}))
        response = {
            "status": "success",
            "items": [
                {"cart_uid": item.get('cart_uid'), "part_number": item.get('part_number'), "material": item.get('material', None), "thickness": item.get('thickness', None), "quantity": item.get('quantity', 1)}
                for item in cart_items
            ]
        }
        if partial_warnings:
            response["partial_warnings"] = partial_warnings
        return jsonify(response)
    return jsonify({"status": "error", "message": "No valid files processed"}), 400

@main_bp.route("/remove", methods=["POST"])
@cross_origin()
def remove():
    order_id = session.get('order_id')
    if not order_id:
        order_id = str(uuid.uuid4())
        session['order_id'] = order_id
    cart_uid = request.form.get("cart_uid")
    if not cart_uid:
        return jsonify({"error": "No item specified for removal."}), 400
    # MongoDB remove logic
    db.order_items.delete_one({"cart_uid": cart_uid, "order_id": order_id})
    return jsonify({"success": True})

@main_bp.route("/calculate", methods=["POST"])
@cross_origin()
def calculate():
    logging.info(f"/calculate received form: {dict(request.form)}")
    order_id = session.get('order_id')
    if not order_id:
        order_id = str(uuid.uuid4())
        session['order_id'] = order_id
    cart_items = list(db.order_items.find({"order_id": order_id}))
    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    try:
        # Diagnostic: Log all cart_items types and reprs
        for idx, item in enumerate(cart_items):
            logging.info(f"cart_items[{idx}]: type={type(item)}, repr={repr(item)}")
        invalid_items = []
        for item in cart_items:
            if not isinstance(item, dict):
                logging.error(f"Skipping non-dict cart_item: {repr(item)} of type {type(item)}")
                continue
            logging.info(f"Processing cart_uid={item['cart_uid']}, expecting keys: material_{item['cart_uid']}, thickness_{item['cart_uid']}, quantity_{item['cart_uid']}")
            material_key = f"material_{item['cart_uid']}"
            thickness_key = f"thickness_{item['cart_uid']}"
            quantity_key = f"quantity_{item['cart_uid']}"
            item['material'] = request.form.get(material_key, '').strip()
            if not item.get('material', None) or item.get('material', None) not in AVAILABLE_MATERIALS:
                invalid_items.append({"part_number": item['part_number'], "message": "Invalid or missing material"})
            try:
                item['thickness'] = float(request.form.get(thickness_key, ''))
            except (ValueError, TypeError):
                item['thickness'] = None
            if not item.get('thickness', None) or item.get('thickness', None) not in AVAILABLE_THICKNESSES:
                invalid_items.append({"part_number": item['part_number'], "message": "Invalid or missing thickness"})
            try:
                item['quantity'] = int(request.form.get(quantity_key, 1))
            except (ValueError, TypeError):
                item['quantity'] = 1
            if not isinstance(item.get('quantity', 1), int) or item.get('quantity', 1) < 1:
                invalid_items.append({"part_number": item['part_number'], "message": "Invalid quantity (must be >= 1)"})
            # Update MongoDB with modified item
            db.order_items.update_one({"cart_uid": item['cart_uid']}, {"$set": {"material": item['material'], "thickness": item['thickness'], "quantity": item['quantity']}})

        if invalid_items:
            return jsonify({"error": "Invalid items in cart", "invalid_items": invalid_items}), 400

        inputs = load_inputs()
        material_densities = dxf_parser.load_material_densities()
        breakdown = costing.calculate_costs(cart_items, inputs, material_densities)

        # Update order total in MongoDB
        order = create_order(order_id, {"items": cart_items}, "pending")  # Simplified update
        order['total'] = breakdown['total_sell_price']
        db.orders.update_one({"_id": order['_id']}, {"$set": {"total": breakdown['total_sell_price']}})

        session['calculated'] = True
        session['order_total'] = float(breakdown['total_sell_price'])
        session['order_total_breakdown'] = {'detailed_breakdown': breakdown['detailed_breakdown']}  # Store breakdown separately
        response = {
            "total_sell_price": breakdown["total_sell_price"],
            "detailed_breakdown": [
                dict(item, cart_uid=cart_item['cart_uid']) if 'cart_uid' not in item else item
                for cart_item, item in zip(cart_items, breakdown["detailed_breakdown"])
            ]
        }
        if invalid_items:
            response["invalid_items"] = invalid_items
        # Send receipt email if user is authenticated and email is available
        user_email = None
        if current_user.is_authenticated:
            user_email = getattr(current_user, 'email', None)
        if user_email:
            try:
                order_details = ''
                for item in cart_items:
                    order_details += f"{item.get('part_number', 'Part')}: {item.get('quantity', 1)} x {item.get('material', '')} {item.get('thickness', '')}\n"
                send_receipt_email(user_email, order_details, breakdown['total_sell_price'])
                logging.info(f"Receipt email sent to {user_email}")
            except Exception as e:
                logging.error(f"Failed to send receipt email: {e}")

        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in calculate route: {str(e)}", exc_info=True)
        return jsonify({"error": f"Exception: {str(e)}"}), 500

@main_bp.route("/api/clear", methods=["POST"])
@cross_origin()
def api_clear():
    session.pop('calculated', None)
    try:
        order_id = session.get('order_id')
        logging.info(f"[DIAG] /api/clear order_id: {order_id}, session: {dict(session)}")
        if order_id:
            try:
                db.order_items.delete_many({"order_id": order_id})
                db.orders.delete_one({"_id": order_id, "status": "pending"})
                logging.info(f"[DIAG] /api/clear: Cleared order_items and order for order_id={order_id}")
            except Exception as db_exc:
                logging.error(f"[DIAG] /api/clear DB error: {db_exc}", exc_info=True)
            session.pop('order_id', None)
        else:
            logging.info(f"[DIAG] /api/clear: No order_id in session; nothing to clear.")
        # Always return success for idempotency
        return jsonify({"success": True}), 200
    except Exception as e:
        logging.error(f"[DIAG] Error in /api/clear route: {str(e)} | session: {dict(session)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/clear', methods=['GET', 'POST'])
@cross_origin()
def clear():
    # Clear cart and session data
    order_id = session.get('order_id')
    if order_id:
        try:
            db.order_items.delete_many({"order_id": order_id})
            db.orders.delete_one({"_id": order_id, "status": "pending"})
        except Exception as e:
            logging.error(f"Error clearing cart for order_id={order_id}: {e}", exc_info=True)
        session.pop('order_id', None)
    session.pop('calculated', None)
    # Optionally clear other session keys (user_id, id_token, etc.) if needed
    return redirect('/')

@main_bp.route('/', methods=['GET', 'POST'])
@cross_origin()
def index():
    try:
        cart_items = session.get('cart_items', [])
        order_id = session.get('order_id')
        if order_id:
            cart_items = list(db.order_items.find({"order_id": order_id}))
        logging.info(f"[DIAG] index: len(items)={len(cart_items)}, items={[{item['cart_uid'], item['part_number'], item.get('material', None), item.get('thickness', None), item.get('quantity', 1)} for item in cart_items]}, calculated={session.get('calculated')}")
        return render_template(
            "customer_index.html",
            cart_items=cart_items,
            order_id=order_id
        )
    except Exception as e:
        logging.error(f"Error in index(): {e}", exc_info=True)
        flash(f"An error occurred: {e}", "error")
        return render_template(
            "customer_index.html",
            cart_items=[],
            order_id=None
        )

@main_bp.route('/order_history')
@cross_origin()
def order_history():
    if 'user_email' not in session:
        flash('Please sign in to view your order history.', 'error')
        return redirect(url_for('main.index'))
    user_email = session['user_email']
    orders = list(db.orders.find({
        'user_email': user_email,
        'status': {'$in': ['succeeded', 'paid', 'completed']}
    }).sort('created_at', -1))
    tz = pytz.timezone('America/New_York')
    for order in orders:
        if order.get('created_at'):
            order['local_purchase_date'] = pytz.utc.localize(order['created_at']).astimezone(tz)
        else:
            order['local_purchase_date'] = None
    return render_template('order_history.html', orders=orders)

@main_bp.route('/current_orders')
@cross_origin()
def current_orders():
    if 'user_email' not in session:
        flash('Please sign in to view your current orders.', 'error')
        return redirect(url_for('main.index'))
    user_email = session['user_email']
    orders = list(db.orders.find({
        'user_email': user_email,
        'status': {'$in': ['pending', 'in_progress']}
    }).sort('created_at', -1))
    tz = pytz.timezone('America/New_York')
    for order in orders:
        if order.get('created_at'):
            order['local_purchase_date'] = pytz.utc.localize(order['created_at']).astimezone(tz)
        else:
            order['local_purchase_date'] = None
    return render_template('current_orders.html', current_orders=orders)

@main_bp.route("/guest_checkout", methods=["GET"])
@cross_origin()
def guest_checkout():
    firebase_config = {
        "apiKey": os.environ.get("FIREBASE_API_KEY", ""),
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.environ.get("FIREBASE_APP_ID", ""),
        "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID", "")
    }
    for k in list(firebase_config.keys()):
        v = firebase_config[k]
        if v is None or str(v).lower() == "undefined":
            firebase_config[k] = ""
    logging.info(f"[DIAG] /guest_checkout firebase_config: {firebase_config}")
    return render_template("guest_checkout.html", firebase_config=firebase_config)

@main_bp.route('/.well-known/<path:path>')
@cross_origin()
def well_known(path):
    logging.info(f"404 suppressed for {path}")
    return '', 204

@main_bp.route('/checkout', methods=['GET', 'POST'])
@cross_origin()
def checkout():
    import logging
    from bson import ObjectId
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            cart = data.get('cart')
            quote = data.get('quote')
            guest_info = data.get('guestInfo')
            user_id = None
            # If user is logged in, associate order with Firebase UID from session
            id_token = session.get('id_token')
            if id_token:
                try:
                    from firebase_admin import get_app, auth
                    firebase_app = get_app(name='default')
                    decoded_token = auth.verify_id_token(id_token, app=firebase_app)
                    user_id = decoded_token['uid']
                except Exception as e:
                    logging.error(f"Failed to verify Firebase token: {e}")
            order_id = session.get('order_id')
            if not order_id:
                order_id = str(uuid.uuid4())
                session['order_id'] = order_id
            # Guarantee order document exists for any order_id (UUID or ObjectId)
            if db.orders.count_documents({'_id': order_id}) == 0:
                db.orders.insert_one({
                    '_id': order_id,
                    'status': 'pending',
                    'created_at': datetime.utcnow(),
                    'items': [],
                    'total': 0,
                })
            # Save guest info or user_id to order
            update_fields = {}
            if user_id:
                update_fields['user_id'] = user_id
            elif guest_info:
                update_fields['guest_info'] = guest_info
            # Save cart and quote if provided
            if cart:
                update_fields['items'] = cart
            if quote and 'total_sell_price' in quote:
                update_fields['total'] = quote['total_sell_price']
            update_fields['updated_at'] = datetime.utcnow()
            try:
                db.orders.update_one({'_id': order_id}, {'$set': update_fields})
            except Exception as e:
                logging.error(f"Failed to update order in checkout POST: {e}")
            # Respond with Stripe redirect URL or success
            return jsonify({'success': True, 'order_id': order_id})
        else:
            # Fallback: legacy form POST
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            flash(f'Guest checkout for {name} ({email}) received.', 'info')
    order_id = session.get('order_id')
    if not order_id:
        order_id = str(uuid.uuid4())
        session['order_id'] = order_id
    # Guarantee order document exists for any order_id (UUID or ObjectId)
    if db.orders.count_documents({'_id': order_id}) == 0:
        db.orders.insert_one({
            '_id': order_id,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'items': [],
            'total': 0,
        })

    items = list(db.order_items.find({"order_id": order_id}))
    if not items:
        flash('No items in cart.', 'error')
        return redirect(url_for('.index'))
    # Handle order_total as a float and initialize breakdown
    total_sell_price = session.get('order_total', 0)
    detailed_breakdown = session.get('calculated', False) and session.get('order_total_breakdown', {}).get('detailed_breakdown', []) or []
    breakdown = {'total_sell_price': total_sell_price, 'detailed_breakdown': detailed_breakdown}
    # Merge unit_price from detailed_breakdown into items
    for item, detail in zip(items, breakdown.get('detailed_breakdown', [])):
        item['unit_price'] = detail.get('unit_price', 0)
        item['cost_per_part'] = detail.get('sell_price_per_part', item.get('unit_price', 0) * item.get('quantity', 1))
    # --- PATCH: update order doc with correct total and items ---
    try:
        db.orders.update_one(
            {'_id': order_id},
            {'$set': {
                'total': total_sell_price,
                'items': items,
                'updated_at': datetime.utcnow(),
            }}
        )
    except Exception as e:
        logging.error(f"Failed to update order total/items in checkout: {e}")
    user_data = current_user.to_dict() if current_user.is_authenticated else None
    # Serve the legacy Jinja template for checkout (hybrid React-in-legacy)
    # Inject correct React asset filenames for hybrid embedding
    react_css = 'assets/index-SES_qBDA.css'
    react_js = 'assets/index-CLkeOeYP.js'  # Use the latest or correct hashed JS file
    return render_template('checkout.html', items=items, breakdown=breakdown, user_data=user_data, react_css=react_css, react_js=react_js)


@main_bp.route('/get_flashes', methods=['GET'])
@cross_origin()
def get_flashes():
    from flask import get_flashed_messages
    messages = get_flashed_messages(with_categories=True)
    # Format: [{category, message}]
    return jsonify([{'category': cat, 'message': msg} for cat, msg in messages])

if __name__ == "__main__":
    print(f"Blueprint endpoints: {[rule.endpoint for rule in main_bp.url_map.iter_rules()]}")