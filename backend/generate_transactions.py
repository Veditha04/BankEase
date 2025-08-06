# generate_transactions.py

from faker import Faker
from random import randint, uniform, choice
from backend.app import db, Transaction, Account, User, app

fake = Faker()

def generate_fake_transactions(count=10000):
    with app.app_context():
        accounts = Account.query.all()

        print(f"👥 Total Accounts: {len(accounts)}")
        print(f"🔁 Generating {count} transactions...")

        for _ in range(count):
            sender = choice(accounts)
            receiver = choice(accounts)

            # Prevent self-transfer
            while sender.id == receiver.id:
                receiver = choice(accounts)

            # Only transfer amount less than current balance
            if sender.balance <= 10:
                continue

            amount = round(uniform(5.0, min(1000.0, sender.balance)), 2)

            # Update balances
            sender.balance -= amount
            receiver.balance += amount

            # Create transaction
            tx = Transaction(
                from_account=sender.id,
                to_account=receiver.id,
                amount=amount,
                timestamp=fake.date_time_between(start_date='-1y', end_date='now')
            )

            db.session.add(tx)

        db.session.commit()
        print(f"✅ {count} fake transactions created and saved.")

if __name__ == "__main__":
    generate_fake_transactions(count=10000)
