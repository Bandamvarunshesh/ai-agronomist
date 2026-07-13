import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

import markerIcon2xUrl from "leaflet/dist/images/marker-icon-2x.png";
import markerIconUrl from "leaflet/dist/images/marker-icon.png";
import markerShadowUrl from "leaflet/dist/images/marker-shadow.png";

import { reverseGeocode, type ReverseGeocodeResult } from "../../lib/api/geocoding";
import { InlineAlert } from "../ui/Feedback";
import type { FarmFormValues } from "./FarmForm";

type LeafletLocationPickerProps = {
  authToken?: string | null;
  values: FarmFormValues;
  onChange: (field: keyof FarmFormValues, value: string) => void;
};

type LatLng = {
  lat: number;
  lng: number;
};

const INDIA_CENTER: LatLng = { lat: 20.5937, lng: 78.9629 };

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
});

function numericCoordinate(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

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
    if (!position) {
      return;
    }
    map.setView(position, Math.max(map.getZoom(), 14), { animate: true });
  }, [map, position]);

  return null;
}

export function LeafletLocationPicker({
  authToken,
  values,
  onChange,
}: LeafletLocationPickerProps) {
  const initialHadLocationRef = useRef(
    Boolean(
      values.latitude ||
        values.longitude ||
        values.location ||
        values.village ||
        values.district ||
        values.state,
    ),
  );
  const replacementConfirmedRef = useRef(false);
  const lookupRequestRef = useRef(0);
  const [message, setMessage] = useState<string | null>(null);
  const [lookupStatus, setLookupStatus] = useState<"idle" | "loading" | "error">("idle");

  const selectedPosition = useMemo<LatLng | null>(() => {
    const latitude = numericCoordinate(values.latitude);
    const longitude = numericCoordinate(values.longitude);

    if (latitude === null || longitude === null) {
      return null;
    }

    return { lat: latitude, lng: longitude };
  }, [values.latitude, values.longitude]);

  const confirmLocationReplacement = () => {
    if (!initialHadLocationRef.current || replacementConfirmedRef.current) {
      return true;
    }

    const confirmed = window.confirm("Replace the existing saved farm location?");
    replacementConfirmedRef.current = confirmed;
    return confirmed;
  };

  const applyReverseGeocode = (result: ReverseGeocodeResult) => {
    if (result.formatted_address) {
      onChange("location", result.formatted_address);
      onChange("formatted_address", result.formatted_address);
    }
    if (result.locality) {
      onChange("locality", result.locality);
      onChange("village", result.locality);
    }
    if (result.district) {
      onChange("district", result.district);
    }
    if (result.state) {
      onChange("state", result.state);
    }
    if (result.country) {
      onChange("country", result.country);
    }
    if (result.postal_code) {
      onChange("postal_code", result.postal_code);
    }
  };

  const applyPosition = (
    position: LatLng,
    source: FarmFormValues["location_source"],
    lookupAddress = true,
  ) => {
    onChange("latitude", position.lat.toFixed(6));
    onChange("longitude", position.lng.toFixed(6));
    onChange("location_source", source);

    if (!lookupAddress || !authToken) {
      return;
    }

    const requestId = lookupRequestRef.current + 1;
    lookupRequestRef.current = requestId;
    setLookupStatus("loading");
    setMessage("Looking up address...");

    void reverseGeocode(authToken, position.lat, position.lng)
      .then((result) => {
        if (lookupRequestRef.current !== requestId) {
          return;
        }
        applyReverseGeocode(result);
        setLookupStatus("idle");
        setMessage(result.cache_hit ? "Address loaded from cache." : null);
      })
      .catch((error) => {
        if (lookupRequestRef.current !== requestId) {
          return;
        }
        setLookupStatus("error");
        setMessage(
          error instanceof Error
            ? error.message
            : "Address lookup is temporarily unavailable.",
        );
      });
  };

  const handleMapSelection = (position: LatLng) => {
    if (!confirmLocationReplacement()) {
      return;
    }
    applyPosition(position, "map_selection");
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setLookupStatus("error");
      setMessage("This browser does not support current location.");
      return;
    }

    if (!confirmLocationReplacement()) {
      return;
    }

    setLookupStatus("loading");
    setMessage("Requesting current location...");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        applyPosition(
          {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          },
          "current_location",
        );
      },
      (error) => {
        setLookupStatus("error");
        if (error.code === error.PERMISSION_DENIED) {
          setMessage("Location permission was denied.");
        } else if (error.code === error.TIMEOUT) {
          setMessage("Current location timed out.");
        } else {
          setMessage("Current location is unavailable.");
        }
      },
      {
        enableHighAccuracy: true,
        maximumAge: 60000,
        timeout: 10000,
      },
    );
  };

  const mapCenter = selectedPosition || INDIA_CENTER;

  return (
    <section className="location-picker">
      <div className="panel-header">
        <div>
          <h3 className="section-title">Farm location</h3>
          <p className="surface-copy">
            Use current location, tap the map, or drag the marker to choose the farm point.
          </p>
        </div>
        <button
          className="button button-secondary"
          onClick={handleUseCurrentLocation}
          type="button"
        >
          Use Current Location
        </button>
      </div>

      {message ? (
        <InlineAlert
          title={lookupStatus === "error" ? "Location lookup unavailable" : "Location update"}
          message={message}
          tone={lookupStatus === "error" ? "warning" : "info"}
        />
      ) : null}

      <div className="selected-coordinate-panel" aria-live="polite">
        <div>
          <div className="detail-label">Latitude</div>
          <div className="detail-value">{values.latitude || "Not selected"}</div>
        </div>
        <div>
          <div className="detail-label">Longitude</div>
          <div className="detail-value">{values.longitude || "Not selected"}</div>
        </div>
      </div>

      <MapContainer
        center={mapCenter}
        className="farm-location-map"
        scrollWheelZoom={false}
        zoom={selectedPosition ? 14 : 5}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onSelect={handleMapSelection} />
        <MapCenter position={selectedPosition} />
        {selectedPosition ? (
          <Marker
            draggable
            eventHandlers={{
              dragend(event) {
                const marker = event.target as L.Marker;
                const nextPosition = marker.getLatLng();
                handleMapSelection({
                  lat: nextPosition.lat,
                  lng: nextPosition.lng,
                });
              },
            }}
            position={selectedPosition}
          />
        ) : null}
      </MapContainer>
    </section>
  );
}
