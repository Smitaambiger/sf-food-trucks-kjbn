interface Truck {
  permit: string;
  applicant: string;
  food_items: string | null;
  address: string | null;
  location_description: string | null;
  status: string;
  latitude: number;
  longitude: number;
  distance_km: number;
}

interface NearbyTrucksResponse {
  query_lat: number;
  query_lon: number;
  radius_km: number;
  count: number;
  results: Truck[];
}

interface ErrorResponse {
  detail: string;
}

const DEFAULT_CENTER: [number, number] = [37.7749, -122.4194]; // San Francisco

const map = L.map("map").setView(DEFAULT_CENTER, 13);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  maxZoom: 19,
}).addTo(map);

let userMarker: LeafletMarker | null = null;
let truckMarkers: LeafletMarker[] = [];
let currentPoint: { lat: number; lon: number } | null = null;

function requireElementById<T extends HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) {
    throw new Error(`Expected an element with id "${id}" in the page`);
  }
  return el as T;
}

const statusLine = requireElementById<HTMLParagraphElement>("status-line");
const resultsPane = requireElementById<HTMLElement>("results");
const radiusInput = requireElementById<HTMLInputElement>("radius-input");
const foodTypeInput = requireElementById<HTMLInputElement>("food-type-input");

function setStatus(text: string): void {
  statusLine.textContent = text;
}

function clearTruckMarkers(): void {
  truckMarkers.forEach((m) => map.removeLayer(m));
  truckMarkers = [];
}

function setPoint(lat: number, lon: number): void {
  currentPoint = { lat, lon };

  if (userMarker) map.removeLayer(userMarker);
  userMarker = L.marker([lat, lon], { title: "Search location" }).addTo(map);
  map.setView([lat, lon], 14);

  void searchNearby();
}

async function searchNearby(): Promise<void> {
  if (!currentPoint) return;

  const radiusKm = parseFloat(radiusInput.value) || 1;
  const foodType = foodTypeInput.value.trim();

  const params = new URLSearchParams({
    lat: String(currentPoint.lat),
    lon: String(currentPoint.lon),
    radius_km: String(radiusKm),
  });
  if (foodType) params.set("food_type", foodType);

  setStatus("Searching...");

  try {
    const response = await fetch(`/api/v1/trucks/nearby?${params.toString()}`);
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as Partial<ErrorResponse>;
      throw new Error(body.detail || `Request failed (${response.status})`);
    }
    const data = (await response.json()) as NearbyTrucksResponse;
    renderResults(data);
    setStatus(`${data.count} truck(s) found within ${data.radius_km} km`);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    setStatus(`Error: ${message}`);
    resultsPane.innerHTML = "";
  }
}

function renderResults(data: NearbyTrucksResponse): void {
  clearTruckMarkers();
  resultsPane.innerHTML = "";

  if (data.results.length === 0) {
    resultsPane.innerHTML = '<p class="empty-hint">No trucks found in this area. Try a bigger radius.</p>';
    return;
  }

  data.results.forEach((truck) => {
    const marker = L.marker([truck.latitude, truck.longitude])
      .addTo(map)
      .bindPopup(`<strong>${truck.applicant}</strong><br>${truck.food_items || "N/A"}`);
    truckMarkers.push(marker);

    const card = document.createElement("div");
    card.className = "truck-card";
    card.innerHTML = `
      <h3>${truck.applicant}</h3>
      <p>${truck.food_items || "Menu not listed"}</p>
      <p>${truck.address || truck.location_description || ""}</p>
      <p class="distance">${truck.distance_km} km away</p>
    `;
    card.addEventListener("click", () => {
      map.setView([truck.latitude, truck.longitude], 16);
      marker.openPopup();
    });
    resultsPane.appendChild(card);
  });
}

requireElementById<HTMLButtonElement>("locate-btn").addEventListener("click", () => {
  if (!navigator.geolocation) {
    setStatus("Geolocation is not supported by this browser.");
    return;
  }
  setStatus("Locating you...");
  navigator.geolocation.getCurrentPosition(
    (pos) => setPoint(pos.coords.latitude, pos.coords.longitude),
    (err) => setStatus(`Could not get location: ${err.message}`)
  );
});

requireElementById<HTMLButtonElement>("search-btn").addEventListener("click", () => {
  if (!currentPoint) {
    setStatus("Pick a location first: use your location or click the map.");
    return;
  }
  void searchNearby();
});

map.on("click", (e) => setPoint(e.latlng.lat, e.latlng.lng));

setPoint(DEFAULT_CENTER[0], DEFAULT_CENTER[1]);
