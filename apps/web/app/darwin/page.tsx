"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { LANG_KEY, Lang, makeT } from "../i18n";
import { DARWIN } from "./data";
import {
  buildMercatorCloud,
  colorsFromHeight,
  colorsFromIntensity,
  createLidar3DLayer,
  decodeF32,
} from "./lidar3d";
import "./darwin.css";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const MAPLIBRE_CSS = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css";
const MAPLIBRE_JS = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js";
const OVERLAY_URL = `${API}/lidar/map-overlay?max_points=2000000`;
const GPS_URL = `${API}/session/gps`;

const ESRI_IMAGERY =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ESRI_LABELS =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyNS = any;

type OverlayBounds = {
  west: number;
  south: number;
  east: number;
  north: number;
  zmin: number;
  zmax: number;
};

type ColorMode = "intensity" | "height";

type GpsPoint = {
  image_name: string;
  lat: number;
  lon: number;
  alt_m?: number | null;
  heading_deg?: number | null;
  detector?: string;
  scene_kind?: string;
  has_crack?: boolean;
  n_cracks?: number;
  exif_source?: string;
  address?: string;
  thumb?: string;
};

function escapeHtml(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

type OverlayPayload = {
  format?: string;
  count: number;
  bounds: OverlayBounds;
  files?: { name: string; sampled: number }[];
  xyz_b64: string;
  intensity_b64?: string;
  z_stretch?: { lo: number; hi: number };
  intensity_stretch?: { lo: number; hi: number };
  note?: string;
};

type OverlayMemory = {
  overlay: OverlayPayload;
  xyz: Float32Array;
  intensity: Float32Array;
};
let OVERLAY_MEMORY: OverlayMemory | null = null;

declare global {
  interface Window {
    maplibregl?: AnyNS;
  }
}

function loadCss(href: string) {
  return new Promise<void>((resolve, reject) => {
    if (document.querySelector(`link[href="${href}"]`)) {
      resolve();
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load CSS ${href}`));
    document.head.appendChild(link);
  });
}

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`) as HTMLScriptElement | null;
    if (existing) {
      if (window.maplibregl) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error(`Failed to load ${src}`)), {
        once: true,
      });
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(script);
  });
}

function makeMount(host: HTMLDivElement) {
  while (host.firstChild) host.removeChild(host.firstChild);
  const mount = document.createElement("div");
  mount.className = "darwin-engine-mount";
  mount.style.width = "100%";
  mount.style.height = "100%";
  host.appendChild(mount);
  return mount;
}

async function bootMap(host: HTMLDivElement) {
  await loadCss(MAPLIBRE_CSS);
  await loadScript(MAPLIBRE_JS);
  const maplibregl = window.maplibregl;
  if (!maplibregl) throw new Error("MapLibre chưa load");

  const mount = makeMount(host);
  const map = new maplibregl.Map({
    container: mount,
    style: {
      version: 8,
      sources: {
        esri: {
          type: "raster",
          tiles: [ESRI_IMAGERY],
          tileSize: 256,
          attribution: "Esri",
          maxzoom: 19,
        },
        labels: {
          type: "raster",
          tiles: [ESRI_LABELS],
          tileSize: 256,
          attribution: "Esri",
          maxzoom: 19,
        },
      },
      layers: [
        { id: "esri", type: "raster", source: "esri" },
        { id: "labels", type: "raster", source: "labels" },
      ],
    },
    center: [DARWIN.lon, DARWIN.lat],
    zoom: 15,
    pitch: 60,
    bearing: -28,
    maxPitch: 85,
    antialias: true,
    dragRotate: true,
    pitchWithRotate: true,
    touchPitch: true,
  });

  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-left");
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 120 }), "bottom-right");

  // and look like “LiDAR disappeared” on remount.
  await new Promise<void>((resolve, reject) => {
    const t = window.setTimeout(() => reject(new Error("MapLibre load timeout")), 30000);
    map.once("load", () => {
      window.clearTimeout(t);
      resolve();
    });
  });

  await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
  map.resize();
  return { map, maplibregl };
}

