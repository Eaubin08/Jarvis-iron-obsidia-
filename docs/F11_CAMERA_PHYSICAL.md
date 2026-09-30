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


## Dual-camera mode

Jarjar can keep multiple physical cameras as independent capture sources.
The canonical V0 composition is `CameraRig`, where every camera has its own
`CameraRuntime` and observation identity.

Automatic discovery/validation:

```powershell
python -m scripts.smoke_f11_dual_camera
```

The default scan is bounded to indices 0..4. To pin known cameras:

```powershell
$env:JARJAR_CAMERA_INDICES="0,1"
python -m scripts.smoke_f11_dual_camera
```

Success requires two independent fresh evidence frames and ends with:

`F11_DUAL_PHYSICAL: PASS`

Camera feeds are not fused at this stage. Keeping observations separate avoids
inventing cross-camera identity or spatial correspondence before a later
calibration layer exists.


## Validated target-machine camera mapping

Physical validation on the target machine established the canonical V0 pair:

- `device_index=0`: fresh 640x480 frame PASS;
- `device_index=1`: fresh 1280x720 frame PASS.

OpenCV also exposed indices 2 and 3 during discovery. Because backend indices
can alias or expose alternate capture mappings, those extra indices are
discovery-only and are not treated as distinct physical camera identities.
The V0 rig should pin 0 and 1 unless a future device-identity layer proves a
different mapping.
