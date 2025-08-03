# run_batch_dxf.py
# Script to manually run batch_parse_dxf and log results (for manual regression testing)
import os
import logging
from test_dxf_parse_batch import batch_parse_dxf, check_and_recover_log_file

if __name__ == "__main__":
    test_dir = r"C:\Users\shawng\CascadeProjects\PlasmaProject v1-1-7\Inputs\primary_validation"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, 'batch_dxf_parse_test.log')
    check_and_recover_log_file(log_path)
    batch_parse_dxf(test_dir)
    logging.info("Batch DXF parse test complete. See batch_dxf_parse_test.log for details.")
