
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Use importlib to load the module
spec = importlib.util.spec_from_file_location("wsgi", "app.py")
wsgi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wsgi)

# Access the app object
application = wsgi.app