async function loadOverlayMemory(force = false, signal?: AbortSignal): Promise<OverlayMemory> {
  if (!force && OVERLAY_MEMORY) return OVERLAY_MEMORY;

  const url = force ? `${OVERLAY_URL}&force=1` : OVERLAY_URL;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(await res.text());
  const overlay = (await res.json()) as OverlayPayload;
  if (overlay.format !== "lidar-3d" || !overlay.xyz_b64 || !overlay.intensity_b64) {
    throw new Error("API overlay thiếu xyz/intensity — restart backend rồi Rebuild");
  }
  const mem: OverlayMemory = {
    overlay,
    xyz: decodeF32(overlay.xyz_b64),
    intensity: decodeF32(overlay.intensity_b64),
  };
  mem.overlay = {
    ...overlay,
    xyz_b64: "",
    intensity_b64: "",
  };
  OVERLAY_MEMORY = mem;
  return mem;
}

function fitLidar(map: AnyNS, b: OverlayBounds) {
  map.fitBounds(
    [
      [b.west, b.south],
      [b.east, b.north],
    ],
    { padding: 40, pitch: 60, bearing: -30, duration: 900, maxZoom: 17.5 },
  );
}

function gpsBounds(points: GpsPoint[]): [[number, number], [number, number]] | null {
  if (!points.length) return null;
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  for (const p of points) {
    west = Math.min(west, p.lon);
    east = Math.max(east, p.lon);
    south = Math.min(south, p.lat);
    north = Math.max(north, p.lat);
  }
  if (east - west < 0.0004) {
    west -= 0.0002;
    east += 0.0002;
  }
  if (north - south < 0.0004) {
    south -= 0.0002;
    north += 0.0002;
  }
  return [
    [west, south],
    [east, north],
  ];
}

function fitGps(map: AnyNS, points: GpsPoint[]) {
  const b = gpsBounds(points);
  if (!b) return;
  map.fitBounds(b, { padding: 80, pitch: 55, bearing: -25, duration: 1100, maxZoom: 18 });
}

function fitLidarAndGps(map: AnyNS, lidar: OverlayBounds, points: GpsPoint[]) {
  const gb = gpsBounds(points);
  if (!gb) {
    fitLidar(map, lidar);
    return;
  }
  const west = Math.min(lidar.west, gb[0][0]);
  const south = Math.min(lidar.south, gb[0][1]);
  const east = Math.max(lidar.east, gb[1][0]);
  const north = Math.max(lidar.north, gb[1][1]);
  map.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    { padding: 60, pitch: 55, bearing: -28, duration: 1000, maxZoom: 17.5 },
  );
}

function fmt(n: number) {
  return `${Math.round(n)}°`;
}

function clearGpsMarkers(markers: AnyNS[]) {
  for (const m of markers) {
    try {
      m.remove();
    } catch {
      // ignore
    }
  }
  markers.length = 0;
}

function spreadGps(points: GpsPoint[]): Array<GpsPoint & { _lng: number; _lat: number }> {
  const used = new Map<string, number>();
  return points.map((p) => {
    const key = `${p.lat.toFixed(5)},${p.lon.toFixed(5)}`;
    const n = used.get(key) || 0;
    used.set(key, n + 1);
    const angle = (n * 55 * Math.PI) / 180;
    const radius = n === 0 ? 0 : 0.000045 * n;
    return {
      ...p,
      _lng: p.lon + Math.cos(angle) * radius,
      _lat: p.lat + Math.sin(angle) * radius,
    };
  });
}

