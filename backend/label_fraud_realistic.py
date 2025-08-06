from app import db, Transaction, app
from datetime import datetime
import random
import pandas as pd  # ✅ Step 1: Import pandas

def label_realistic_fraud():
    with app.app_context():
        print(f"\n📍 Database URI being used: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("🔍 Labeling transactions with fraud patterns...\n")
        
        txns = Transaction.query.all()
        fraud_count = 0

        for txn in txns:
            reasons = []

            if txn.amount > 900:
                reasons.append("high_amount")

            if txn.timestamp and txn.timestamp.hour < 5:
                reasons.append("odd_hour")

            if txn.from_account == txn.to_account:
                reasons.append("same_account")

            if reasons and random.random() < 0.7:
                txn.is_fraud = True
                fraud_count += 1

        db.session.commit()
        print(f"✅ {fraud_count} transactions labeled as fraud.\n")

        # ✅ Step 2: Export labeled transactions to CSV
        print("📤 Exporting labeled data to fraud_dataset.csv...")

        all_txns = Transaction.query.all()
        txn_data = [{
            "from_account": txn.from_account,
            "to_account": txn.to_account,
            "amount": txn.amount,
            "timestamp": txn.timestamp,
            "is_fraud": txn.is_fraud
        } for txn in all_txns]

        df = pd.DataFrame(txn_data)
        df.to_csv("fraud_dataset.csv", index=False)
        print("✅ fraud_dataset.csv exported successfully.")

if __name__ == "__main__":
    label_realistic_fraud()
