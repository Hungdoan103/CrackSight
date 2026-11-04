"""HF-style: LiDAR bird-eye → Qwen3.5-4B-3D-Coder → Three.js voxel HTML."""

from __future__ import annotations

from pathlib import Path

from crackinspect.lidar_3d import generate_scene_via_llama_server, render_birdeye_preview


def main() -> None:
    preview = render_birdeye_preview(None, max_points=80_000, out_name="lidar_birdeye_223582")
    layers = preview["layers"]
    ext = preview.get("extent_m") or {}
    layer_lines = "\n".join(
        f"- {row['layer']}: {row['name']} ({row['count_total']:,} pts)" for row in layers
    )
    prompt = (
        "create this scene using voxels 3d\n\n"
        "Reference is a top-down LiDAR preview of road inspection corridor site 223582. "
        f"Extent about {ext.get('x', 0):.0f}m x {ext.get('y', 0):.0f}m. "
        "Interpret the image and rebuild it as a deliberate Three.js voxel/block scene "
        "with clear depth and readable silhouettes. "
        "Colors: green tree canopy clusters, yellow utility wires as thin voxel lines, "
        "orange powerline poles, dark asphalt ribbon, navy background #07101c. "
        "One self-contained HTML only. Orbit left-drag, pan right-drag, wheel zoom. "
        "Keep under 280 lines. Must end with </html>.\n"
        f"{layer_lines}"
    )
    print("IMAGE", preview["image"], flush=True)
    print("PROMPT_HEAD", prompt[:320], flush=True)
    meta = generate_scene_via_llama_server(
        prompt,
        Path(preview["image"]),
        temperature=0.65,
        max_tokens=8192,
        out_stem="qwen3d_223582_voxel",
    )
    print("OK", meta["html"], meta["bytes"], meta["view_url"], flush=True)


if __name__ == "__main__":
    main()
