# dxf_parser.py
# This script parses DXF files to extract cut lengths, areas, weights, and preview data for Ohio Drum's quoting tool.
# Shawn started this project March 3, 2025, on X.com, moved to Grok.com ~March 17. All code by Grok with Shawn's guidance.
# 2025-04-04: Added pierce_count and lead_in_out_length to parsing output (ref: Shawn's request for plasma cutting accuracy)
# 2025-04-04: Updated pierce_count to reflect continuous cut paths instead of per-entity (ref: Shawn's clarification on quoting needs)
# 2025-04-XX: Switched to density-based weight calculation (ref: Shawn's request for smarter weight system)
# 2025-04-12: Added 'import json' to fix F821/Pylance 'undefined name json' error in parse_dxf (Grok fix)

import ezdxf  # Library for reading DXF files
import math
import os
import csv
import logging
import json  # Added to support config file loading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_material_densities(file_path="material_densities.csv"):
    """
    Load material densities from a CSV file.
    Each row should have 'material' and 'density' columns.
    """
    material_densities = []
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            material_densities.append(row)
    return material_densities


def get_density(material, material_densities):
    """
    Retrieve the density for a given material from the list of material densities.
    """
    for mat in material_densities:
        if mat["material"] == material:
            return float(mat["density"])
    raise ValueError(f"Material {material} not found in material_densities.csv")


def is_point_inside_boundary(point, boundary):
    """
    Check if a point is inside a given boundary (min_x, max_x, min_y, max_y).
    """
    x, y = point
    return (boundary['min_x'] <= x <= boundary['max_x'] and boundary['min_y'] <= y <= boundary['max_y'])


def detect_closed_loops(lines, arcs, unit_scale):
    """
    Detect closed loops from lines and arcs to identify boundaries and cutouts.
    """
    tolerance = 0.001  # Tolerance for considering points as connected
    segments = []
    for start_x, start_y, end_x, end_y, length in lines:
        segments.append(((start_x, start_y), (end_x, end_y), length))
    for center_x, center_y, radius, start_angle, end_angle, length in arcs:
        start_x = center_x + radius * math.cos(math.radians(start_angle))
        start_y = center_y + radius * math.sin(math.radians(start_angle))
        end_x = center_x + radius * math.cos(math.radians(end_angle))
        end_y = center_y + radius * math.sin(math.radians(end_angle))
        segments.append(((start_x, start_y), (end_x, end_y), length))

    loops = []
    used = set()
    for i, (start, end, length) in enumerate(segments):
        if i in used:
            continue
        loop = [start]
        current = end
        used.add(i)
        while True:
            next_seg = None
            for j, (s, e, l) in enumerate(segments):
                if j in used:
                    continue
                if math.hypot(s[0] - current[0], s[1] - current[1]) < tolerance:
                    next_seg = j
                    loop.append(s)
                    current = e
                    used.add(j)
                    break
                elif math.hypot(e[0] - current[0], e[1] - current[1]) < tolerance:
                    next_seg = j
                    loop.append(e)
                    current = s
                    used.add(j)
                    break
            if next_seg is None or math.hypot(current[0] - loop[0][0], current[1] - loop[0][1]) < tolerance:
                if len(loop) > 2:
                    loops.append((loop, sum(seg[2] for seg in segments if seg[0] in loop or seg[1] in loop)))
                break
    return loops


def calculate_area(vertices):
    """
    Calculate the area of a polygon defined by its vertices using the shoelace formula.
    """
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2


