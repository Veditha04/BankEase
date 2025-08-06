# seed_data.py

import click
from faker import Faker
import random
from werkzeug.security import generate_password_hash
from backend.app import db, User, Account, app

fake = Faker()
Faker.seed(42)  # Ensures consistent fake data across runs

@click.command()
@click.option('--users', default=1000, help='Number of fake users to generate')
@click.option('--reset', is_flag=True, help='Reset the database before seeding')
def seed(users, reset):
    with app.app_context():
        print(f"\n📍 Database URI being used: {app.config['SQLALCHEMY_DATABASE_URI']}")

        if reset:
            confirm = input("⚠️ This will DELETE ALL data. Continue? (y/n): ")
            if confirm.lower() != 'y':
                print("❌ Operation cancelled.")
                return
            db.drop_all()
            db.create_all()
            print("✅ Database reset complete.\n")

        # Step 1: Ensure test users exist
        print("👥 Ensuring test users exist...")
        test_users = [
            {"username": "john_doe", "email": "john@bankease.com", "password": "test123", "balance": 1000.0},
            {"username": "jane_smith", "email": "jane@bankease.com", "password": "test123", "balance": 500.0}
        ]

        for u in test_users:
            existing = User.query.filter_by(email=u['email']).first()
            if not existing:
                user = User(username=u['username'], email=u['email'])
                user.set_password(u['password'])
                db.session.add(user)
                db.session.flush()  # get user.id
                acc = Account(user_id=user.id, balance=u['balance'])
                db.session.add(acc)
        db.session.commit()
        print("✅ Test users & accounts ready.\n")

        # Step 2: Generate unique fake users
        print(f"👤 Creating {users} fake users with accounts...")

        existing_usernames = {u.username for u in User.query.with_entities(User.username).all()}
        existing_emails = {u.email for u in User.query.with_entities(User.email).all()}

        created_count = 0
        attempts = 0
        max_attempts = users * 3  # Avoid infinite loop

        while created_count < users and attempts < max_attempts:
            profile = fake.simple_profile()
            username = profile['username']
            email = profile['mail']
            password = generate_password_hash(fake.password(length=10, special_chars=True))

            if username in existing_usernames or email in existing_emails:
                attempts += 1
                continue

            user = User(username=username, email=email, password_hash=password)
            db.session.add(user)
            db.session.flush()

            acc = Account(user_id=user.id, balance=round(random.uniform(100.0, 10000.0), 2))
            db.session.add(acc)

            existing_usernames.add(username)
            existing_emails.add(email)
            created_count += 1
            attempts += 1

        db.session.commit()
        print(f"✅ {created_count} unique fake users + accounts created successfully.\n")

if __name__ == '__main__':
    seed()


