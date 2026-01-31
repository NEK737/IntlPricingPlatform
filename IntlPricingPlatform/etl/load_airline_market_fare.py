import os
import pandas as pd
import sqlalchemy as sa

# ---------- CONFIG ----------
CSV_PATH = os.path.join("data", "raw", "airline_market_fare_prediction.csv")

SQL_SERVER = r"NEK-PC\PROD"
SQL_DATABASE = "IntlPricingDB"
SQL_DRIVER = "ODBC Driver 18 for SQL Server"
STAGING_TABLE_NAME = "AirlineMarketFare_Staging"
# ----------------------------


def get_engine():
    conn_str = (
        f"mssql+pyodbc://@{SQL_SERVER}/{SQL_DATABASE}"
        f"?driver={SQL_DRIVER.replace(' ', '+')}"
        f"&trusted_connection=yes"
        f"&Encrypt=no"
    )
    engine = sa.create_engine(conn_str, fast_executemany=True)
    return engine


def load_airline_market_fare_to_staging():
    print(f"Reading CSV from: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    print("Original columns / dtypes:")
    print(df.dtypes)

    # ---- Basic sanity checks ----
    expected_cols = [
        "MktCoupons",
        "OriginCityMarketID",
        "DestCityMarketID",
        "OriginAirportID",
        "DestAirportID",
        "Carrier",
        "NonStopMiles",
        "RoundTrip",
        "ODPairID",
        "Pax",
        "CarrierPax",
        "Average_Fare",
        "Market_share",
        "Market_HHI",
        "LCC_Comp",
        "Multi_Airport",
        "Circuity",
        "Slot",
        "Non_Stop",
        "MktMilesFlown",
        "OriginCityMarketID_freq",
        "DestCityMarketID_freq",
        "OriginAirportID_freq",
        "DestAirportID_freq",
        "Carrier_freq",
        "ODPairID_freq",
    ]

    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in CSV: {missing}")

    # ---- Clean up column names (optional but nice) ----
    # We'll create snake_case versions but keep original names too.
    # For now, let's only standardize for SQL friendliness.
    df.columns = [c.strip() for c in df.columns]

    # ---- Handle the few null values in *_freq columns ----
    freq_cols = [
        "DestCityMarketID_freq",
        "OriginAirportID_freq",
        "DestAirportID_freq",
        "Carrier_freq",
        "ODPairID_freq",
    ]
    for col in freq_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    print("After basic cleaning, null counts:")
    print(df.isna().sum())

    # ---- Connect to SQL Server ----
    engine = get_engine()

   # --------- CHUNKED LOAD STARTS HERE ---------
    print(f"Preparing staging table: {STAGING_TABLE_NAME}")

    # 1) Create empty table structure (no data)
    df_head = df.head(0)  # same columns, no rows
    df_head.to_sql(
        STAGING_TABLE_NAME,
        engine,
        if_exists="replace",   # drop & recreate table
        index=False,
    )

    # 2) Insert data in chunks
    chunksize = 5000  # you can go smaller if memory is tight
    total_rows = len(df)
    print(f"Loading {total_rows} rows in chunks of {chunksize}...")

    with engine.begin() as conn:
        for start in range(0, total_rows, chunksize):
            end = min(start + chunksize, total_rows)
            chunk = df.iloc[start:end]
            print(f"Inserting rows {start} to {end - 1} ...")
            chunk.to_sql(
                STAGING_TABLE_NAME,
                conn,
                if_exists="append",
                index=False,
            )

    print("Chunked load complete. Verifying row count from SQL Server...")

    with engine.connect() as conn:
        result = conn.execute(sa.text(f"SELECT COUNT(*) FROM {STAGING_TABLE_NAME};"))
        row_count = result.scalar()
        print(f"Row count in {STAGING_TABLE_NAME}: {row_count}")


if __name__ == "__main__":
    load_airline_market_fare_to_staging()
