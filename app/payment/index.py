from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
import stripe
from flask_socketio import emit
from flask_jwt_extended import jwt_required
import json
from . import payment
from app import socketio

DATABASE_FILE = 'chat_database.json'

def load_database():
    """Load chat data from the JSON file."""
    with open(DATABASE_FILE, 'r') as f:
        return json.load(f)

def save_database(data):
    """Save chat data to the JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@payment.before_app_request
def setup_stripe():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

@payment.route('/payment-success', methods=['GET'])
def payment_success():
    return render_template('success.html')

@payment.route('/prepare-form', methods=['GET'])
def prepare_form():
    payment_link_url = request.args.get('payment_link_url')

    if not payment_link_url:
        return jsonify({'error': 'Payment link URL is required'}), 400

    # Pass the payment link to the template
    return render_template('payment_form.html', payment_link_url=payment_link_url)


@payment.route('/prepare-payment', methods=['GET'])
@jwt_required()
def prepare_payment():
    return render_template('preparation.html')

@payment.route('/create-product', methods=['GET', 'POST'])
@jwt_required()
def create_product():
    if request.method == 'POST':
        try:
            product_name = request.form['product_name']
            price_amount = int(request.form['price_amount']) * 100  # Convert to cents
            chat_id = request.form['chat_id']

            # Create Product
            product = stripe.Product.create(name=product_name)

            # Create Price for the Product
            price = stripe.Price.create(
                currency="usd",
                unit_amount=price_amount,
                product=product['id'],
            )

            # Create Payment Link
            payment_link = stripe.PaymentLink.create(
                line_items=[{"price": price['id'], "quantity": 1}],
                after_completion={"type": "redirect", "redirect": {"url": "https://shopmeai.com/payment/payment-success"}},
                billing_address_collection="auto",
                shipping_address_collection={
                    'allowed_countries':['US']
                }
            )

            # Emit message to chat (optional)
            message = f"[payment_url]url:{payment_link['url']}amount:{float(price_amount)/100}$"
            database = load_database()
            if chat_id in database:
                database[chat_id]["messages"].append({"sender": "admin", "text": message})
                save_database(database)
            emit('receive_message', {"sender": "admin", "text": message}, to=chat_id, namespace='/')

        except Exception as e:
            print(str(e))
            return jsonify({'error': str(e)}), 500

    return render_template('preparation.html')