from flask_sqlalchemy import SQLAlchemy
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import jwt
from models import User,db
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})  # Adjust the origin to match your React app



JWT_SECRET = "your_jwt_secret_key"  # Use a strong, secure secret key for JWT

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'

from models import db  # Import the db instance from models.py
db.init_app(app)  # Initialize the app with the db instance


# Image model
class Images(db.Model):
    __tablename__ = 'images'  # Conventionally lowercase table names
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(50), nullable=False)  # Assuming user_id is a string
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)  # Automatically set the upload time

@app.route('/api/images', methods=['GET'])
def get_images():
    images = Images.query.all()
    return jsonify([{
        'id': img.id,
        'filename': img.filename,
        'user_id': img.user_id,
        'upload_time': img.upload_time.isoformat()  # Return as ISO format for better readability
    } for img in images])

@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['image']
    user_id = request.form.get('user_id')
    
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    # Save the file
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # Save image info to database
    new_image = Images(filename=filename, user_id=user_id)
    db.session.add(new_image)
    db.session.commit()
    
    return jsonify({"message": "Image uploaded successfully!"}), 201

@app.route('/api/delete/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    image = Images.query.get(image_id)
    
    if image:
        db.session.delete(image)
        db.session.commit()
        
        # Delete the image file from the server
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        
        return jsonify({"message": "Image deleted successfully!"}), 200
    else:
        return jsonify({"message": "Image not found!"}), 404

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]  # Extract the token

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.user = data  # Store decoded user data in request
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401

        return f(*args, **kwargs)

    return decorated

# Generate JWT Token
def generate_jwt(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

# Route for registering a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    # Check if the user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "User already exists"}), 400

    # Create a new user and hash the password
    new_user = User(username=username, email=email, name=name)
    new_user.set_password(password)

    # Add new user to the database
    db.session.add(new_user)
    db.session.commit()

    jwt_token = generate_jwt(new_user)
    return jsonify({"message": "User registered successfully", "token": jwt_token}), 201

# Route for login with JWT
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    uname = data.get('uname')
    password = data.get('password')

    # Find user by email
    user = User.query.filter_by(username=uname).first()

    # Check if user exists and password matches
    if user and user.check_password(password):
        # Generate JWT token
        token = generate_jwt(user)

        return jsonify({"message": "Login successful", "token": token}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401

@app.route('/dashboard')
@token_required
def dashboard():
    user = request.user
    return jsonify({"username": user['username']}), 200

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()  # Fetch all users from the database
    users_list = [
        {
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'email': user.email,
            'pass': user.password
        } for user in users
    ]
    return jsonify(users_list), 200 

if __name__ == '__main__':
    # Create the upload directory if it does not exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)
