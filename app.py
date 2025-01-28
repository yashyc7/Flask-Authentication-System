from flask import Flask, url_for, redirect, request, flash, render_template, jsonify
from flask_login import (
    UserMixin,
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import numpy as np
import os
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Ensure your secret key is strong and random

# Setup the database URI and initialize SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Initializing Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# User class to represent the user table in the database
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    face_encoding = db.Column(db.LargeBinary, nullable=True)  # Store face encoding

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return str(self.id)

# Create the database and tables if they don't exist
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function to save face encodings
def extract_face_encoding(image_path):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

    if len(faces) == 1:
        x, y, w, h = faces[0]
        face_region = gray[y:y + h, x:x + w]
        face_encoding = cv2.resize(face_region, (100, 100))  # Normalize size
        return face_encoding.flatten()  # Convert to 1D array
    return None

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if "email" in request.form:  # Email & password login
            email = request.form["email"]
            password = request.form["password"]
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Invalid email or password", "danger")
        elif "face_login" in request.files:  # Face recognition login
            file = request.files["face_login"]
            image_path = os.path.join("temp", file.filename)
            file.save(image_path)

            input_encoding = extract_face_encoding(image_path)
            os.remove(image_path)  # Remove temp file

            if input_encoding is not None:
                users = User.query.all()
                for user in users:
                    if user.face_encoding is not None:
                        db_encoding = np.frombuffer(user.face_encoding, dtype=np.uint8)
                        if np.linalg.norm(input_encoding - db_encoding) < 5000:  # Distance threshold
                            login_user(user)
                            return redirect(url_for("dashboard"))
            flash("Face not recognized", "danger")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        file = request.files["face_image"]
        image_path = os.path.join("temp", file.filename)
        file.save(image_path)

        # Extract face encoding
        face_encoding = extract_face_encoding(image_path)
        os.remove(image_path)

        if face_encoding is None:
            flash("No face detected. Please try again.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already taken", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password, face_encoding=face_encoding.tobytes())
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)  # Temporary folder for images
    app.run(debug=True)
