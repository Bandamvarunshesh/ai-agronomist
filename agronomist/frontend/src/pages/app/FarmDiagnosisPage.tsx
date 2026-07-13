import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { InlineAlert } from "../../components/ui/Feedback";
import { useToast } from "../../components/ui/ToastProvider";
import { ApiError } from "../../lib/api/client";
import {
  diagnoseFarmImage,
  listCropImages,
  storeDiagnosisResult,
  uploadCropImage,
  type CropImage,
} from "../../lib/api/diagnosis";
import { getFarm, type Farm } from "../../lib/api/farms";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatFileSize(value: number) {
  if (value >= 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(2)} MB`;
  }
  if (value >= 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${value} B`;
}

export function FarmDiagnosisPage() {
  const { farmId = "" } = useParams();
  const { state } = useAuth();
  const { pushToast } = useToast();
  const navigate = useNavigate();
  const takePhotoInputRef = useRef<HTMLInputElement | null>(null);
  const uploadPhotoInputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [images, setImages] = useState<CropImage[]>([]);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [diagnosing, setDiagnosing] = useState(false);
  const hasFarmSelected = Boolean(farmId);
  const farmBackPath = hasFarmSelected ? `/app/farms/${farmId}` : "/app/farms";

  useEffect(() => {
    if (!farmId) {
      setStatus("ready");
      setError(null);
      setFarm(null);
      setImages([]);
      setSelectedImageId(null);
      return;
    }

    if (state.status !== "authenticated" || !state.token) {
      return;
    }

    let cancelled = false;

    const loadPage = async () => {
      setStatus("loading");
      setError(null);

      try {
        const [farmResponse, imagesResponse] = await Promise.all([
          getFarm(state.token!, farmId),
          listCropImages(state.token!, farmId),
        ]);

        if (cancelled) {
          return;
        }

        setFarm(farmResponse);
        setImages(imagesResponse);
        setSelectedImageId((current) => {
          if (current && imagesResponse.some((image) => image.id === current)) {
            return current;
          }
          return imagesResponse[0]?.id || null;
        });
        setStatus("ready");
      } catch (loadError) {
        if (cancelled) {
          return;
        }

        if (loadError instanceof ApiError && loadError.status === 403) {
          setError(
            "Diagnosis tools are only available for farmer accounts with access to this farm.",
          );
        } else if (loadError instanceof ApiError && loadError.status === 404) {
          setError("This farm or its images could not be found.");
        } else {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load diagnosis tools right now.",
          );
        }
        setStatus("error");
      }
    };

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, [farmId, refreshTick, state.status, state.token]);

  const selectedImage = useMemo(
    () => images.find((image) => image.id === selectedImageId) || null,
    [images, selectedImageId],
  );

  useEffect(() => {
    if (!uploadFile) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(uploadFile);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [uploadFile]);

  const clearFileInputs = () => {
    if (takePhotoInputRef.current) {
      takePhotoInputRef.current.value = "";
    }
    if (uploadPhotoInputRef.current) {
      uploadPhotoInputRef.current.value = "";
    }
  };

  const handleFileSelection = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setUploadFile(file);
  };

  const openTakePhoto = () => {
    clearFileInputs();
    takePhotoInputRef.current?.click();
  };

  const openUploadPhoto = () => {
    clearFileInputs();
    uploadPhotoInputRef.current?.click();
  };

  const handleUpload = async () => {
    if (!state.token || !uploadFile || !farmId) {
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const image = await uploadCropImage(state.token, farmId, uploadFile);
      setImages((current) => [image, ...current.filter((item) => item.id !== image.id)]);
      setSelectedImageId(image.id);
      setUploadFile(null);
      clearFileInputs();
      pushToast({
        title: "Image uploaded",
        message: `${image.original_filename} is ready for diagnosis.`,
        tone: "success",
      });
    } catch (uploadError) {
      const detail =
        uploadError instanceof Error
          ? uploadError.message
          : "Unable to upload the image right now.";
      setError(detail);
      pushToast({
        title: "Upload failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDiagnose = async () => {
    if (!state.token || !selectedImageId || !farmId) {
      return;
    }

    setDiagnosing(true);
    setError(null);

    try {
      const diagnosis = await diagnoseFarmImage(state.token, farmId, selectedImageId);
      const bundle = {
        diagnosis,
        farm,
        image: images.find((image) => image.id === diagnosis.crop_image_id) || null,
      };
      storeDiagnosisResult(bundle);
      pushToast({
        title: "Diagnosis complete",
        message: `${diagnosis.disease_name} result is ready to review.`,
        tone: "success",
      });
      navigate(`/app/farms/${farmId}/diagnoses/${diagnosis.id}`, {
        state: bundle,
      });
    } catch (diagnosisError) {
      const detail =
        diagnosisError instanceof Error
          ? diagnosisError.message
          : "Unable to run diagnosis right now.";
      setError(detail);
      pushToast({
        title: "Diagnosis failed",
        message: detail,
        tone: "error",
      });
    } finally {
      setDiagnosing(false);
    }
  };

  return (
    <section className="page-stack">
      <article className="surface-card page-header">
        <div>
          <div className="eyebrow">AI diagnosis</div>
          <h2 className="surface-title">
            {farm ? `${farm.farm_name} diagnosis workspace` : "Diagnosis workspace"}
          </h2>
          <p className="surface-copy">
            Upload farm images, choose the one you want analyzed, and send it to the
            existing diagnosis API.
          </p>
        </div>
        <div className="button-row">
          <Link className="button button-ghost button-link" to={farmBackPath}>
            Back to farm
          </Link>
          <button
            className="button button-secondary"
            onClick={() => setRefreshTick((current) => current + 1)}
          >
            {status === "loading" ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </article>

      {error ? (
        <InlineAlert
          title="Diagnosis tools unavailable"
          message={error}
        />
      ) : null}

      {!hasFarmSelected ? (
        <InlineAlert
          title="No farm selected"
          message="Choose a farm before taking or uploading a crop photo for diagnosis."
          tone="info"
        />
      ) : null}

      <div className="dashboard-grid">
        <article className="surface-card">
          <div className="panel-header">
            <div>
              <h3 className="section-title">Upload image</h3>
              <p className="surface-copy">
                Accepted formats are JPG, PNG, and WEBP, matching the backend upload
                rules.
              </p>
            </div>
          </div>

          <div className="form-stack">
            <div className="photo-action-row">
              <button
                className="button button-primary"
                disabled={!hasFarmSelected || uploading}
                onClick={openTakePhoto}
                type="button"
              >
                Take Photo
              </button>
              <button
                className="button button-secondary"
                disabled={!hasFarmSelected || uploading}
                onClick={openUploadPhoto}
                type="button"
              >
                Upload Photo
              </button>
              <input
                accept="image/*"
                aria-label="Take crop photo"
                capture="environment"
                className="hidden-file-input"
                onChange={handleFileSelection}
                ref={takePhotoInputRef}
                type="file"
              />
              <input
                accept="image/*"
                aria-label="Upload crop photo"
                className="hidden-file-input"
                onChange={handleFileSelection}
                ref={uploadPhotoInputRef}
                type="file"
              />
            </div>

            {uploadFile ? (
              <div className="image-preview-panel">
                {previewUrl ? (
                  <img
                    alt="Selected crop preview"
                    className="image-preview"
                    src={previewUrl}
                  />
                ) : null}
                <div className="preview-copy">
                  <div className="list-title">{uploadFile.name}</div>
                  <div className="list-meta">
                    {uploadFile.type || "Image file"} | {formatFileSize(uploadFile.size)}
                  </div>
                </div>
              </div>
            ) : (
              <InlineAlert
                title="No photo selected"
                message={
                  hasFarmSelected
                    ? "Take a new crop photo or upload an existing photo before submitting."
                    : "Select a farm first, then take or upload a crop photo."
                }
                tone="info"
              />
            )}

            <div className="button-row">
              <div className="list-meta">
                {uploadFile ? uploadFile.name : "No file selected"}
              </div>
              <button
                className="button button-primary"
                disabled={!hasFarmSelected || !uploadFile || uploading}
                onClick={handleUpload}
                type="button"
              >
                {uploading ? "Uploading..." : "Upload selected image"}
              </button>
            </div>
          </div>
        </article>

        <article className="surface-card">
          <div className="panel-header">
            <div>
              <h3 className="section-title">Run diagnosis</h3>
              <p className="surface-copy">
                Pick one uploaded image and send it to the backend diagnosis service.
              </p>
            </div>
            <button
              className="button button-primary"
              disabled={!hasFarmSelected || !selectedImageId || diagnosing || status !== "ready"}
              onClick={handleDiagnose}
              type="button"
            >
              {diagnosing ? "Diagnosing..." : "Diagnose selected image"}
            </button>
          </div>

          {selectedImage ? (
            <div className="diagnosis-highlight">
              <div className="list-title">{selectedImage.original_filename}</div>
              <div className="list-meta">
                {selectedImage.content_type} | {formatFileSize(selectedImage.file_size)} |
                {" "}uploaded {formatDate(selectedImage.uploaded_at)}
              </div>
            </div>
          ) : (
            <InlineAlert
              title="No image selected"
              message="Upload an image first, or choose one from the list below before running diagnosis."
              tone="info"
            />
          )}
        </article>
      </div>

      <article className="surface-card">
        <div className="panel-header">
          <div>
            <h3 className="section-title">Uploaded images</h3>
            <p className="surface-copy">
              The list is driven by the existing farm image API and sorted by newest upload.
            </p>
          </div>
        </div>

        {status === "loading" ? (
          <div className="list-stack">
            {Array.from({ length: 3 }).map((_, index) => (
              <div className="list-item list-item-block" key={index}>
                <div className="list-title">Loading image metadata...</div>
                <div className="list-meta">Fetching uploaded files from the backend.</div>
              </div>
            ))}
          </div>
        ) : images.length ? (
          <div className="list-stack">
            {images.map((image) => {
              const isSelected = image.id === selectedImageId;

              return (
                <label className="image-choice" key={image.id}>
                  <input
                    checked={isSelected}
                    className="choice-radio"
                    name="selected-image"
                    onChange={() => setSelectedImageId(image.id)}
                    type="radio"
                  />
                  <div className="list-item list-item-block">
                    <div className="panel-header">
                      <div>
                        <div className="list-title">{image.original_filename}</div>
                        <div className="list-meta">
                          {image.content_type} | {formatFileSize(image.file_size)}
                        </div>
                      </div>
                      {isSelected ? <div className="pill">Selected</div> : null}
                    </div>
                    <div className="list-body">Uploaded {formatDate(image.uploaded_at)}</div>
                    <div className="list-meta">Stored as {image.file_path}</div>
                  </div>
                </label>
              );
            })}
          </div>
        ) : (
          <InlineAlert
            title="No images uploaded yet"
            message="Start by uploading a crop image for this farm, then run diagnosis on it."
            tone="info"
          />
        )}
      </article>
    </section>
  );
}
