from pathlib import Path

from PIL import Image

from jarvis.integrations.local_vision_cognition import LocalVisionCognition


def test_screen_visual_input_is_downscaled_without_touching_original(tmp_path):
    source = tmp_path / "desktop.png"
    Image.new("RGB", (3200, 1080)).save(source)

    provider = LocalVisionCognition(
        screen_max_dimension=1280,
        vision_cache_dir=tmp_path / "vision-cache",
    )
    prepared = provider._prepare_visual_input(source, "live-screen")

    assert prepared != source
    assert source.exists()
    with Image.open(source) as original:
        assert original.size == (3200, 1080)
    with Image.open(prepared) as resized:
        assert max(resized.size) == 1280


def test_camera_visual_input_is_not_resized(tmp_path):
    source = tmp_path / "camera.jpg"
    Image.new("RGB", (1920, 1080)).save(source)

    provider = LocalVisionCognition(
        screen_max_dimension=1280,
        vision_cache_dir=tmp_path / "vision-cache",
    )
    assert provider._prepare_visual_input(source, "live-camera:camera-0") == source
