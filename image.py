from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'

db = SQLAlchemy(app)

# Image model
class Images(db.Model):
    __tablename__ = 'Images'  # Specify the table name explicitly
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(50), nullable=False)  # Assuming user_id is a string
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)  # Automatically set the upload time

@app.route('/api/images', methods=['GET'])
def get_images():
    images = Images.query.all()  # Update to use Images
    return jsonify([{'id': img.id, 'filename': img.filename, 'user_id': img.user_id, 'upload_time': img.upload_time} for img in images])

@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['image']
    user_id = request.form.get('user_id')  # Get user ID from form data
    
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    # Save the file
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # Save image info to database
    new_image = Images(filename=filename, user_id=user_id)  # Use Images model
    db.session.add(new_image)
    db.session.commit()
    
    return jsonify({"message": "Image uploaded successfully!"}), 201

@app.route('/api/delete/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    image = Images.query.get(image_id)  # Use Images model
    
    if image:
        # Remove the image from the database
        db.session.delete(image)
        db.session.commit()
        
        # Optionally, delete the image file from the server
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        
        return jsonify({"message": "Image deleted successfully!"}), 200
    else:
        return jsonify({"message": "Image not found!"}), 404


if __name__ == '__main__':
    # Create the upload directory if it does not exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)
