#costing.py
#Created to calculate the cost of a part based on the material, thickness, and length.
#Separated from main.py and dxf_parser.py on 2025-07-07
#All code by Grok with Shawn's guidance.

import logging
from app.utils import dxf_parser

def convert_value(value, from_unit, to_unit, unit_conversions):
    """Convert a value from one unit to another using UNIT_CONVERSIONS."""
    if from_unit not in unit_conversions or to_unit not in unit_conversions[from_unit]:
        return value
    return value * unit_conversions[from_unit][to_unit]

def calculate_costs(cart_items, inputs, material_densities):
    """Calculate material, labor, and machine costs for cart items, distributing order-level costs by cut time."""
    logging.debug(f"Processing cart_items: {[item.get('part_number') for item in cart_items]}")
    unit_conversions = {
        "hour": {"min": 60}, "min": {"min": 1}, "sec": {"min": 1 / 60},
        "$/hour": {"$/min": 1 / 60}, "$/min": {"$/min": 1}, "in/min": {"in/min": 1},
        "in": {"in": 1}, "$/lb": {"$/lb": 1}, "unitless": {"unitless": 1}
    }
    total_sell_price = 0
    detailed_breakdown = []

    # Calculate unique material-thickness combinations
    unique_material_thickness = set((item.get('material'), item.get('thickness')) for item in cart_items if item.get('material') and item.get('thickness'))
    num_unique_material_thickness = len(unique_material_thickness)
    num_parts = sum(item.get('quantity', 1) or 1 for item in cart_items)

    # Calculate order-level setup and changeover times
    order_setup_time = inputs.get("order_setup_time", {"value": 0.0, "unit": "min"})["value"]
    thickness_changeover_time = inputs.get("thickness_changeover_time", {"value": 0.0, "unit": "min"})["value"]
    order_changeover_time = (num_unique_material_thickness - 1) * thickness_changeover_time if num_unique_material_thickness > 1 else 0

    # Calculate per-part times and costs
    per_part_labor_times = []
    for item in cart_items:
        if not item.get('material') or not item.get('thickness'):
            logging.info(f"Skipping {item.get('part_number')}: missing material or thickness")
            continue

        try:
            density = dxf_parser.get_density(item.get('material'), material_densities)
        except ValueError as e:
            logging.warning(f"Failed to get density for {item.get('material')}: {e}")
            density = 0

        # Material cost (using gross area for pricing)
        gross_area = item.get('gross_area_sqin')
        if gross_area is None:
            gross_area = (item.get('gross_max_x', 0) - item.get('gross_min_x', 0)) * (item.get('gross_max_y', 0) - item.get('gross_min_y', 0))
        # NOTE: Pricing now uses gross area instead of net area
        material_efficiency = inputs.get("material_efficiency", {"value": 0.9, "unit": "unitless"})["value"]
        adjusted_gross_area = gross_area / material_efficiency if material_efficiency > 0 else gross_area
        volume = adjusted_gross_area * item.get('thickness', 0)
        weight = volume * density
        steel_cost_per_lb = inputs.get("steel_cost_per_lb", {"value": 0.0, "unit": "$/lb"})["value"]
        material_cost = weight * steel_cost_per_lb

        # Cutting time based on thickness
        thickness = item.get('thickness', 0)
        cut_speed = (
            inputs.get("cut_speed_0.375", {"value": 60.0, "unit": "in/min"})["value"] if thickness <= 0.375 else
            inputs.get("cut_speed_0.75", {"value": 40.0, "unit": "in/min"})["value"] if thickness <= 0.75 else
            inputs.get("cut_speed_1.0", {"value": 25.0, "unit": "in/min"})["value"]
        )
        length = item.get('length', 0)
        cut_time = length / cut_speed if length and cut_speed > 0 else 0

        # Pierce time
        pierce_count = item.get('pierce_count', 0)
        pierce_time = pierce_count * inputs.get("pierce_time", {"value": 0.0, "unit": "sec"})["value"] / 60 if pierce_count else 0

        # Cleanup time based on thickness
        cleanup_time = (
            inputs.get("cleanup_assembly_time_thick", {"value": 45.0, "unit": "sec"})["value"] / 60 if thickness >= 0.75 else
            inputs.get("cleanup_assembly_time_thin", {"value": 15.0, "unit": "sec"})["value"] / 60
        )

        # Per-part labor time
        per_part_labor_time = cut_time + pierce_time + cleanup_time
        per_part_labor_times.append((item, per_part_labor_time))

    # Calculate order-level labor and machine costs
    total_per_part_labor_time = sum((item.get('quantity', 1) or 1) * per_part_labor_time for item, per_part_labor_time in per_part_labor_times)
    order_labor_time = total_per_part_labor_time + order_setup_time + order_changeover_time
    direct_labor_rate = inputs.get("direct_labor_rate", {"value": 0.0, "unit": "$/hour"})["value"]
    labor_cost = order_labor_time * convert_value(direct_labor_rate, "$/hour", "$/min", unit_conversions)
    machine_rate_per_min = inputs.get("machine_rate_per_min", {"value": 0.0, "unit": "$/min"})["value"]
    order_setup_machine_cost = order_setup_time * machine_rate_per_min
    changeover_machine_cost = order_changeover_time * machine_rate_per_min
    order_level_machine_cost = order_setup_machine_cost + changeover_machine_cost

    # Distribute costs and calculate final price
    for item, per_part_labor_time in per_part_labor_times:
        if total_per_part_labor_time > 0:
            labor_cost_per_part = labor_cost * (per_part_labor_time / total_per_part_labor_time)
            machine_cost_order_per_part = order_level_machine_cost * (per_part_labor_time / total_per_part_labor_time)
        else:
            labor_cost_per_part = 0
            machine_cost_order_per_part = 0

        material_cost = material_cost
        machine_cost_per_part = cut_time * machine_rate_per_min
        total_machine_cost_per_part = machine_cost_per_part + machine_cost_order_per_part
        cogs_per_part = material_cost + labor_cost_per_part + total_machine_cost_per_part
        margin = inputs.get("margin", {"value": 0.0, "unit": "unitless"})["value"]
        price_per_part = cogs_per_part / (1 - margin) if margin < 1 else cogs_per_part
        sell_price_per_part = price_per_part * (item.get('quantity', 1) or 1)
        total_sell_price += sell_price_per_part

        logging.info(f"Item {item.get('part_number')}: material_cost={material_cost:.2f}, labor_cost_per_part={labor_cost_per_part:.2f}, total_machine_cost_per_part={total_machine_cost_per_part:.2f}, cogs_per_part={cogs_per_part:.2f}, price_per_part={price_per_part:.2f}, sell_price_per_part={sell_price_per_part:.2f}")

        detailed_breakdown.append({
            "part_number": item.get('part_number'),
            "quantity": item.get('quantity', 1) or 1,
            "material": item.get('material'),
            "thickness": item.get('thickness'),
            "unit_price": price_per_part,
            "sell_price_per_part": sell_price_per_part
        })

    breakdown = {"total_sell_price": total_sell_price, "detailed_breakdown": detailed_breakdown}
    logging.info(f"calculate_costs returning: {breakdown}")
    return breakdown