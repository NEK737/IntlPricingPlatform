import React, { useMemo, useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Card, CardContent } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Badge } from "./components/ui/badge";
import { Loader2, MapPin, Users, ShieldQuestion, Send } from "lucide-react";
import "./App.css";

//import React, { useState, useEffect } from "react";

// --- API Helpers ---
async function fetchFacilities(borough = "") {
  const baseUrl = "http://localhost:8000";  // 👈 use backend port explicitly
  const url = borough
    ? `${baseUrl}/api/facilities?borough=${borough}`
    : `${baseUrl}/api/facilities`;
  const res = await fetch(url);
  return res.json();
}

async function sendChat(role, message, facility_id = null) {
  const res = await fetch("http://localhost:8000/api/chat", {  // 👈 also update this
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, message, facility_id }),
  });
  return res.json();
}



// --- Risk Marker Factory ---
const riskIcon = (risk) => {
  const color = risk >= 85 ? "#16a34a" : risk >= 70 ? "#eab308" : risk >= 50 ? "#f97316" : "#dc2626";
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 24 24' fill='none' stroke='${color}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 10c0 7-9 12-9 12S3 17 3 10a9 9 0 1 1 18 0Z'/><circle cx='12' cy='10' r='3' fill='${color}'/></svg>`;
  return L.divIcon({ html: svg, className: "", iconSize: [32, 32], iconAnchor: [16, 30], popupAnchor: [0, -28] });
};

function FlyTo({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.flyTo(center, 13, { duration: 0.8 });
  }, [center]);
  return null;
}

export default function App() {
  const [role, setRole] = useState("consumer");
  const [facilities, setFacilities] = useState([]);
  const [center, setCenter] = useState([40.7128, -74.006]); // NYC
  const [selected, setSelected] = useState(null);

  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
  fetchFacilities().then((data) => {
    console.log("📡 FACILITIES RECEIVED FROM API:", data);
    setFacilities(data);
  });
}, []);


  const handleSend = async (text, facility = null) => {
    const msg = text.trim();
    if (!msg) return;
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setDraft("");
    setLoading(true);
    try {
      const response = await sendChat(role, msg, facility?.id);
      setMessages((m) => [...m, { role: "assistant", content: response.reply }]);
    } finally {
      setLoading(false);
    }
  };

  return (
  <div className="w-full h-screen grid grid-cols-1 lg:grid-cols-5 gap-4 p-4 bg-gray-50">
    {/* 🗺️ Map Section */}
    <div className="col-span-1 lg:col-span-3 h-[85vh]">
      <MapContainer
        center={center}
        zoom={11}
        scrollWheelZoom={true}
        className="h-full w-full rounded-xl border border-gray-200 z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FlyTo center={center} />
<Marker position={[40.7128, -74.006]}>
  <Popup>NYC Center Marker (Test)</Popup>
</Marker>

        {/* Facility Markers */}
{facilities.map((f, idx) => {
  // ensure numeric coordinates
  const lat = parseFloat(f.LATITUDE);
  const lon = parseFloat(f.LONGITUDE);

  if (!lat || !lon || isNaN(lat) || isNaN(lon)) return null;

  // pick a color/risk
  const risk =
    f.RISK_FLAG === "high" ? 90 :
    f.RISK_FLAG === "warning" ? 70 :
    f.RISK_FLAG === "low" ? 40 : 50;

  return (
    <Marker
      key={f.id || idx}
      position={[lat, lon]}
      icon={riskIcon(risk)}
      eventHandlers={{ click: () => setSelected(f) }}
    >
      <Popup>
        <div className="space-y-1">
          <div className="font-semibold flex items-center gap-2">
            <MapPin className="w-4 h-4" /> {f.DBA}
          </div>
          <div className="text-sm">Cuisine: {f.CUISINE_DESCRIPTION}</div>
          <div className="text-sm">Score: <b>{f.SCORE || "N/A"}</b></div>
          <div className="text-sm">Grade: {f.GRADE}</div>
          <div className="text-sm">Borough: {f.BORO}</div>
          <div className="text-xs">Risk: {f.RISK_FLAG}</div>
          <Button
            size="sm"
            className="mt-2"
            onClick={() => handleSend(`How safe is ${f.DBA}?`, f)}
          >
            Ask about this place
          </Button>
        </div>
      </Popup>
    </Marker>
  );
})}

      </MapContainer>
      console.log("Facilities data:", facilities);

    </div>

    {/* 💬 Chat Section */}
    <div className="col-span-1 lg:col-span-2">
      <Card className="h-full">
        <CardContent className="flex flex-col h-full">
          <div className="flex items-center justify-between mb-2">
            <Tabs value={role} onValueChange={setRole}>
              <TabsList className="grid grid-cols-2">
                <TabsTrigger value="consumer" className="flex items-center gap-2">
                  <Users className="w-4 h-4" /> Consumer
                </TabsTrigger>
                <TabsTrigger value="authority" className="flex items-center gap-2">
                  <ShieldQuestion className="w-4 h-4" /> Authority
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <Badge variant="secondary">AI Chat</Badge>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 p-2 border rounded-lg bg-white">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`p-2 rounded-lg ${
                  m.role === "assistant" ? "bg-slate-100" : "bg-blue-100"
                }`}
              >
                <span className="text-xs font-bold">
                  {m.role === "assistant" ? "Assistant" : "You"}:
                </span>{" "}
                {m.content}
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Thinking…
              </div>
            )}
          </div>

          <div className="flex gap-2 mt-2">
            <Input
              placeholder="Type your question..."
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend(draft, selected)}
            />
            <Button onClick={() => handleSend(draft, selected)} disabled={loading}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
);
}
