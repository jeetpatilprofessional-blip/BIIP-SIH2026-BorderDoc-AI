#!/usr/bin/env python3
"""
BIIP-SIH2026 Model Download Script
Downloads InsightFace models for face verification
"""
import os
import sys
import zipfile
import urllib.request
from pathlib import Path
from tqdm import tqdm

MODEL_DIR = Path(__file__).parent.parent / "backend" / "models" / "insightface"
MODEL_URLS = [
    "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
    "https://insightface.s3.us-west-2.amazonaws.com/buffalo_l.zip",
]
MODEL_FILES = [
    "buffalo_l.onnx",
    "1k3d68.onnx",
    "2d106det.onnx",
    "det_10g.onnx",
    "genderage.onnx",
    "w600k_r50.onnx",
]


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_file(url: str, dest: Path) -> bool:
    """Download a file with progress bar"""
    try:
        print(f"Downloading from {url}...")
        with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=dest.name) as t:
            urllib.request.urlretrieve(url, dest, reporthook=t.update_to)
        return True
    except Exception as e:
        print(f"Failed to download from {url}: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """Extract zip file"""
    try:
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True
    except Exception as e:
        print(f"Failed to extract {zip_path}: {e}")
        return False


def verify_models(model_dir: Path) -> bool:
    """Verify all required model files exist"""
    missing = []
    for model_file in MODEL_FILES:
        if not (model_dir / model_file).exists():
            missing.append(model_file)

    if missing:
        print(f"Missing model files: {missing}")
        return False

    print("All model files verified!")
    return True


def main():
    print("=" * 50)
    print("BIIP-SIH2026 Model Downloader")
    print("=" * 50)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if verify_models(MODEL_DIR):
        print("Models already present and verified.")
        return 0

    # Try each URL
    zip_path = MODEL_DIR / "buffalo_l.zip"
    downloaded = False

    for url in MODEL_URLS:
        if download_file(url, zip_path):
            downloaded = True
            break

    if not downloaded:
        print("All download sources failed.")
        print("You can manually download from:")
        for url in MODEL_URLS:
            print(f"  {url}")
        print(f"Place buffalo_l.zip in {MODEL_DIR} and run this script again.")
        return 1

    # Extract
    if not extract_zip(zip_path, MODEL_DIR):
        return 1

    # Clean up zip
    zip_path.unlink(missing_ok=True)

    # Verify
    if verify_models(MODEL_DIR):
        print("\nModel download complete!")
        print(f"Models location: {MODEL_DIR}")
        return 0
    else:
        print("\nModel verification failed after extraction.")
        return 1


if __name__ == "__main__":
    sys.exit(main())