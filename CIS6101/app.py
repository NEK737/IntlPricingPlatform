import os
from pathlib import Path
from math import radians, sin, cos, asin, sqrt

import numpy as np
import pandas as pd
from flask import Flask, request, render_template_string
import folium
from folium.plugins import MarkerCluster, HeatMap

# -----------------------
# CONFIG
# -----------------------
DATA_FILE = "map_dataset.csv"  # use your lightweight file for speed; or merged_inspection_iot_data_cleaned.csv
DEFAULT_CENTER = [40.7128, -74.0060]
DEFAULT_ZOOM = 11
SAMPLE_MAX_DEFAULT = 15000     # default cap for responsiveness
MAX_ROWS_FOR_DISTANCE = 120000 # safety cap before distance filtering

# -----------------------
# LOAD DATA (once)
# -----------------------
if not Path(DATA_FILE).exists():
    raise FileNotFoundError(f"Could not find {DATA_FILE}")

df = pd.read_csv(DATA_FILE, low_memory=False)
needed = ["Latitude","Longitude","BORO","GRADE","Risk_Flag","SCORE",
          "DBA","CUISINE DESCRIPTION","INSPECTION DATE",
          "Temperature_F","Humidity_percent","Air_Quality_Index","Surface_Score"]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df = df.dropna(subset=["Latitude","Longitude"]).copy()
df["BORO"] = df["BORO"].astype(str).str.strip().str.upper()
df["GRADE"] = df["GRADE"].astype(str).str.strip().str.upper()
df["Risk_Flag"] = df["Risk_Flag"].fillna("Unknown").str.lower()
df["DBA_clean"] = df["DBA"].astype(str).str.strip().str.upper()
df["CUISINE_clean"] = df["CUISINE DESCRIPTION"].astype(str).str.strip().str.upper()

BOROS = sorted([b for b in df["BORO"].dropna().unique() if b not in ("MISSING","NAN")])
GRADES = ["A","B","C","PENDING","UNKNOWN"]
risk_colors = {"high":"red","warning":"orange","normal":"green","unknown":"blue"}

