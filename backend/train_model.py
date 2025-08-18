import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    roc_curve,
    auc,
    f1_score,
)
import joblib

import os
import glob

# Clear old plots
for f in glob.glob("plots/*.png"):
    os.remove(f)


# Load dataset
df = pd.read_csv("fraud_dataset.csv")

# Feature engineering from timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["hour"] = df["timestamp"].dt.hour
df["dayofweek"] = df["timestamp"].dt.dayofweek

# Drop original timestamp (now we have derived useful features)
df.drop(columns=["timestamp"], inplace=True)

# Separate features and target
X = df.drop("is_fraud", axis=1)
y = df["is_fraud"]

# Split data
X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# Scale features
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train_raw)
X_test = scaler.transform(X_test_raw)

# Save scaler
joblib.dump(scaler, "models/scaler.pkl")

def plot_confusion(y_true, y_pred, model_name):
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot()
    plt.title(f"{model_name} - Confusion Matrix")
    plt.savefig(f"plots/{model_name}_confusion_matrix.png")
    plt.close()

def plot_roc(y_true, y_scores, model_name):
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    plt.plot(fpr, tpr, label=f'AUC = {roc_auc:.2f}')
    plt.plot([0, 1], [0, 1], linestyle='--')
    plt.title(f'{model_name} - ROC Curve')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.legend()
    plt.savefig(f"plots/{model_name}_roc_curve.png")
    plt.close()

print("\n🤖 Training Logistic Regression...")
lr = LogisticRegression(max_iter=1000)
lr.fit(X_train, y_train)
lr_preds = lr.predict(X_test)
print("\n📊 Logistic Regression Results:")
print(classification_report(y_test, lr_preds))
plot_confusion(y_test, lr_preds, "LogisticRegression")
plot_roc(y_test, lr.predict_proba(X_test)[:, 1], "LogisticRegression")
X_scaled = scaler.fit_transform(X)
print(f"📉 Logistic CV F1: {cross_val_score(lr, X_scaled, y, cv=5, scoring='f1').mean():.2f}")


print("\n⚡ Training XGBoost Classifier...")
xgb = XGBClassifier(use_label_encoder=False, eval_metric="logloss")
xgb.fit(X_train, y_train)
xgb_preds = xgb.predict(X_test)
print("\n📊 XGBoost Results:")
print(classification_report(y_test, xgb_preds))
plot_confusion(y_test, xgb_preds, "XGBoost")
plot_roc(y_test, xgb.predict_proba(X_test)[:, 1], "XGBoost")
X_scaled = scaler.fit_transform(X)
print(f"📉 XGBoost CV F1: {cross_val_score(xgb, X, y, cv=5, scoring='f1').mean():.2f}")

xgb_importance = pd.Series(xgb.feature_importances_, index=X.columns)
xgb_importance.sort_values().plot(kind='barh', title='XGBoost Feature Importances')
plt.tight_layout()
plt.savefig("plots/xgb_feature_importances.png")
plt.close()

print("\n🌲 Training Random Forest Classifier...")
rf = RandomForestClassifier(random_state=42)
rf.fit(X_train, y_train)
rf_preds = rf.predict(X_test)
print("\n📊 Random Forest Results:")
print(classification_report(y_test, rf_preds))
plot_confusion(y_test, rf_preds, "RandomForest")
plot_roc(y_test, rf.predict_proba(X_test)[:, 1], "RandomForest")
X_scaled = scaler.fit_transform(X)
print(f"📉 RF CV F1: {cross_val_score(rf, X, y, cv=5, scoring='f1').mean():.2f}")

rf_importance = pd.Series(rf.feature_importances_, index=X.columns)
rf_importance.sort_values().plot(kind='barh', title='Random Forest Feature Importances')
plt.tight_layout()
plt.savefig("plots/rf_feature_importances.png")
plt.close()

print("\n✅ Saving models...")
joblib.dump(lr, "models/logistic_model.pkl")
joblib.dump(xgb, "models/xgb_model.pkl")
joblib.dump(rf, "models/rf_model.pkl")


print("\n📋 Summary:")
print(f"Logistic F1: {f1_score(y_test, lr_preds):.2f}")
print(f"XGBoost F1: {f1_score(y_test, xgb_preds):.2f}")
print(f"Random Forest F1: {f1_score(y_test, rf_preds):.2f}")

model_names = ["Logistic", "XGBoost", "Random Forest"]
lr_f1 = f1_score(y_test, lr_preds)
xgb_f1 = f1_score(y_test, xgb_preds)
rf_f1 = f1_score(y_test, rf_preds)
f1_scores = [lr_f1, xgb_f1, rf_f1]

plt.figure(figsize=(6,4))
plt.bar(model_names, f1_scores)
plt.ylabel("F1 Score")
plt.title("Model Comparison")
plt.ylim(0, 1)
plt.savefig("plots/model_comparison.png")
print("📊 model_comparison.png saved!")
