from flask import Blueprint, request, jsonify
from app.utils import dxf_parser, costing
from app import db
from app.routes.main import load_inputs
import json
from datetime import datetime
import os
import tempfile
import uuid

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

@debug_bp.route('/parse', methods=['POST'])
def parse_dxf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    files = request.files.getlist('file')
    material = request.form.get('material', 'A36 Steel')
    thickness = float(request.form.get('thickness', 0.25))

    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No selected file"}), 400
    if not any(f.filename.lower().endswith('.dxf') for f in files):
        return jsonify({"error": "File must be a .dxf"}), 400

    order_id = str(uuid.uuid4())
    results = []
    for file in files:
        if not file.filename.lower().endswith('.dxf'):
            continue
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        try:
            parse_result = dxf_parser.parse_dxf(temp_file_path)
            cart_uid = str(uuid.uuid4())
            order_item = {
                'cart_uid': cart_uid,
                'order_id': order_id,
                'part_number': file.filename,
                'preview': json.dumps(parse_result.get('preview', [])),
                'gross_min_x': parse_result.get('gross_min_x', 0),
                'gross_max_x': parse_result.get('gross_max_x', 0),
                'gross_min_y': parse_result.get('gross_min_y', 0),
                'gross_max_y': parse_result.get('gross_max_y', 0),
                'net_area_sqin': parse_result.get('net_area_sqin', 0),
                'gross_area_sqin': parse_result.get('gross_area_sqin', 0),
                'total_length': parse_result.get('total_length', 0),
                'pierce_count': parse_result.get('entity_count', {}).get('PIERCE', 0),
                'material': material,
                'thickness': thickness,
                'quantity': 1
            }
            db.order_items.insert_one(order_item)
            results.append(order_item)
        except Exception as e:
            return jsonify({"error": f"Failed to parse {file.filename}: {str(e)}"}), 400
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    inputs = load_inputs()
    # Use dxf_parser.load_material_densities if available, fallback to hardcoded values
    material_densities = getattr(dxf_parser, 'load_material_densities', lambda: {
        "A36 Steel": 0.283, "Stainless 304": 0.289, "Aluminum 6061": 0.098
    })()
    cart_items = [item for item in results]
    cost_result = costing.calculate_costs(cart_items, inputs, material_densities)

    return jsonify({
        "status": "success",
        "items": [{"cart_uid": item['cart_uid'], "part_number": item['part_number'], "material": item['material'], "thickness": item['thickness'], "quantity": item['quantity']} for item in cart_items],
        "cost_result": cost_result,
        "order_id": order_id
    }), 200