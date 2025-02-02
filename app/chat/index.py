from flask import request, render_template, redirect, url_for, make_response, jsonify, current_app as app, flash
from flask_jwt_extended import get_jwt_identity, jwt_required, create_access_token, get_jwt, verify_jwt_in_request, decode_token
from werkzeug.utils import secure_filename
from flask_socketio import emit, join_room
import uuid
import json
import stripe
import os
from datetime import datetime, timedelta
from . import chat
from app import socketio
from werkzeug.security import generate_password_hash, check_password_hash

# Database simulation setup
DATABASE_FILE = 'chat_database.json'
if not os.path.exists(DATABASE_FILE):
    with open(DATABASE_FILE, 'w') as f:
        json.dump({}, f)


# Admin login credentials
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "admin"
}

@chat.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'GET':
        # Render the registration HTML form
        return render_template('register.html')

    # Handle POST request for user registration
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Validation checks
    if not username or not password:
        flash("Username and password are required.", "danger")
        return render_template('register.html')
    
    # Initialize database if it does not exist
    if not os.path.exists("shop_database.json"):
        with open("shop_database.json", "w") as f:
            json.dump({"users": {}}, f)

    # Load existing data from the database
    with open("shop_database.json", "r") as f:
        database = json.load(f)

    users = database.get("users", {})

    # Check if username already exists
    if username in [user["username"] for user in users.values()]:
        flash("Username already exists. Please choose another one.", "danger")
        return render_template('register.html')

    # Hash the password
    hashed_password = generate_password_hash(password)

    # Generate a unique user ID
    user_id = str(uuid.uuid4())

    # Save the user data
    users[user_id] = {
        "username": username,
        "password": hashed_password,
        "chat_ids": []
    }
    database["users"] = users

    # Save the updated database
    with open("shop_database.json", "w") as f:
        json.dump(database, f)

    # Flash a success message and redirect to login page
    flash("Registration successful. Please login.", "success")
    return redirect(url_for('chat.user_login'))


@chat.route('/login', methods=['GET', 'POST'])
def user_login():
    """Authenticate user and issue JWT."""
    if request.method == 'GET':
        # Render the login HTML form
        return render_template('user_login.html')

    # Handle POST request for login
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for('chat.user_login'))

    # Open the database file and read the user data
    with open("shop_database.json", "r") as f:
        database = json.load(f)

    users = database.get("users", {})

    for user_id, user_data in users.items():
        if user_data["username"] == username:
            # Verify the password
            if check_password_hash(user_data["password"], password):
                # Create JWT token with user identity and additional claims
                additional_claims = {'role': 'user'}
                access_token = create_access_token(identity=user_id, additional_claims=additional_claims)
                
                # Create the response object
                response = make_response(redirect(url_for('chat.index')))
                response.set_cookie("access_token", access_token, httponly=True)

                flash("Login successful.", "success")
                return response
            
            # If password doesn't match
            flash("Invalid credentials.", "danger")
            break

    # If user is not found
    flash("Invalid credentials.", "danger")
    return redirect(url_for('chat.user_login'))

@chat.route('/logout', methods=['GET'])
def user_logout():
    """Logout the user by clearing the access token cookie."""
    response = make_response(redirect(url_for('chat.user_login')))
    response.set_cookie('access_token', '', expires=0)
    return response

# Utility functions
def load_database():
    """Load chat data from the JSON file."""
    with open(DATABASE_FILE, 'r') as f:
        return json.load(f)
    
def load_user_database():
    """Load user data from the JSON file."""
    with open("shop_database.json", "r") as f:
        return json.load(f)

