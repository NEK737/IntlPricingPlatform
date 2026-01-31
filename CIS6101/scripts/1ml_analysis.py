"""
ML Analysis Script for NYC Food Safety + IoT Data
-------------------------------------------------
This script performs:
- Data loading & preprocessing
- Exploratory Data Analysis (EDA)
- Hypothesis testing
- Predictive modeling (Random Forest, SVM, MLP)
- Result saving (metrics, plots, reports)

Author: Ebenezer O. (github.com/ebenezero)
Date: 2025-09


"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
from scipy import stats

# -------------------------------
# CONFIGURATION
# -------------------------------
DATA_FILE = "merged_inspection_iot_data_full.csv"
ARTIFACT_DIR = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# -------------------------------
# LOAD DATA
# -------------------------------
print("Loading dataset...")
df = pd.read_csv(DATA_FILE, low_memory=False)

# -------------------------------
# PREPROCESSING
# -------------------------------
# Convert inspection dates
df["INSPECTION DATE"] = pd.to_datetime(df["INSPECTION DATE"], errors="coerce")

# Derived temporal fields
df["Inspection_Year"] = df["INSPECTION DATE"].dt.year
df["Inspection_Month"] = df["INSPECTION DATE"].dt.to_period("M")

# Binary target variable (score-based)
df["Score_Bad"] = (df["SCORE"] >= 28).astype(int)

# Multiclass target variable (IoT risk-based)
df["Risk_Flag"] = df["Risk_Flag"].fillna("unknown")
y_multi = df["Risk_Flag"].map({"normal": 0, "warning": 1, "high": 2, "unknown": 3})

# -------------------------------
# EXPLORATORY DATA ANALYSIS
# -------------------------------
# Histogram of inspection scores
plt.figure(figsize=(8,5))
sns.histplot(df["SCORE"].dropna(), bins=30, color="darkred", kde=True)
plt.title("Distribution of Inspection Scores")
plt.xlabel("Score")
plt.ylabel("Count")
plt.savefig(os.path.join(ARTIFACT_DIR, "eda_score_dist.png"))
plt.close()

# Correlation heatmap
plt.figure(figsize=(10,6))
sns.heatmap(df[["Temperature_F", "Humidity_percent", "Air_Quality_Index", "Surface_Score", "SCORE"]].corr(), annot=True, cmap="coolwarm")
plt.title("Correlation Heatmap")
plt.savefig(os.path.join(ARTIFACT_DIR, "eda_corr_heatmap.png"))
plt.close()

# -------------------------------
# HYPOTHESIS TESTING
# -------------------------------
# Compare scores between high-risk and normal restaurants
high_risk_scores = df[df["Risk_Flag"] == "high"]["SCORE"].dropna()
normal_scores = df[df["Risk_Flag"] == "normal"]["SCORE"].dropna()

t_stat, p_val = stats.ttest_ind(high_risk_scores, normal_scores, equal_var=False)
with open(os.path.join(ARTIFACT_DIR, "stats_hypothesis_test.txt"), "w") as f:
    f.write(f"T-test: t={t_stat:.3f}, p={p_val:.3e}\n")

# -------------------------------
# MODELING (Binary Classification)
# -------------------------------
X = df[["Temperature_F", "Humidity_percent", "Air_Quality_Index", "Surface_Score"]].fillna(0)
y = df["Score_Bad"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

models = {
    "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
    "SVM": SVC(probability=True, random_state=42),
    "MLP": MLPClassifier(max_iter=300, random_state=42)
}

results = []
for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:,1] if hasattr(model, "predict_proba") else np.zeros_like(preds)

    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds)
    rec = recall_score(y_test, preds)
    auc = roc_auc_score(y_test, probs)

    results.append([name, acc, prec, rec, auc])

    # Confusion matrix
    cm = confusion_matrix(y_test, preds)
    disp = ConfusionMatrixDisplay(cm, display_labels=["Good","Bad"])
    disp.plot(cmap="Blues")
    plt.title(f"Confusion Matrix - {name}")
    plt.savefig(os.path.join(ARTIFACT_DIR, f"cm_{name}.png"))
    plt.close()

# Save model performance
pd.DataFrame(results, columns=["Model","Accuracy","Precision","Recall","AUC"]).to_csv(
    os.path.join(ARTIFACT_DIR, "binary_results.csv"), index=False
)

print("Analysis complete. Results saved in 'artifacts/' folder.")
