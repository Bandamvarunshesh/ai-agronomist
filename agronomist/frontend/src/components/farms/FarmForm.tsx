import { lazy, Suspense, type FormEvent } from "react";
import { Link } from "react-router-dom";

import type { Farm, FarmCreateInput } from "../../lib/api/farms";

const LeafletLocationPicker = lazy(() =>
  import("./LeafletLocationPicker").then((module) => ({
    default: module.LeafletLocationPicker,
  })),
);

export type FarmFormValues = {
  farm_name: string;
  crop: string;
  location: string;
  village: string;
  locality: string;
  district: string;
  state: string;
  latitude: string;
  longitude: string;
  formatted_address: string;
  country: string;
  postal_code: string;
  location_source: "current_location" | "map_selection" | "manual";
  soil_type: string;
  land_size_acres: string;
  irrigation_type: string;
  sowing_date: string;
};

export const emptyFarmFormValues: FarmFormValues = {
  farm_name: "",
  crop: "",
  location: "",
  village: "",
  locality: "",
  district: "",
  state: "",
  latitude: "",
  longitude: "",
  formatted_address: "",
  country: "",
  postal_code: "",
  location_source: "manual",
  soil_type: "",
  land_size_acres: "",
  irrigation_type: "",
  sowing_date: "",
};

export function farmToFormValues(farm: Farm): FarmFormValues {
  return {
    farm_name: farm.farm_name,
    crop: farm.crop,
    location: farm.location,
    village: farm.village,
    locality: farm.locality || "",
    district: farm.district,
    state: farm.state,
    latitude: farm.latitude || "",
    longitude: farm.longitude || "",
    formatted_address: farm.formatted_address || "",
    country: farm.country || "",
    postal_code: farm.postal_code || "",
    location_source:
      farm.location_source === "current_location" ||
      farm.location_source === "map_selection"
        ? farm.location_source
        : "manual",
    soil_type: farm.soil_type || "",
    land_size_acres: farm.land_size_acres,
    irrigation_type: farm.irrigation_type || "",
    sowing_date: farm.sowing_date || "",
  };
}

export function farmFormValuesToPayload(
  values: FarmFormValues,
): FarmCreateInput {
  const normalize = (value: string) => value.trim();
  const optional = (value: string) => {
    const normalized = value.trim();
    return normalized ? normalized : null;
  };

  return {
    farm_name: normalize(values.farm_name),
    crop: normalize(values.crop),
    location: normalize(values.location),
    village: normalize(values.village),
    locality: optional(values.locality),
    district: normalize(values.district),
    state: normalize(values.state),
    latitude: optional(values.latitude),
    longitude: optional(values.longitude),
    formatted_address: optional(values.formatted_address),
    country: optional(values.country),
    postal_code: optional(values.postal_code),
    location_source: values.location_source,
    soil_type: optional(values.soil_type),
    land_size_acres: normalize(values.land_size_acres),
    irrigation_type: optional(values.irrigation_type),
    sowing_date: optional(values.sowing_date),
  };
}

type FarmFormProps = {
  values: FarmFormValues;
  onChange: (field: keyof FarmFormValues, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  submitLabel: string;
  submitting: boolean;
  cancelTo: string;
  authToken?: string | null;
};

export function FarmForm({
  values,
  onChange,
  onSubmit,
  submitLabel,
  submitting,
  cancelTo,
  authToken,
}: FarmFormProps) {
  return (
    <form className="form-stack" onSubmit={onSubmit}>
      <div className="form-grid">
        <label className="field">
          <span className="field-label">Farm name</span>
          <input
            className="input"
            value={values.farm_name}
            onChange={(event) => onChange("farm_name", event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Primary crop</span>
          <input
            className="input"
            value={values.crop}
            onChange={(event) => onChange("crop", event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Land size (acres)</span>
          <input
            className="input"
            type="number"
            inputMode="decimal"
            min="0.01"
            step="0.01"
            value={values.land_size_acres}
            onChange={(event) => onChange("land_size_acres", event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Sowing date</span>
          <input
            className="input"
            type="date"
            value={values.sowing_date}
            onChange={(event) => onChange("sowing_date", event.target.value)}
          />
        </label>

        <label className="field field-span-full">
          <span className="field-label">Location</span>
          <input
            className="input"
            value={values.location}
            onChange={(event) => {
              onChange("location", event.target.value);
              onChange("location_source", "manual");
            }}
            required
          />
        </label>

        <div className="field-span-full">
          <Suspense fallback={<p className="surface-copy">Loading map...</p>}>
            <LeafletLocationPicker
              authToken={authToken}
              values={values}
              onChange={onChange}
            />
          </Suspense>
        </div>

        <label className="field">
          <span className="field-label">Village / locality</span>
          <input
            className="input"
            value={values.village}
            onChange={(event) => {
              onChange("village", event.target.value);
              onChange("locality", event.target.value);
              onChange("location_source", "manual");
            }}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">District</span>
          <input
            className="input"
            value={values.district}
            onChange={(event) => {
              onChange("district", event.target.value);
              onChange("location_source", "manual");
            }}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">State</span>
          <input
            className="input"
            value={values.state}
            onChange={(event) => {
              onChange("state", event.target.value);
              onChange("location_source", "manual");
            }}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Latitude</span>
          <input
            className="input"
            inputMode="decimal"
            max="90"
            min="-90"
            type="number"
            step="0.000001"
            value={values.latitude}
            onChange={(event) => {
              onChange("latitude", event.target.value);
              onChange("location_source", "manual");
            }}
          />
        </label>

        <label className="field">
          <span className="field-label">Longitude</span>
          <input
            className="input"
            inputMode="decimal"
            max="180"
            min="-180"
            type="number"
            step="0.000001"
            value={values.longitude}
            onChange={(event) => {
              onChange("longitude", event.target.value);
              onChange("location_source", "manual");
            }}
          />
        </label>

        <label className="field field-span-full">
          <span className="field-label">Formatted address</span>
          <input
            className="input"
            value={values.formatted_address}
            onChange={(event) => {
              onChange("formatted_address", event.target.value);
              onChange("location_source", "manual");
            }}
          />
        </label>

        <label className="field">
          <span className="field-label">Country</span>
          <input
            className="input"
            value={values.country}
            onChange={(event) => {
              onChange("country", event.target.value);
              onChange("location_source", "manual");
            }}
          />
        </label>

        <label className="field">
          <span className="field-label">Postal code</span>
          <input
            className="input"
            value={values.postal_code}
            onChange={(event) => {
              onChange("postal_code", event.target.value);
              onChange("location_source", "manual");
            }}
          />
        </label>

        <label className="field">
          <span className="field-label">Soil type</span>
          <input
            className="input"
            value={values.soil_type}
            onChange={(event) => onChange("soil_type", event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field-label">Irrigation type</span>
          <input
            className="input"
            value={values.irrigation_type}
            onChange={(event) => onChange("irrigation_type", event.target.value)}
          />
        </label>
      </div>

      <div className="button-row">
        <Link className="button button-ghost button-link" to={cancelTo}>
          Cancel
        </Link>
        <button className="button button-primary" disabled={submitting} type="submit">
          {submitting ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
