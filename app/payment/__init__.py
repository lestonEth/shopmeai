from flask import Blueprint

payment = Blueprint('payment', __name__, template_folder='templates')

from . import index