def save_database(data):
    """Save chat data to the JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def cleanup_chats():
    """Remove inactive chats older than an hour."""
    database = load_database()
    now = datetime.utcnow()
    to_delete = []

    for chat_id, chat_data in database.items():
        created_at = datetime.fromisoformat(chat_data["timestamp"])
        if not chat_data["messages"] and now - created_at > timedelta(hours=1):
            to_delete.append(chat_id)

    for chat_id in to_delete:
        del database[chat_id]

    save_database(database)

def add_chat(first_message, chat_id):
    """Create a new chat with the first message."""
    cleanup_chats()
    database = load_database()
    database[chat_id] = {
        "messages": [{"sender": "user", "text": first_message}],
        "active": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    save_database(database)
    return chat_id

def add_message_to_chat(chat_id, message, sender):
    # Load the current database
    database = load_database()
    
    # Get the current timestamp
    timestamp = datetime.utcnow().isoformat()
    
    # Create the message dictionary
    new_message = {
        "sender": sender,
        "text": message
    }
    
    # Check if the chat already exists in the database
    if chat_id in database:
        # Append the new message to the chat's messages list
        database[chat_id]["messages"].append(new_message)
    else:
        # If chat doesn't exist, create a new chat entry
        database[chat_id] = {
            "messages": [new_message],
            "active": True,
            "timestamp": timestamp
        }
    
    # Update the timestamp for the chat
    database[chat_id]["timestamp"] = timestamp
    
    # Save the updated database back to the file
    save_database(database)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@chat.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads for a chat."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file:
        if file.filename == "blob" or not '.' in file.filename:
            file_extension = file.content_type.split('/')[-1]  # Extract extension from MIME type
            filename = f"{str(uuid.uuid4())}.{file_extension}"
        else:
            filename = secure_filename(file.filename)

        # Ensure the file type is allowed
        if allowed_file(filename):
            directory = "app/" + app.config["UPLOAD_FOLDER"]
            file_path = os.path.join(directory, filename)
            file.save(file_path)
            
            # Save file details to the database
            chat_id = request.form.get("chat_id")  # Get the chat_id from the form data
            database = load_database()

            # Assuming you want to save the file URL in the chat's messages
            if chat_id not in database:
                database[chat_id] = {"messages": []}


            return jsonify({"file_url": f"/{file_path}"}), 200
        else:
            return jsonify({"error": "Invalid file type"}), 400
    return jsonify({"error": "Invalid request"}), 400

@socketio.on('send_image')
def handle_send_image(data):
    """Handle image messages in chats."""
    chat_id = data['chat_id']
    image_url = data['image'][4:]
    sender = data['sender']

    database = load_database()
    
        
    if chat_id in database:
        if not database[chat_id]["active"]:
            database[chat_id]["active"] = True
        database[chat_id]["messages"].append({"sender": sender, "image": image_url, "text": ""})
        save_database(database)

        emit('receive_message', {"sender": sender, "image": image_url}, to=chat_id, role="admin")

@chat.route('/', methods=['GET', 'POST'])
@jwt_required(optional=True)
def index():
    jwt_data = get_jwt()
    if jwt_data.get('role') == "admin":
        return redirect(url_for('chat.admin_dashboard'))
    elif jwt_data.get('role') == "user":
        pass
    else:
        return redirect(url_for('chat.user_login'))
    """Render the homepage and create a new chat session."""
    user_id = get_jwt_identity()
    users_db = load_user_database()
    users = users_db.get("users", {})
    user = users.get(user_id, {})
    if not user_id:
        # If the user is not logged in, redirect to the login page
        flash("You must be logged in to start a chat.", "danger")
        return redirect(url_for('chat.user_login'))
    
    if request.method == 'POST':
        # Create a new chat when the button is clicked
        chat_id = str(uuid.uuid4())
        database = load_database()
        database[chat_id] = {
            "messages": [],
            "active": False,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_database(database)

        
        user["chat_ids"].append(chat_id)

        with open("shop_database.json", "w") as f:
            json.dump(users_db, f, indent=4)
        flash("Chat session created successfully.", "success")
        return redirect(url_for('chat.client_chat', chat_id=chat_id))
    
    # If GET request, just render the page without creating a new chat
    return render_template('index.html', user=user, role=jwt_data.get('role'))


@chat.context_processor
def inject_is_admin():
    """Check if the current user is an admin."""
    is_admin = False
    token = request.cookies.get('access_token_cookie')
    if token:
        try:
            jwt_data = decode_token(token)
            if jwt_data.get("role") == "admin":
                is_admin = True
  
        except Exception:
            pass
    return {"is_admin": is_admin}

@chat.route('/chat/<chat_id>', methods=['GET'])
@jwt_required(optional=True)
def client_chat(chat_id):
    role = ""
    jwt_data = get_jwt()
    if jwt_data.get('role') == "admin":
        role = "admin"
    elif jwt_data.get('role') == "user":
        role = "user"
    else:
        return redirect(url_for('chat.user_login'))
    
    """Render the chat interface for a specific chat session."""
    database = load_database()

    try:
        verify_jwt_in_request(optional=True)
        jwt_data = get_jwt()
        print(f"JWT Data: {jwt_data}, Role: {jwt_data.get('role')}")

        if jwt_data.get("role") == "admin": 
            role = "admin"
        elif jwt_data.get("role") == "user":
            is_admin = False
        else:
            return redirect(url_for('chat.user_login'))
    except Exception:
        pass

    if chat_id not in database:
        database[chat_id] = {
            "messages": [],
            "active": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_database(database)

    return render_template('client_chat.html', chat_id=chat_id, messages=database[chat_id]["messages"], role=role)


@socketio.on('send_message')
def handle_send_message(data):
    """Handle text messages in chats."""
    chat_id = data['chat_id']
    message = data['message']
    sender = data['sender']

    database = load_database()
    if chat_id in database:
        if not database[chat_id]["active"]:
            database[chat_id]["active"] = True
        database[chat_id]["messages"].append({"sender": sender, "text": message})
        save_database(database)
        emit('receive_message', {"sender": sender, "text": message}, to=chat_id)

@socketio.on('join_chat')
def handle_join_chat(data):
    """Add a user to a specific chat room."""
    chat_id = data['chat_id']
    join_room(chat_id)

@chat.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Admin login endpoint."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            additional_claims = {'role': 'admin'}
            access_token = create_access_token(identity='admin', additional_claims=additional_claims)
            
            response = make_response(redirect(url_for('chat.admin_dashboard')))
            response.set_cookie('access_token', access_token, httponly=True)
            return response
        return render_template('admin_login.html', error="Invalid credentials.")

    return render_template('admin_login.html')

@chat.route('/admin_dashboard', methods=['GET'])
@jwt_required()
def admin_dashboard():
    """Admin dashboard showing active chats."""
    role = ""
    jwt_data = get_jwt()
    if jwt_data.get('role') == "admin":
        role = "admin"
    database = load_database()
    chats_overview = [
        {"chat_id": chat_id, "first_message": chat_data["messages"][0]["text"]}
        for chat_id, chat_data in database.items()
        if chat_data["active"] and chat_data["messages"]
    ]
    return render_template('admin_dashboard.html', chats=chats_overview, role=role)

@chat.route('/delete_chat/<chat_id>', methods=['POST'])
@jwt_required()
def delete_chat(chat_id):
    """Delete a chat session."""
    database = load_database()
    if chat_id in database:
        del database[chat_id]
        save_database(database)
    return redirect(url_for('chat.admin_dashboard'))

