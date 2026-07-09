import { apiRequest } from "./client";
import type { Farm } from "./farms";

export type CropImage = {
  id: string;
  farm_id: string;
  file_path: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  uploaded_at: string;
};

export type Diagnosis = {
  id: string;
  farm_id: string;
  crop_image_id: string;
  disease_name: string;
  confidence_score: number;
  severity: string;
  possible_causes: string[];
  organic_treatment: string[];
  chemical_treatment: string[];
  prevention_steps: string[];
  escalate_to_human: boolean;
  raw_vision_output: Record<string, unknown>;
  created_at: string;
};

export type DiagnosisResultBundle = {
  diagnosis: Diagnosis;
  farm: Farm | null;
  image: CropImage | null;
};

const DIAGNOSIS_STORAGE_KEY = "ai-agronomist.diagnosis-results";

export async function listCropImages(authToken: string, farmId: string) {
  return apiRequest<CropImage[]>(`/farms/${farmId}/images?skip=0&limit=100`, {
    method: "GET",
    authToken,
  });
}

export async function uploadCropImage(
  authToken: string,
  farmId: string,
  file: File,
) {
  const formData = new FormData();
  formData.set("image", file);

  return apiRequest<CropImage>(`/farms/${farmId}/images`, {
    method: "POST",
    authToken,
    body: formData,
  });
}

export async function diagnoseFarmImage(
  authToken: string,
  farmId: string,
  imageId?: string | null,
) {
  return apiRequest<Diagnosis>(`/farms/${farmId}/diagnose`, {
    method: "POST",
    authToken,
    body: imageId ? { image_id: imageId } : {},
  });
}

function readStoredBundles(): Record<string, DiagnosisResultBundle> {
  const raw = window.sessionStorage.getItem(DIAGNOSIS_STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object"
      ? (parsed as Record<string, DiagnosisResultBundle>)
      : {};
  } catch {
    return {};
  }
}

export function storeDiagnosisResult(bundle: DiagnosisResultBundle) {
  const current = readStoredBundles();
  current[bundle.diagnosis.id] = bundle;
  window.sessionStorage.setItem(DIAGNOSIS_STORAGE_KEY, JSON.stringify(current));
}

export function readDiagnosisResult(diagnosisId: string) {
  const current = readStoredBundles();
  return current[diagnosisId] || null;
}
