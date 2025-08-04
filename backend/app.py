from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

app = Flask(__name__)

# Database configuration
db_path = Path("/Users/vedithareddyavuthu/Projects/BankEase/backend/instance/bankease.db")
db_path.parent.mkdir(parents=True, exist_ok=True)

# Verify permissions
if not os.access(db_path.parent, os.W_OK):
    raise PermissionError(f"Cannot write to {db_path.parent}")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

print("Database URI being used:", app.config['SQLALCHEMY_DATABASE_URI'])

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


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    balance = db.Column(db.Float, default=0.0)

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
        "db_path": os.path.abspath('bankease.db')
    })

@app.route('/add-test-data')
def add_test_data():
    try:
        # Create test users
        user1 = User(username="john_doe", email="john@bankease.com")
        user1.set_password("testpassword1")  

        user2 = User(username="jane_smith", email="jane@bankease.com")
        user2.set_password("testpassword2")  
        
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        
        # Create accounts for these users
        account1 = Account(user_id=user1.id, balance=1000.0)
        account2 = Account(user_id=user2.id, balance=500.0)
        
        db.session.add(account1)
        db.session.add(account2)
        db.session.commit()
        
        return jsonify({"message": "Test data added successfully!"})
    
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5050))
    app.run(debug=True, port=port)


