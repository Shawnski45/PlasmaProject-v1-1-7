from app import create_app
from flask_migrate import stamp

app = create_app()
with app.app_context():
    stamp()
