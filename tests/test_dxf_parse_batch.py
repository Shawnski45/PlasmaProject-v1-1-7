# test_dxf_parse_batch.py
# Purpose: Batch-parse a directory of DXF files using the main dxf_parser module and log summary results.
# This script is intended for regression testing and validation of geometry extraction, entity handling,
# and error reporting across a range of DXF files. Output includes detailed logs and a CSV summary for review.

import os
import sys
import logging
import time
# print removed: f"[DEBUG] Current working directory: {os.getcwd()}")
script_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(script_dir, 'batch_dxf_parse_test.log')
sys.path.insert(0, os.path.abspath(os.path.join(script_dir, '..', 'app', 'utils')))
import dxf_parser
import csv
import shutil
from datetime import datetime

# --- Robust log file integrity check and recovery ---
def check_and_recover_log_file(log_path):
    """
    Checks if the log file is valid UTF-8 and optionally if lines match the expected format.
    If corrupted, renames the file and ensures a fresh log can be started.
    """
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    # Optionally, check for expected log format (timestamp - LEVEL - message)
                    if i > 100:  # Don't check whole file if large
                        break
        except (UnicodeDecodeError, OSError) as e:
            # Log file is corrupted or unreadable
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            corrupt_path = log_path + f'.corrupt.{ts}'
            try:
                shutil.move(log_path, corrupt_path)
                # print removed: f"[WARNING] Corrupted log file renamed to {corrupt_path}.")
            except Exception as move_ex:
                pass
                # print removed: f"[ERROR] Failed to rename corrupted log file: {move_ex}")
            # Create a fresh log file
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('')

# Perform log file integrity check before configuring logging
check_and_recover_log_file(log_path)

# Configure logging to file and console for this script, with error handling
try:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8', mode='a'),
            logging.StreamHandler()
        ]
    )
except Exception as log_ex:
    # print removed: f"[ERROR] Failed to configure logging: {log_ex}")
    raise

