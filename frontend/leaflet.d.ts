/**
 * Minimal ambient typings for the subset of Leaflet used here.
 * Leaflet is loaded from a CDN <script> tag (no npm dependency for a
 * minimal front-end), so we declare just enough shape to type-check
 * against instead of pulling in the full @types/leaflet package.
 */

interface LeafletMouseEvent {
  latlng: { lat: number; lng: number };
}

interface LeafletMap {
  setView(center: [number, number], zoom: number): LeafletMap;
  removeLayer(layer: LeafletMarker): LeafletMap;
  on(event: "click", handler: (event: LeafletMouseEvent) => void): LeafletMap;
}

interface LeafletMarker {
  addTo(target: LeafletMap | LeafletLayerGroup): LeafletMarker;
  bindPopup(html: string): LeafletMarker;
  openPopup(): LeafletMarker;
}

interface LeafletLayerGroup {
  addTo(map: LeafletMap): LeafletLayerGroup;
}

interface LeafletTileLayer {
  addTo(map: LeafletMap): LeafletTileLayer;
}

interface LeafletStatic {
  map(elementId: string): LeafletMap;
  tileLayer(urlTemplate: string, options: { attribution: string; maxZoom: number }): LeafletTileLayer;
  marker(latlng: [number, number], options?: { title?: string }): LeafletMarker;
}

declare const L: LeafletStatic;
