from flask import Blueprint

chat = Blueprint('chat', __name__, template_folder='templates', static_folder='static')

from . import index