def parse_dxf(file_path, config_file=None, material="A36 Steel", thickness=0.25):
    """
    Parse a DXF file to extract total cut length, net area, gross boundaries, weights, and preview data.
    """
    total_length = 0
    net_area_sqin = 0
    gross_min_x, gross_min_y = float('inf'), float('inf')
    gross_max_x, gross_max_y = float('-inf'), float('-inf')
    entity_count = {"LINE": 0, "ARC": 0, "CIRCLE": 0, "LWPOLYLINE": 0, "POLYLINE": 0,
                    "INSERT": 0, "SPLINE": 0, "ELLIPSE": 0, "HATCH": 0, "OTHER": 0}
    outer_boundaries = []
    inner_cutouts = []
    outer_perimeter = 0
    lines = []
    arcs = []
    preview = []
    pierce_count = 0
    lead_in_out_length = 0

    # Default configuration for parsing
    config = {
        "unit_scale_mm_to_in": 0.0393701,
        "unit_scale_cm_to_in": 0.393701,
        "unit_scale_m_to_in": 39.3701,
        "unit_scale_ft_to_in": 12.0,
        "max_recursion_depth": 10,
        "ignored_entities": ["TEXT", "MTEXT"],
        "cut_layers": ["0"],
        "default_unit": 1,
        "lead_in_length": 0.5,
        "lead_out_length": 0.5
    }
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config.update(json.load(f))

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DXF file not found: {file_path}")
        logging.info(f"Attempting to read DXF file: {file_path}")
        doc = ezdxf.readfile(file_path)
    except FileNotFoundError as e:
        logging.error(f"Error: {e}")
        return 0, 0, 0, 0, 0, 0, 0, 0, 0, entity_count, 0, [], 0, 0
    except Exception as e:
        logging.error(f"Error reading DXF file {file_path}: {e}")
        return 0, 0, 0, 0, 0, 0, 0, 0, 0, entity_count, 0, [], 0, 0

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

    processed_entities = set()

    def apply_transformation(x, y, insert=(0, 0), xscale=1.0, yscale=1.0, rotation=0):
        """
        Apply transformation (scaling, rotation, insertion) to coordinates.
        """
        x = x * xscale + insert[0]
        y = y * yscale + insert[1]
        if rotation:
            rad = math.radians(rotation)
            x_new = x * math.cos(rad) - y * math.sin(rad)
            y_new = x * math.sin(rad) + y * math.cos(rad)
            x = x_new
            y = y_new
        return x * unit_scale, y * unit_scale

    def process_entity(entity, insert=(0, 0), xscale=1.0, yscale=1.0, rotation=0, depth=0):
        """
        Recursively process each entity in the DXF file, applying transformations and calculating lengths and areas.
        """
        nonlocal total_length, gross_min_x, gross_max_x, gross_min_y, gross_max_y, net_area_sqin, outer_perimeter, preview
        entity_id = id(entity)
        if entity_id in processed_entities or depth > config["max_recursion_depth"]:
            logging.warning(f"Skipping entity {entity.dxftype()} due to depth {depth} or duplicate")
            return
        processed_entities.add(entity_id)

        entity_type = entity.dxftype()
        layer = entity.dxf.layer
        if entity_type in config["ignored_entities"]:
            logging.info(f"Ignoring entity {entity_type} on layer {layer}")
            return

        is_cut_entity = layer in config["cut_layers"]

        try:
            if entity_type == "LINE":
                start_x, start_y = apply_transformation(entity.dxf.start[0], entity.dxf.start[1], insert, xscale, yscale, rotation)
                end_x, end_y = apply_transformation(entity.dxf.end[0], entity.dxf.end[1], insert, xscale, yscale, rotation)
                length = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5
                if is_cut_entity:
                    lines.append((start_x, start_y, end_x, end_y, length))
                    total_length += length
                    preview.append({"type": "line", "start": [start_x, start_y], "end": [end_x, end_y]})
                gross_min_x = min(gross_min_x, start_x, end_x)
                gross_max_x = max(gross_max_x, start_x, end_x)
                gross_min_y = min(gross_min_y, start_y, end_y)
                gross_max_y = max(gross_max_y, start_y, end_y)
                entity_count["LINE"] += 1
                logging.info(f"LINE on layer {layer}: Start=({start_x:.2f}, {start_y:.2f}), End=({end_x:.2f}, {end_y:.2f}), Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")

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
                logging.info(f"ARC on layer {layer}: Center=({center_x:.2f}, {center_y:.2f}), Radius={radius:.2f}, Angle={abs(end_angle - start_angle):.2f} deg, Length={length:.2f} in{' (cut)' if is_cut_entity else ''}")

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
                logging.info(f"CIRCLE on layer {layer}: Center=({center_x:.2f}, {center_y:.2f}), Radius={radius:.2f}, Length={length:.2f} in, Area={math.pi * radius ** 2:.2f} sqin{' (cut)' if is_cut_entity else ''}")

            elif entity_type in ("LWPOLYLINE", "POLYLINE"):
                if entity_type == "POLYLINE":
                    vertices = [(v.dxf.x, v.dxf.y) for v in entity.vertices if hasattr(v, 'dxf')]
                else:
                    raw_points = entity.get_points()
                    seen = set()
                    vertices = []
                    for p in raw_points:
                        pt = (p[0], p[1])
                        if pt not in seen:
                            seen.add(pt)
                            vertices.append(pt)
                points = [(apply_transformation(p[0], p[1], insert, xscale, yscale, rotation)[0],
                           apply_transformation(p[0], p[1], insert, xscale, yscale, rotation)[1]) for p in vertices]
                segment_lengths = []
                n = len(points)
                total_seg_length = 0
                for i in range(n):
                    x1, y1 = points[i]
                    x2, y2 = points[(i + 1) % n]
                    length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                    segment_lengths.append(length)
                    total_seg_length += length
                if is_cut_entity:
                    total_length += total_seg_length
                    for i in range(n):
                        start = points[i]
                        end = points[(i + 1) % n]
                        preview.append({"type": "line", "start": [start[0], start[1]], "end": [end[0], end[1]]})
                gross_min_x = min(gross_min_x, min(p[0] for p in points))
                gross_max_x = max(gross_max_x, max(p[0] for p in points))
                gross_min_y = min(gross_min_y, min(p[1] for p in points))
                gross_max_y = max(gross_max_y, max(p[1] for p in points))
                if entity.closed or (entity_type == "POLYLINE" and entity.is_closed):
                    area = calculate_area(points)
                    if is_cut_entity:
                        boundary = {
                            'min_x': min(p[0] for p in points), 'max_x': max(p[0] for p in points),
                            'min_y': min(p[1] for p in points), 'max_y': max(p[1] for p in points),
                            'area': area, 'points': points, 'perimeter': total_seg_length
                        }
                        outer_boundaries.append(boundary)
                    logging.info(f"{entity_type} on layer {layer}: Points={len(points)}, Closed, Total Length={total_seg_length:.2f} in, Area={area:.2f} sqin{' (cut)' if is_cut_entity else ''}")
                else:
                    logging.info(f"{entity_type} on layer {layer}: Points={len(points)}, Open, Total Length={total_seg_length:.2f} in")
                entity_count[entity_type] += 1

            elif entity_type == "ELLIPSE":
                entity_count["ELLIPSE"] += 1
                logging.warning(f"ELLIPSE on layer {layer}: Currently unsupported")

            elif entity_type == "HATCH":
                entity_count["HATCH"] += 1
                logging.warning(f"HATCH on layer {layer}: Currently unsupported")

            elif entity_type == "INSERT":
                block = doc.blocks[entity.dxf.name]
                insert_point = (entity.dxf.insert[0], entity.dxf.insert[1])
                xscale = entity.dxf.xscale if entity.dxf.hasattr('xscale') else 1.0
                yscale = entity.dxf.yscale if entity.dxf.hasattr('yscale') else 1.0
                rotation = entity.dxf.rotation if entity.dxf.hasattr('rotation') else 0
                entity_count["INSERT"] += 1
                logging.info(f"INSERT on layer {layer}: InsertPoint=({insert_point[0]:.2f}, {insert_point[1]:.2f}), Scale=({xscale:.2f}, {yscale:.2f}), Rotation={rotation:.2f} deg")
                for block_entity in block:
                    process_entity(block_entity, insert_point, xscale, yscale, rotation, depth + 1)

            elif entity_type == "SPLINE":
                control_points = [(p[0], p[1]) for p in entity.control_points]
                points = [apply_transformation(p[0], p[1], insert, xscale, yscale, rotation) for p in control_points]
                segment_lengths = []
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                    segment_lengths.append(length)
                    if is_cut_entity:
                        total_length += length
                        preview.append({"type": "line", "start": [x1, y1], "end": [x2, y2]})
                    gross_min_x = min(gross_min_x, x1, x2)
                    gross_max_x = max(gross_max_x, x1, x2)
                    gross_min_y = min(gross_min_y, y1, y2)
                    gross_max_y = max(gross_max_y, y1, y2)
                entity_count["SPLINE"] += 1
                logging.info(f"SPLINE on layer {layer}: Points={len(points)}, Total Length={sum(segment_lengths):.2f} in")

            else:
                entity_count["OTHER"] += 1
                logging.warning(f"Unsupported entity type: {entity_type} on layer {layer}")

        except Exception as e:
            logging.error(f"Error processing entity {entity_type} on layer {layer}: {e}")

    total_entities = 0
    for entity in msp.query('*'):
        total_entities += 1
        logging.info(f"Processing entity #{total_entities}: {entity.dxftype()} on layer {entity.dxf.layer}")
        process_entity(entity)

    if total_entities == 0:
        logging.warning(f"No entities found in modelspace of {file_path}")

    loops = detect_closed_loops(lines, arcs, unit_scale)
    if outer_boundaries:
        pierce_count = len(outer_boundaries)
        for loop_area, loop, loop_perimeter in [(calculate_area(loop), loop, perimeter) for loop, perimeter in loops]:
            boundary = {
                'min_x': min(p[0] for p in loop), 'max_x': max(p[0] for p in loop),
                'min_y': min(p[1] for p in loop), 'max_y': max(p[1] for p in loop),
                'area': loop_area, 'points': loop, 'perimeter': loop_perimeter
            }
            inner_cutouts.append(boundary)
            pierce_count += 1
            logging.info(f"Detected inner loop cutout: Perimeter={loop_perimeter:.2f} in, Area={loop_area:.2f} sqin")
    elif loops and not outer_boundaries:
        loop_areas = [(calculate_area(loop), loop, perimeter) for loop, perimeter in loops]
        loop_areas.sort(reverse=True)
        outer_loop_area, outer_loop, outer_perimeter = loop_areas[0]
        net_area_sqin = outer_loop_area
        outer_boundary = {
            'min_x': min(p[0] for p in outer_loop), 'max_x': max(p[0] for p in outer_loop),
            'min_y': min(p[1] for p in outer_loop), 'max_y': max(p[1] for p in outer_loop),
            'area': outer_loop_area, 'points': outer_loop, 'perimeter': outer_perimeter
        }
        outer_boundaries.append(outer_boundary)
        pierce_count = 1
        logging.info(f"Detected outer loop: Perimeter={outer_perimeter:.2f} in, Area={net_area_sqin:.2f} sqin")
        for area, loop, perimeter in loop_areas[1:]:
            all_points_inside = all(is_point_inside_boundary(p, outer_boundary) for p in loop)
            if all_points_inside:
                inner_cutouts.append({'area': area, 'points': loop, 'perimeter': perimeter})
                pierce_count += 1
                logging.info(f"Subtracting inner loop cutout: Area={area:.2f} sqin")

    if outer_boundaries:
        outer_boundaries.sort(key=lambda b: b['area'], reverse=True)
        outer_boundary = outer_boundaries[0]
        outer_perimeter = outer_boundary['perimeter']
        net_area_sqin = outer_boundary['area']
        logging.info(f"Outer boundary area: {net_area_sqin:.2f} sqin")
        for boundary in outer_boundaries[1:] + inner_cutouts:
            if 'center' in boundary:
                center = boundary['center']
                if is_point_inside_boundary(center, outer_boundary):
                    net_area_sqin -= boundary['area']
                    pierce_count += 1
                    logging.info(f"Subtracting inner circle cutout: Center=({center[0]:.2f}, {center[1]:.2f}), Area={boundary['area']:.2f} sqin")
            else:
                all_points_inside = all(is_point_inside_boundary(p, outer_boundary) for p in boundary['points'])
                if all_points_inside:
                    net_area_sqin -= boundary['area']
                    logging.info(f"Subtracting inner polyline/loop cutout: Area={boundary['area']:.2f} sqin")

    inputs = {}
    try:
        with open("inputs.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                inputs[row["parameter"]] = float(row["value"])
    except Exception as e:
        logging.error(f"Error loading inputs.csv: {e}, using defaults")
        inputs["kerf_thickness"] = 0.05
        inputs["skeleton_thickness"] = 0.1

    lead_in_out_length = pierce_count * (config["lead_in_length"] + config["lead_out_length"])
    total_length += lead_in_out_length

    # Try to load material densities, but skip weights if missing
    try:
        material_densities = load_material_densities()
        density = get_density(material, material_densities)
    except Exception as e:
        logging.warning(f"Material densities missing or failed to load: {e}. Setting weights to 0.")
        density = 0
    if gross_max_x > gross_min_x and gross_max_y > gross_min_y:
        gross_min_x -= (inputs["skeleton_thickness"] + inputs["kerf_thickness"] / 2)
        gross_max_x += (inputs["skeleton_thickness"] + inputs["kerf_thickness"] / 2)
        gross_min_y -= (inputs["skeleton_thickness"] + inputs["kerf_thickness"] / 2)
        gross_max_y += (inputs["skeleton_thickness"] + inputs["kerf_thickness"] / 2)
        width = (gross_max_x - gross_min_x)
        height = (gross_max_y - gross_min_y)
        kerf_area = total_length * inputs["kerf_thickness"]
        gross_area_sqin = (width * height) + kerf_area
    else:
        gross_area_sqin = 0
    gross_weight_lb = gross_area_sqin * thickness * density if density else 0
    net_weight_lb = net_area_sqin * thickness * density if density else 0

    if gross_max_x == float('-inf') or gross_min_x == float('inf'):
        logging.warning(f"No valid geometry in {file_path}, using defaults")
        gross_min_x, gross_min_y, gross_max_x, gross_max_y = 0, 0, 0, 0
        gross_area_sqin = 0
        gross_weight_lb = 0

    if entity_count["OTHER"] > 0:
        logging.info(f"Total unsupported entities (OTHER): {entity_count['OTHER']}")

    logging.info(f"Summary for {file_path}:")
    logging.info(f"  Total Cut Length: {total_length:.2f} in")
    logging.info(f"  Pierce Count: {pierce_count}")
    logging.info(f"  Lead-in/Out Length: {lead_in_out_length:.2f} in")
    logging.info(f"  Gross Boundaries: [{gross_min_x:.4f}, {gross_min_y:.4f}] to [{gross_max_x:.4f}, {gross_max_y:.4f}]")
    logging.info(f"  Gross Area: {gross_area_sqin:.2f} sqin")
    logging.info(f"  Gross Weight: {gross_weight_lb:.2f} lb")
    logging.info(f"  Net Area: {net_area_sqin:.2f} sqin")
    logging.info(f"  Net Weight: {net_weight_lb:.2f} lb")
    logging.info(f"  Entity Counts: {entity_count}")

    return (total_length, net_area_sqin, gross_min_x, gross_min_y, gross_max_x, gross_max_y,
            gross_area_sqin, gross_weight_lb, net_weight_lb, entity_count, outer_perimeter, preview, pierce_count)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python dxf_parser.py <dxf_file_path> [config_file_path]")
    else:
        file_path = sys.argv[1]
        config_path = sys.argv[2] if len(sys.argv) > 2 else None
        result = parse_dxf(file_path, config_path)
        print(f"Final Result: {result}")
