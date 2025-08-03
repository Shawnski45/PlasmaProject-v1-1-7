import os
import pytest
from firebase_admin import credentials, initialize_app, delete_app, _apps

@pytest.fixture(scope="module")
def clear_firebase():
    # Ensure no app is already initialized
    for app in list(_apps.values()):
        delete_app(app)
    yield
    for app in list(_apps.values()):
        delete_app(app)

def test_firebase_credentials_valid(clear_firebase):
    """Test that Firebase credentials from environment variables are valid and can initialize Firebase Admin SDK."""
    cred_dict = {
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
    }
    missing = [k for k, v in cred_dict.items() if not v]
    assert not missing, f"Missing Firebase credential fields: {missing}"
    try:
        cred = credentials.Certificate(cred_dict)
        app = initialize_app(cred)
        assert app is not None
    except Exception as e:
        pytest.fail(f"Firebase credentials validation failed: {e}")
