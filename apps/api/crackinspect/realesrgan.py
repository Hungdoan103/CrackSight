from __future__ import annotations

import base64
import io
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from .config import REALESRGAN_CKPT, SHARPEN_DIR
from .deblur import release_gopro

_model: nn.Module | None = None

class ResidualDenseBlock(nn.Module):
    def __init__(self, num_feat: int = 64, num_grow_ch: int = 32) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x

class RRDB(nn.Module):
    def __init__(self, num_feat: int, num_grow_ch: int = 32) -> None:
        super().__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x

class RRDBNet(nn.Module):
    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_block: int = 23,
        num_grow_ch: int = 32,
    ) -> None:
        super().__init__()
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))

def release_realesrgan() -> None:
    global _model
    if _model is not None:
        del _model
        _model = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def _load() -> nn.Module:
    global _model
    if _model is not None:
        return _model
    if not REALESRGAN_CKPT.exists():
        raise FileNotFoundError(f"Không thấy Real-ESRGAN: {REALESRGAN_CKPT}")
    release_gopro()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net = RRDBNet()
    raw = torch.load(REALESRGAN_CKPT, map_location="cpu", weights_only=False)
    if isinstance(raw, dict):
        state = raw.get("params_ema") or raw.get("params") or raw
    else:
        state = raw
    net.load_state_dict(state, strict=True)
    net.to(device)
    net.eval()
    _model = net
    return net

def _lucy_richardson(rgb: np.ndarray, iters: int = 6, sigma: float = 0.85) -> np.ndarray:
    kernel = cv2.getGaussianKernel(5, sigma)
    psf = kernel @ kernel.T
    img = np.clip(rgb.astype(np.float32) / 255.0, 0, 1)
    out = img.copy()
    for _ in range(iters):
        est = np.stack([cv2.filter2D(out[:, :, c], -1, psf) for c in range(3)], axis=2)
        est = np.clip(est, 1e-4, None)
        ratio = img / est
        back = np.stack([cv2.filter2D(ratio[:, :, c], -1, psf) for c in range(3)], axis=2)
        out = np.clip(out * back, 0, 1)
    return (out * 255.0).round().astype(np.uint8)

def _context_box(
    display: tuple[int, int, int, int],
    sw: int,
    sh: int,
    side: int = 160,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = display
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    side = max(side, x2 - x1, y2 - y1)
    half = side / 2
    cx1 = int(round(cx - half))
    cy1 = int(round(cy - half))
    cx2 = cx1 + int(round(side))
    cy2 = cy1 + int(round(side))
    if cx1 < 0:
        cx2 -= cx1
        cx1 = 0
    if cy1 < 0:
        cy2 -= cy1
        cy1 = 0
    if cx2 > sw:
        cx1 = max(0, cx1 - (cx2 - sw))
        cx2 = sw
    if cy2 > sh:
        cy1 = max(0, cy1 - (cy2 - sh))
        cy2 = sh
    return cx1, cy1, max(cx1 + 4, cx2), max(cy1 + 4, cy2)

def enhance_rgb(rgb: np.ndarray) -> np.ndarray:
    src = np.asarray(rgb)
    if src.ndim != 3 or src.size == 0:
        return src
    h0, w0 = src.shape[:2]
    work = src
    max_side = 192
    if max(h0, w0) > max_side:
        scale = max_side / max(h0, w0)
        work = cv2.resize(
            src,
            (max(4, int(w0 * scale)), max(4, int(h0 * scale))),
            interpolation=cv2.INTER_AREA,
        )
    tensor = torch.from_numpy(work.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
    net = _load()
    device = next(net.parameters()).device
    with torch.inference_mode():
        out = net(tensor.to(device)).clamp(0, 1)[0].cpu()
    vis = (out.permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
    if vis.shape[0] != h0 * 4 or vis.shape[1] != w0 * 4:
        vis = cv2.resize(vis, (w0 * 4, h0 * 4), interpolation=cv2.INTER_CUBIC)
    return vis

def enhance_inspect_jpeg(full: np.ndarray, display: tuple[int, int, int, int]) -> str:
    sh, sw = full.shape[:2]
    ctx = _context_box(display, sw, sh, side=160)
    context = full[ctx[1] : ctx[3], ctx[0] : ctx[2]]
    hr = enhance_rgb(_lucy_richardson(context))
    sx = hr.shape[1] / max(1, context.shape[1])
    sy = hr.shape[0] / max(1, context.shape[0])
    dx1 = int(round((display[0] - ctx[0]) * sx))
    dy1 = int(round((display[1] - ctx[1]) * sy))
    dx2 = int(round((display[2] - ctx[0]) * sx))
    dy2 = int(round((display[3] - ctx[1]) * sy))
    dx1 = max(0, min(hr.shape[1] - 1, dx1))
    dy1 = max(0, min(hr.shape[0] - 1, dy1))
    dx2 = max(dx1 + 1, min(hr.shape[1], dx2))
    dy2 = max(dy1 + 1, min(hr.shape[0], dy2))
    vis = hr[dy1:dy2, dx1:dx2]
    buf = io.BytesIO()
    Image.fromarray(vis).save(buf, format="JPEG", quality=95)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def cache_path(image_name: str, inst_id: int) -> Path:
    SHARPEN_DIR.mkdir(parents=True, exist_ok=True)
    return SHARPEN_DIR / f"{Path(image_name).stem}_{inst_id}_realesrgand.jpg"
