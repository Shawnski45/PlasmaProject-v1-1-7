# dxf_parser.py
# Parses DXF files to estimate plasma cutting costs by measuring cutting geometry (torch paths).
# Shawn started this project March 3, 2025, on X.com, moved to Grok.com ~March 17.
# All code by Grok with Shawn's guidance.
# 2025-07-05: Fixed LWPOLYLINE has_bulge, enhanced POLYLINE/SPLINE handling, improved layer logic.
# 2025-07-05: Fixed linting errors (indentation of apply_transformation and process_entity).
# 2025-07-07: Refactored to remove pricing logic, moved to costing.py.
# 2025-07-14: Fixed linting errors (added except clauses, corrected indentation).

import ezdxf
from ezdxf.math import Vec2
import math
import os
import csv
import logging
import time
import json
from shapely.geometry import LineString, Polygon

TOLERANCE = 0.001  # Global tolerance for geometric ops

def load_material_densities(file_path=None):
    """Load material density from CSV, robust to working directory and columns."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    search_paths = [
        os.path.join(project_root, "material_densities.csv"),
        os.path.join(project_root, "app", "material_densities.csv"),
        os.path.join(project_root, "app", "utils", "material_densities.csv"),
    ]
    if file_path:
        search_paths.insert(0, file_path)
    for path in search_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames or not set(["material", "density"]).issubset(reader.fieldnames):
                        logging.error(f"material_densities.csv found at {path} but missing required columns ['material','density']")
                        return None
                    data = [row for row in reader]
                    if not data:
                        logging.error(f"material_densities.csv at {path} is empty!")
                        return None
                    logging.info(f"material_densities.csv loaded from {path}")
                    return data
            except Exception as e:
                logging.error(f"Failed to load material_densities.csv from {path}: {e}")
                return None
    logging.warning(f"material_densities.csv not found in any expected location: {search_paths}")
    return None

def load_inputs_csv():
    """Load input parameters from inputs.csv for parsing, providing safe defaults if file is missing."""
    inputs = {}
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    inputs_file = os.path.join(project_root, 'inputs.csv')
    resolved_path = os.path.abspath(inputs_file)
    logging.info(f"Attempting to load inputs.csv from: {resolved_path}")
    required_keys = ['kerf_thickness', 'skeleton_thickness']
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
                        if key in required_keys:
                            try:
                                inputs[key] = {"value": float(value), "unit": unit}
                            except ValueError:
                                logging.warning(f"Invalid value for {key} in inputs.csv: {value}")
                                inputs[key] = {"value": 0.0, "unit": unit}
                logging.info(f"Loaded inputs: {inputs}")
        except Exception as e:
            logging.error(f"Failed to parse inputs.csv: {e}")
            for key in required_keys:
                inputs[key] = {"value": 0.0, "unit": "unitless"}
    else:
        logging.warning(f"Could not load inputs.csv from {resolved_path}. Using safe defaults.")
        for key in required_keys:
            inputs[key] = {"value": 0.0, "unit": "unitless"}
    return inputs

def get_density(material, material_densities):
    """Retrieve density for a material."""
    for mat in material_densities:
        if mat["material"] == material:
            return float(mat["density"])
    raise ValueError(f"Material {material} not found in material_densities.csv")

def is_point_inside_boundary(point, boundary):
    """Check if point is inside boundary (min_x, max_x, min_y, max_y)."""
    x, y = point
    return (boundary['min_x'] <= x <= boundary['max_x'] and boundary['min_y'] <= y <= boundary['max_y'])

def arc_length_from_bulge(p1, p2, bulge):
    """Calculate arc length from bulge value between two points."""
    chord = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    theta = 4 * math.atan(abs(bulge))
    radius = chord / (2 * math.sin(theta / 2)) if theta != 0 else 0
    return radius * theta if radius > 0 else chord

def calculate_area(vertices):
    """Calculate polygon area using shoelace formula."""
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2

def parse_dxf(file_path, config_file=None, material="A36 Steel", thickness=0.25):
    """Parse DXF to extract cutting geometry for plasma torch cost estimation."""
    config = {
        "unit_scale_mm_to_in": 0.0393701,
        "unit_scale_cm_to_in": 0.393701,
        "unit_scale_m_to_in": 39.3701,
        "unit_scale_ft_to_in": 12.0,
        "default_unit": 1,
        "max_entities": 1000,
        "max_recursion_depth": 10,
        "ignored_entities": ["TEXT", "MTEXT", "DIMENSION", "LEADER"],
        "cut_layers": [
            "0", "1", "Layer 1", "Plan 1", "CUT", "CUTTING", "OUTLINE", "PROFILE", "VISIBLE (ANSI)",
            "Defpoints", "PEN_1", "PEN_2", "PEN_3", "PEN_4", "PEN_5"
        ],
        "reference_layers": [
            "REFERENCE", "REF", "CENTER", "CENTERLINE", "CONSTRUCTION", "HIDDEN", "PHANTOM", "AXIS",
            "DIMENSION", "ANNOTATION", "TEXT", "GUIDE", "GRID", "TITLE", "BORDER", "VIEWPORT", "SHEET",
            "LAYOUT", "NOTES", "SYMBOLS", "MARKUP", "BACKGROUND"
        ],
        "timeout_seconds": 30,
        "lead_in_length": 0.1,
        "lead_out_length": 0.1,
    }
    contour_count = 0

    # Validate material and thickness before parsing
    allowed_materials = ["A36 Steel", "Stainless 304", "Stainless 316", "Aluminum 3003", "Aluminum 6061"]
    allowed_thicknesses = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
    if not material or material not in allowed_materials:
        raise ValueError(f"Invalid or missing material: {material}. Allowed: {allowed_materials}")
    if not thickness or thickness not in allowed_thicknesses:
        raise ValueError(f"Invalid or missing thickness: {thickness}. Allowed: {allowed_thicknesses}")

    # Load inputs.csv for kerf_thickness and skeleton_thickness
    inputs_data = load_inputs_csv()
    config["kerf_thickness"] = inputs_data.get("kerf_thickness", {"value": 0.05, "unit": "in"})["value"]
    config["skeleton_thickness"] = inputs_data.get("skeleton_thickness", {"value": 0.1, "unit": "in"})["value"]

    total_length = 0
    net_area_sqin = 0
    gross_min_x, gross_min_y = float('inf'), float('inf')
    gross_max_x, gross_max_y = float('-inf'), float('-inf')
    entity_count = {"LINE": 0, "ARC": 0, "CIRCLE": 0, "LWPOLYLINE": 0, "POLYLINE": 0,
                    "INSERT": 0, "SPLINE": 0, "ELLIPSE": 0, "HATCH": 0, "3DFACE": 0, "POLYFACE": 0, "OTHER": 0}
    outer_boundaries = []
    inner_cutouts = []
    lines = []
    arcs = []
    preview = []
    processed_entities = set()

    try:
        start_time = time.time()
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        units = doc.header.get('$INSUNITS', config["default_unit"])
        unit_scale = 1.0
        if units == 4:
            unit_scale = config["unit_scale_mm_to_in"]
        elif units == 5:
            unit_scale = config["unit_scale_cm_to_in"]
        elif units == 6:
            unit_scale = config["unit_scale_m_to_in"]
        elif units == 2:
            unit_scale = config["unit_scale_ft_to_in"]
        logging.info(f"Detected units: {units}, applying scale factor: {unit_scale}")

        layers_found = set(e.dxf.layer for e in msp if hasattr(e.dxf, 'layer'))
        logging.info(f"Layers in DXF: {layers_found}")

        # --- Begin: Special logic for layer 0/1 ---
        # Scan for any cutting geometry on layer 0
        has_cut_on_layer0 = False
        for e in msp:
            if hasattr(e.dxf, 'layer') and e.dxf.layer.strip().lower() == '0':
                entity_type = e.dxftype().upper()
                if entity_type in ('LINE', 'ARC', 'CIRCLE', 'POLYLINE', 'LWPOLYLINE', 'SPLINE', 'ELLIPSE', 'HATCH', '3DFACE', 'POLYFACE'):
                    has_cut_on_layer0 = True
                    break
        # If true, treat all lines on layer 1 as reference
        treat_layer1_as_reference = has_cut_on_layer0
        # --- End: Special logic for layer 0/1 ---

        def apply_transformation(x, y, insert=(0, 0), xscale=1.0, yscale=1.0, rotation=0):
            x = x * xscale + insert[0]
            y = y * yscale + insert[1]
            if rotation:
                rad = math.radians(rotation)
                x_new = x * math.cos(rad) - y * math.sin(rad)
                y_new = x * math.sin(rad) + y * math.cos(rad)
                x, y = x_new, y_new
            return x * unit_scale, y * unit_scale

        def process_entity(entity, insert=(0, 0), xscale=1.0, yscale=1.0, rotation=0, depth=0):
            nonlocal total_length, gross_min_x, gross_max_x, gross_min_y, gross_max_y, net_area_sqin, preview
            if time.time() - start_time > config["timeout_seconds"]:
                logging.error(f"Timeout exceeded ({config['timeout_seconds']}s) processing {file_path}")
                raise TimeoutError("Parsing timeout")

            entity_id = id(entity)
            if entity_id in processed_entities or depth > config["max_recursion_depth"]:
                logging.warning(f"Skipping entity {entity.dxftype()} due to depth {depth} or duplicate")
                return
            processed_entities.add(entity_id)

            entity_type = entity.dxftype()
            layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'Unknown'
            try:
                dxf_attrs = {k: getattr(entity.dxf, k, None) for k in dir(entity.dxf) if not k.startswith('_') and not callable(getattr(entity.dxf, k, None))}
            except Exception as e:
                dxf_attrs = f"<error reading dxf attrs: {e}>"
            logging.debug(f"ENTITY DEBUG: type={entity_type}, layer={layer}, dxf_attrs={dxf_attrs}")
            layer_clean = layer.lower().strip()
            cut_layers_clean = [l.lower().strip() for l in config["cut_layers"]]
            reference_layers_clean = [l.lower().strip() for l in config.get("reference_layers", [])]
            construction_layers = ["construction", "reference", "center", "centerline"]
            construction_layers_clean = [l.lower().strip() for l in construction_layers]

            if treat_layer1_as_reference and layer_clean == '1':
                is_reference_entity = True
                is_cut_entity = False
            else:
                is_reference_entity = layer_clean in reference_layers_clean or layer_clean in construction_layers_clean
                is_cut_entity = layer_clean in cut_layers_clean and not is_reference_entity
            logging.debug(f"Entity {entity_type} original layer: '{layer}' cleaned: '{layer_clean}' | is_cut_entity: {is_cut_entity} | is_reference_entity: {is_reference_entity}")

            if is_reference_entity or not is_cut_entity:
                logging.info(f"Skipping entity {entity_type} on non-cut/construction/reference layer '{layer}' (not counted as cut geometry)")
                return

            try:
                if entity_type == "LINE":
                    start_x, start_y = apply_transformation(entity.dxf.start[0], entity.dxf.start[1], insert, xscale, yscale, rotation)
                    end_x, end_y = apply_transformation(entity.dxf.end[0], entity.dxf.end[1], insert, xscale, yscale, rotation)
                    length = math.hypot(end_x - start_x, end_y - start_y)
                    if is_cut_entity:
                        lines.append((start_x, start_y, end_x, end_y, length))
                        total_length += length
                        preview.append({"type": "line", "start": [start_x, start_y], "end": [end_x, end_y]})
                    gross_min_x = min(gross_min_x, start_x, end_x)
                    gross_max_x = max(gross_max_x, start_x, end_x)
                    gross_min_y = min(gross_min_y, start_y, end_y)
                    gross_max_y = max(gross_max_y, start_y, end_y)
                    entity_count["LINE"] += 1
                    logging.info(f"LINE on layer {layer}: Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "ARC":
                    center_x, center_y = apply_transformation(entity.dxf.center[0], entity.dxf.center[1], insert, xscale, yscale, rotation)
                    radius = entity.dxf.radius * (xscale + yscale) / 2 * unit_scale
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    if end_angle < start_angle:
                        end_angle += 360
                    length = 2 * math.pi * radius * (abs(end_angle - start_angle) / 360)
                    if is_cut_entity:
                        arcs.append((center_x, center_y, radius, start_angle, end_angle, length))
                        total_length += length
                        preview.append({"type": "arc", "center": [center_x, center_y], "radius": radius,
                                        "start_angle": start_angle, "end_angle": end_angle})
                    gross_min_x = min(gross_min_x, center_x - radius)
                    gross_max_x = max(gross_max_x, center_x + radius)
                    gross_min_y = min(gross_min_y, center_y - radius)
                    gross_max_y = max(gross_max_y, center_y + radius)
                    entity_count["ARC"] += 1
                    logging.info(f"ARC on layer {layer}: Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "CIRCLE":
                    center_x, center_y = apply_transformation(entity.dxf.center[0], entity.dxf.center[1], insert, xscale, yscale, rotation)
                    radius = entity.dxf.radius * (xscale + yscale) / 2 * unit_scale
                    length = 2 * math.pi * radius
                    if is_cut_entity:
                        total_length += length
                        outer_boundaries.append({
                            'center': (center_x, center_y), 'radius': radius, 'area': math.pi * radius ** 2,
                            'min_x': center_x - radius, 'max_x': center_x + radius,
                            'min_y': center_y - radius, 'max_y': center_y + radius,
                            'perimeter': length
                        })
                        preview.append({"type": "circle", "center": [center_x, center_y], "radius": radius})
                    gross_min_x = min(gross_min_x, center_x - radius)
                    gross_max_x = max(gross_max_x, center_x + radius)
                    gross_min_y = min(gross_min_y, center_y - radius)
                    gross_max_y = max(gross_max_y, center_y + radius)
                    entity_count["CIRCLE"] += 1
                    logging.info(f"CIRCLE on layer {layer}: Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "LWPOLYLINE":
                    points = []
                    for pt in entity:
                        x, y = apply_transformation(pt[0], pt[1], insert, xscale, yscale, rotation)
                        points.append((x, y))
                    if len(points) > 1:
                        length = sum(math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]) for i in range(1, len(points)))
                        if entity.closed:
                            length += math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1])
                        if is_cut_entity:
                            preview_points = points + [points[0]] if entity.closed else points
                            total_length += length
                            preview.append({"type": "lwpolyline", "points": preview_points})
                        gross_min_x = min(gross_min_x, *(p[0] for p in points))
                        gross_max_x = max(gross_max_x, *(p[0] for p in points))
                        gross_min_y = min(gross_min_y, *(p[1] for p in points))
                        gross_max_y = max(gross_max_y, *(p[1] for p in points))
                        entity_count["LWPOLYLINE"] += 1
                        logging.info(f"LWPOLYLINE on layer {layer}: Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "POLYLINE":
                    points = []
                    poly_length = 0
                    try:
                        if hasattr(entity, 'is_polyface_mesh') and entity.is_polyface_mesh:
                            for sub_entity in entity.virtual_entities():
                                process_entity(sub_entity, insert, xscale, yscale, rotation, depth + 1)
                        else:
                            vertices = []
                            for v in entity.vertices:
                                if hasattr(v.dxf, 'location'):
                                    loc = v.dxf.location
                                    vertices.append((loc[0], loc[1]))
                                elif hasattr(v.dxf, 'x') and hasattr(v.dxf, 'y'):
                                    vertices.append((v.dxf.x, v.dxf.y))
                                else:
                                    logging.warning(f"POLYLINE on layer {layer}: Invalid vertex format")
                                    continue
                            points = [apply_transformation(p[0], p[1], insert, xscale, yscale, rotation) for p in vertices]
                            if len(points) > 1:
                                for i in range(len(points) - 1):
                                    p1 = points[i]
                                    p2 = points[i + 1]
                                    seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                                    poly_length += seg_len
                                if hasattr(entity, 'is_closed') and entity.is_closed and len(points) > 2:
                                    p1 = points[-1]
                                    p2 = points[0]
                                    seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                                    poly_length += seg_len
                            if is_cut_entity:
                                total_length += poly_length
                                preview.append({"type": "polyline", "points": points})
                    except Exception as e:
                        logging.warning(f"POLYLINE on layer {layer}: Error processing: {e}")
                    entity_count["POLYLINE"] += 1
                    logging.info(f"POLYLINE on layer {layer}: Length={poly_length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "SPLINE":
                    try:
                        spline_attrs = {
                            'degree': getattr(entity.dxf, 'degree', None),
                            'control_points': len(getattr(entity, 'control_points', [])),
                            'knots': len(getattr(entity, 'knots', [])) if hasattr(entity, 'knots') else 0,
                            'weights': len(getattr(entity, 'weights', [])) if hasattr(entity, 'weights') else 0,
                            'is_rational': getattr(entity, 'is_rational', None),
                            'layer': layer,
                            'is_cut_entity': is_cut_entity
                        }
                        logging.info(f"[SPLINE ATTRS] {spline_attrs}")
                    except Exception as logex:
                        logging.warning(f"[SPLINE ATTRS] Could not log SPLINE attributes: {logex}")
                    if not is_cut_entity:
                        logging.warning(f"SPLINE entity on non-cut layer '{layer}' detected. Preview and count will still be included for diagnostics.")
                    try:
                        spline_points = []
                        try:
                            flattened = entity.flattening(TOLERANCE)
                            spline_points = [apply_transformation(p[0], p[1], insert, xscale, yscale, rotation) for p in flattened]
                            if len(spline_points) > 500:
                                logging.warning("SPLINE has >500 points, simplification skipped due to ezdxf 1.4.2 limitation")
                        except Exception as e:
                            logging.warning(f"SPLINE on layer {layer}: Flattening failed: {e}")
                            raise ValueError("Failed to flatten spline")
                        if not spline_points:
                            logging.error(f"SPLINE failed in {file_path}: knots={len(entity.knots) if hasattr(entity, 'knots') else 'N/A'}, control_points={len(entity.control_points) if hasattr(entity, 'control_points') else 'N/A'}, degree={getattr(entity.dxf, 'degree', 'N/A')}")
                            preview.append({"type": "error", "message": f"SPLINE processing failed: insufficient points"})
                            return
                        spline_length = 0
                        if spline_points and len(spline_points) >= 2:
                            for i in range(len(spline_points) - 1):
                                p1 = spline_points[i]
                                p2 = spline_points[i + 1]
                                seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                                spline_length += seg_len
                            if is_cut_entity:
                                total_length += spline_length
                            preview.append({
                                "type": "polyline",
                                "points": spline_points,
                                "source": "spline-approx"
                            })
                            logging.debug(f"SPLINE preview geometry extracted as polyline: {len(spline_points)} points")
                        else:
                            raise ValueError("Flattened spline has <2 points")
                        spline_data = {
                            "type": "spline",
                            "degree": getattr(entity.dxf, 'degree', None),
                            "control_points": [apply_transformation(p[0], p[1], insert, xscale, yscale, rotation) for p in getattr(entity, 'control_points', [])],
                            "knots": list(getattr(entity, 'knots', [])),
                            "weights": list(getattr(entity, 'weights', [])),
                            "is_rational": getattr(entity, 'is_rational', False)
                        }
                        preview.append(spline_data)
                        for x, y in spline_points:
                            gross_min_x = min(gross_min_x, x)
                            gross_max_x = max(gross_max_x, x)
                            gross_min_y = min(gross_min_y, y)
                            gross_max_y = max(gross_max_y, y)
                    except Exception as e:
                        logging.warning(f"SPLINE on layer {layer}: Error flattening or measuring spline: {e}")
                        try:
                            ctrl_points = [apply_transformation(p[0], p[1], insert, xscale, yscale, rotation) for p in getattr(entity, 'control_points', [])]
                            if ctrl_points and len(ctrl_points) >= 2:
                                spline_length = 0
                                for i in range(len(ctrl_points) - 1):
                                    p1 = ctrl_points[i]
                                    p2 = ctrl_points[i + 1]
                                    seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                                    spline_length += seg_len
                                if is_cut_entity:
                                    total_length += spline_length
                                preview.append({
                                    "type": "polyline",
                                    "points": ctrl_points,
                                    "source": "spline-control-fallback"
                                })
                                for x, y in ctrl_points:
                                    gross_min_x = min(gross_min_x, x)
                                    gross_max_x = max(gross_max_x, x)
                                    gross_min_y = min(gross_min_y, y)
                                    gross_max_y = max(gross_max_y, y)
                            else:
                                raise ValueError("Control points fallback has <2 points")
                        except Exception as ee:
                            logging.error(f"SPLINE fallback failed on layer {layer}: {ee}")
                            preview.append({
                                "type": "error",
                                "message": f"SPLINE processing failed on layer {layer}: {ee}"
                            })
                    finally:
                        entity_count["SPLINE"] += 1
                    logging.info(f"SPLINE on layer {layer}: Length={spline_length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "ELLIPSE":
                    try:
                        center_x, center_y = apply_transformation(entity.dxf.center[0], entity.dxf.center[1], insert, xscale, yscale, rotation)
                        major_axis = entity.dxf.major_axis
                        ratio = entity.dxf.radius_ratio
                        start_param = entity.dxf.start_param
                        end_param = entity.dxf.end_param
                        num_points = 64
                        ellipse_points = []
                        for i in range(num_points + 1):
                            t = start_param + (end_param - start_param) * i / num_points
                            x = center_x + major_axis[0] * math.cos(t) * xscale
                            y = center_y + major_axis[1] * math.sin(t) * yscale * ratio
                            x, y = apply_transformation(x, y, insert, xscale, yscale, rotation)
                            ellipse_points.append((x, y))
                        ellipse_length = sum(math.hypot(ellipse_points[i + 1][0] - ellipse_points[i][0], ellipse_points[i + 1][1] - ellipse_points[i][1])
                                            for i in range(num_points))
                        if is_cut_entity:
                            total_length += ellipse_length
                            preview.append({"type": "ellipse", "points": ellipse_points})
                        entity_count["ELLIPSE"] += 1
                        logging.info(f"ELLIPSE on layer {layer}: Length={ellipse_length:.2f} in{' (cut)' if is_cut_entity else ''}")
                    except Exception as e:
                        logging.warning(f"ELLIPSE on layer {layer}: Error measuring ellipse: {e}")
                elif entity_type == "HATCH":
                    length = 0.0
                    hatch_points = []
                    for path in entity.paths:
                        for edge in path.edges:
                            if edge.TYPE == "LineEdge":
                                start_x, start_y = apply_transformation(edge.start[0], edge.start[1], insert, xscale, yscale, rotation)
                                end_x, end_y = apply_transformation(edge.end[0], edge.end[1], insert, xscale, yscale, rotation)
                                seg_len = math.hypot(end_x - start_x, end_y - start_y)
                                if is_cut_entity:
                                    length += seg_len
                                    lines.append((start_x, start_y, end_x, end_y, seg_len))
                                    hatch_points.append((start_x, start_y))
                                    hatch_points.append((end_x, end_y))
                            elif edge.TYPE == "ArcEdge":
                                center_x, center_y = apply_transformation(edge.center[0], edge.center[1], insert, xscale, yscale, rotation)
                                radius = edge.radius * (xscale + yscale) / 2 * unit_scale
                                start_angle = edge.start_angle
                                end_angle = edge.end_angle
                                if end_angle < start_angle:
                                    end_angle += 360
                                seg_len = 2 * math.pi * radius * (abs(end_angle - start_angle) / 360)
                                if is_cut_entity:
                                    length += seg_len
                                    arcs.append((center_x, center_y, radius, start_angle, end_angle, seg_len))
                                    hatch_points.append((center_x, center_y))
                    if is_cut_entity and hatch_points:
                        total_length += length
                        preview.append({"type": "hatch", "points": hatch_points})
                    for x, y in hatch_points:
                        gross_min_x = min(gross_min_x, x)
                        gross_max_x = max(gross_max_x, x)
                        gross_min_y = min(gross_min_y, y)
                        gross_max_y = max(gross_max_y, y)
                    entity_count["HATCH"] += 1
                    logging.info(f"HATCH on layer {layer}: Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "3DFACE":
                    points = []
                    for p in entity.dxf.get_points():
                        points.append(apply_transformation(p[0], p[1], insert, xscale, yscale, rotation))
                    length = 0
                    for i in range(len(points)):
                        p1 = points[i]
                        p2 = points[(i + 1) % len(points)]
                        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                        if is_cut_entity:
                            length += seg_len
                            lines.append((p1[0], p1[1], p2[0], p2[1], seg_len))
                    if is_cut_entity:
                        total_length += length
                        preview.append({"type": "3dface", "points": points})
                    for x, y in points:
                        gross_min_x = min(gross_min_x, x)
                        gross_max_x = max(gross_max_x, x)
                        gross_min_y = min(gross_min_y, y)
                        gross_max_y = max(gross_max_y, y)
                    entity_count["3DFACE"] += 1
                    logging.info(f"3DFACE on layer {layer}: Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")
                elif entity_type == "POLYFACE":
                    for sub_entity in entity.virtual_entities():
                        process_entity(sub_entity, insert, xscale, yscale, rotation, depth + 1)
                    entity_count["POLYFACE"] += 1
                    logging.info(f"POLYFACE on layer {layer}: Processed sub-entities")
                elif entity_type == "INSERT":
                    block = doc.blocks[entity.dxf.name]
                    insert_point = (entity.dxf.insert[0], entity.dxf.insert[1])
                    xscale = entity.dxf.xscale if hasattr(entity.dxf, 'xscale') else 1.0
                    yscale = entity.dxf.yscale if hasattr(entity.dxf, 'yscale') else 1.0
                    rotation = entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0
                    for block_entity in block:
                        process_entity(block_entity, insert_point, xscale, yscale, rotation, depth + 1)
                    entity_count["INSERT"] += 1
                    logging.info(f"INSERT on layer {layer}: Processed block {entity.dxf.name}")
                else:
                    entity_count["OTHER"] += 1
                    logging.info(f"Skipping entity {entity_type} on layer {layer}")
            except Exception as e:
                logging.error(f"Error processing {entity_type} on layer {layer}: {e}")

        entity_processed = 0
        for entity in msp.query('*'):
            if entity_processed >= config["max_entities"]:
                logging.warning(f"Max entities ({config['max_entities']}) reached for {file_path}, stopping")
                break
            process_entity(entity)
            entity_processed += 1
            if entity_processed % 100 == 0:
                logging.info(f"Processed {entity_processed} entities in {file_path}")

        if not preview:
            logging.error(f"No preview geometry generated for {file_path}. Entity counts: {entity_count}")
            preview.append({"type": "error", "message": f"No cuttable geometry could be parsed from {os.path.basename(file_path)}."})

        if outer_boundaries:
            outer_boundaries.sort(key=lambda b: b['area'], reverse=True)
            outer_boundary = outer_boundaries[0]
            net_area_sqin = outer_boundary['area']
            for boundary in outer_boundaries[1:] + inner_cutouts:
                if 'center' in boundary:
                    center = boundary['center']
                    if is_point_inside_boundary(center, outer_boundary):
                        net_area_sqin -= boundary['area']
                else:
                    all_points_inside = all(is_point_inside_boundary(p, outer_boundary) for p in boundary['points'])
                    if all_points_inside:
                        net_area_sqin -= boundary['area']

        logging.info(f"Summary for {file_path}:")
        logging.info(f"  Total Cut Length: {total_length:.2f} in")
        logging.info(f"  Gross Area: {(gross_max_x - gross_min_x) * (gross_max_y - gross_min_y):.2f} sqin")
        logging.info(f"  Net Area: {net_area_sqin:.2f} sqin")
        logging.info(f"  Entity Counts: {entity_count}")

        if not preview:
            preview = [{"type": "warning", "message": f"No cutting geometry extracted from {os.path.basename(file_path)}. Check layers: {layers_found}"}]

        try:
            logging.info(f"DXF PREVIEW GENERATED: {json.dumps(preview)[:500]}")
        except Exception as e:
            logging.warning(f"Failed to log preview: {e}")

        if gross_min_x == float('inf') or gross_max_x == float('-inf'):
            gross_min_x = gross_max_x = 0
        if gross_min_y == float('inf') or gross_max_y == float('-inf'):
            gross_min_y = gross_max_y = 0
        if total_length > 0 and (gross_max_x == gross_min_x or gross_max_y == gross_min_y):
            all_points = []
            for item in preview:
                if 'points' in item and isinstance(item['points'], list):
                    all_points.extend(item['points'])
                elif 'center' in item:
                    all_points.append(item['center'])
            if all_points:
                xs = [pt[0] for pt in all_points]
                ys = [pt[1] for pt in all_points]
                gross_min_x, gross_max_x = min(xs), max(xs)
                gross_min_y, gross_max_y = min(ys), max(ys)
                logging.warning(f"Bounding box recalculated from preview points for {file_path}: "
                                f"({gross_min_x}, {gross_min_y}) - ({gross_max_x}, {gross_max_y})")
        if abs(gross_max_x - gross_min_x) > 1e6 or abs(gross_max_y - gross_min_y) > 1e6:
            logging.error(f"Invalid bounds for {file_path}: gross_x=({gross_min_x},{gross_max_x}), gross_y=({gross_min_y},{gross_max_y})")
            return {
                "total_length": 0,
                "net_area_sqin": 0,
                "gross_min_x": 0,
                "gross_min_y": 0,
                "gross_max_x": 0,
                "gross_max_y": 0,
                "gross_area_sqin": 0,
                "entity_count": entity_count,
                "preview": [{"type": "error", "message": f"Invalid bounds in {os.path.basename(file_path)}"}],
                "contour_count": 0
            }
        return {
            "total_length": total_length,
            "net_area_sqin": net_area_sqin,
            "gross_min_x": gross_min_x,
            "gross_min_y": gross_min_y,
            "gross_max_x": gross_max_x,
            "gross_max_y": gross_max_y,
            "gross_area_sqin": (gross_max_x - gross_min_x) * (gross_max_y - gross_min_y),
            "entity_count": entity_count,
            "preview": preview,
            "contour_count": contour_count
        }

    except TimeoutError:
        logging.error(f"Parsing timeout for {file_path}")
        return {
            "total_length": total_length,
            "net_area_sqin": net_area_sqin,
            "gross_min_x": gross_min_x if gross_min_x != float('inf') else 0,
            "gross_min_y": gross_min_y if gross_min_y != float('inf') else 0,
            "gross_max_x": gross_max_x if gross_max_x != float('-inf') else 0,
            "gross_max_y": gross_max_y if gross_max_y != float('-inf') else 0,
            "gross_area_sqin": (gross_max_x - gross_min_x) * (gross_max_y - gross_min_y),
            "entity_count": entity_count,
            "preview": [{"type": "error", "message": f"Timeout parsing {os.path.basename(file_path)}"}],
            "contour_count": contour_count
        }
    except Exception as e:
        logging.error(f"Failed to parse {file_path}: {e}")
        return {
            "total_length": 0,
            "net_area_sqin": 0,
            "gross_min_x": 0,
            "gross_min_y": 0,
            "gross_max_x": 0,
            "gross_max_y": 0,
            "gross_area_sqin": 0,
            "entity_count": entity_count,
            "preview": [{"type": "error", "message": f"Failed to parse {os.path.basename(file_path)}: {e}"}],
            "contour_count": contour_count
        }