import os
import firebase_admin
from firebase_admin import credentials

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(os.environ.get('FIREBASE_ADMIN_CREDENTIAL'))  # Path to service account JSON
    firebase_admin.initialize_app(cred, {
        'projectId': os.environ.get('FIREBASE_PROJECT_ID'),
    })