# -----------------------
# UTILS
# -----------------------
def haversine_np(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points (in miles). Vectorized for arrays."""
    # convert degrees to radians
    lat1 = np.radians(lat1); lon1 = np.radians(lon1)
    lat2 = np.radians(lat2); lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    R_miles = 3958.7613
    return R_miles * c

def make_popup(row):
    dba = str(row.get("DBA","N/A"))
    cuisine = str(row.get("CUISINE DESCRIPTION","N/A"))
    grade = str(row.get("GRADE","Unknown"))
    score = row.get("SCORE","N/A")
    ins_date = str(row.get("INSPECTION DATE","N/A"))
    risk = str(row.get("Risk_Flag","unknown")).title()
    temp = row.get("Temperature_F","–")
    hum = row.get("Humidity_percent","–")
    aqi = row.get("Air_Quality_Index","–")
    surf = row.get("Surface_Score","–")
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

def build_map(df_view, add_heatmap=True, center=None, zoom=None):
    if center is None: center = DEFAULT_CENTER
    if zoom is None: zoom = DEFAULT_ZOOM
    m = folium.Map(location=center, zoom_start=zoom, tiles="cartodbpositron")
    clus = MarkerCluster(name="Restaurants").add_to(m)

    for _, r in df_view.iterrows():
        lat, lon = r["Latitude"], r["Longitude"]
        color = risk_colors.get(str(r["Risk_Flag"]).lower(), "blue")
        folium.CircleMarker(
            [lat, lon], radius=4, color=color, fill=True, fill_opacity=0.85,
            popup=make_popup(r)
        ).add_to(clus)

    if add_heatmap and not df_view.empty:
        heat_df = df_view.dropna(subset=["Latitude","Longitude","SCORE"]).copy()
        if not heat_df.empty:
            s = heat_df["SCORE"].clip(lower=0, upper=50)
            weights = (s - s.min()) / (s.max() - s.min() + 1e-6)
            HeatMap(list(zip(heat_df["Latitude"], heat_df["Longitude"], weights)),
                    radius=12, blur=14, min_opacity=0.2, name="Score Heat").add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m.get_root().render()

# -----------------------
# FLASK
# -----------------------
app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html>
<h1 style="color:red;">TEST VERSION — Should See This</h1>
<head>
  <meta charset="utf-8">
  <title>NYC Food Safety — Search & Near Me</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f7f7f9}
    .container{max-width:1200px;margin:22px auto;padding:0 16px}
    .card{background:#fff;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.06);padding:16px;margin-bottom:14px}
    h1{font-size:20px;margin:0 0 10px}
    form{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;align-items:end}
    label{font-size:12px;color:#333;display:block;margin-bottom:6px}
    select,input,button{padding:10px 12px;font-size:14px;border:1px solid #ddd;border-radius:10px;background:#fff}
    button{border:none;background:#2d6cdf;color:#fff;cursor:pointer;font-weight:600;transition:.15s transform ease}
    button:hover{transform:translateY(-1px)}
    .row{display:flex;gap:8px;flex-wrap:wrap}
    .chip{display:inline-block;padding:6px 10px;border-radius:999px;background:#eef2ff;color:#1f3bb3;font-size:12px;margin-right:6px}
    #map{height:74vh;border-radius:12px;overflow:hidden}
    .hint{font-size:12px;color:#666;margin-top:6px}
  </style>
  <script>
    function useMyLocation(){
      if(!navigator.geolocation){ alert("Geolocation not supported by this browser."); return; }
      navigator.geolocation.getCurrentPosition(function(pos){
        document.getElementById('lat').value = pos.coords.latitude.toFixed(6);
        document.getElementById('lon').value = pos.coords.longitude.toFixed(6);
        document.getElementById('near').value = '1';
        document.getElementById('filterForm').submit();
      }, function(err){
        alert("Could not get your location: " + err.message);
      }, {enableHighAccuracy:true, timeout:8000, maximumAge:0});
    }
  </script>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>NYC Food Safety — Search & Near Me</h1>
      <form id="filterForm" method="get" action="/">
        <div>
          <label for="q">Search (Name or Cuisine)</label>
          <input type="text" id="q" name="q" value="{{ q }}" placeholder="e.g., PIZZA, STARBUCKS, SUSHI">
        </div>
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
          <label for="radius">Radius (miles) for "Near Me"</label>
          <select name="radius" id="radius">
            {% for r in [1,2,3,5,7,10] %}
              <option value="{{r}}" {% if radius == r %}selected{% endif %}>{{r}} miles</option>
            {% endfor %}
          </select>
          <div class="hint">Click “Use my location” to apply radius search.</div>
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
        <input type="hidden" id="lat" name="lat" value="{{ lat if lat else '' }}">
        <input type="hidden" id="lon" name="lon" value="{{ lon if lon else '' }}">
        <input type="hidden" id="near" name="near" value="{{ near }}">
        <div class="row">
          <button type="submit">Update Map</button>
          <!-- Added explicitly: Use my location button -->
          <button type="button" onclick="useMyLocation()" style="background:#1abc9c; color:#fff;">Use my location</button>
        </div>
      </form>
      <div style="margin-top:10px;">
        <span class="chip">Search: {{ q if q else '—' }}</span>
        <span class="chip">Borough: {{ boro if boro else 'All' }}</span>
        <span class="chip">Grade: {{ grade if grade else 'All' }}</span>
        <span class="chip">Risk: {{ risk if risk else 'All' }}</span>
        <span class="chip">Radius: {{ radius if near=='1' else '—' }} {{ 'miles' if near=='1' else '' }}</span>
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

@app.route("/", methods=["GET"])
def index():
    # Query params
    q = request.args.get("q","").strip().upper()
    boro = request.args.get("boro","").strip().upper()
    grade = request.args.get("grade","").strip().upper()
    risk = request.args.get("risk","").strip().lower()
    limit = int(request.args.get("limit", SAMPLE_MAX_DEFAULT) or SAMPLE_MAX_DEFAULT)

    near = request.args.get("near","0")
    lat = request.args.get("lat","").strip()
    lon = request.args.get("lon","").strip()
    radius = int(request.args.get("radius", 3))

    # Base view
    view = df

    # Text search (DBA or Cuisine)
    if q:
        view = view[(view["DBA_clean"].str.contains(q, na=False)) |
                    (view["CUISINE_clean"].str.contains(q, na=False))]

    if boro:
        view = view[view["BORO"] == boro]
    if grade:
        view = view[view["GRADE"] == grade]
    if risk:
        view = view[view["Risk_Flag"] == risk]

    # Near-me distance filter (if lat/lon provided)
    center = None
    if near == "1" and lat and lon:
        try:
            lat0 = float(lat); lon0 = float(lon)
            center = [lat0, lon0]
            # safety cap before computing distances
            if view.shape[0] > MAX_ROWS_FOR_DISTANCE:
                view = view.sample(MAX_ROWS_FOR_DISTANCE, random_state=42)
            distances = haversine_np(lat0, lon0, view["Latitude"].values, view["Longitude"].values)
            view = view.assign(_dist_mi=distances)
            view = view[view["_dist_mi"] <= radius].sort_values("_dist_mi")
        except ValueError:
            pass

    point_count = view.shape[0]

    # Limit rows for display speed
    if limit and limit > 0 and view.shape[0] > limit:
        view = view.head(limit)

    # Center map on search center if provided, else default
    map_html = build_map(view, add_heatmap=True, center=center or DEFAULT_CENTER,
                         zoom=13 if center else DEFAULT_ZOOM)

    return render_template_string(
        TEMPLATE,
        q=q, boros=BOROS, grades=GRADES, boro=boro if boro else "", grade=grade if grade else "",
        risk=risk if risk else "", radius=radius, limit=limit, lat=lat, lon=lon, near=near,
        point_count=point_count, map_html=map_html
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
