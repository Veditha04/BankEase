from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from pathlib import Path
import os
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
from api import api_bp 
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import logging

load_dotenv()

app = Flask(__name__)
# Logging configuration
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("bankease")
# CORS configuration
ENV = os.getenv("FLASK_ENV", "development").lower()

DEV_ORIGINS = ["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:3000", "http://127.0.0.1:3000"]

PROD_ORIGINS = os.getenv("FRONTEND_ORIGINS", "").split(",") if os.getenv("FRONTEND_ORIGINS") else []

ALLOWED_ORIGINS = DEV_ORIGINS if ENV != "production" else PROD_ORIGINS

CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Error handlers (need logger to be set up already)
@app.errorhandler(HTTPException)
def handle_http(e: HTTPException):
    logger.warning(f"HTTP {e.code} on {request.path}: {e.description}")
    return jsonify({"error": e.name, "status": e.code}), e.code

@app.errorhandler(Exception)
def handle_any(e: Exception):
    logger.exception(f"Unhandled exception on {request.path}")
    return jsonify({"error": "Internal server error"}), 500

# Register blueprint for all API routes (e.g., /api/predict, /api/status)
app.register_blueprint(api_bp, url_prefix="/api")

# Database configuration
db_path = Path("/Users/vedithareddyavuthu/Projects/BankEase/backend/instance/bankease.db")
db_path.parent.mkdir(parents=True, exist_ok=True)

# Verify permissions
if not os.access(db_path.parent, os.W_OK):
    raise PermissionError(f"Cannot write to {db_path.parent}")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

print("Database URI being used:", app.config['SQLALCHEMY_DATABASE_URI'])

# JWT config
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret')
jwt = JWTManager(app)

# Initialize database
db = SQLAlchemy(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Account and Transaction models
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    balance = db.Column(db.Float, default=0.0)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_account = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    to_account = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_fraud = db.Column(db.Boolean, default=False)


# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return jsonify({"message": "BankEase DB Connected!"})

@app.route('/where-is-db')
def where_is_db():
    return jsonify({
        "current_directory": os.getcwd(),
        "db_path": str(db_path.absolute())
    })

@app.route('/add-test-data')
def add_test_data():
    try:
        user1 = User(username="john_doe", email="john@bankease.com")
        user1.set_password("test123")  
        user2 = User(username="jane_smith", email="jane@bankease.com")
        user2.set_password("test123")

        db.session.add_all([user1, user2])
        db.session.commit()

        account1 = Account(user_id=user1.id, balance=1000)
        account2 = Account(user_id=user2.id, balance=500)

        db.session.add_all([account1, account2])
        db.session.commit()

        return jsonify({"message": "Test users and accounts added."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['username', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Required fields: {', '.join(required_fields)}"}), 400
            
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username exists"}), 409
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "Email exists"}), 409
            
        # Create user with hashed password
        new_user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password'])
        )

        db.session.add(new_user)
        db.session.commit()
        
        # Create account
        new_account = Account(user_id=new_user.id, balance=0.0)
        db.session.add(new_account)
        db.session.commit()
        
        return jsonify({
            "message": "Registration successful",
            "user_id": new_user.id,
            "account_id": new_account.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity violation (likely duplicate entry)"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"SQLAlchemy error: {str(e)}")
        return jsonify({"error": "Database operation failed"}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
# login route   
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# Protected route example
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = int(get_jwt_identity())
    return jsonify(logged_in_as=current_user_id), 200

# Transfer money between accounts
@app.route('/transfer', methods=['POST'])
@jwt_required()
def transfer():
    data = request.get_json()
    from_id = data['from_account']
    to_id = data['to_account']
    amount = data['amount']

    from_acc = Account.query.get(from_id)
    to_acc = Account.query.get(to_id)

    if not from_acc or not to_acc:
        return jsonify({"error": "Invalid account ID(s)"}), 400

    if from_acc.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    from_acc.balance -= amount
    to_acc.balance += amount

    txn = Transaction(from_account=from_id, to_account=to_id, amount=amount)
    db.session.add(txn)
    db.session.commit()

    return jsonify({"message": "Transfer successful"}), 200

# Get balance of an account
@app.route('/balance/<int:account_id>', methods=['GET'])
@jwt_required()
def get_balance(account_id):
    account = Account.query.get_or_404(account_id)
    return jsonify(balance=account.balance)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Resource not found",
        "status_code": 404,
        "documentation": "https://github.com/veditha/BankEase/docs"  # Update later
    }), 404
# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 error: {str(e)}")  # Log to console
    return jsonify({
        "error": "Internal server error",
        "status_code": 500
    }), 500
# Handle 400 errors
@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        "error": "Bad request",
        "status_code": 400
    }), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5050))
    app.run(debug=True, port=port)


