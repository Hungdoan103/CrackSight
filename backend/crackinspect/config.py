from __future__ import annotations

import os
from pathlib import Path

INSPECT_ROOT = Path(__file__).resolve().parents[2]
CRACKVLM_ROOT = Path(os.environ.get("CRACKVLM_ROOT", r"E:\Dự án FPT\CrackVLM"))
PROJECT_ROOT = CRACKVLM_ROOT
TRAINING_DIR = PROJECT_ROOT / "Training - Testing"
CONGLOMERATE_WEIGHTS = (
    PROJECT_ROOT
    / "models"
    / "Conglomerate"
    / "Conglomerate Concrete Crack Detection - Trained Model"
    / "crack_weights_20.pt"
)
LCW_WEIGHTS = (
    PROJECT_ROOT
    / "models"
    / "LCW"
    / "LCW Concrete Crack Detection - Trained Model"
    / "LCW_cracked_weights_20.pt"
)
SCENE_MAX_SIDE = 512
ANNOTATED_ROOT = PROJECT_ROOT / "Datasets" / "dataset_concrete_annotated"
SAMPLE_ANNOTATED = ANNOTATED_ROOT / "Test" / "CFD_001_meta.jpg"
SAMPLE_UNKNOWN = INSPECT_ROOT / "tests" / "fixtures" / "unknown_field.jpg"
SAMPLE_LCW = (
    PROJECT_ROOT
    / "Datasets"
    / "Labeled Cracks in the Wild (LCW) Dataset"
    / "16624672"
    / "LCW Concrete Crack Detection"
    / "LCW Concrete Crack Detection"
    / "512x512"
    / "Test"
    / "images"
    / "30.jpeg"
)

STORE_DIR = INSPECT_ROOT / "store"
SUMMARIES_PATH = STORE_DIR / "summaries.jsonl"
SESSION_PATH = STORE_DIR / "session.json"
LAST_BATCH_PATH = STORE_DIR / "last_batch.json"
UPLOAD_DIR = STORE_DIR / "uploads"
OVERLAY_DIR = STORE_DIR / "overlays"
SHARPEN_DIR = STORE_DIR / "sharpen"
BASICVSR_ROOT = INSPECT_ROOT / "BasicVSR_PlusPlus"
GOPRO_CKPT = BASICVSR_ROOT / "chkpts" / "basicvsr_plusplus_deblur_gopro-3c5bb9b5.pth"
REDS4_CKPT = (
    BASICVSR_ROOT / "chkpts" / "basicvsr_plusplus_c64n7_8x1_600k_reds4_20210217-db622b2f.pth"
)
SPYNET_CKPT = BASICVSR_ROOT / "chkpts" / "spynet_20210409-c6c1bd09.pth"
REALESRGAN_CKPT = BASICVSR_ROOT / "chkpts" / "RealESRGAN_x4plus.pth"
NTIRE_CKPT = BASICVSR_ROOT / "chkpts" / "basicvsr_plusplus_c128n25_ntire_vsr_20210311-1ff35292.pth"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_VL_MODEL = os.environ.get("OLLAMA_VL_MODEL", "qwen3-vl:4b")
SOURCE_KINDS = ("dashcam", "survey", "cctv", "uav", "unknown")
INPUT_SIZE = 512
CRACK_THRESHOLD = 0.001
DESCRIBE_MIN_RATIO = 0.002
DESCRIBE_MIN_PIXELS = 400
VL_MAX_SIDE = 768
VLM_ROUTE = os.environ.get("CRACKINSPECT_VLM_ROUTE", "0").strip().lower() in {"1", "true", "yes", "on"}
_MULTI_RAW = os.environ.get("CRACKINSPECT_MULTI_AGENT", "0").strip().lower()
MULTI_AGENT_MODE = "full" if _MULTI_RAW in {"full", "3", "all"} else ("1" if _MULTI_RAW in {"1", "true", "yes", "on"} else "0")
SCENE_CAPTION = os.environ.get("CRACKINSPECT_SCENE_CAPTION", "1").strip().lower() in {"1", "true", "yes", "on"}
DESCRIBE_VL = os.environ.get("CRACKINSPECT_DESCRIBE_VL", "0").strip().lower() in {"1", "true", "yes", "on"}
DETECT_SIFT = os.environ.get("CRACKINSPECT_DETECT_SIFT", "0").strip().lower() in {"1", "true", "yes", "on"}
LCW_RETRY = os.environ.get("CRACKINSPECT_LCW_RETRY", "0").strip().lower() in {"1", "true", "yes", "on"}
KEEP_MODELS = os.environ.get("CRACKINSPECT_KEEP_MODELS", "1").strip().lower() in {"1", "true", "yes", "on"}
try:
    DETECT_BATCH = max(1, int(os.environ.get("CRACKINSPECT_DETECT_BATCH", "8")))
except ValueError:
    DETECT_BATCH = 8
try:
    POST_WORKERS = max(1, int(os.environ.get("CRACKINSPECT_POST_WORKERS", "4")))
except ValueError:
    POST_WORKERS = 4
try:
    CAPTION_WORKERS = max(1, int(os.environ.get("CRACKINSPECT_CAPTION_WORKERS", "2")))
except ValueError:
    CAPTION_WORKERS = 2

HF_HOME = Path(os.environ.get("HF_HOME", r"E:\Dự án FPT\models\huggingface"))
LIDAR_3D_MODEL_DIR = Path(
    os.environ.get(
        "CRACKINSPECT_3D_MODEL_DIR",
        str(INSPECT_ROOT / "models" / "Qwen3.5-4B-3D-Coder"),
    )
)
LIDAR_3D_GGUF = LIDAR_3D_MODEL_DIR / "Qwen3.5-4B-3D-Coder-Q4_K_M.gguf"
LIDAR_3D_MMPROJ = LIDAR_3D_MODEL_DIR / "mmproj-Qwen3.5-4B-BF16.gguf"
LIDAR_3D_REPO = "ccore/Qwen3.5-4B-3D-Coder"
LIDAR_SCENE_DIR = STORE_DIR / "lidar_scenes"
LLAMA_SERVER_URL = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080")
LIDAR_DATA_ROOT = Path(
    os.environ.get("CRACKINSPECT_LIDAR_DATA", str(INSPECT_ROOT / "Data" / "223582"))
)
LIDAR_MAP_ROOT = Path(
    os.environ.get(
        "CRACKINSPECT_LIDAR_MAP",
        str(INSPECT_ROOT / "Data" / "Pointcloud off grounds"),
    )
)
LIDAR_MAP_CACHE = STORE_DIR / "lidar_map" / "offground_overlay.json"
