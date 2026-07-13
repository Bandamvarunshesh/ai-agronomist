import { useEffect, useMemo } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

import markerIcon2xUrl from "leaflet/dist/images/marker-icon-2x.png";
import markerIconUrl from "leaflet/dist/images/marker-icon.png";
import markerShadowUrl from "leaflet/dist/images/marker-shadow.png";

type LatLng = { lat: number; lng: number };

type SettingsLocationPickerProps = {
  latitude: number | null;
  longitude: number | null;
  onSelect: (position: LatLng, source: "current_location" | "map_selection") => void;
};

const INDIA_CENTER: LatLng = { lat: 20.5937, lng: 78.9629 };

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
});

function MapClickHandler({ onSelect }: { onSelect: (position: LatLng) => void }) {
  useMapEvents({
    click(event) {
      onSelect({ lat: event.latlng.lat, lng: event.latlng.lng });
    },
  });
  return null;
}

function MapCenter({ position }: { position: LatLng | null }) {
  const map = useMap();

  useEffect(() => {
    if (position) {
      map.setView(position, Math.max(map.getZoom(), 13), { animate: true });
    }
  }, [map, position]);

  return null;
}

export function SettingsLocationPicker({
  latitude,
  longitude,
  onSelect,
}: SettingsLocationPickerProps) {
  const position = useMemo<LatLng | null>(() => {
    if (latitude === null || longitude === null) {
      return null;
    }
    return { lat: latitude, lng: longitude };
  }, [latitude, longitude]);

  return (
    <MapContainer
      center={position || INDIA_CENTER}
      className="farm-location-map"
      scrollWheelZoom={false}
      zoom={position ? 13 : 5}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapClickHandler onSelect={(next) => onSelect(next, "map_selection")} />
      <MapCenter position={position} />
      {position ? (
        <Marker
          draggable
          eventHandlers={{
            dragend(event) {
              const marker = event.target as L.Marker;
              const next = marker.getLatLng();
              onSelect({ lat: next.lat, lng: next.lng }, "map_selection");
            },
          }}
          position={position}
        />
      ) : null}
    </MapContainer>
  );
}