def batch_parse_dxf(directory, material="A36 Steel", thickness=0.25):
    """
    Parse all DXF files in the given directory using the main dxf_parser,
    log detailed results, and summarize geometry extraction success/failure.
    Also outputs a CSV summary and flags files with no geometry for manual review.
    """
    def is_preview_valid(preview):
        if not preview or not isinstance(preview, list):
            return False
        for item in preview:
            if not isinstance(item, dict):
                return False
            if "type" not in item:
                return False
            # For lines/polylines, check points
            if item["type"] in ("lwpolyline", "polyline"):
                if "points" not in item or not item["points"]:
                    return False
            # For circles/arcs, check center/radius
            if item["type"] == "circle":
                if "center" not in item or "radius" not in item:
                    return False
        return True

    results = []
    flagged_files = []
    csv_rows = []
    for fname in os.listdir(directory):
        if fname.lower().endswith('.dxf'):
            fpath = os.path.join(directory, fname)
            logging.info(f"\n---\nParsing file: {fpath}")
            try:
                import ezdxf
                import time
                parse_start = time.time()
                doc = ezdxf.readfile(fpath)
                logging.info(f"DXF file metadata: {doc.header}")
                logging.info(f"DXF file version: {doc.dxfversion}")
                logging.info(f"DXF file units: {doc.header.get('$INSUNITS', 'Unknown')}")
                msp = doc.modelspace()
                result = dxf_parser.parse_dxf(fpath, material=material, thickness=thickness)
                preview = result.get('preview', [])
                entity_count = result.get('entity_count', {})
                total_length = result.get('total_length', 0)
                net_area = result.get('net_area_sqin', 0)
                preview_types = set(e.get('type') for e in preview) if isinstance(preview, list) else set()
                has_geometry = any(e.get('type') != 'warning' for e in preview) if isinstance(preview, list) else False
                preview_valid = is_preview_valid(preview)
                logging.info(f"Geometry summary: total_length={total_length}, net_area={net_area}, entity_count={entity_count}")
                
                # Enhanced diagnostic logging for POLYLINE/LWPOLYLINE
                import os as _os
                verbose = bool(_os.environ.get('VERBOSE_LOGGING', '0') not in ['0', 'false', 'False'])
                polyline_types = {'POLYLINE', 'LWPOLYLINE'}
                for entity in preview if isinstance(preview, list) else []:
                    etype = entity.get('type')
                    if etype in polyline_types:
                        vertices = entity.get('vertices') or entity.get('points')
                        bulges = entity.get('bulges') if 'bulges' in entity else None
                        msg = f"{etype} entity: "
                        if vertices is not None:
                            msg += f"num_vertices={len(vertices)}"
                            if len(vertices) == 0:
                                logging.warning(f"{etype} entity in {fname} has NO vertices: {entity}")
                        else:
                            msg += "vertices attribute missing"
                            logging.warning(f"{etype} entity in {fname} missing vertices attribute: {entity}")
                        if bulges is not None:
                            msg += f", has_bulges={any(b != 0 for b in bulges) if isinstance(bulges, (list, tuple)) else bool(bulges)}"
                        else:
                            msg += ", no bulge data"
                        if verbose:
                            logging.debug(msg + f" | entity: {entity}")
                        else:
                            logging.info(msg)
                if has_geometry:
                    logging.info(f"Preview geometry extracted for {fname}.")
                else:
                    logging.warning(f"NO geometry extracted for {fname}. Preview: {preview}")
                    flagged_files.append(fname)
                if not preview_valid:
                    logging.warning(f"INVALID preview for {fname}. This file may not render in the UI.")
                    flagged_files.append(fname)
                results.append((fname, True, entity_count, total_length, net_area, preview, preview_valid))
                pierce_count = result.get('pierce_count', 0)
                contour_count = result.get('contour_count', 0)
                gross_area = result.get('gross_area_sqin', 0)
                gross_weight = result.get('gross_weight_lb', 0)
                net_weight = result.get('net_weight_lb', 0)
                outer_perimeter = result.get('outer_perimeter', 0)
                csv_rows.append({
                    "filename": fname,
                    "total_length": total_length,
                    "net_area": net_area,
                    "pierce_count": pierce_count,
                    "contour_count": contour_count,
                    "gross_area": gross_area,
                    "gross_weight": gross_weight,
                    "net_weight": net_weight,
                    "entity_count": entity_count,
                    "outer_perimeter": outer_perimeter,
                    "preview_valid": preview_valid
                })
            except Exception as e:
                logging.error(f"Exception parsing {fname}: {e}", exc_info=True)
                results.append((fname, False, {}, 0, 0, str(e)))
                csv_rows.append({
                    'filename': fname,
                    'success': False,
                    'total_length': 0,
                    'net_area': 0,
                    'pierce_count': 0,
                    'contour_count': 0,
                    'gross_area': 0,
                    'gross_weight': 0,
                    'net_weight': 0,
                    'entity_count': '{}',
                    'outer_perimeter': 0
                })
                flagged_files.append(fname)

    # Write CSV summary
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'batch_dxf_parse_summary.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "filename", "total_length", "net_area", "pierce_count", "contour_count", "gross_area", "gross_weight", "net_weight", "entity_count", "outer_perimeter", "preview_valid"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    logging.info(f"CSV summary written to {csv_path}")

    # Log flagged files for manual review
    if flagged_files:
        logging.warning(f"\nFiles flagged for manual review (no geometry or parse error):\n" + '\n'.join(flagged_files))
    else:
        logging.info("All files parsed with geometry extracted.")

    return results

import pytest

def test_batch_parse_dxf():
    test_dir = r"C:\Users\shawng\CascadeProjects\PlasmaProject v1-1-7\Inputs\primary_validation"
    results = batch_parse_dxf(test_dir)
    for result in results:
        fname, success, entity_count, total_length, net_area, preview, preview_valid = result
        assert isinstance(preview, list), f"Preview not a list in {fname}"
        assert total_length >= 0, f"Negative total length in {fname}"
        # If the file parsed successfully and has length, gross_area should be in a reasonable range
        if success and total_length > 0:
            # gross_area is only in the CSV, so check preview_valid as proxy for geometry
            assert preview_valid, f"Preview invalid for {fname}"
            # Optionally, check preview contains at least one geometry or error
            assert any(p.get('type') in ['line', 'arc', 'circle', 'polyline', 'lwpolyline', 'spline', 'error'] for p in preview), f"No valid preview or error in {fname}"
