# F11 — Physical camera baseline

Status: STRUCTURAL IMPLEMENTED / PHYSICAL VALIDATION PENDING

The existing `CameraRuntime` remains the canonical permission boundary.
`OpenCVCameraProvider` is capture-only:

- opens one explicitly selected local camera device;
- captures a fresh frame;
- persists local evidence under `runtime_data/camera_snapshots`;
- records dimensions and device index;
- performs no face recognition;
- performs no gesture classification;
- has no action authority.

Gesture interpretation remains a separate layer. Any future gesture-derived
action must still become an `ActionRequest` and pass the normal action policy.

## Install

```powershell
python -m pip install "opencv-python>=4.10,<5"
```

## Physical smoke

```powershell
python -m scripts.smoke_f11_camera
```

Optional camera selection:

```powershell
$env:JARJAR_CAMERA_INDEX="1"
python -m scripts.smoke_f11_camera
```

Expected final line on success:

`F11_PHYSICAL: PASS`
