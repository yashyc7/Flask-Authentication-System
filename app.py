from flask import Flask, url_for, redirect, request, flash, render_template
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

app = Flask(__name__)
app.secret_key = "bG5vZkFlZmY2TnNzNzE1MHhXZWd1Nm0pNTYjlhg9"  # Ensure your secret key is strong and random

# Setup the database URI and initialize SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable unnecessary tracking of modifications
db = SQLAlchemy(app)

# Initializing Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# User class to represent the user table in the database
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return str(self.id)  # Return the unique user ID for Flask-Login

# Create the database and tables if they don't exist
with app.app_context():
    db.create_all()

# User loader callback function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Use user_id as an integer

# Route for the login page
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Query the database to find the user by email
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

# Route for the dashboard page after login is completed
@app.route("/dashboard")
@login_required  # Ensure the user is logged in
def dashboard():
    return render_template('dashboard.html')

# Route for logging out
@app.route("/logout",methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Route for user registration
@app.route("/registration", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Check if the email already exists in the database
        if User.query.filter_by(email=email).first():
            flash("Email is already taken", "danger")
            return redirect(url_for("register"))

        # Create and store the new user in the database
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()  # Commit the transaction to the database
        flash("Registration successful", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

if __name__ == "__main__":
    app.run(debug=True)
