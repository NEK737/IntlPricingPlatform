import os
from pathlib import Path
from datetime import datetime

import pandas as pd
from flask import Flask, request, render_template_string
import folium
from folium.plugins import MarkerCluster, HeatMap

# -----------------------
# CONFIG
# -----------------------
DATA_FILE = "merged_inspection_iot_data_cleaned.csv"  # your cleaned dataset
SAMPLE_MAX = 15000      # cap number of points for responsiveness
DEFAULT_CENTER = [40.7128, -74.0060]  # NYC
DEFAULT_ZOOM = 11

# -----------------------
# LOAD DATA (once)
# -----------------------
if not Path(DATA_FILE).exists():
    raise FileNotFoundError(f"Could not find {DATA_FILE} in the working directory")

df = pd.read_csv(DATA_FILE, low_memory=False)

# minimal sanity checks
needed = ["Latitude", "Longitude", "BORO", "GRADE", "Risk_Flag", "SCORE", "DBA",
          "CUISINE DESCRIPTION", "INSPECTION DATE", "Temperature_F",
          "Humidity_percent", "Air_Quality_Index", "Surface_Score"]
missing_cols = [c for c in needed if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

# clean basics
df = df.dropna(subset=["Latitude", "Longitude"]).copy()
df["BORO"] = df["BORO"].astype(str).str.strip().str.upper()
df["GRADE"] = df["GRADE"].astype(str).str.strip().str.upper()
df["Risk_Flag"] = df["Risk_Flag"].fillna("Unknown").str.lower()

# lists for filter UI
BOROS = sorted([b for b in df["BORO"].dropna().unique() if b not in ("MISSING", "NAN")])
GRADES = ["A", "B", "C", "PENDING", "UNKNOWN"]  # display choices
# map to actual values present
all_grades_in_data = set(df["GRADE"].unique())

# risk color mapping
RISK_COLORS = {
    "high": "red",
    "warning": "orange",
    "normal": "green",
    "unknown": "blue"
}

# -----------------------
# FLASK APP
# -----------------------
app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NYC Food Safety Map</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; padding: 0; background:#f7f7f9; }
    .container { max-width: 1200px; margin: 24px auto; padding: 0 16px; }
    .card { background: #fff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.06); padding: 18px; margin-bottom: 16px; }
    h1 { font-size: 20px; margin: 0 0 12px; }
    form { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; align-items: end; }
    label { font-size: 13px; color:#333; display:block; margin-bottom:6px; }
    select, input, button {
      padding: 10px 12px; font-size: 14px; border: 1px solid #ddd; border-radius: 10px; outline: none; background:#fff;
    }
    button {
      border: none; background: #2d6cdf; color: #fff; cursor: pointer; font-weight: 600;
      transition: 0.15s transform ease;
    }
    button:hover { transform: translateY(-1px); }
    .chip { display:inline-block; padding:6px 10px; border-radius: 999px; background:#eef2ff; color:#1f3bb3; font-size:12px; margin-right:6px; }
    #map { height: 74vh; border-radius: 12px; overflow: hidden; }
    .hint { font-size: 12px; color: #666; margin-top: 6px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>NYC Food Safety — Interactive Map</h1>
      <form method="get" action="/">
        <div>
          <label for="boro">Borough</label>
          <select name="boro" id="boro">
            <option value="">All Boroughs</option>
            {% for b in boros %}
              <option value="{{b}}" {% if b == boro %}selected{% endif %}>{{b}}</option>
            {% endfor %}
          </select>
        </div>
        <div>
          <label for="grade">Grade</label>
          <select name="grade" id="grade">
            <option value="">All Grades</option>
            {% for g in grades %}
              <option value="{{g}}" {% if g == grade %}selected{% endif %}>{{g}}</option>
            {% endfor %}
          </select>
        </div>
        <div>
          <label for="risk">Risk</label>
          <select name="risk" id="risk">
            <option value="">All Risk Levels</option>
            <option value="normal"  {% if risk == 'normal'  %}selected{% endif %}>Normal</option>
            <option value="warning" {% if risk == 'warning' %}selected{% endif %}>Warning</option>
            <option value="high"    {% if risk == 'high'    %}selected{% endif %}>High</option>
            <option value="unknown" {% if risk == 'unknown' %}selected{% endif %}>Unknown</option>
          </select>
        </div>
        <div>
          <label for="heatmap">Layers</label>
          <select name="heatmap" id="heatmap">
            <option value="on"  {% if heatmap == 'on' %}selected{% endif %}>Include Heatmap</option>
            <option value="off" {% if heatmap == 'off' %}selected{% endif %}>No Heatmap</option>
          </select>
        </div>
        <div>
          <label for="limit">Point Limit</label>
          <select name="limit" id="limit">
            {% for n in [2000, 5000, 10000, 15000, 25000, 50000] %}
              <option value="{{n}}" {% if limit == n %}selected{% endif %}>{{"{:,}".format(n)}}</option>
            {% endfor %}
            <option value="0" {% if limit == 0 %}selected{% endif %}>No Limit (may be slow)</option>
          </select>
        </div>
        <div>
          <button type="submit">Update Map</button>
          <div class="hint">Tip: use smaller limits for faster rendering.</div>
        </div>
      </form>
      <div style="margin-top:10px;">
        <span class="chip">Borough: {{ boro if boro else 'All' }}</span>
        <span class="chip">Grade: {{ grade if grade else 'All' }}</span>
        <span class="chip">Risk: {{ risk if risk else 'All' }}</span>
        <span class="chip">Points: {{ "{:,}".format(point_count) }}</span>
      </div>
    </div>

    <div class="card" id="map">
      {{ map_html|safe }}
    </div>
  </div>
</body>
</html>
"""

def make_popup(row):
    dba = str(row.get("DBA", "N/A"))
    cuisine = str(row.get("CUISINE DESCRIPTION", "N/A"))
    grade = str(row.get("GRADE", "Unknown"))
    score = row.get("SCORE", "N/A")
    ins_date = str(row.get("INSPECTION DATE", "N/A"))
    risk = str(row.get("Risk_Flag", "unknown")).title()
    temp = row.get("Temperature_F", "–")
    hum = row.get("Humidity_percent", "–")
    aqi = row.get("Air_Quality_Index", "–")
    surf = row.get("Surface_Score", "–")

    html = f"""
    <b>{dba}</b><br>
    <b>Cuisine:</b> {cuisine}<br>
    <b>Grade:</b> {grade} &nbsp;|&nbsp; <b>Score:</b> {score}<br>
    <b>Inspection:</b> {ins_date}<br>
    <b>Risk:</b> {risk}<br>
    <hr style="margin:4px 0;">
    <b>IoT (sample):</b><br>
    Temp: {temp}°F &nbsp;|&nbsp; Humidity: {hum}%<br>
    AQI: {aqi} &nbsp;|&nbsp; Surface Cleanliness: {surf}
    """
    return folium.Popup(html, max_width=350)

def build_map(df_view, add_heatmap=True, limit=SAMPLE_MAX):
    # Downsample for performance
    if limit and limit > 0 and df_view.shape[0] > limit:
        df_view = df_view.sample(limit, random_state=42)

    m = folium.Map(location=DEFAULT_CENTER, zoom_start=DEFAULT_ZOOM, tiles="cartodbpositron")

    cluster = MarkerCluster(name="Restaurants").add_to(m)

    for _, r in df_view.iterrows():
        lat, lon = r["Latitude"], r["Longitude"]
        risk = str(r["Risk_Flag"]).lower()
        color = RISK_COLORS.get(risk, "blue")

        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.85,
            popup=make_popup(r)
        ).add_to(cluster)

    if add_heatmap:
        heat_df = df_view.dropna(subset=["Latitude", "Longitude", "SCORE"]).copy()
        if not heat_df.empty:
            s = heat_df["SCORE"].clip(lower=0, upper=50)
            weights = (s - s.min()) / (s.max() - s.min() + 1e-6)
            heat_data = list(zip(heat_df["Latitude"], heat_df["Longitude"], weights))
            HeatMap(heat_data, radius=12, blur=14, min_opacity=0.2, name="Score Heat").add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    # Return full HTML (so we can embed directly)
    return m.get_root().render()

@app.route("/", methods=["GET"])
def index():
    # Read filters from query params
    boro = request.args.get("boro", "").strip().upper()
    grade = request.args.get("grade", "").strip().upper()
    risk = request.args.get("risk", "").strip().lower()
    heatmap = request.args.get("heatmap", "on").lower()
    limit_str = request.args.get("limit", str(SAMPLE_MAX))
    try:
        limit = int(limit_str)
    except ValueError:
        limit = SAMPLE_MAX

    # Apply filters
    view = df
    if boro:
        view = view[view["BORO"] == boro]
    if grade:
        # accept "UNKNOWN" even if not present; it will just filter to none
        view = view[view["GRADE"] == grade]
    if risk:
        view = view[view["Risk_Flag"] == risk]

    point_count = view.shape[0]

    add_heatmap = (heatmap == "on")
    map_html = build_map(view, add_heatmap=add_heatmap, limit=limit)

    return render_template_string(
        TEMPLATE,
        boros=BOROS,
        grades=[g for g in GRADES if g in all_grades_in_data or g == "UNKNOWN"],
        boro=boro if boro else "",
        grade=grade if grade else "",
        risk=risk if risk else "",
        heatmap=heatmap,
        limit=limit,
        point_count=point_count,
        map_html=map_html
    )

if __name__ == "__main__":
    # For local dev only; use a production server (gunicorn/uvicorn) for deployment
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