function mountGpsMarkers(
  map: AnyNS,
  maplibregl: AnyNS,
  points: GpsPoint[],
  markersOut: AnyNS[],
  labels: { crack: (n: number) => string; none: string },
) {
  clearGpsMarkers(markersOut);
  const border = (crack: boolean) => (crack ? "#f87171" : "#fbbf24");
  for (const p of spreadGps(points)) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `darwin-gps-pin${p.has_crack ? " crack" : ""}`;
    el.style.cssText = [
      "width:48px",
      "height:48px",
      "min-width:48px",
      "max-width:48px",
      "padding:0",
      "margin:0",
      "box-sizing:border-box",
      "overflow:hidden",
      "border-radius:10px",
      `border:2px solid ${border(!!p.has_crack)}`,
      "background:#0f172a",
      "cursor:pointer",
      "display:block",
      "box-shadow:0 4px 14px rgba(0,0,0,.55)",
      "position:relative",
    ].join(";");
    el.title = p.image_name || "GPS";
    if (p.thumb) {
      const img = document.createElement("img");
      img.src = p.thumb;
      img.alt = p.image_name || "photo";
      img.draggable = false;
      img.style.cssText =
        "width:48px;height:48px;max-width:48px;max-height:48px;object-fit:cover;display:block;pointer-events:none;";
      el.appendChild(img);
    } else {
      el.textContent = "GPS";
      el.style.color = "#fbbf24";
      el.style.fontSize = "10px";
      el.style.fontWeight = "700";
    }

    const crackLine =
      (p.n_cracks || 0) > 0 ? labels.crack(p.n_cracks || 0) : labels.none;
    const alt =
      p.alt_m != null && Number.isFinite(p.alt_m) ? ` · ${p.alt_m.toFixed(1)} m` : "";
    const address = (p.address || "").trim();
    const name = escapeHtml(p.image_name || "photo");
    const addrHtml = address
      ? `<span class="darwin-gps-addr">${escapeHtml(address)}</span><br/>`
      : "";
    el.title = address ? `${p.image_name || "GPS"} — ${address}` : p.image_name || "GPS";
    const thumbHtml = p.thumb
      ? `<img src="${escapeHtml(p.thumb)}" alt="" style="width:160px;height:160px;object-fit:cover;border-radius:6px;display:block;margin-bottom:6px;" />`
      : "";
    const html = `<div class="darwin-gps-popup" style="max-width:180px;">${thumbHtml}<strong>${name}</strong>${addrHtml}<span>${p.lat.toFixed(6)}, ${p.lon.toFixed(6)}${alt}</span><br/><span>${escapeHtml(
      crackLine,
    )}${p.exif_source ? ` · ${escapeHtml(p.exif_source)}` : ""}</span></div>`;

    const marker = new maplibregl.Marker({ element: el, anchor: "bottom" })
      .setLngLat([p._lng, p._lat])
      .setPopup(new maplibregl.Popup({ offset: 18, maxWidth: "200px" }).setHTML(html))
      .addTo(map);
    markersOut.push(marker);
  }
}

