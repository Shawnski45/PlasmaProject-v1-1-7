"""
test_utils.py
Tests utility functions in app/utils/ (e.g., dxf_parser) for correct parsing, error handling, and edge cases.
Development-only: logs parsing results and error cases.
"""
import pytest
from app.utils import dxf_parser
import os

def test_parse_dxf_valid():
    # This test assumes a valid sample DXF file exists in tests/data/sample.dxf
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample.dxf")
    if not os.path.exists(sample_path):
        pytest.skip("No sample.dxf available for DXF parsing test.")
    result = dxf_parser.parse_dxf(sample_path)
    assert isinstance(result, dict)
    assert "entities" in result

def test_parse_dxf_invalid():
    # This test passes a non-existent file and expects an exception
    with pytest.raises(Exception):
        dxf_parser.parse_dxf("/nonexistent/file.dxf")

# Development-only: log parsing result
def test_dev_parse_log(capsys):
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample.dxf")
    if not os.path.exists(sample_path):
        pytest.skip("No sample.dxf available for DXF parsing test.")
    result = dxf_parser.parse_dxf(sample_path)
    
    out, _ = capsys.readouterr()
    assert "[DEV] DXF parse result:" in out
