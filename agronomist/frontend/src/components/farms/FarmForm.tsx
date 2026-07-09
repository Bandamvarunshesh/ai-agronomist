import { type FormEvent } from "react";
import { Link } from "react-router-dom";

import type { Farm, FarmCreateInput } from "../../lib/api/farms";

export type FarmFormValues = {
  farm_name: string;
  crop: string;
  location: string;
  village: string;
  district: string;
  state: string;
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
  district: "",
  state: "",
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
    district: farm.district,
    state: farm.state,
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
    district: normalize(values.district),
    state: normalize(values.state),
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
};

export function FarmForm({
  values,
  onChange,
  onSubmit,
  submitLabel,
  submitting,
  cancelTo,
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
            onChange={(event) => onChange("location", event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Village</span>
          <input
            className="input"
            value={values.village}
            onChange={(event) => onChange("village", event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">District</span>
          <input
            className="input"
            value={values.district}
            onChange={(event) => onChange("district", event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">State</span>
          <input
            className="input"
            value={values.state}
            onChange={(event) => onChange("state", event.target.value)}
            required
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