function DarwinPageInner() {
  const searchParams = useSearchParams();
  const focusGps = searchParams.get("focus") === "gps";

  const hostRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<AnyNS | null>(null);
  const maplibreRef = useRef<AnyNS | null>(null);
  const layerRef = useRef<AnyNS | null>(null);
  const memRef = useRef<OverlayMemory | null>(null);
  const gpsMarkersRef = useRef<AnyNS[]>([]);
  const gpsPointsRef = useRef<GpsPoint[]>([]);
  const bootIdRef = useRef(0);

  const [lang, setLang] = useState<Lang>("vi");
  const t = useMemo(() => makeT(lang), [lang]);
  const [statusKey, setStatusKey] = useState<
    "darwinInit" | "darwinLoading" | "darwinCacheAttach" | "darwinReady" | "darwinReadyCache" | "darwinSampling" | "darwinRebuildOk" | "error"
  >("darwinInit");
  const [statusErr, setStatusErr] = useState("");
  const [warn, setWarn] = useState(false);
  const [lidarOn, setLidarOn] = useState(true);
  const [lidarBusy, setLidarBusy] = useState(false);
  const [lidarCount, setLidarCount] = useState(0);
  const [gpsCount, setGpsCount] = useState(0);
  const [gpsPhotosOn, setGpsPhotosOn] = useState(true);
  const gpsPhotosOnRef = useRef(true);
  const [exaggerate, setExaggerate] = useState(1);
  const [colorMode, setColorMode] = useState<ColorMode>("height");
  const [bearing, setBearing] = useState(-28);
  const [pitch, setPitch] = useState(60);

  useEffect(() => {
    const saved = window.localStorage.getItem(LANG_KEY);
    if (saved === "en" || saved === "vi") setLang(saved);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const modeLabel =
    colorMode === "intensity" ? t("darwinModeIntensity") : t("darwinModeHeight");

  const statusText = useMemo(() => {
    if (statusKey === "error") return statusErr || t("darwinInit");
    if (statusKey === "darwinReady" || statusKey === "darwinReadyCache" || statusKey === "darwinRebuildOk") {
      return t(statusKey, { mode: modeLabel, n: lidarCount.toLocaleString(lang === "en" ? "en-US" : "vi-VN") });
    }
    return t(statusKey);
  }, [statusKey, statusErr, modeLabel, lidarCount, lang, t]);

  const mountCloud = (mem: OverlayMemory, exag: number, mode: ColorMode) => {
    const map = mapRef.current;
    const maplibregl = maplibreRef.current;
    if (!map || !maplibregl || map._removed) return;

    const { overlay, xyz, intensity } = mem;
    let colors: Float32Array;
    if (mode === "intensity") {
      const lo = overlay.intensity_stretch?.lo ?? 0;
      const hi = overlay.intensity_stretch?.hi ?? 255;
      colors = colorsFromIntensity(intensity, lo, hi);
    } else {
      const lo = overlay.z_stretch?.lo ?? overlay.bounds.zmin;
      const hi = overlay.z_stretch?.hi ?? overlay.bounds.zmax;
      colors = colorsFromHeight(xyz, lo, hi);
    }

    const cloud = buildMercatorCloud(maplibregl, xyz, colors, exag, overlay.bounds.zmin);

    if (map.getLayer("lidar-3d")) {
      try {
        map.removeLayer("lidar-3d");
      } catch {
        // ignore
      }
    }
    const layer = createLidar3DLayer(maplibregl, "lidar-3d", cloud);
    layer.visible = lidarOn;
    layerRef.current = layer;
    map.addLayer(layer);
    map.triggerRepaint();
  };

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const bootId = ++bootIdRef.current;
    const ac = new AbortController();
    let map: AnyNS | null = null;

    (async () => {
      try {
        const booted = await bootMap(host);
        if (bootId !== bootIdRef.current) {
          booted.map.remove();
          return;
        }
        map = booted.map;
        mapRef.current = map;
        maplibreRef.current = booted.maplibregl;

        const sync = () => {
          if (!map || map._removed) return;
          setBearing(map.getBearing());
          setPitch(map.getPitch());
        };
        sync();
        map.on("move", sync);
        map.once("idle", () => map?.resize?.());

        setWarn(false);

        let gpsPoints: GpsPoint[] = [];
        try {
          const langQ =
            window.localStorage.getItem(LANG_KEY) === "en" ? "en" : "vi";
          const gpsRes = await fetch(`${GPS_URL}?lang=${langQ}`, { signal: ac.signal });
          if (gpsRes.ok) {
            const gpsJson = (await gpsRes.json()) as { points?: GpsPoint[] };
            gpsPoints = Array.isArray(gpsJson.points) ? gpsJson.points : [];
          }
        } catch {
        }
        if (bootId !== bootIdRef.current || !map || map._removed) return;
        gpsPointsRef.current = gpsPoints;
        setGpsCount(gpsPoints.length);
        if (gpsPoints.length && maplibreRef.current && gpsPhotosOnRef.current) {
          mountGpsMarkers(map, maplibreRef.current, gpsPoints, gpsMarkersRef.current, {
            crack: (n) => t("darwinGpsPopupCrack", { n }),
            none: t("darwinGpsPopupNone"),
          });
        }

        setLidarBusy(true);
        const cached = !!OVERLAY_MEMORY;
        setStatusKey(cached ? "darwinCacheAttach" : "darwinLoading");

        try {
          const mem = await loadOverlayMemory(false, ac.signal);
          if (bootId !== bootIdRef.current) return;
          memRef.current = mem;
          mountCloud(mem, exaggerate, colorMode);
          setLidarCount(mem.overlay.count);
          setLidarOn(true);
          setLidarBusy(false);
          setStatusKey(cached ? "darwinReadyCache" : "darwinReady");
          if (focusGps && gpsPoints.length) {
            fitGps(map, gpsPoints);
          } else if (gpsPoints.length) {
            fitLidarAndGps(map, mem.overlay.bounds, gpsPoints);
          } else {
            fitLidar(map, mem.overlay.bounds);
          }
        } catch (lidarErr) {
          if (bootId !== bootIdRef.current) return;
          if ((lidarErr as Error)?.name === "AbortError") return;
          setLidarBusy(false);
          if (gpsPoints.length) {
            fitGps(map, gpsPoints);
            setWarn(true);
            setStatusKey("error");
            setStatusErr(
              lidarErr instanceof Error ? lidarErr.message : String(lidarErr),
            );
          } else {
            throw lidarErr;
          }
        }
      } catch (err) {
        if (bootId !== bootIdRef.current) return;
        if ((err as Error)?.name === "AbortError") return;
        setLidarBusy(false);
        setWarn(true);
        setStatusKey("error");
        setStatusErr(err instanceof Error ? err.message : String(err));
      }
    })();

    return () => {
      bootIdRef.current += 1;
      ac.abort();
      layerRef.current = null;
      clearGpsMarkers(gpsMarkersRef.current);
      try {
        map?.remove?.();
      } catch {
        // ignore
      }
      if (mapRef.current === map) mapRef.current = null;
      if (hostRef.current) {
        while (hostRef.current.firstChild) hostRef.current.removeChild(hostRef.current.firstChild);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (layerRef.current) {
      layerRef.current.visible = lidarOn;
      mapRef.current?.triggerRepaint?.();
    }
  }, [lidarOn]);

  useEffect(() => {
    gpsPhotosOnRef.current = gpsPhotosOn;
    const map = mapRef.current;
    const ml = maplibreRef.current;
    if (!map || map._removed || !ml) return;
    if (!gpsPhotosOn) {
      clearGpsMarkers(gpsMarkersRef.current);
      return;
    }
    if (!gpsPointsRef.current.length) return;
    mountGpsMarkers(map, ml, gpsPointsRef.current, gpsMarkersRef.current, {
      crack: (n) => t("darwinGpsPopupCrack", { n }),
      none: t("darwinGpsPopupNone"),
    });
  }, [gpsPhotosOn, t]);

  useEffect(() => {
    const mem = memRef.current;
    if (!mem || !mapRef.current || mapRef.current._removed) return;
    mountCloud(mem, exaggerate, colorMode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exaggerate, colorMode]);

  const fly = (opts: { bearing?: number; pitch?: number }) => {
    const m = mapRef.current;
    if (!m || m._removed) return;
    m.easeTo({
      bearing: opts.bearing ?? m.getBearing(),
      pitch: opts.pitch ?? m.getPitch(),
      duration: 700,
    });
  };

  const goLidar = () => {
    const m = mapRef.current;
    const b = memRef.current?.overlay.bounds;
    if (!m || m._removed || !b) return;
    fitLidar(m, b);
  };

  const goGps = () => {
    const m = mapRef.current;
    if (!m || m._removed || !gpsPointsRef.current.length) return;
    fitGps(m, gpsPointsRef.current);
  };

  const rebuild = async () => {
    const m = mapRef.current;
    if (!m || m._removed) return;
    setLidarBusy(true);
    setStatusKey("darwinSampling");
    try {
      OVERLAY_MEMORY = null;
      const mem = await loadOverlayMemory(true);
      memRef.current = mem;
      mountCloud(mem, exaggerate, colorMode);
      fitLidar(m, mem.overlay.bounds);
      setLidarCount(mem.overlay.count);
      setLidarOn(true);
      setWarn(false);
      setStatusKey("darwinRebuildOk");
    } catch (err) {
      setWarn(true);
      setStatusKey("error");
      setStatusErr(err instanceof Error ? err.message : String(err));
    } finally {
      setLidarBusy(false);
    }
  };

  return (
    <div className="darwin-shell">
      <header className="darwin-top">
        <div>
          <h1>{t("darwinTitle")}</h1>
          <p>
            {t("darwinSub", { bearing: fmt(bearing), pitch: fmt(pitch) })}
            {lidarCount
              ? t("darwinPts", { n: lidarCount.toLocaleString(lang === "en" ? "en-US" : "vi-VN") })
              : ""}
            {gpsCount ? t("darwinGpsPts", { n: gpsCount }) : ""}
          </p>
        </div>
        <div className="darwin-actions">
          <div className="lang-switch" role="group" aria-label="Language">
            <button
              type="button"
              className={lang === "vi" ? "on" : ""}
              title={t("langVi")}
              onClick={() => setLang("vi")}
            >
              VI
            </button>
            <button
              type="button"
              className={lang === "en" ? "on" : ""}
              title={t("langEn")}
              onClick={() => setLang("en")}
            >
              EN
            </button>
          </div>
          <Link
            href="/"
            onClick={() => {
              try {
                sessionStorage.setItem("crackinspect:restore-batch", "1");
              } catch {
                // ignore
              }
            }}
          >
            {t("darwinBack")}
          </Link>
          <button
            type="button"
            className={lidarOn ? "on" : ""}
            onClick={() => setLidarOn((v) => !v)}
            disabled={lidarBusy || !lidarCount}
          >
            {lidarOn ? t("darwinHideLidar") : t("darwinShowLidar")}
          </button>
          <button type="button" onClick={goLidar} disabled={!lidarCount}>
            {t("darwinZoomLidar")}
          </button>
          <button
            type="button"
            className={gpsPhotosOn && gpsCount ? "on" : ""}
            onClick={() => setGpsPhotosOn((v) => !v)}
            disabled={!gpsCount}
          >
            {gpsPhotosOn ? t("darwinHidePhotos") : t("darwinShowPhotos")}
          </button>
          <button type="button" className={gpsCount ? "on" : ""} onClick={goGps} disabled={!gpsCount}>
            {t("darwinZoomGps")}
          </button>
          <button type="button" onClick={() => fly({ pitch: 0, bearing: 0 })}>
            {t("darwinTopDown")}
          </button>
          <button type="button" className="on" onClick={() => fly({ pitch: 70, bearing: -40 })}>
            {t("darwinTilt70")}
          </button>
          <button
            type="button"
            className={colorMode === "intensity" ? "on" : ""}
            onClick={() => setColorMode("intensity")}
            disabled={!lidarCount}
          >
            {t("darwinIntensity")}
          </button>
          <button
            type="button"
            className={colorMode === "height" ? "on" : ""}
            onClick={() => setColorMode("height")}
            disabled={!lidarCount}
          >
            {t("darwinHeight")}
          </button>
          <label className="darwin-exag">
            {t("darwinExag", { n: exaggerate.toFixed(1) })}
            <input
              type="range"
              min={1}
              max={6}
              step={0.5}
              value={exaggerate}
              onChange={(e) => setExaggerate(Number(e.target.value))}
              disabled={!lidarCount}
            />
          </label>
          <button type="button" onClick={() => void rebuild()} disabled={lidarBusy}>
            {lidarBusy ? t("darwinRebuilding") : t("darwinRebuild")}
          </button>
        </div>
      </header>
      <div className="darwin-stage">
        <div ref={hostRef} id="darwin-map" />
        <div className="darwin-license" aria-label="License">
          <span className="darwin-license-data">{t("darwinLicense")}</span>
          <span className="darwin-license-org">{t("darwinLicenseOrg")}</span>
        </div>
        <div className={`darwin-status${warn ? " warn" : ""}`}>
          <b>{t("darwinHint")}</b>
          <span className="darwin-status-meta">{statusText}</span>
          <span className="darwin-status-meta">
            {gpsCount ? t("darwinGpsReady", { n: gpsCount }) : t("darwinGpsNone")}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function DarwinPage() {
  return (
    <Suspense fallback={<div className="darwin-shell" />}>
      <DarwinPageInner />
    </Suspense>
  );
}
