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
from torchvision.ops import deform_conv2d

from .config import NTIRE_CKPT, SHARPEN_DIR

_model: nn.Module | None = None

class ConvModule(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, act=True):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
        self.activate = nn.ReLU(inplace=True) if act else nn.Identity()

    def forward(self, x):
        return self.activate(self.conv(x))

class ResidualBlockNoBN(nn.Module):
    def __init__(self, mid_channels=64):
        super().__init__()
        self.conv1 = nn.Conv2d(mid_channels, mid_channels, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(mid_channels, mid_channels, 3, 1, 1, bias=True)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return x + self.conv2(self.relu(self.conv1(x)))

class ResidualBlocksWithInputConv(nn.Module):
    def __init__(self, in_channels, out_channels, num_blocks):
        super().__init__()
        blocks = [ResidualBlockNoBN(out_channels) for _ in range(num_blocks)]
        self.main = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, 1, 1, bias=True),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Sequential(*blocks),
        )

    def forward(self, feat):
        return self.main(feat)

class PixelShufflePack(nn.Module):
    def __init__(self, in_channels, out_channels, scale_factor, upsample_kernel):
        super().__init__()
        self.scale_factor = scale_factor
        self.upsample_conv = nn.Conv2d(
            in_channels,
            out_channels * scale_factor * scale_factor,
            upsample_kernel,
            padding=(upsample_kernel - 1) // 2,
        )

    def forward(self, x):
        return F.pixel_shuffle(self.upsample_conv(x), self.scale_factor)

def flow_warp(x, flow, padding_mode="zeros"):
    _, _, h, w = x.size()
    grid_y, grid_x = torch.meshgrid(torch.arange(0, h, device=x.device), torch.arange(0, w, device=x.device), indexing="ij")
    grid = torch.stack((grid_x, grid_y), 2).type_as(x)
    grid_flow = grid + flow
    grid_flow_x = 2.0 * grid_flow[..., 0] / max(w - 1, 1) - 1.0
    grid_flow_y = 2.0 * grid_flow[..., 1] / max(h - 1, 1) - 1.0
    return F.grid_sample(
        x,
        torch.stack((grid_flow_x, grid_flow_y), dim=3),
        mode="bilinear",
        padding_mode=padding_mode,
        align_corners=True,
    )

class SPyNetBasicModule(nn.Module):
    def __init__(self):
        super().__init__()
        self.basic_module = nn.Sequential(
            ConvModule(8, 32, 7, 1, 3),
            ConvModule(32, 64, 7, 1, 3),
            ConvModule(64, 32, 7, 1, 3),
            ConvModule(32, 16, 7, 1, 3),
            ConvModule(16, 2, 7, 1, 3, act=False),
        )

    def forward(self, tensor_input):
        return self.basic_module(tensor_input)

class SPyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.basic_module = nn.ModuleList([SPyNetBasicModule() for _ in range(6)])
        self.register_buffer("mean", torch.Tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer("std", torch.Tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def compute_flow(self, ref, supp):
        n, _, h, w = ref.size()
        ref = [(ref - self.mean) / self.std]
        supp = [(supp - self.mean) / self.std]
        for _ in range(5):
            ref.append(F.avg_pool2d(ref[-1], 2, 2, count_include_pad=False))
            supp.append(F.avg_pool2d(supp[-1], 2, 2, count_include_pad=False))
        ref, supp = ref[::-1], supp[::-1]
        flow = ref[0].new_zeros(n, 2, h // 32, w // 32)
        for level in range(len(ref)):
            flow_up = flow if level == 0 else F.interpolate(flow, scale_factor=2, mode="bilinear", align_corners=True) * 2.0
            flow = flow_up + self.basic_module[level](
                torch.cat([ref[level], flow_warp(supp[level], flow_up.permute(0, 2, 3, 1), padding_mode="border"), flow_up], 1)
            )
        return flow

    def forward(self, ref, supp):
        h, w = ref.shape[2:4]
        w_up = w if w % 32 == 0 else 32 * (w // 32 + 1)
        h_up = h if h % 32 == 0 else 32 * (h // 32 + 1)
        ref = F.interpolate(ref, size=(h_up, w_up), mode="bilinear", align_corners=False)
        supp = F.interpolate(supp, size=(h_up, w_up), mode="bilinear", align_corners=False)
        flow = F.interpolate(self.compute_flow(ref, supp), size=(h, w), mode="bilinear", align_corners=False)
        flow[:, 0] *= float(w) / float(w_up)
        flow[:, 1] *= float(h) / float(h_up)
        return flow

class SecondOrderDeformableAlignment(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, padding=1, deform_groups=16, max_residue_magnitude=10):
        super().__init__()
        self.max_residue_magnitude = max_residue_magnitude
        self.deform_groups = deform_groups
        self.stride = 1
        self.padding = padding
        self.dilation = 1
        self.weight = nn.Parameter(torch.Tensor(out_channels, in_channels, kernel_size, kernel_size))
        self.bias = nn.Parameter(torch.Tensor(out_channels))
        self.conv_offset = nn.Sequential(
            nn.Conv2d(3 * out_channels + 4, out_channels, 3, 1, 1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, 1, 1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, 1, 1),
            nn.LeakyReLU(negative_slope=0.1, inplace=True),
            nn.Conv2d(out_channels, 27 * deform_groups, 3, 1, 1),
        )
        nn.init.kaiming_uniform_(self.weight, a=1)
        nn.init.zeros_(self.bias)

    def forward(self, x, extra_feat, flow_1, flow_2):
        extra_feat = torch.cat([extra_feat, flow_1, flow_2], dim=1)
        o1, o2, mask = torch.chunk(self.conv_offset(extra_feat), 3, dim=1)
        offset = self.max_residue_magnitude * torch.tanh(torch.cat((o1, o2), dim=1))
        offset_1, offset_2 = torch.chunk(offset, 2, dim=1)
        offset_1 = offset_1 + flow_1.flip(1).repeat(1, offset_1.size(1) // 2, 1, 1)
        offset_2 = offset_2 + flow_2.flip(1).repeat(1, offset_2.size(1) // 2, 1, 1)
        offset = torch.cat([offset_1, offset_2], dim=1)
        mask = torch.sigmoid(mask)
        return deform_conv2d(x, offset, self.weight, self.bias, self.stride, self.padding, self.dilation, mask)

class BasicVSRPlusPlusGoPro(nn.Module):
    def __init__(self, mid_channels=64, num_blocks=7, is_low_res_input=True):
        super().__init__()
        self.mid_channels = mid_channels
        self.is_low_res_input = is_low_res_input
        self.cpu_cache = False
        self.spynet = SPyNet()
        if is_low_res_input:
            self.feat_extract = ResidualBlocksWithInputConv(3, mid_channels, 5)
        else:
            self.feat_extract = nn.Sequential(
                nn.Conv2d(3, mid_channels, 3, 2, 1),
                nn.LeakyReLU(negative_slope=0.1, inplace=True),
                nn.Conv2d(mid_channels, mid_channels, 3, 2, 1),
                nn.LeakyReLU(negative_slope=0.1, inplace=True),
                ResidualBlocksWithInputConv(mid_channels, mid_channels, 5),
            )
        self.deform_align = nn.ModuleDict()
        self.backbone = nn.ModuleDict()
        for i, module in enumerate(["backward_1", "forward_1", "backward_2", "forward_2"]):
            self.deform_align[module] = SecondOrderDeformableAlignment(2 * mid_channels, mid_channels)
            self.backbone[module] = ResidualBlocksWithInputConv((2 + i) * mid_channels, mid_channels, num_blocks)
        self.reconstruction = ResidualBlocksWithInputConv(5 * mid_channels, mid_channels, 5)
        self.upsample1 = PixelShufflePack(mid_channels, mid_channels, 2, 3)
        self.upsample2 = PixelShufflePack(mid_channels, 64, 2, 3)
        self.conv_hr = nn.Conv2d(64, 64, 3, 1, 1)
        self.conv_last = nn.Conv2d(64, 3, 3, 1, 1)
        self.img_upsample = nn.Upsample(scale_factor=4, mode="bilinear", align_corners=False)
        self.lrelu = nn.LeakyReLU(negative_slope=0.1, inplace=True)
        self.is_mirror_extended = False

    def check_if_mirror_extended(self, lqs):
        self.is_mirror_extended = False
        if lqs.size(1) % 2 == 0:
            left, right = torch.chunk(lqs, 2, dim=1)
            if torch.norm(left - right.flip(1)) == 0:
                self.is_mirror_extended = True

    def compute_flow(self, lqs):
        n, t, c, h, w = lqs.size()
        lqs_1 = lqs[:, :-1].reshape(-1, c, h, w)
        lqs_2 = lqs[:, 1:].reshape(-1, c, h, w)
        flows_backward = self.spynet(lqs_1, lqs_2).view(n, t - 1, 2, h, w)
        flows_forward = None if self.is_mirror_extended else self.spynet(lqs_2, lqs_1).view(n, t - 1, 2, h, w)
        return flows_forward, flows_backward

    def propagate(self, feats, flows, module_name):
        n, t, _, h, w = flows.size()
        frame_idx = list(range(0, t + 1))
        flow_idx = list(range(-1, t))
        mapping_idx = list(range(0, len(feats["spatial"])))
        mapping_idx += mapping_idx[::-1]
        if "backward" in module_name:
            frame_idx = frame_idx[::-1]
            flow_idx = frame_idx
        feat_prop = flows.new_zeros(n, self.mid_channels, h, w)
        for i, idx in enumerate(frame_idx):
            feat_current = feats["spatial"][mapping_idx[idx]]
            if i > 0:
                flow_n1 = flows[:, flow_idx[i]]
                cond_n1 = flow_warp(feat_prop, flow_n1.permute(0, 2, 3, 1))
                feat_n2 = torch.zeros_like(feat_prop)
                flow_n2 = torch.zeros_like(flow_n1)
                cond_n2 = torch.zeros_like(cond_n1)
                if i > 1:
                    feat_n2 = feats[module_name][-2]
                    flow_n2 = flows[:, flow_idx[i - 1]]
                    flow_n2 = flow_n1 + flow_warp(flow_n2, flow_n1.permute(0, 2, 3, 1))
                    cond_n2 = flow_warp(feat_n2, flow_n2.permute(0, 2, 3, 1))
                cond = torch.cat([cond_n1, feat_current, cond_n2], dim=1)
                feat_prop = torch.cat([feat_prop, feat_n2], dim=1)
                feat_prop = self.deform_align[module_name](feat_prop, cond, flow_n1, flow_n2)
            feat = [feat_current] + [feats[k][idx] for k in feats if k not in ["spatial", module_name]] + [feat_prop]
            feat_prop = feat_prop + self.backbone[module_name](torch.cat(feat, dim=1))
            feats[module_name].append(feat_prop)
        if "backward" in module_name:
            feats[module_name] = feats[module_name][::-1]
        return feats

    def upsample(self, lqs, feats):
        outputs = []
        mapping_idx = list(range(0, len(feats["spatial"])))
        mapping_idx += mapping_idx[::-1]
        for i in range(lqs.size(1)):
            hr = [feats[k].pop(0) for k in feats if k != "spatial"]
            hr.insert(0, feats["spatial"][mapping_idx[i]])
            hr = self.reconstruction(torch.cat(hr, dim=1))
            hr = self.lrelu(self.upsample1(hr))
            hr = self.lrelu(self.upsample2(hr))
            hr = self.lrelu(self.conv_hr(hr))
            hr = self.conv_last(hr)
            if self.is_low_res_input:
                hr = hr + self.img_upsample(lqs[:, i])
            else:
                hr = hr + lqs[:, i]
            outputs.append(hr)
        return torch.stack(outputs, dim=1)

    def forward(self, lqs):
        n, t, c, h, w = lqs.size()
        if self.is_low_res_input:
            lqs_downsample = lqs.clone()
        else:
            lqs_downsample = F.interpolate(lqs.view(-1, c, h, w), scale_factor=0.25, mode="bicubic").view(n, t, c, h // 4, w // 4)
        self.check_if_mirror_extended(lqs)
        feats = {"spatial": [self.feat_extract(lqs[:, i]) for i in range(t)]}
        flows_forward, flows_backward = self.compute_flow(lqs_downsample)
        for iter_ in [1, 2]:
            for direction in ["backward", "forward"]:
                module = f"{direction}_{iter_}"
                feats[module] = []
                flows = flows_backward if direction == "backward" else (flows_backward.flip(1) if flows_forward is None else flows_forward)
                feats = self.propagate(feats, flows, module)
        return self.upsample(lqs, feats)

def release_gopro() -> None:
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
    if not NTIRE_CKPT.exists():
        raise FileNotFoundError(f"Không thấy checkpoint NTIRE VSR: {NTIRE_CKPT}")
    try:
        from .realesrgan import release_realesrgan

        release_realesrgan()
    except Exception:
        pass
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net = BasicVSRPlusPlusGoPro(mid_channels=128, num_blocks=25, is_low_res_input=True)
    raw = torch.load(NTIRE_CKPT, map_location="cpu", weights_only=False)
    state = raw["state_dict"] if isinstance(raw, dict) and "state_dict" in raw else raw
    gen = {k[len("generator.") :]: v for k, v in state.items() if k.startswith("generator.")}
    if not gen:
        gen = state
    net.load_state_dict(gen, strict=False)
    net.to(device)
    net.eval()
    _model = net
    return net

def _pad_mod(rgb: np.ndarray, mod: int = 4) -> tuple[np.ndarray, tuple[int, int]]:
    h, w = rgb.shape[:2]
    ph = (mod - h % mod) % mod
    pw = (mod - w % mod) % mod
    if ph or pw:
        rgb = np.pad(rgb, ((0, ph), (0, pw), (0, 0)), mode="reflect")
    return rgb, (h, w)

def _unsharp(rgb: np.ndarray, amount: float = 1.5, sigma: float = 0.9) -> np.ndarray:
    blur = cv2.GaussianBlur(rgb, (0, 0), sigma)
    sharp = cv2.addWeighted(rgb, amount, blur, 1.0 - amount, 0)
    lab = cv2.cvtColor(np.clip(sharp, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=1.4, tileGridSize=(4, 4)).apply(l)
    return np.clip(cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB), 0, 255).astype(np.uint8)

def _zoom_lanczos(rgb: np.ndarray, target: int = 520) -> np.ndarray:
    h, w = rgb.shape[:2]
    scale = target / max(h, w)
    if scale <= 1.05:
        return rgb
    out = cv2.resize(rgb, (max(1, int(round(w * scale))), max(1, int(round(h * scale)))), interpolation=cv2.INTER_LANCZOS4)
    return _unsharp(out, amount=1.35, sigma=0.75)

def sharpen_rgb(rgb: np.ndarray, frames: int = 3) -> np.ndarray:
    if rgb.size == 0:
        return rgb
    src = np.asarray(rgb)
    if src.ndim != 3:
        return src
    h0, w0 = src.shape[:2]
    work = src
    max_side = 80
    if max(h0, w0) > max_side:
        scale = max_side / max(h0, w0)
        work = np.array(
            Image.fromarray(src).resize((max(4, int(w0 * scale)), max(4, int(h0 * scale))), Image.BICUBIC)
        )
    padded, (oh, ow) = _pad_mod(work, 4)
    tensor = torch.from_numpy(padded.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
    seq = tensor.repeat(1, frames, 1, 1, 1)
    net = _load()
    device = next(net.parameters()).device
    with torch.inference_mode():
        out = net(seq.to(device))[0, frames // 2].clamp(0, 1).cpu()
    vis = (out.permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
    vis = vis[: oh * 4, : ow * 4]
    target = (w0 * 4, h0 * 4)
    if (vis.shape[1], vis.shape[0]) != target:
        vis = np.array(Image.fromarray(vis).resize(target, Image.BICUBIC))
    return vis

def _context_box(box: tuple[int, int, int, int], sw: int, sh: int, side: int = 192) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    cx = (x1 + x2 + 1) / 2
    cy = (y1 + y2 + 1) / 2
    half = side / 2
    cx1 = int(round(cx - half))
    cy1 = int(round(cy - half))
    cx2 = cx1 + side
    cy2 = cy1 + side
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

def sharpen_then_zoom(
    full: np.ndarray,
    box: tuple[int, int, int, int],
    display: tuple[int, int, int, int],
) -> np.ndarray:
    sh, sw = full.shape[:2]
    ctx = _context_box(box, sw, sh, side=192)
    context = full[ctx[1] : ctx[3], ctx[0] : ctx[2]]
    hr = sharpen_rgb(context)
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
    patch = hr[dy1:dy2, dx1:dx2]
    return _zoom_lanczos(patch, target=520)

def sharpen_crop_jpeg(rgb: np.ndarray) -> str:
    sharp = _zoom_lanczos(sharpen_rgb(rgb), target=520)
    buf = io.BytesIO()
    Image.fromarray(sharp).save(buf, format="JPEG", quality=95)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def sharpen_inspect_jpeg(full: np.ndarray, display: tuple[int, int, int, int]) -> str:
    crop = full[display[1] : display[3], display[0] : display[2]]
    sharp = sharpen_rgb(crop)
    buf = io.BytesIO()
    Image.fromarray(sharp).save(buf, format="JPEG", quality=95)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def cache_path(image_name: str, inst_id: int) -> Path:
    SHARPEN_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(image_name).stem
    return SHARPEN_DIR / f"{stem}_{inst_id}_ntire.jpg"
