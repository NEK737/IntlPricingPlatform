import os
import joblib
import pandas as pd
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Chat"])

# -------------------------------------------------------------------
# ✅ Correct paths to your real data and models
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # C:\Projects\CIS610
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "merged_inspection_iot_data_cleaned.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

# -------------------------------------------------------------------
# ✅ Load your trained models
# -------------------------------------------------------------------
models = {
    "random_forest": joblib.load(os.path.join(MODEL_DIR, "random_forest.pkl")),
    "svm_rbf": joblib.load(os.path.join(MODEL_DIR, "svm_rbf.pkl")),
    "mlp": joblib.load(os.path.join(MODEL_DIR, "mlp.pkl")),
}

# -------------------------------------------------------------------
# ✅ Load dataset for lookups
# -------------------------------------------------------------------
use_cols = ["CAMIS", "DBA", "BORO", "CUISINE DESCRIPTION", "SCORE", "GRADE", "LATITUDE", "LONGITUDE", "RISK_FLAG"]
df = pd.read_csv(DATA_PATH, usecols=use_cols, low_memory=False)
df.columns = [c.lower() for c in df.columns]
id_col = next((c for c in df.columns if "facility" in c or "dba" in c or "name" in c), None)

@router.post("/chat")
def chat_endpoint(payload: dict):
    role = payload.get("role")
    message = payload.get("message", "").lower()
    facility_id = payload.get("facility_id")

    # --- Model selection ---
    if "svm" in message:
        model_key, model_name = "svm_rbf", "SVM (RBF)"
    elif "mlp" in message or "neural" in message:
        model_key, model_name = "mlp", "Neural Network (MLP)"
    else:
        model_key, model_name = "random_forest", "Random Forest"
    model = models[model_key]

    # --- Identify facility ---
    facility_name = None
    if "test kitchen" in message:
        facility_name = "Test Kitchen"
    elif "demo diner" in message:
        facility_name = "Demo Diner"
    elif facility_id:
        facility_name = facility_id

    if id_col and facility_name:
        row = df[df[id_col].str.contains(facility_name, case=False, na=False)]
    else:
        row = df.sample(1)

    if row.empty:
        return {"reply": "Couldn't find that facility in dataset."}

    # Drop target or text columns before prediction
    for col in ["risk_score", "target", "label", "name", "facility", "dba"]:
        if col in row.columns:
            row = row.drop(columns=[col])

    # --- Predict ---
    try:
        pred = model.predict(row)[0]
        reply = f"Using {model_name}, predicted risk for '{facility_name or 'sample facility'}' = {pred:.2f}"
    except Exception as e:
        reply = f"Prediction failed: {e}"

    return {"reply": reply}
