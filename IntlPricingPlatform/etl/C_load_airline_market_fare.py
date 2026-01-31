"""
File: etl/load_airline_market_fare.py

Purpose
-------
1. Read the raw CSV file: data/raw/airline_market_fare_prediction.csv
2. Do light cleaning / type enforcement
3. Load the data into SQL Server staging table: dbo.AirlineMarketFare_Staging
   - Uses chunked inserts to avoid MemoryError.
   - Connection string uses environment variables (recommended for GitHub).

How to run
----------
(venv) python etl/load_airline_market_fare.py
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text


# -------------------------------------------------------------------
# 1. Build SQLAlchemy connection string from environment variables
#    (DO NOT hard-code credentials in a public repo)
# -------------------------------------------------------------------
def get_connection_string() -> str:
    server = os.getenv("MSSQL_SERVER", "localhost")
    database = os.getenv("MSSQL_DATABASE", "IntlPricingDB")
    user = os.getenv("MSSQL_USER", "")
    password = os.getenv("MSSQL_PASSWORD", "")
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

    if user and password:
        # SQL auth
        conn_str = (
            f"mssql+pyodbc://{user}:{password}@{server}/{database}"
            f"?driver={driver.replace(' ', '+')}"
        )
    else:
        # Windows auth (Trusted_Connection)
        conn_str = (
            f"mssql+pyodbc://@{server}/{database}"
            f"?driver={driver.replace(' ', '+')}"
            "&Trusted_Connection=yes"
        )

    return conn_str


# -------------------------------------------------------------------
# 2. Small helper to print basic info about the DataFrame
# -------------------------------------------------------------------
def log_df_info(df: pd.DataFrame, label: str) -> None:
    print(f"\n=== {label} ===")
    print(f"Rows: {len(df):,}")
    print("Dtypes:")
    print(df.dtypes)
    print("Null counts:")
    print(df.isna().sum())


# -------------------------------------------------------------------
# 3. Load the CSV, clean, and push to SQL Server staging table
# -------------------------------------------------------------------
def load_airline_market_fare_to_staging() -> None:
    csv_path = os.path.join("data", "raw", "airline_market_fare_prediction.csv")
    print(f"Reading CSV from: {csv_path}")

    # Explicit dtypes for numeric columns to keep memory under control.
    # Adjust if your CSV has slightly different column names.
    dtype_map = {
        "MktCoupons": "int64",
        "OriginCityMarketID": "int64",
        "DestCityMarketID": "int64",
        "OriginAirportID": "int64",
        "DestAirportID": "int64",
        "Carrier": "int64",
        "NonStopMiles": "float64",
        "RoundTrip": "float64",
        "ODPairID": "int64",
        "Pax": "float64",
        "CarrierPax": "float64",
        "Average_Fare": "float64",
        "Market_share": "float64",
        "Market_HHI": "float64",
        "LCC_Comp": "int64",
        "Multi_Airport": "int64",
        "Circuity": "float64",
        "Slot": "int64",
        "Non_Stop": "float64",
        "MktMilesFlown": "float64",
        "OriginCityMarketID_freq": "float64",
        "DestCityMarketID_freq": "float64",
        "OriginAirportID_freq": "float64",
        "DestAirportID_freq": "float64",
        "Carrier_freq": "float64",
        "ODPairID_freq": "float64",
    }

    df = pd.read_csv(csv_path, dtype=dtype_map)

    # Basic cleaning: strip column names, drop obvious duplicates
    df.columns = [c.strip() for c in df.columns]
    df = df.drop_duplicates()

    log_df_info(df, "After basic cleaning")

    # Convert column names to align with SQL staging table
    # (You can keep them identical, this is just an example)
    df = df.rename(
        columns={
            "Average_Fare": "AvgFare",
            "Market_share": "MarketShare",
            "Market_HHI": "MarketHHI",
        }
    )

    # ----------------------------------------------------------------
    # Write to SQL Server using chunks to avoid MemoryError
    # ----------------------------------------------------------------
    conn_str = get_connection_string()
    engine = create_engine(conn_str, fast_executemany=True)

    table_name = "AirlineMarketFare_Staging"
    schema_name = "dbo"

    print(f"\nLoading data into SQL Server table: {schema_name}.{table_name}")

    with engine.begin() as conn:
        # Optional: truncate the staging table before load
        conn.execute(text(f"IF OBJECT_ID('{schema_name}.{table_name}', 'U') IS NOT NULL "
                          f"TRUNCATE TABLE {schema_name}.{table_name};"))

        # Use chunksize + method='multi' to reduce memory usage
        df.to_sql(
            name=table_name,
            con=conn,
            schema=schema_name,
            if_exists="append",
            index=False,
            chunksize=5000,
            method="multi",
        )

    print("✅ Load complete.")


if __name__ == "__main__":
    load_airline_market_fare_to_staging()
