import os
from app import create_app
from app.routes.debug import debug_bp

os.environ['FLASK_DEBUG'] = '1'  # Force debug mode
app = create_app()
print("Debug mode enabled. Running app with debug blueprint registered via __init__.py...")
app.run(debug=True)