# DEPRECATED: Do not run this file!
# All logic has been migrated to the modular app structure (see app/__init__.py and app/routes/main.py).
# This file is kept only as a placeholder and for historical reference.
raise RuntimeError("Do not run parser_app.py directly. Use the Flask CLI with the app factory in app/__init__.py. Example: 'flask run --app app:create_app'")

import logging
logging.basicConfig(
    filename='error.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)

from app.utils import dxf_parser

# --- Order Management ---
@app.route("/order_history")
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id, status='succeeded').order_by(Order.purchase_date.desc()).all()
    tz = pytz.timezone('America/New_York')
    for order in orders:
        order.local_purchase_date = pytz.utc.localize(order.purchase_date).astimezone(tz)
    return render_template('order_history.html', orders=orders)


@app.route("/order_detail/<order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id, status='succeeded').first()
    if not order:
        flash('Order not found or access denied.', 'error')
        return redirect(url_for('order_history'))
    tz = pytz.timezone('America/New_York')
    order.local_purchase_date = pytz.utc.localize(order.purchase_date).astimezone(tz)
    previews = []
    production_dir = f'orders/files/{order.id}'
    if os.path.exists(production_dir):
        for item in order.items:
            file_path = os.path.join(production_dir, item.part_number)
            if os.path.exists(file_path):
                try:
                    parse_result = dxf_parser.parse_dxf(file_path, material=item.material, thickness=item.thickness)
                    total_length, net_area_sqin, gross_min_x, gross_min_y, gross_max_x, gross_max_y, gross_area_sqin, gross_weight_lb, net_weight_lb, entity_count_dict, outer_perimeter, preview, pierce_count = parse_result
                    previews.append({
                        'part_number': item.part_number,
                        'preview': json.dumps(preview),
                        'gross_min_x': gross_min_x,
                        'gross_max_x': gross_max_x,
                        'gross_min_y': gross_min_y,
                        'gross_max_y': gross_max_y
                    })
                except Exception as e:
                    logger.error(f"Error parsing {file_path} for preview: {str(e)}", exc_info=True)
    return render_template('order_detail.html', order=order, previews=previews)


@app.route("/reorder/<order_id>")
@login_required
def reorder(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id, status='succeeded').first()
    if not order:
        flash('Order not found or access denied.', 'error')
        return redirect(url_for('order_history'))
    pending_orders = Order.query.filter_by(user_id=current_user.id, status='pending').all()
    for pending_order in pending_orders:
        OrderItem.query.filter_by(order_id=pending_order.id).delete()
        db.session.delete(pending_order)
    new_order = Order(
        id=generate_order_number(),
        user_id=current_user.id,
        total=0,
        status='pending'
    )
    db.session.add(new_order)
    db.session.commit()
    production_dir = f'orders/files/{order.id}'
    new_production_dir = f'orders/files/{new_order.id}'
    os.makedirs(new_production_dir, exist_ok=True)
    cart_items = []
    for item in order.items:
        src_path = os.path.join(production_dir, item.part_number)
        if not os.path.exists(src_path):
            flash(f"DXF file for {item.part_number} not found. Order may be incomplete.", 'error')
            continue
        new_path = os.path.join(new_production_dir, item.part_number)
        copyfile(src_path, new_path)
        try:
            parse_result = dxf_parser.parse_dxf(new_path, material=item.material, thickness=item.thickness)
            total_length, net_area_sqin, gross_min_x, gross_min_y, gross_max_x, gross_max_y, gross_area_sqin, gross_weight_lb, net_weight_lb, entity_count_dict, outer_perimeter, preview, pierce_count = parse_result
            entity_count = sum(entity_count_dict.values())
            new_item = OrderItem(
                order_id=new_order.id,
                part_number=item.part_number,
                quantity=item.quantity,
                material=item.material,
                thickness=item.thickness,
                length=total_length,
                net_area_sqin=net_area_sqin,
                gross_area_sqin=gross_area_sqin,
                net_weight_lb=net_weight_lb,
                outer_perimeter=outer_perimeter,
                gross_min_x=gross_min_x,
                gross_min_y=gross_min_y,
                gross_max_x=gross_max_x,
                gross_max_y=gross_max_y,
                gross_weight_lb=gross_weight_lb,
                entity_count=entity_count,
                preview=json.dumps(preview),
                pierce_count=pierce_count,
                unit_price=0,
                cost_per_part=0
            )
            db.session.add(new_item)
            cart_items.append(new_item)
            upload = Upload(order_id=new_order.id, file_path=new_path)
            db.session.add(upload)
        except Exception as e:
            logger.error(f"Error reparsing {item.part_number}: {str(e)}", exc_info=True)
            flash(f"Error processing {item.part_number}.", 'error')
    if cart_items:
        try:
            inputs = load_inputs()
            material_densities = dxf_parser.load_material_densities()
            breakdown = recalculate_cart(cart_items, inputs, material_densities)
            new_order.total = breakdown['total_sell_price']
            for item in cart_items:
                for breakdown_item in breakdown['detailed_breakdown']:
                    if breakdown_item['part_number'] == item.part_number:
                        item.unit_price = breakdown_item['unit_price']
                        item.cost_per_part = breakdown_item['sell_price_per_part']
                        break
            session['calculated'] = True
            db.session.commit()
        except Exception as e:
            logger.error(f"Error recalculating cart on reorder: {str(e)}", exc_info=True)
            db.session.rollback()
            flash('Error recalculating order. Please try again.', 'error')
            return redirect(url_for('order_history'))
    else:
        db.session.rollback()
        flash('No valid items found to reorder.', 'error')
        return redirect(url_for('order_history'))
    flash('Order recreated successfully!', 'success')
    return redirect(url_for('customer_index'))


@app.route("/clear")
def clear():
    if current_user.is_authenticated:
        pending_orders = Order.query.filter_by(status='pending', user_id=current_user.id).all()
    else:
        pending_orders = Order.query.filter_by(status='pending', id=session.get('order_id')).all()
    for order in pending_orders:
        OrderItem.query.filter_by(order_id=order.id).delete()
        db.session.delete(order)
    db.session.commit()
    session.pop('order_id', None)
    session.pop('calculated', None)
    logger.info("Cart cleared, all pending orders removed")
    flash("All items cleared", "success")
    return redirect(url_for("customer_index"))


@app.route("/remove", methods=["POST"])
def remove():
    if current_user.is_authenticated:
        cart_items = OrderItem.query.join(Order).filter(Order.status == 'pending', Order.user_id == current_user.id).all()
    else:
        order_id = session.get('order_id')
        cart_items = OrderItem.query.join(Order).filter(Order.status == 'pending', Order.id == order_id, Order.user_id is None).all()
    part_number = request.form.get("part_number")
    if part_number:
        item_to_remove = next((item for item in cart_items if item.part_number == part_number), None)
        if item_to_remove:
            db.session.delete(item_to_remove)
            db.session.commit()
            cart_items = [item for item in cart_items if item.part_number != part_number]
            logger.info(f"Removed {part_number} from cart. Updated cart: {len(cart_items)} items")
            flash(f"Removed {part_number}", "success")
    try:
        inputs = load_inputs()
        material_densities = dxf_parser.load_material_densities()
        breakdown = recalculate_cart(cart_items, inputs, material_densities)
        if cart_items:
            order = Order.query.filter_by(id=cart_items[0].order_id).first()
            order.total = breakdown['total_sell_price']
            db.session.commit()
    except Exception as e:
        logger.error(f"Error recalculating cart after removal: {str(e)}", exc_info=True)
        raise
    return redirect(url_for("customer_index"))


@app.route("/update_price", methods=["POST"])
def update_price():
    data = request.json
    order_id = session.get('order_id')
    if current_user.is_authenticated:
        cart_items = OrderItem.query.join(Order).filter(Order.status == 'pending', Order.user_id == current_user.id).all()
    else:
        cart_items = OrderItem.query.filter_by(order_id=order_id).all()
        logger.info(f"Queried OrderItems for order_id {order_id}: Found {len(cart_items)} items: {[item.part_number for item in cart_items]}")
    try:
        inputs = load_inputs()
        material_densities = dxf_parser.load_material_densities()
    except Exception as e:
        logger.error(f"Error loading inputs or material density for price update: {str(e)}", exc_info=True)
        raise
    part_number = secure_filename(data.get("part_number", ""))
    logger.info(f"Received update_price request for part: {part_number}, order_id: {order_id}, full data: {data}")
    item = next((i for i in cart_items if i.part_number == part_number), None)
    if not item:
        available_parts = [i.part_number for i in cart_items]
        logger.error(f"Part not found: {part_number}. Available parts: {available_parts}")
        return jsonify({"error": f"Part not found: {part_number}"}), 404
    qty = data.get("quantity", item.quantity)
    try:
        item.quantity = int(qty) if qty not in ("", None) else 0
    except (ValueError, TypeError):
        item.quantity = 0
    item.material = data.get("material", item.material)
    item.thickness = float(data.get("thickness", item.thickness) or item.thickness)
    session['calculated'] = False
    breakdown = recalculate_cart(cart_items, inputs, material_densities)
    db.session.commit()
    updated_item = next((i for i in breakdown["detailed_breakdown"] if i["part_number"] == part_number), None)
    return jsonify({
        "part_number": updated_item["part_number"], "quantity": updated_item["quantity"],
        "material": updated_item["material"], "thickness": updated_item["thickness"],
        "unit_price": updated_item["unit_price"], "sell_price_per_part": updated_item["sell_price_per_part"],
        "total": breakdown["total_sell_price"]
    })


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if current_user.is_authenticated:
        cart_items = OrderItem.query.join(Order).filter(Order.status == 'pending', Order.user_id == current_user.id).all()
    else:
        order_id = session.get('order_id')
        if not order_id or not OrderItem.query.filter_by(order_id=order_id).first():
            flash('Your cart is empty!', 'error')
            return redirect(url_for('customer_index'))
        cart_items = OrderItem.query.filter_by(order_id=order_id).all()
    if not cart_items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('customer_index'))
    try:
        inputs = load_inputs()
        material_densities = dxf_parser.load_material_densities()
    except Exception as e:
        logger.error(f"Error loading inputs or material density for checkout: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load pricing data'}), 500
    breakdown = recalculate_cart(cart_items, inputs, material_densities)
    if request.method == "POST":
        if request.content_type != 'application/json':
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        try:
            data = request.get_json()
            session['checkout_data'] = data
            return jsonify({'redirect': url_for('checkout_process')})
        except Exception as e:
            logger.error(f"Error processing checkout POST: {str(e)}", exc_info=True)
            return jsonify({'error': 'Invalid request data'}), 400
    if current_user.is_authenticated:
        user_data = {
            'company_name': current_user.company or '',
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'email': current_user.email,
            'phone': current_user.phone
        }
        return render_template('checkout.html', items=cart_items, breakdown=breakdown, user_data=user_data, STRIPE_PUBLIC_KEY=app.config['STRIPE_PUBLIC_KEY'])
    else:
        return render_template('checkout_guest.html', items=cart_items, breakdown=breakdown, STRIPE_PUBLIC_KEY=app.config['STRIPE_PUBLIC_KEY'])


@app.route("/checkout_process", methods=["GET", "POST"])
def checkout_process():
    if current_user.is_authenticated:
        cart_items = OrderItem.query.join(Order).filter(Order.status == 'pending', Order.user_id == current_user.id).all()
    else:
        order_id = session.get('order_id')
        if not order_id:
            return jsonify({'error': 'No cart found'}), 400
        cart_items = OrderItem.query.filter_by(order_id=order_id).all()
        logger.info(f"Checkout process queried OrderItems for order_id {order_id}: Found {len(cart_items)} items: {[item.part_number for item in cart_items]}")
    if not cart_items:
        logger.error(f"Cart empty in checkout_process for order_id {order_id}")
        return jsonify({'error': 'Cart is empty'}), 400
    try:
        inputs = load_inputs()
        material_densities = dxf_parser.load_material_densities()
    except Exception as e:
        logger.error(f"Error loading inputs or material density for checkout: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load pricing data'}), 500
    breakdown = recalculate_cart(cart_items, inputs, material_densities)
    order_id = cart_items[0].order_id
    order = db.session.get(Order, order_id)
    if request.method == "POST":
        try:
            data = request.get_json()
            logger.info(f"Checkout process received data: {data}")
            session['checkout_data'] = data
            if current_user.is_authenticated:
                company_name = current_user.company or ''
                first_name = current_user.first_name
                last_name = current_user.last_name
                email = current_user.email
                phone = current_user.phone
            else:
                company_name = data.get('company_name', '')
                first_name = data.get('first_name')
                last_name = data.get('last_name')
                email = data.get('email')
                phone = data.get('phone')
            if not all([first_name, last_name, email, phone]):
                logger.error(f"Missing checkout data: first_name={first_name}, last_name={last_name}, email={email}, phone={phone}")
                return jsonify({'error': 'Missing required checkout information'}), 400
            order.company_name = company_name
            order.first_name = first_name
            order.last_name = last_name
            order.email = email
            order.phone = phone
            order.user_id = current_user.id if current_user.is_authenticated else None
            order.total = breakdown['total_sell_price']
            db.session.commit()
            os.makedirs('temp_orders', exist_ok=True)
            for item in cart_items:
                src_path = os.path.join(app.config['UPLOAD_FOLDER'], item.part_number)
                if os.path.exists(src_path):
                    upload = Upload(order_id=order_id, file_path=src_path)
                    db.session.add(upload)
            db.session.commit()
            stripe_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Plasma Table Burnouts Order',
                        },
                        'unit_amount': int(breakdown['total_sell_price'] * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('confirm', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('customer_index', _external=True),
                metadata={'order_id': order_id}
            )
            order.stripe_session_id = stripe_session.id
            db.session.commit()
            logger.info(f"Created Stripe session: {stripe_session.id}")
            return jsonify({'session_id': stripe_session.id})
        except Exception as e:
            logger.error(f"Error processing checkout POST: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to process payment'}), 500
    logger.info(f"Rendering checkout with STRIPE_PUBLIC_KEY: {app.config['STRIPE_PUBLIC_KEY']}")
    if current_user.is_authenticated:
        user_data = {
            'company_name': current_user.company or '',
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'email': current_user.email,
            'phone': current_user.phone
        }
        return render_template('checkout.html', items=cart_items, breakdown=breakdown, user_data=user_data, STRIPE_PUBLIC_KEY=app.config['STRIPE_PUBLIC_KEY'])
    else:
        return redirect(url_for('checkout_guest'))


@app.route('/confirm')
def confirm():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Checkout session not found.', 'error')
        return redirect(url_for('customer_index'))
    try:
        stripe_session = stripe.checkout.Session.retrieve(session_id)
        if stripe_session.payment_status != 'paid':
            flash('Payment not successful. Please try again.', 'error')
            return redirect(url_for('customer_index'))
        payment_intent_id = stripe_session.payment_intent
        logger.info(f"Confirming session {session_id}, payment_intent: {payment_intent_id}")
    except Exception as e:
        logger.error(f"Error retrieving Stripe session {session_id}: {str(e)}", exc_info=True)
        flash('Invalid checkout session.', 'error')
        return redirect(url_for('customer_index'))
    if current_user.is_authenticated:
        order = Order.query.filter_by(user_id=current_user.id, stripe_session_id=session_id).first()
    else:
        order_id = session.get('order_id')
        order = Order.query.filter_by(id=order_id, user_id=None, stripe_session_id=session_id).first()
    if not order:
        logger.error(f"No order found for session {session_id}, order_id {session.get('order_id', 'None')}")
        flash('No pending order found.', 'error')
        return redirect(url_for('customer_index'))
    order.status = 'succeeded'
    order.payment_intent_id = payment_intent_id
    order.purchase_date = datetime.now(ZoneInfo('UTC'))
    if not current_user.is_authenticated:
        stripe_email = stripe_session.customer_details.get('email') if stripe_session.customer_details else None
        order.email = order.email if order.email else stripe_email
    order.phone = stripe_session.customer_details.get('phone', order.phone) if stripe_session.customer_details else order.phone
    db.session.commit()
    production_dir = f'orders/files/{order.id}'
    os.makedirs(production_dir, exist_ok=True)
    uploads = Upload.query.filter_by(order_id=order.id).all()
    for upload in uploads:
        src = upload.file_path
        filename = os.path.basename(src)
        dst = os.path.join(production_dir, filename)
        if src != dst and os.path.exists(src):
            if os.path.exists(dst):
                os.remove(dst)
            try:
                os.rename(src, dst)
            except Exception as e:
                logger.error(f"Error moving file {src} to {dst}: {str(e)}", exc_info=True)
                flash(f"Error processing file {filename}.", 'error')
    if not current_user.is_authenticated:
        session['completed_order_id'] = order.id
    flash('Payment successful! Your order has been confirmed.', 'success')
    return redirect(url_for('success'))


@app.route("/success")
def success():
    if current_user.is_authenticated:
        order = Order.query.filter_by(user_id=current_user.id, status='succeeded').order_by(Order.purchase_date.desc()).first()
    else:
        order_id = session.get('completed_order_id')
        order = Order.query.filter_by(id=order_id, user_id=None, status='succeeded').first() if order_id else None
    if current_user.is_authenticated:
        pending_orders = Order.query.filter_by(status='pending', user_id=current_user.id).all()
    else:
        pending_orders = Order.query.filter_by(status='pending', id=session.get('order_id'), user_id=None).all()
    for order_to_clear in pending_orders:
        OrderItem.query.filter_by(order_id=order_to_clear.id).delete()
        db.session.delete(order_to_clear)
    db.session.commit()
    session.pop('order_id', None)
    session.pop('calculated', None)
    session.pop('checkout_data', None)
    session.pop('completed_order_id', None)
    logger.info("Cart cleared after checkout")
    if not order:
        return redirect(url_for('customer_index'))
    return render_template('success.html', order=order)


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/dev")
def dev_index():
    if not app.debug and os.getenv('DEV_ACCESS', 'false') != 'true':
        flash('Access denied. Operations login required.', 'error')
        return redirect(url_for('customer_index'))
    order_id = session.get('order_id')
    if current_user.is_authenticated:
        cart_items = OrderItem.query.join(Order).filter(Order.status == 'pending', Order.user_id == current_user.id).all()
    else:
        cart_items = OrderItem.query.filter_by(order_id=order_id).all()
    breakdown = None
    if cart_items:
        try:
            inputs = load_inputs()
            material_densities = dxf_parser.load_material_densities()
            breakdown = recalculate_cart(cart_items, inputs, material_densities)
        except Exception as e:
            logger.error(f"Error loading inputs or density in dev view: {str(e)}", exc_info=True)
            raise
    return render_template('dev_index.html', items=cart_items, breakdown=breakdown)


# --- Main Route ---
@app.route("/", methods=["GET", "POST"])
def customer_index():
    if not current_user.is_authenticated and 'order_id' not in session:
        session['order_id'] = generate_order_number()
        session.permanent = True
        logger.info(f"Generated new order_id: {session['order_id']}")
    order_id = session.get('order_id')
    if current_user.is_authenticated:
        pending_orders = Order.query.filter_by(status='pending', user_id=current_user.id).all()
        if pending_orders:
            order_id = pending_orders[0].id
            cart_items = OrderItem.query.filter_by(order_id=order_id).all()
        else:
            order_id = generate_order_number()
            order = Order(id=order_id, total=0, status='pending', user_id=current_user.id)
            db.session.add(order)
            db.session.commit()
            cart_items = []
        order_history = Order.query.filter(Order.user_id == current_user.id, Order.status == 'succeeded').order_by(Order.purchase_date.desc()).all()
    else:
        cart_items = OrderItem.query.filter_by(order_id=order_id).all()
        order_history = []
    logger.info(f"Current order_id: {order_id}, Cart items: {[item.part_number for item in cart_items]}")
    breakdown = None
    if cart_items and session.get('calculated', False):
        try:
            inputs = load_inputs()
            material_densities = dxf_parser.load_material_densities()
            breakdown = recalculate_cart(cart_items, inputs, material_densities)
            order = Order.query.filter_by(id=cart_items[0].order_id).first()
            if order:
                order.total = breakdown['total_sell_price']
                db.session.commit()
        except Exception as e:
            logger.error(f"Error recalculating cart: {str(e)}", exc_info=True)
            flash('Failed to calculate cart prices.', 'error')
    if request.method == "POST":
        if 'files[]' in request.files:
            logger.info(f"Form data received: {request.form}")
            files = request.files.getlist("files[]")
            new_items = []
            if files and files[0].filename and 'update_only' not in request.form:
                existing_parts = {item.part_number for item in cart_items}
                try:
                    inputs = load_inputs()
                    material_densities = dxf_parser.load_material_densities()
                except Exception as e:
                    logger.error(f"Failed to load inputs or material density: {str(e)}", exc_info=True)
                    flash('Failed to load pricing data.', 'error')
                    return jsonify({'error': 'Failed to load pricing data'}), 500
                order = Order.query.filter_by(id=order_id).first()
                if not order:
                    order_id = generate_order_number()
                    order = Order(id=order_id, total=0, status='pending', user_id=current_user.id if current_user.is_authenticated else None)
                    db.session.add(order)
                    db.session.commit()
                    if not current_user.is_authenticated:
                        session['order_id'] = order_id
                    logger.info(f"Created order_id: {order_id}")
                for file in files:
                    if file and file.filename.endswith('.dxf'):
                        filename = secure_filename(file.filename)
                        if filename in existing_parts:
                            continue
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        try:
                            material = request.form.get(f"material_{filename}", "A36 Steel")
                            thickness = float(request.form.get(f"thickness_{filename}", "0.25"))
                            parse_result = dxf_parser.parse_dxf(file_path, material=material, thickness=thickness)
                            (total_length, net_area_sqin, gross_min_x, gross_min_y, gross_max_x, gross_max_y,
                             gross_area_sqin, gross_weight_lb, net_weight_lb, entity_count_dict, outer_perimeter,
                             preview, pierce_count) = parse_result
                            entity_count = sum(entity_count_dict.values())
                            new_item = OrderItem(
                                order_id=order_id, part_number=filename, quantity=0, material=material, thickness=thickness,
                                length=total_length, net_area_sqin=net_area_sqin, gross_area_sqin=gross_area_sqin,
                                net_weight_lb=net_weight_lb, outer_perimeter=outer_perimeter,
                                gross_min_x=gross_min_x, gross_min_y=gross_min_y, gross_max_x=gross_max_x,
                                gross_max_y=gross_max_y, gross_weight_lb=gross_weight_lb, entity_count=entity_count,
                                preview=json.dumps(preview), pierce_count=pierce_count, unit_price=0, cost_per_part=0
                            )
                            new_items.append(new_item)
                            flash(f"Added {filename} to cart", "success")
                        except Exception as e:
                            logger.error(f"Error parsing {filename}: {str(e)}", exc_info=True)
                            flash(f"Failed to process file {filename}: {str(e)}", 'error')
                            continue
                if new_items:
                    for item in new_items:
                        db.session.add(item)
                    try:
                        db.session.commit()
                        logger.info(f"Committed {len(new_items)} items to order {order_id}")
                        cart_items = OrderItem.query.filter_by(order_id=order_id).all()
                        logger.info(f"Post-commit check: Found {len(cart_items)} items for order {order_id}: {[item.part_number for item in cart_items]}")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Commit failed for order {order_id}: {str(e)}", exc_info=True)
                        flash('Failed to save cart items.', 'error')
                        return jsonify({'error': 'Failed to save cart items'}), 500
                    logger.info(f"Cart after upload: {len(cart_items)} items")
                    session['calculated'] = False
                    breakdown = recalculate_cart(cart_items, inputs, material_densities)
        if 'update_only' in request.form:
            logger.info(f"Processing update_only with form data: {request.form}")
            for item in cart_items:
                qty_key = f"quantity_{item.part_number}"
                mat_key = f"material_{item.part_number}"
                thick_key = f"thickness_{item.part_number}"
                try:
                    item.quantity = int(request.form.get(qty_key, item.quantity))
                except (ValueError, TypeError):
                    item.quantity = item.quantity
                item.material = request.form.get(mat_key, item.material)
                try:
                    item.thickness = float(request.form.get(thick_key, item.thickness))
                except (ValueError, TypeError):
                    item.thickness = item.thickness
            try:
                inputs = load_inputs()
                material_densities = dxf_parser.load_material_densities()
                breakdown = recalculate_cart(cart_items, inputs, material_densities)
                order = Order.query.filter_by(id=cart_items[0].order_id).first()
                order.total = breakdown['total_sell_price']
                session['calculated'] = True
                db.session.commit()
                logger.info(f"Updated cart: {len(cart_items)} items with quantities: {[item.quantity for item in cart_items]}")
            except Exception as e:
                logger.error(f"Error recalculating cart: {str(e)}", exc_info=True)
                flash('Failed to calculate cart.', 'error')
                return jsonify({'error': 'Failed to calculate cart'}), 500
    return render_template("customer_index.html", items=cart_items, breakdown=breakdown, thicknesses=AVAILABLE_THICKNESSES, order_history=order_history, calculated=session.get('calculated', False))


# --- Main ---
if __name__ == "__main__":
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace("sqlite:///", "")
        logger.info(f"Database URI: {db_uri}")
        logger.info(f"Expected DB path: {db_path}")
        if os.path.exists(db_path):
            logger.info("Database file exists, checking tables...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Existing tables: {tables}")
        else:
            logger.info("Database file not found, creating tables...")
            db.create_all()
            logger.info("Database tables created successfully.")
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, port=5001)
