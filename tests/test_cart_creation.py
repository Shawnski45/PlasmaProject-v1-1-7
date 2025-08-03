import os
import io
import pytest
from app import create_app, db
from app.models import Order, OrderItem

# Use a sample DXF file from your Inputs/primary_validation directory
PRIMARY_VALIDATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Inputs/primary_validation'))

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_cart_creation_batch(client):
    dxf_files = [f for f in os.listdir(PRIMARY_VALIDATION_DIR) if f.lower().endswith('.dxf')]
    assert dxf_files, f"No DXF files found in {PRIMARY_VALIDATION_DIR}"
    # Prepare all files for a single multi-file POST
    files = []
    for dxf_file in dxf_files:
        with open(os.path.join(PRIMARY_VALIDATION_DIR, dxf_file), 'rb') as f:
            files.append((io.BytesIO(f.read()), dxf_file))
    data = {
        'material': 'A36 Steel',
        'thickness': 0.25
    }
    # Use 'files[]' to match common frontend conventions for multi-upload
    multi_file_data = []
    for file_obj, filename in files:
        multi_file_data.append(('files[]', (file_obj, filename)))
    # Combine form fields and files
    from werkzeug.datastructures import MultiDict
    post_data = MultiDict(list(data.items()) + multi_file_data)
    response = client.post('/', data=post_data, content_type='multipart/form-data', follow_redirects=True)
    # Check response
    assert response.status_code == 200, f"Failed to upload files: status {response.status_code}"
    html = response.data.decode('utf-8').lower()
    assert ("cart" in html or "success" in html or "added to cart" in html), "No cart or confirmation found in response for multi-file upload"
    # print removed: f"HTML snippet for multi-file upload:\n", html[:300])
    # Check that an OrderItem was created for each file
    with client.application.app_context():
        for dxf_file in dxf_files:
            item = OrderItem.query.filter_by(part_number=dxf_file).first()
            assert item is not None, f"OrderItem was not created for {dxf_file}"
            # print removed: f"SUCCESS: {dxf_file} -> OrderItem ID {item.id}")
