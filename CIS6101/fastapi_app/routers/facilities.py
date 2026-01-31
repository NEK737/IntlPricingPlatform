from fastapi import APIRouter, Query
import pandas as pd
import os
import joblib
import numpy as np

router = APIRouter()

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "merged_inspection_iot_data_cleaned.csv")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "random_forest.pkl")

print(f"📂 Data path: {DATA_PATH}")
print(f"🤖 Model path: {MODEL_PATH}")

# Load model safely
model = None
try:
    model = joblib.load(MODEL_PATH)
    print("✅ Random Forest model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")

# Load dataset
try:
    df = pd.read_csv(DATA_PATH, low_memory=False)
    print(f"✅ Dataset loaded successfully: {len(df)} rows")
except Exception as e:
    print(f"❌ Error loading data: {e}")
    df = pd.DataFrame()

@router.get("/facilities")
async def get_facilities(borough: str = Query(None, description="Optional borough filter")):
    if df.empty:
        return []

    # Normalize column names
    df.columns = df.columns.str.upper()

    facilities = df.copy()
    if borough:
        facilities = facilities[facilities["BORO"].str.contains(borough, case=False, na=False)]

    # Ensure numeric columns
    for col in ["LATITUDE", "LONGITUDE"]:
        facilities[col] = pd.to_numeric(facilities[col], errors="coerce")

    # Drop missing coordinates
    facilities = facilities.dropna(subset=["LATITUDE", "LONGITUDE"])

    # Limit for performance
    facilities = facilities.head(500)

    # Rename for frontend consistency
    records = facilities[[
        "CAMIS", "DBA", "BORO", "CUISINE DESCRIPTION",
        "SCORE", "GRADE", "LATITUDE", "LONGITUDE", "RISK_FLAG"
    ]].rename(columns={
        "CAMIS": "id",
        "DBA": "DBA",
        "BORO": "BORO",
        "CUISINE DESCRIPTION": "CUISINE_DESCRIPTION",
        "SCORE": "SCORE",
        "GRADE": "GRADE",
        "LATITUDE": "LATITUDE",
        "LONGITUDE": "LONGITUDE",
        "RISK_FLAG": "RISK_FLAG"
    }).to_dict(orient="records")

    return records
