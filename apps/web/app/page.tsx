"use client";

import {
  AlertCircle,
  BarChart3,
  Bell,
  CheckCircle2,
  Download,
  Eye,
  FileText,
  History,
  Home,
  Box,
  Maximize2,
  Minimize2,
  MessageCircle,
  RotateCcw,
  Scan,
  Settings,
  Sparkles,
  TriangleAlert,
  UploadCloud,
  Video,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  DragEvent,
  FormEvent,
  PointerEvent,
  ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  LANG_KEY,
  actionLabel,
  axisLabel,
  levelLabel,
  localizeSceneReason,
  localizeSeverity,
  localizeSheet,
  makeT,
  type Lang,
  type TFn,
} from "./i18n";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type BBox = { x1: number; y1: number; x2: number; y2: number };
type PanelLayout = { cell: number; gap: number; caption: number };

type Instance = {
  id: number;
  score?: number;
  axis?: string;
  level?: string;
  action?: string;
  length_mm?: number | null;
  width_avg_mm?: number | null;
  length_px?: number;
  width_avg_px?: number;
  crop_data?: string;
  bbox?: BBox;
  sift_ok?: boolean;
  _image?: string;
};

type ConditionAssessment = {
  agent_id: string;
  role: string;
  model: string;
  grade: string;
  evidence: string[];
  confidence?: number;
  error?: string | null;
};

type ConditionOut = {
  rules_version?: string;
  assessments?: ConditionAssessment[];
  supervisor?: {
    decision?: string;
    grade?: string;
    rationale?: string;
    rule_ids?: string[];
    synthesis?: string;
  };
  pm?: {
    action?: string;
    note?: string;
    grade?: string | null;
    feedback?: string;
  } | null;
  final?: {
    grade?: string;
    evidence?: string[];
    status?: string;
  };
  detector_hint?: string;
};

type RecordOut = {
  image_name: string;
  detector?: string;
  lat?: number | null;
  lon?: number | null;
  length_mm?: number | null;
  width_avg_mm?: number | null;
  device?: string | null;
  exif_source?: string | null;
  stats?: string;
  vl_summary?: string;
  description_vi?: string;
  description_en?: string;
  grade?: string | null;
  condition?: ConditionOut | null;
  instances?: Instance[];
  preview_data?: string;
  original_data?: string;
  scene_kind?: string;
  scene_reason?: string;
  source_kind?: string;
  structure_report?: {
    structural_element?: string;
    defect_type?: string[] | string;
    severity_level?: string;
    location_description?: string;
    recommended_action?: string;
  } | null;
  panel_data?: string;
  overlay_recall?: number | null;
  overlay_precision?: number | null;
  overlay_f1?: number | null;
  overlay_iou?: number | null;
  overlay_tp?: number | null;
  overlay_fp?: number | null;
  overlay_fn?: number | null;
  overlay_quality?: string;
  overlay_quality_vi?: string;
  overlay_quality_en?: string;
  overlay_lang?: string;
  overlay_kind?: string;
  width?: number;
  height?: number;
  image_w?: number;
  image_h?: number;
  panel_layout?: PanelLayout;
  survey_object?: string;
  review?: {
    object?: string;
    count?: number;
    count_text?: string;
    focus?: {
      id: number;
      length: string;
      width: string;
      axis: string;
      risk: string;
      level?: string;
    } | null;
    others?: string;
    actions?: string[];
  };
};

type CloseupFields = {
  detail?: string;
  length?: string;
  width?: string;
  risk?: string;
  position?: string;
  text?: string;
};

type Bundle = { records: RecordOut[]; problem: string; report: string };
type LasFile = { name: string; points: number; layer: string; bytes: number };
type Tab = "ketqua" | "mota" | "hoidap" | "baocao" | "lichsu";
type PhotoTab = "hientruong" | "cancanh";
type SourceKind = "unknown" | "dashcam" | "survey" | "cctv" | "uav";
const SOURCE_KINDS: SourceKind[] = ["unknown", "dashcam", "survey", "cctv", "uav"];

function sceneBucket(rec: RecordOut): PhotoTab {
  if (rec.scene_kind === "hientruong" || rec.scene_kind === "cancanh") return rec.scene_kind;
  const d = String(rec.detector || "").toLowerCase();
  return d.startsWith("lcw") ? "hientruong" : "cancanh";
}
type ChatMsg = { role: "user" | "ai"; text: string };
type ViewMode = "deeplab" | "original" | "eval" | "raw";

function measure(mm: number | null | undefined, px: number | undefined, digits: number, unit = "mm") {
  if (mm != null) return `${mm.toFixed(digits)} ${unit}`;
  if (px != null) return `${px.toFixed(0)} px`;
  return "—";
}

function pillClass(level?: string) {
  if (level === "cao") return "pill pill-high";
  if (level === "trung bình") return "pill pill-mid";
  if (level === "nhẹ") return "pill pill-low";
  return "pill pill-none";
}

function barColor(level?: string) {
  if (level === "cao") return "#ef4444";
  if (level === "trung bình") return "#f97316";
  return "#10b981";
}

const DEFAULT_PANEL: PanelLayout = { cell: 512, gap: 8, caption: 32 };

function clampBoxPct(box: BBox, crop: { x1: number; y1: number; w: number; h: number }) {
  const left = ((box.x1 - crop.x1) / crop.w) * 100;
  const top = ((box.y1 - crop.y1) / crop.h) * 100;
  const width = ((box.x2 - box.x1 + 1) / crop.w) * 100;
  const height = ((box.y2 - box.y1 + 1) / crop.h) * 100;
  const l = Math.min(100, Math.max(0, left));
  const t = Math.min(100, Math.max(0, top));
  return {
    left: `${l}%`,
    top: `${t}%`,
    width: `${Math.min(100 - l, Math.max(0, width))}%`,
    height: `${Math.min(100 - t, Math.max(0, height))}%`,
  };
}

function inspectCrop(box: BBox, srcW: number, srcH: number) {
  const bw = Math.max(1, box.x2 - box.x1 + 1);
  const bh = Math.max(1, box.y2 - box.y1 + 1);
  const small = Math.max(bw, bh) < 48;
  const pad = small ? Math.max(8, Math.round(Math.max(bw, bh) * 0.55)) : Math.max(14, Math.round(Math.max(bw, bh) * 0.7));
  const minSide = small ? Math.max(36, Math.max(bw, bh) + 16) : 72;
  let x1 = box.x1 - pad;
  let y1 = box.y1 - pad;
  let x2 = box.x2 + 1 + pad;
  let y2 = box.y2 + 1 + pad;
  if (x2 - x1 < minSide) {
    const extra = (minSide - (x2 - x1)) / 2;
    x1 -= extra;
    x2 += extra;
  }
  if (y2 - y1 < minSide) {
    const extra = (minSide - (y2 - y1)) / 2;
    y1 -= extra;
    y2 += extra;
  }
  if (x1 < 0) {
    x2 -= x1;
    x1 = 0;
  }
  if (y1 < 0) {
    y2 -= y1;
    y1 = 0;
  }
  if (x2 > srcW) {
    x1 = Math.max(0, x1 - (x2 - srcW));
    x2 = srcW;
  }
  if (y2 > srcH) {
    y1 = Math.max(0, y1 - (y2 - srcH));
    y2 = srcH;
  }
  x1 = Math.max(0, Math.floor(x1));
  y1 = Math.max(0, Math.floor(y1));
  x2 = Math.min(srcW, Math.ceil(x2));
  y2 = Math.min(srcH, Math.ceil(y2));
  return { x1, y1, x2, y2, w: Math.max(1, x2 - x1), h: Math.max(1, y2 - y1) };
}

function formatIdRange(ids: number[], t: TFn) {
  const sorted = [...ids].sort((a, b) => a - b);
  if (sorted.length === 0) return "";
  if (sorted.length <= 3) return sorted.map((id) => `#${id}`).join(", ");
  const consec = sorted.every((id, i) => i === 0 || id === sorted[i - 1] + 1);
  return consec ? `#${sorted[0]}–#${sorted[sorted.length - 1]}` : t("cracksN", { n: sorted.length });
}

function CloseupLines({
  fields,
  note,
  t,
}: {
  fields?: CloseupFields | null;
  note?: string;
  t: TFn;
}) {
  if (!fields?.detail && !fields?.length) {
    return <p>{note || t("closeupWait")}</p>;
  }
  return (
    <dl className="closeup-fields">
      <div>
        <dt>{t("closeupDetail")}</dt>
        <dd>{localizeSheet(fields.detail, t)}</dd>
      </div>
      <div>
        <dt>{t("length")}</dt>
        <dd>{localizeSheet(fields.length, t)}</dd>
      </div>
      <div>
        <dt>{t("width")}</dt>
        <dd>{localizeSheet(fields.width, t)}</dd>
      </div>
      <div>
        <dt>{t("closeupRisk")}</dt>
        <dd>{localizeSheet(fields.risk, t)}</dd>
      </div>
      <div>
        <dt>{t("closeupPos")}</dt>
        <dd>{localizeSheet(fields.position, t)}</dd>
      </div>
    </dl>
  );
}

function cleanAgentNote(text?: string | null, max = 180) {
  let s = (text || "").replace(/\s+/g, " ").trim();
  if (!s) return "";
  if (/^(okay|so,|first,|let me|i need to|i'm the|the input is)/i.test(s)) return "";
  if (s.length > max) s = `${s.slice(0, max).trim()}…`;
  return s;
}

type PipeStepId = "detect" | "assess" | "supervisor" | "pm" | "final";

function ConditionPanel({ condition, t }: { condition?: ConditionOut | null; t: TFn }) {
  const [step, setStep] = useState<PipeStepId>("final");
  if (!condition?.supervisor && !condition?.final) return null;

  const decision = condition.supervisor?.decision || "";
  const status = condition.final?.status || decision;
  const badgeClass =
    status === "supported" || status === "resolved"
      ? "cond-badge ok"
      : status === "refer"
        ? "cond-badge refer"
        : "cond-badge open";
  const badgeLabel =
    status === "supported"
      ? t("condSupported")
      : status === "resolved"
        ? t("condResolved")
        : status === "refer"
          ? t("condRefer")
          : t("condUnresolved");

  const assessments = condition.assessments || [];
  const assessGrade =
    assessments.length === 1
      ? assessments[0].grade || "—"
      : assessments.length
        ? `${assessments.length}`
        : "—";
  const supervisorState =
    condition.supervisor?.decision === "supported"
      ? "ok"
      : condition.supervisor?.decision === "unresolved"
        ? "warn"
        : "idle";
  const pmState = !condition.pm ? "skip" : condition.pm.action === "resolve" ? "ok" : "warn";
  const finalState =
    status === "supported" || status === "resolved" ? "ok" : status === "refer" ? "warn" : "idle";

  const nodes: { id: PipeStepId; title: string; sub: string; state: string }[] = [
    {
      id: "detect",
      title: t("pipeDetect"),
      sub: condition.detector_hint || "—",
      state: "ok",
    },
    {
      id: "assess",
      title: t("pipeAssess"),
      sub: assessGrade,
      state: assessments.length ? "ok" : "idle",
    },
    {
      id: "supervisor",
      title: t("pipeSupervisor"),
      sub: condition.supervisor?.decision || "—",
      state: supervisorState,
    },
    {
      id: "pm",
      title: t("pipePm"),
      sub: condition.pm?.action || t("pipeSkipped"),
      state: pmState,
    },
    {
      id: "final",
      title: t("pipeFinal"),
      sub: `${badgeLabel} · ${condition.final?.grade || condition.supervisor?.grade || "—"}`,
      state: finalState,
    },
  ];

  let detail: ReactNode = null;
  if (step === "detect") {
    detail = (
      <p>
        {t("pipeDetectHint")}: <b>{condition.detector_hint || "—"}</b>
      </p>
    );
  } else if (step === "assess") {
    detail = assessments.length ? (
      <ul className="pipe-list">
        {assessments.map((a) => (
          <li key={a.agent_id}>
            <b>
              {a.agent_id} · {a.grade || "—"}
            </b>
            {a.error ? <span className="muted"> ({a.error})</span> : null}
            {(a.evidence || []).length > 0 ? (
              <ul>
                {(a.evidence || []).slice(0, 3).map((ev, i) => (
                  <li key={`${a.agent_id}-${i}`}>{localizeSheet(ev, t)}</li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>
    ) : (
      <p className="muted">{t("pipeNoAssess")}</p>
    );
  } else if (step === "supervisor") {
    const note =
      cleanAgentNote(condition.supervisor?.rationale) ||
      cleanAgentNote(condition.supervisor?.synthesis) ||
      t("pipeNoNote");
    detail = (
      <p>
        {t("pipeDecision")}: <b>{condition.supervisor?.decision || "—"}</b>
        {" · "}
        {t("condGrade")}: <b>{condition.supervisor?.grade || "—"}</b>
        <br />
        <span className="muted">{localizeSheet(note, t)}</span>
      </p>
    );
  } else if (step === "pm") {
    if (!condition.pm) {
      detail = <p className="muted">{t("pipePmSkipHint")}</p>;
    } else {
      const note = cleanAgentNote(condition.pm.note) || t("pipeNoNote");
      detail = (
        <p>
          {t("pipeAction")}: <b>{condition.pm.action}</b>
          {condition.pm.grade ? (
            <>
              {" · "}
              {t("condGrade")}: <b>{condition.pm.grade}</b>
            </>
          ) : null}
          <br />
          <span className="muted">{localizeSheet(note, t)}</span>
        </p>
      );
    }
  } else {
    detail = (
      <p>
        {t("pipeStatus")}: <b>{badgeLabel}</b>
        {" · "}
        {t("condGrade")}: <b>{condition.final?.grade || condition.supervisor?.grade || "—"}</b>
      </p>
    );
  }

  return (
    <div className="condition-box">
      <div className="condition-head">
        <span className={badgeClass}>{badgeLabel}</span>
        <span className="condition-grade">
          {t("condGrade")}: {condition.final?.grade || condition.supervisor?.grade || "—"}
        </span>
      </div>
      <p className="pipe-hint muted">{t("pipeHint")}</p>
      <div className="pipe" role="list">
        {nodes.map((node, i) => (
          <div key={node.id} className="pipe-item" role="listitem">
            {i > 0 ? <span className="pipe-arrow" aria-hidden="true">
              →
            </span> : null}
            <button
              type="button"
              className={`pipe-node state-${node.state}${step === node.id ? " on" : ""}`}
              onClick={() => setStep(node.id)}
              aria-pressed={step === node.id}
            >
              <span className="pipe-title">{node.title}</span>
              <span className="pipe-sub">{node.sub}</span>
            </button>
          </div>
        ))}
      </div>
      <div className="pipe-detail">{detail}</div>
    </div>
  );
}

function SceneCaption({
  rec,
  lang,
  t,
}: {
  rec?: RecordOut | null;
  lang: Lang;
  t: TFn;
}) {
  const vi = (rec?.description_vi || rec?.vl_summary || "").trim();
  const en = (rec?.description_en || "").trim();
  const usedViFallback = lang === "en" && !en && !!vi;
  const proseRaw =
    lang === "en"
      ? en || vi || rec?.stats || t("noVlm")
      : vi || en || rec?.stats || t("noVlm");
  const prose = localizeSheet(String(proseRaw), t);
  const timeBit = (rec?.device || rec?.exif_source || "").trim() || t("none");
  const gpsBit =
    rec?.lat != null && rec?.lon != null
      ? `${rec.lat.toFixed(6)}, ${rec.lon.toFixed(6)}`
      : t("none");
  const sourceKey = String(rec?.source_kind || "unknown") as SourceKind;
  const sourceLabel =
    sourceKey === "dashcam"
      ? t("sourceDashcam")
      : sourceKey === "survey"
        ? t("sourceSurvey")
        : sourceKey === "cctv"
          ? t("sourceCctv")
          : sourceKey === "uav"
            ? t("sourceUav")
            : t("sourceUnknown");
  const report = rec?.structure_report;
  const defects = report?.defect_type;
  const defectText = Array.isArray(defects)
    ? defects.map((d) => localizeSheet(String(d), t)).join(", ") || t("none")
    : localizeSheet(String(defects || t("none")), t);
  return (
    <div className="scene-caption-wrap">
      <p className="scene-meta">
        {t("time")}: {timeBit} · {t("gps")}: {gpsBit} · {t("source")}: {sourceLabel}
      </p>
      {report ? (
        <div className="scene-caption structure-card">
          <strong>{t("structureTitle")}</strong>
          <dl className="structure-fields">
            <div>
              <dt>{t("structuralElement")}</dt>
              <dd>{localizeSheet(report.structural_element, t) || t("none")}</dd>
            </div>
            <div>
              <dt>{t("defectType")}</dt>
              <dd>{defectText}</dd>
            </div>
            <div>
              <dt>{t("severityLevel")}</dt>
              <dd>
                <span className={`sev sev-${String(report.severity_level || "Low").toLowerCase()}`}>
                  {localizeSeverity(report.severity_level || "Low", t)}
                </span>
              </dd>
            </div>
            <div>
              <dt>{t("locationDescription")}</dt>
              <dd>{localizeSheet(report.location_description, t) || t("none")}</dd>
            </div>
            <div>
              <dt>{t("recommendedAction")}</dt>
              <dd>{localizeSheet(report.recommended_action, t) || t("none")}</dd>
            </div>
          </dl>
          {usedViFallback ? <p className="muted">{t("enCaptionFallback")}</p> : null}
        </div>
      ) : (
        <div className="scene-caption">
          <strong>{t("description")}</strong>
          {usedViFallback ? <p className="muted">{t("enCaptionFallback")}</p> : null}
          <p>{prose}</p>
        </div>
      )}
    </div>
  );
}

function ReviewFields({
  rec,
  closeup,
  closeupId,
  closeupNote,
  t,
}: {
  rec?: RecordOut | null;
  closeup?: CloseupFields | null;
  closeupId?: number | null;
  closeupNote?: string;
  t: TFn;
}) {
  const review = rec?.review;
  if (!review) {
    return (
      <>
        <ConditionPanel condition={rec?.condition} t={t} />
      </>
    );
  }
  return (
    <>
    <ConditionPanel condition={rec?.condition} t={t} />
    <dl className="fields">
      <div>
        <dt>{t("reviewObject")}</dt>
        <dd>{localizeSheet(review.object, t)}</dd>
      </div>
      <div>
        <dt>{t("reviewCount")}</dt>
        <dd>{localizeSheet(review.count_text, t)}</dd>
      </div>
      {review.focus ? (
        <div>
          <dt>{t("reviewFocus", { id: review.focus.id })}</dt>
          <dd>
            <div>
              {t("reviewSize", {
                length: localizeSheet(review.focus.length, t),
                width: localizeSheet(review.focus.width, t),
              })}
            </div>
            <div>{t("reviewAxis", { axis: localizeSheet(review.focus.axis, t) })}</div>
            <div>{t("reviewRisk", { risk: localizeSheet(review.focus.risk, t) })}</div>
          </dd>
        </div>
      ) : null}
      {closeupId != null ? (
        <div>
          <dt>{t("reviewCloseup", { id: closeupId })}</dt>
          <dd>
            <CloseupLines fields={closeup} note={closeupNote} t={t} />
          </dd>
        </div>
      ) : null}
      <div>
        <dt>{t("reviewOthers")}</dt>
        <dd>{localizeSheet(review.others, t)}</dd>
      </div>
      <div>
        <dt>{t("reviewActions")}</dt>
        <dd>
          <ul>
            {(review.actions || []).map((act) => (
              <li key={act}>{actionLabel(act, t)}</li>
            ))}
          </ul>
        </dd>
      </div>
    </dl>
    </>
  );
}

function summarizeActions(items: Instance[]) {
  const groups = new Map<string, { action: string; ids: number[]; priority: boolean }>();
  for (const item of items) {
    const action = item.action || "theo dõi định kỳ";
    const cur = groups.get(action) || { action, ids: [], priority: item.level === "cao" };
    cur.ids.push(item.id);
    cur.priority = cur.priority || item.level === "cao";
    groups.set(action, cur);
  }
  return [...groups.values()].sort((a, b) => Number(b.priority) - Number(a.priority));
}

function loadImageSize(src: string): Promise<{ w: number; h: number }> {
  return new Promise((resolve, reject) => {
    const im = new window.Image();
    im.onload = () => resolve({ w: im.naturalWidth, h: im.naturalHeight });
    im.onerror = () => reject(new Error("SIZE_READ_ERROR"));
    im.src = src;
  });
}

function instanceHits(
  item: Instance,
  mode: "panel" | "flat",
  srcW: number,
  srcH: number,
  panel: PanelLayout,
  previewCap: number,
): { left: number; top: number; width: number; height: number }[] {
  const box = item.bbox;
  if (!box || srcW <= 0 || srcH <= 0) return [];
  const x1 = box.x1;
  const y1 = box.y1;
  const x2 = box.x2 + 1;
  const y2 = box.y2 + 1;
  if (mode === "panel") {
    const cellW = panel.cell;
    const cellH = panel.cell + panel.caption;
    const panelW = cellW * 2 + panel.gap;
    const panelH = cellH * 2 + panel.gap;
    const nx1 = (x1 / srcW) * panel.cell;
    const ny1 = (y1 / srcH) * panel.cell;
    const nw = ((x2 - x1) / srcW) * panel.cell;
    const nh = ((y2 - y1) / srcH) * panel.cell;
    const origins = [
      [0, 0],
      [0, cellH + panel.gap],
      [cellW + panel.gap, cellH + panel.gap],
    ];
    return origins.map(([ox, oy]) => ({
      left: ((ox + nx1) / panelW) * 100,
      top: ((oy + panel.caption + ny1) / panelH) * 100,
      width: (nw / panelW) * 100,
      height: (nh / panelH) * 100,
    }));
  }
  const fullH = srcH + previewCap;
  return [
    {
      left: (x1 / srcW) * 100,
      top: ((y1 + previewCap) / fullH) * 100,
      width: ((x2 - x1) / srcW) * 100,
      height: ((y2 - y1) / fullH) * 100,
    },
  ];
}

export default function Page() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("ketqua");
  const [photoTab, setPhotoTab] = useState<PhotoTab>("hientruong");
  const [sourceKind, setSourceKind] = useState<SourceKind>("unknown");
  const [lasFiles, setLasFiles] = useState<LasFile[]>([]);
  const [lidarBusy, setLidarBusy] = useState(false);
  const [lidarViewUrl, setLidarViewUrl] = useState(`${API}/lidar/view/scene_223582.html`);
  const [qwenViewUrl, setQwenViewUrl] = useState("");
  const [qwenBusy, setQwenBusy] = useState(false);
  const [lidarMsg, setLidarMsg] = useState("");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [focusName, setFocusName] = useState("");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [panning, setPanning] = useState(false);
  const [view, setView] = useState<ViewMode>("eval");
  const [localOrig, setLocalOrig] = useState<Record<string, string>>({});
  const [focusCrack, setFocusCrack] = useState<number | null>(null);
  const [inspectId, setInspectId] = useState<number | null>(null);
  const [srcSize, setSrcSize] = useState({ w: 512, h: 512 });
  const [previewCap, setPreviewCap] = useState(0);
  const [hitMode, setHitMode] = useState<"panel" | "flat">("flat");
  const [sharpenSrc, setSharpenSrc] = useState("");
  const [sharpenNote, setSharpenNote] = useState("");
  const [closeupFields, setCloseupFields] = useState<CloseupFields | null>(null);
  const [closeupNote, setCloseupNote] = useState("");
  const [chatMsgs, setChatMsgs] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [cracksExpanded, setCracksExpanded] = useState(false);
  const [gpsFlash, setGpsFlash] = useState(0);
  const [lang, setLang] = useState<Lang>("vi");
  const t = useMemo(() => makeT(lang), [lang]);
  const clickTimer = useRef<number | null>(null);
  const justPanned = useRef(false);
  const panDrag = useRef<{
    id: number;
    x: number;
    y: number;
    ox: number;
    oy: number;
    moved: boolean;
  } | null>(null);

  const records = bundle?.records || [];
  const gpsCount = useMemo(
    () => records.filter((row) => row.lat != null && row.lon != null).length,
    [records],
  );
  const fieldRecords = useMemo(
    () => records.filter((row) => sceneBucket(row) === "hientruong"),
    [records],
  );
  const closeRecords = useMemo(
    () => records.filter((row) => sceneBucket(row) === "cancanh"),
    [records],
  );
  const thumbRecords = photoTab === "hientruong" ? fieldRecords : closeRecords;
  const rec =
    thumbRecords.find((row) => row.image_name === focusName) ||
    thumbRecords[0] ||
    records.find((row) => row.image_name === focusName) ||
    records[0];
  const instances = rec?.instances || [];
  const crackScrollRef = useRef<HTMLDivElement>(null);
  const counts = useMemo(() => {
    const out = { all: instances.length, mid: 0, light: 0 };
    for (const item of instances) {
      if (item.level === "nhẹ") out.light += 1;
      else out.mid += 1;
    }
    return out;
  }, [instances]);

  useEffect(() => {
    if (!records.length) return;
    const focused = records.find((row) => row.image_name === focusName) || records[0];
    setPhotoTab(sceneBucket(focused));
  }, [bundle]);

  const selectPhotoTab = (next: PhotoTab) => {
    setPhotoTab(next);
    const list = next === "hientruong" ? fieldRecords : closeRecords;
    if (!list.some((row) => row.image_name === focusName) && list[0]) {
      setFocusName(list[0].image_name);
    }
  };

  useEffect(() => {
    const saved = window.localStorage.getItem(LANG_KEY);
    if (saved === "en" || saved === "vi") setLang(saved);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  // Restore only the latest Detect batch when returning from Darwin (not on every cold load).
  useEffect(() => {
    const flag = "crackinspect:restore-batch";
    if (typeof window === "undefined" || sessionStorage.getItem(flag) !== "1") return;
    sessionStorage.removeItem(flag);
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${API}/last`);
        if (!res.ok) return;
        const data = (await res.json()) as Bundle;
        if (cancelled || !Array.isArray(data.records) || !data.records.length) return;
        setBundle({
          records: data.records,
          problem: data.problem || "",
          report: data.report || "",
        });
        const first = data.records[0];
        if (first?.image_name) setFocusName(first.image_name);
        setView(first?.panel_data ? "eval" : "deeplab");
        setTab("ketqua");
        setGpsFlash(data.records.filter((row) => row.lat != null && row.lon != null).length);
      } catch {
        // ignore — empty UI until next analyze
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void fetch(`${API}/lidar/files`)
      .then((res) => (res.ok ? res.json() : { files: [] }))
      .then((data) => setLasFiles(data.files || []))
      .catch(() => undefined);
  }, []);

  async function buildLidarViewer() {
    setLidarBusy(true);
    setLidarMsg("");
    try {
      const res = await fetch(`${API}/lidar/build?max_points=180000`, { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      const url = `${API}${data.view_url}`;
      setLidarViewUrl(url);
      setLidarMsg(
        (data.layers || [])
          .map((layer: { name: string; count: number }) => `${layer.name}: ${layer.count.toLocaleString()}`)
          .join(" · ")
      );
    } catch (err) {
      setLidarMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setLidarBusy(false);
    }
  }

  async function runQwen3d() {
    setQwenBusy(true);
    setLidarMsg("");
    try {
      const res = await fetch(`${API}/lidar-3d/from-las?max_points=80000`, { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
      const url = `${API}${data.view_url}`;
      setQwenViewUrl(url);
      setLidarMsg(`Qwen OK · ${data.html_name || "scene"} · ${(data.bytes || 0).toLocaleString()} B`);
      window.open(url, "_blank");
    } catch (err) {
      setLidarMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setQwenBusy(false);
    }
  }

  useEffect(() => {
    setFocusCrack(null);
    setInspectId(null);
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSharpenSrc("");
    setSharpenNote("");
    setCloseupFields(null);
    setCloseupNote("");
    setCracksExpanded(false);
  }, [rec?.image_name]);

  useEffect(() => {
    const el = crackScrollRef.current;
    if (!el || cracksExpanded) return;
    const onWheel = (ev: WheelEvent) => {
      if (el.scrollHeight <= el.clientHeight) return;
      ev.preventDefault();
      ev.stopPropagation();
      el.scrollTop += ev.deltaY;
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [cracksExpanded, instances.length, rec?.image_name]);

  useEffect(() => {
    if (inspectId == null || !rec?.image_name) {
      setSharpenSrc("");
      setSharpenNote("");
      setCloseupFields(null);
      setCloseupNote("");
      return;
    }
    let cancelled = false;
    setSharpenSrc("");
    setSharpenNote(t("sharpening"));
    setCloseupFields(null);
    setCloseupNote(t("closeupWait"));
    const name = encodeURIComponent(rec.image_name);
    void (async () => {
      try {
        const res = await fetch(`${API}/sharpen?image_name=${name}&id=${inspectId}&force=1`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (cancelled) return;
        setSharpenSrc(data.data || "");
        setSharpenNote(
          data.source === "realesrgan" || data.source === "cache"
            ? t("sharpOk")
            : data.error
              ? t("sharpFail", { err: data.error })
              : t("sharpCrop"),
        );
      } catch (exc) {
        if (!cancelled) setSharpenNote(exc instanceof Error ? exc.message : t("sharpErr"));
      }
      try {
        const res = await fetch(`${API}/closeup?image_name=${name}&id=${inspectId}&force=1`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (cancelled) return;
        setCloseupFields({
          detail: data.detail,
          length: data.length,
          width: data.width,
          risk: data.risk,
          position: data.position,
          text: data.text,
        });
        setCloseupNote(data.source === "qwen" ? t("closeupQwen") : t("closeupCached"));
      } catch (exc) {
        if (!cancelled) setCloseupNote(exc instanceof Error ? exc.message : t("closeupErr"));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [inspectId, rec?.image_name, t]);

  useEffect(() => {
    if (focusCrack == null) return;
    document.querySelector(".crack.on")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [focusCrack]);

  useEffect(() => {
    let cancelled = false;
    setHitMode(view === "eval" ? "panel" : "flat");
    async function measureSrc() {
      const fallback = {
        w: rec?.image_w || rec?.width || 512,
        h: rec?.image_h || rec?.height || 512,
      };
      let src = fallback;
      if (rec?.original_data) {
        try {
          src = await loadImageSize(rec.original_data);
        } catch {
          src = fallback;
        }
      }
      let cap = 0;
      let mode: "panel" | "flat" = view === "eval" ? "panel" : "flat";
      if (view === "deeplab" && rec?.preview_data) {
        try {
          const preview = await loadImageSize(rec.preview_data);
          if (preview.w > src.w * 1.35) mode = "panel";
          else cap = Math.max(0, preview.h - src.h);
        } catch {
          cap = 0;
        }
      }
      if (!cancelled) {
        setSrcSize(src);
        setPreviewCap(cap);
        setHitMode(mode);
      }
    }
    void measureSrc();
    return () => {
      cancelled = true;
    };
  }, [rec?.image_name, rec?.original_data, rec?.preview_data, rec?.image_w, rec?.image_h, rec?.width, rec?.height, view]);

  async function postAnalyze(body: FormData | null) {
    setBusy(true);
    setError("");
    setZoom(1);
    setView("deeplab");
    try {
      const res = await fetch(`${API}/analyze`, { method: "POST", body: body || undefined });
      if (!res.ok) throw new Error(await res.text());
      const data = (await res.json()) as Bundle;
      setBundle({
        records: data.records,
        problem: data.problem,
        report: data.report,
      });
      const gpsN = data.records.filter((row) => row.lat != null && row.lon != null).length;
      setGpsFlash(gpsN);
      if (data.records[0]?.image_name) setFocusName(data.records[0].image_name);
      setFocusCrack(null);
      setInspectId(null);
      setZoom(1);
      setView(data.records[0]?.panel_data ? "eval" : "deeplab");
      setTab("ketqua");
    } catch (exc) {
      const msg = exc instanceof Error ? exc.message : t("errAnalyze");
      setError(msg === "SIZE_READ_ERROR" ? t("errSize") : msg);
    } finally {
      setBusy(false);
    }
  }

  function takeFiles(list: FileList | File[]) {
    const next = Array.from(list).filter((file) => file.type.startsWith("image/"));
    if (!next.length) return;
    setFiles((prev) => {
      const byName = new Map<string, File>();
      for (const file of prev) byName.set(file.name, file);
      for (const file of next) byName.set(file.name, file);
      return Array.from(byName.values());
    });
    setLocalOrig((prev) => {
      const extra: Record<string, string> = {};
      for (const file of next) extra[file.name] = URL.createObjectURL(file);
      return { ...prev, ...extra };
    });
    setBundle(null);
    setFocusName("");
    setFocusCrack(null);
    setInspectId(null);
    setGpsFlash(0);
    setError("");
  }

  function clearFiles() {
    setFiles([]);
    setBundle(null);
    setFocusName("");
    setFocusCrack(null);
    setInspectId(null);
    setGpsFlash(0);
    setError("");
  }

  function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (!files.length) {
      setError(t("errNeedFile"));
      return;
    }
    const body = new FormData();
    for (const file of files) body.append("files", file);
    body.append("source_kind", sourceKind);
    body.append("lang", lang);
    void postAnalyze(body);
  }

  function onDrop(ev: DragEvent) {
    ev.preventDefault();
    setDrag(false);
    if (ev.dataTransfer.files.length) takeFiles(ev.dataTransfer.files);
  }

  const originalSrc = rec?.original_data || (rec ? localOrig[rec.image_name] : "") || "";
  const shownImage =
    view === "original" || view === "raw"
      ? originalSrc
      : view === "eval"
        ? rec?.panel_data
        : rec?.preview_data;
  const inspectItem = instances.find((item) => item.id === inspectId && item.bbox);
  const crop =
    inspectItem?.bbox && srcSize.w > 0 && srcSize.h > 0
      ? inspectCrop(inspectItem.bbox, srcSize.w, srcSize.h)
      : null;
  const inspectSrc = originalSrc || rec?.preview_data || "";

  function clearClickTimer() {
    if (clickTimer.current != null) {
      window.clearTimeout(clickTimer.current);
      clickTimer.current = null;
    }
  }

  function bumpZoom(next: number) {
    const z = Math.min(inspectId != null ? 6 : 3, Math.max(0.5, next));
    setZoom(z);
    if (z <= 1) setPan({ x: 0, y: 0 });
  }

  function onStagePointerDown(ev: PointerEvent<HTMLDivElement>) {
    if (zoom <= 1 || ev.detail >= 2) return;
    if ((ev.target as HTMLElement).closest(".tools, .inspect-banner, .box-hit")) return;
    ev.currentTarget.setPointerCapture(ev.pointerId);
    panDrag.current = { id: ev.pointerId, x: ev.clientX, y: ev.clientY, ox: pan.x, oy: pan.y, moved: false };
  }

  function onStagePointerMove(ev: PointerEvent<HTMLDivElement>) {
    const drag = panDrag.current;
    if (!drag || drag.id !== ev.pointerId) return;
    const dx = ev.clientX - drag.x;
    const dy = ev.clientY - drag.y;
    if (!drag.moved && dx * dx + dy * dy < 16) return;
    if (!drag.moved) setPanning(true);
    drag.moved = true;
    justPanned.current = true;
    setPan({ x: drag.ox + dx, y: drag.oy + dy });
  }

  function onStagePointerUp(ev: PointerEvent<HTMLDivElement>) {
    const drag = panDrag.current;
    if (!drag || drag.id !== ev.pointerId) return;
    const moved = drag.moved;
    panDrag.current = null;
    setPanning(false);
    if (moved) {
      window.setTimeout(() => {
        justPanned.current = false;
      }, 80);
    } else {
      justPanned.current = false;
    }
  }

  function onStageDoubleClick(ev: { target: EventTarget | null }) {
    if ((ev.target as HTMLElement | null)?.closest?.(".tools, .inspect-banner")) return;
    if (inspectId == null) return;
    justPanned.current = false;
    clearClickTimer();
    exitInspect();
  }

  function pickCrack(id: number) {
    if (justPanned.current) return;
    clearClickTimer();
    clickTimer.current = window.setTimeout(() => {
      if (inspectId != null) {
        setFocusCrack(id);
        setInspectId(id);
        setZoom(1);
      } else {
        setFocusCrack((cur) => (cur === id ? null : id));
      }
    }, 220);
  }

  function toggleInspect(id: number) {
    justPanned.current = false;
    clearClickTimer();
    setFocusCrack(id);
    setInspectId((cur) => (cur === id ? null : id));
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function exitInspect() {
    setInspectId(null);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function changeView(next: ViewMode) {
    setView(next);
    exitInspect();
  }

  function downloadPreview() {
    if (!shownImage || !rec) return;
    const a = document.createElement("a");
    a.href = shownImage;
    a.download =
      rec.image_name.replace(/\.[^.]+$/, "") +
      (view === "raw" ? "_raw.jpg" : view === "original" ? "_goc.jpg" : view === "eval" ? "_o4.jpg" : "_deeplab.jpg");
    a.click();
  }

  async function sendChat(ev?: FormEvent) {
    ev?.preventDefault();
    const q = chatInput.trim();
    if (!q || !records.length || chatBusy) return;
    setChatInput("");
    setChatMsgs((prev) => [...prev, { role: "user", text: q }]);
    setChatBusy(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_name: rec?.image_name || "",
          question: q,
          inspect_id: inspectId,
          history: chatMsgs.slice(-8).map((msg) => ({ role: msg.role, text: msg.text })),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setChatMsgs((prev) => [...prev, { role: "ai", text: data.answer || t("noAnswer") }]);
    } catch (exc) {
      setChatMsgs((prev) => [
        ...prev,
        { role: "ai", text: exc instanceof Error ? exc.message : t("errChat") },
      ]);
    } finally {
      setChatBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Eye size={20} color="#fff" />
          </div>
          <h1 className="brand-title">InfraVision AI</h1>
          <span className="brand-sub">{t("brandSub")}</span>
        </div>
        <div className="top-actions">
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
          <button type="button" className="bell" aria-label={t("notify")}>
            <Bell size={20} />
            <span className="bell-dot">1</span>
          </button>
          <div className="who">
            <div className="avatar">TN</div>
            <div>
              <div className="who-name">Trương Tấn Nghĩa</div>
              <div className="who-role">{t("roleAdmin")}</div>
            </div>
          </div>
        </div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <nav className="nav">
            <span className="nav-item">
              <Home size={16} />
              {t("navHome")}
            </span>
            <span className="nav-item on">
              <Scan size={16} />
              {t("navAnalyze")}
            </span>
            <span className="nav-item">
              <Video size={16} />
              {t("navVideo")}
            </span>
            <button type="button" className="nav-btn live" onClick={() => setTab("baocao")}>
              <FileText size={16} />
              {t("navReport")}
            </button>
            <button
              type="button"
              className="nav-btn"
              onClick={() => {
                const el = document.getElementById("lidar-panel");
                el?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
            >
              <Box size={16} />
              {t("navLidar")}
            </button>
            <a
              className="nav-btn live"
              href={gpsCount || gpsFlash ? "/darwin?focus=gps" : "/darwin"}
              onClick={() => sessionStorage.setItem("crackinspect:restore-batch", "1")}
            >
              <Box size={16} />
              {t("navDarwin")}
              {gpsCount || gpsFlash ? ` · ${gpsCount || gpsFlash}` : ""}
            </a>
            <span className="nav-item">
              <History size={16} />
              {t("navHistory")}
            </span>
            <span className="nav-item">
              <BarChart3 size={16} />
              {t("navStats")}
            </span>
            <span className="nav-item">
              <Settings size={16} />
              {t("navSettings")}
            </span>
          </nav>
          <div className="model-box">
            <div className="model-head">
              <span>VLM Model</span>
              <span className="pulse" />
            </div>
            <div className="model-ok">{t("modelOn")}</div>
            <div className="model-meta">
              Qwen3-VL 4B
              <br />
              DeepInspect Conglomerate / LCW
            </div>
          </div>
        </aside>

        <form className="workspace" onSubmit={onSubmit}>
          <div className="row">
            <div
              className={`card upload-card${drag ? " drag" : ""}`}
              onDragOver={(ev) => {
                ev.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={onDrop}
            >
              <div className="upload-copy">
                <div className="upload-icon">
                  <UploadCloud size={24} />
                </div>
                <div>
                  <div className="upload-title">{t("dropTitle")}</div>
                  <div className="upload-hint">{t("dropHint")}</div>
                  {files.length > 0 && (
                    <div className="upload-hint">
                      {t("filesChosen", {
                        n: files.length,
                        names: files.map((f) => f.name).join(", "),
                      })}
                    </div>
                  )}
                  {error && <div className="upload-error">{error}</div>}
                  {busy && <div className="upload-busy">{t("busyAnalyze")}</div>}
                  {(gpsFlash > 0 || gpsCount > 0) && (
                    <a
                      className="upload-hint"
                      href="/darwin?focus=gps"
                      style={{ color: "#2563eb", fontWeight: 700 }}
                      onClick={() => sessionStorage.setItem("crackinspect:restore-batch", "1")}
                    >
                      {t("gpsOnDarwin", { n: gpsFlash || gpsCount })}
                    </a>
                  )}
                </div>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                multiple
                className="file-input"
                onChange={(ev) => {
                  takeFiles(ev.target.files || []);
                  ev.target.value = "";
                }}
              />
              <div className="upload-actions">
                <label className="source-label">
                  {t("source")}{" "}
                  <select
                    value={sourceKind}
                    disabled={busy}
                    onChange={(ev) => setSourceKind(ev.target.value as SourceKind)}
                  >
                    {SOURCE_KINDS.map((k) => (
                      <option key={k} value={k}>
                        {k === "dashcam"
                          ? t("sourceDashcam")
                          : k === "survey"
                            ? t("sourceSurvey")
                            : k === "cctv"
                              ? t("sourceCctv")
                              : k === "uav"
                                ? t("sourceUav")
                                : t("sourceUnknown")}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" className="btn btn-blue" onClick={() => inputRef.current?.click()}>
                  {files.length ? t("addMoreImages") : t("pickImages")}
                </button>
                {files.length > 0 && (
                  <button type="button" className="btn btn-dark" disabled={busy} onClick={clearFiles}>
                    {t("clearFiles")}
                  </button>
                )}
                <button type="submit" disabled={busy || !files.length} className="btn btn-dark">
                  {busy ? t("measuring") : t("detect")}
                </button>
              </div>
            </div>

            <div className="side-stack">
              <div id="lidar-panel" className="card lidar-card">
                <div className="sample-label">{t("lidarTitle")}</div>
                <div className="upload-hint">{t("lidarHint")}</div>
                {lasFiles.length === 0 ? (
                  <div className="upload-hint">{t("lidarEmpty")}</div>
                ) : (
                  <ul className="lidar-list">
                    {lasFiles.map((file) => (
                      <li key={file.name}>
                        <span className={`lidar-tag ${file.layer}`}>{file.layer}</span>
                        {file.name}
                        <em>{file.points >= 0 ? file.points.toLocaleString() : "—"} pts</em>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="upload-hint">
                  {lidarMsg || (lasFiles.length ? t("lidarReady", { n: lasFiles.length }) : "")}
                </div>
                <div className="upload-actions">
                  <button type="button" className="btn btn-dark" disabled={lidarBusy || !lasFiles.length} onClick={() => void buildLidarViewer()}>
                    {lidarBusy ? t("lidarBuilding") : t("lidarBuild")}
                  </button>
                  <button
                    type="button"
                    className="btn btn-blue"
                    disabled={!lidarViewUrl}
                    onClick={() => window.open(lidarViewUrl || `${API}/lidar/view/scene_223582.html`, "_blank")}
                  >
                    {t("lidarOpen")}
                  </button>
                  <button type="button" className="btn btn-dark" disabled={qwenBusy || !lasFiles.length} onClick={() => void runQwen3d()}>
                    {qwenBusy ? t("lidarQwenBusy") : t("lidarQwen")}
                  </button>
                  <button
                    type="button"
                    className="btn btn-blue"
                    disabled={!qwenViewUrl}
                    onClick={() => window.open(qwenViewUrl, "_blank")}
                  >
                    {t("lidarQwenOpen")}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="main">
            <div className="viewer-col">
              <div className="view-switch">
                <button
                  type="button"
                  className={view === "eval" && !inspectItem ? "on" : ""}
                  disabled={!rec?.panel_data}
                  onClick={() => changeView("eval")}
                >
                  {t("viewEval")}
                </button>
                <button
                  type="button"
                  className={view === "deeplab" && !inspectItem ? "on" : ""}
                  disabled={!rec?.preview_data}
                  onClick={() => changeView("deeplab")}
                >
                  {t("viewDeepLab")}
                </button>
                <button
                  type="button"
                  className={view === "original" && !inspectItem ? "on" : ""}
                  disabled={!originalSrc}
                  onClick={() => changeView("original")}
                >
                  {t("viewOriginal")}
                </button>
                <button
                  type="button"
                  className={view === "raw" && !inspectItem ? "on" : ""}
                  disabled={!originalSrc}
                  onClick={() => changeView("raw")}
                >
                  {t("viewRaw")}
                </button>
              </div>
              <div className={shownImage ? "viewer has-img" : "viewer"}>
                <div className="tools">
                  <button type="button" title={t("zoomIn")} onClick={() => bumpZoom(zoom + 0.2)}>
                    <ZoomIn size={16} />
                  </button>
                  <button type="button" title={t("zoomOut")} onClick={() => bumpZoom(zoom - 0.2)}>
                    <ZoomOut size={16} />
                  </button>
                  <button type="button" title={t("resetView")} onClick={exitInspect}>
                    <RotateCcw size={16} />
                  </button>
                  <button
                    type="button"
                    title={t("zoomSelected")}
                    disabled={focusCrack == null}
                    onClick={() => focusCrack != null && toggleInspect(focusCrack)}
                  >
                    <Maximize2 size={16} />
                  </button>
                  <button type="button" title={t("download")} onClick={downloadPreview}>
                    <Download size={16} />
                  </button>
                </div>
                {inspectItem && crop && (
                  <button type="button" className="inspect-banner" onClick={exitInspect}>
                    {t("inspecting", { id: inspectItem.id })}
                    {sharpenNote ? ` · ${sharpenNote}` : ""}
                    {t("inspectHint")}
                  </button>
                )}
                <div
                  className={`stage${zoom > 1 ? " can-pan" : ""}${panning ? " panning" : ""}`}
                  onPointerDown={onStagePointerDown}
                  onPointerMove={onStagePointerMove}
                  onPointerUp={onStagePointerUp}
                  onPointerCancel={onStagePointerUp}
                  onDoubleClick={onStageDoubleClick}
                >
                  {inspectItem && crop && inspectSrc ? (
                    <div className="inspect-shell">
                    <div
                      className="inspect-frame"
                      style={{
                        ["--ar" as string]: String(crop.w / Math.max(crop.h, 1)),
                        width: `min(100%, calc(min(70vh, 640px) * ${crop.w / Math.max(crop.h, 1)}))`,
                        aspectRatio: `${crop.w} / ${crop.h}`,
                        transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                      }}
                    >
                      {sharpenSrc ? (
                        <img className="inspect-sharp" src={sharpenSrc} alt={t("altSharp", { id: inspectItem.id })} />
                      ) : (
                        <img
                          className="inspect-img"
                          src={inspectSrc}
                          alt={t("altInspect", { id: inspectItem.id })}
                          style={{
                            width: `${(srcSize.w / crop.w) * 100}%`,
                            height: `${(srcSize.h / crop.h) * 100}%`,
                            left: `${(-crop.x1 / crop.w) * 100}%`,
                            top: `${(-crop.y1 / crop.h) * 100}%`,
                          }}
                        />
                      )}
                      <div className="box-layer" onDoubleClick={() => toggleInspect(inspectItem.id)}>
                        <button
                          type="button"
                          className="box-hit on"
                          style={clampBoxPct(inspectItem.bbox!, crop)}
                          title={t("titleExit", { id: inspectItem.id })}
                          onDoubleClick={(ev) => {
                            ev.stopPropagation();
                            toggleInspect(inspectItem.id);
                          }}
                        >
                          <span className="box-tag">#{inspectItem.id}</span>
                        </button>
                      </div>
                    </div>
                    <aside className="box-caption">
                      <strong>{t("closeupTitle", { id: inspectItem.id })}</strong>
                      <CloseupLines fields={closeupFields} note={closeupNote || t("closeupBusy")} t={t} />
                    </aside>
                    </div>
                  ) : shownImage ? (
                    <div
                      key={`${rec?.image_name || "img"}-${view}`}
                      className="stage-photo"
                      style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
                    >
                      <img
                        src={shownImage}
                        className={view === "eval" ? "eval-full" : ""}
                        alt={
                          view === "raw"
                            ? t("altRaw", { name: rec?.image_name || "" })
                            : view === "original"
                              ? t("altOriginal", { name: rec?.image_name || "" })
                              : view === "eval"
                                ? t("altEval", { name: rec?.image_name || "" })
                                : t("altDeepLab", { name: rec?.image_name || "" })
                        }
                      />
                      {view !== "raw" && (
                      <div className="box-layer">
                        {instances.flatMap((item) =>
                          instanceHits(
                            item,
                            hitMode,
                            srcSize.w,
                            srcSize.h,
                            rec?.panel_layout || DEFAULT_PANEL,
                            hitMode === "flat" && view === "deeplab" ? previewCap : 0,
                          ).map((hit, idx) => (
                            <button
                              key={`${rec?.image_name || "img"}-${item.id}-${idx}`}
                              type="button"
                              className={
                                focusCrack === item.id
                                  ? "box-hit on"
                                  : hitMode === "panel"
                                    ? "box-hit ghost"
                                    : "box-hit"
                              }
                              style={{
                                left: `${hit.left}%`,
                                top: `${hit.top}%`,
                                width: `${hit.width}%`,
                                height: `${hit.height}%`,
                              }}
                              title={t("titleZoom", { id: item.id })}
                              onPointerDown={(ev) => ev.stopPropagation()}
                              onClick={() => pickCrack(item.id)}
                              onDoubleClick={(ev) => {
                                ev.stopPropagation();
                                toggleInspect(item.id);
                              }}
                            >
                              {hitMode === "flat" || focusCrack === item.id ? (
                                <span className="box-tag">#{item.id}</span>
                              ) : null}
                            </button>
                          )),
                        )}
                      </div>
                      )}
                    </div>
                  ) : (
                    <p className="stage-empty">
                      {t("emptyStage")}
                    </p>
                  )}
                </div>
              </div>
              {(rec?.panel_data || rec?.overlay_recall != null) && (
                <div className="eval-box">
                  <div className="eval-grid">
                    <div>
                      <b>{Number(rec.overlay_recall ?? 0).toFixed(2)}</b>
                      <span>Recall</span>
                    </div>
                    <div>
                      <b>{Number(rec.overlay_precision ?? 0).toFixed(2)}</b>
                      <span>Precision</span>
                    </div>
                    <div>
                      <b>{Number(rec.overlay_f1 ?? 0).toFixed(2)}</b>
                      <span>F1</span>
                    </div>
                    <div>
                      <b>{Number(rec.overlay_iou ?? 0).toFixed(2)}</b>
                      <span>IoU</span>
                    </div>
                  </div>
                  <p className="muted">
                    TP {rec.overlay_tp ?? "—"} · FP {rec.overlay_fp ?? "—"} · FN {rec.overlay_fn ?? "—"}
                  </p>
                  {(rec.overlay_quality_en || rec.overlay_quality_vi || rec.overlay_quality) && (
                    <p>
                      {localizeSheet(
                        lang === "en"
                          ? rec.overlay_quality_en || rec.overlay_quality || rec.overlay_quality_vi || ""
                          : rec.overlay_quality_vi || rec.overlay_quality || rec.overlay_quality_en || "",
                        t,
                      )}
                    </p>
                  )}
                </div>
              )}
              <div className="photo-tabs">
                <button
                  type="button"
                  className={photoTab === "hientruong" ? "photo-tab on" : "photo-tab"}
                  onClick={() => selectPhotoTab("hientruong")}
                >
                  {t("photoTabField")}
                  <span className="n">({fieldRecords.length})</span>
                </button>
                <button
                  type="button"
                  className={photoTab === "cancanh" ? "photo-tab on" : "photo-tab"}
                  onClick={() => selectPhotoTab("cancanh")}
                >
                  {t("photoTabClose")}
                  <span className="n">({closeRecords.length})</span>
                </button>
              </div>
              <div className="thumbs">
                {records.length === 0 && [0, 1, 2, 3, 4].map((i) => <div key={i} className="thumb-empty" />)}
                {records.length > 0 && thumbRecords.length === 0 && (
                  <p className="photo-tab-empty">{t("photoTabEmpty")}</p>
                )}
                {thumbRecords.map((item) => (
                  <button
                    key={`${item.image_name}-dl`}
                    type="button"
                    onClick={() => {
                      setFocusName(item.image_name);
                    }}
                  >
                    <img src={item.preview_data} alt={`DeepInspect ${item.image_name}`} className={item.image_name === rec?.image_name ? "on" : ""} />
                  </button>
                ))}
                {originalSrc && rec && thumbRecords.some((r) => r.image_name === rec.image_name) && (
                  <button
                    type="button"
                    onClick={() => {
                      setFocusName(rec.image_name);
                      changeView("original");
                    }}
                  >
                    <img src={originalSrc} alt={t("altOriginal", { name: rec.image_name })} className={view === "original" ? "on" : ""} />
                  </button>
                )}
                {rec?.panel_data && thumbRecords.some((r) => r.image_name === rec.image_name) && (
                  <button
                    type="button"
                    onClick={() => {
                      setFocusName(rec.image_name);
                      changeView("eval");
                    }}
                  >
                    <img src={rec.panel_data} alt={t("altEval", { name: rec.image_name })} className={view === "eval" ? "on" : ""} />
                  </button>
                )}
              </div>
            </div>

            <div className="card panel">
              <div>
                <div className="tabs">
                  {(
                    [
                      ["ketqua", t("tabResult")],
                      ["mota", t("tabDescribe")],
                      ["hoidap", t("tabChat")],
                      ["baocao", t("tabReport")],
                      ["lichsu", t("tabHistory")],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      disabled={id === "lichsu"}
                      onClick={() => setTab(id)}
                      className={tab === id ? "tab on" : "tab"}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {tab === "ketqua" && (
                  <>
                    <ConditionPanel condition={rec?.condition} t={t} />
                    <div className="kpis">
                      <div className="kpi kpi-red">
                        <div className="kpi-ico">
                          <TriangleAlert size={20} />
                        </div>
                        <div>
                          <div className="kpi-n">{rec ? counts.all : 0}</div>
                          <div className="kpi-l">{t("kpiAll")}</div>
                        </div>
                      </div>
                      <div className="kpi kpi-orange">
                        <div className="kpi-ico">
                          <AlertCircle size={20} />
                        </div>
                        <div>
                          <div className="kpi-n">{rec ? counts.mid : 0}</div>
                          <div className="kpi-l">{t("kpiMid")}</div>
                        </div>
                      </div>
                      <div className="kpi kpi-green">
                        <div className="kpi-ico">
                          <CheckCircle2 size={20} />
                        </div>
                        <div>
                          <div className="kpi-n">{rec ? counts.light : 0}</div>
                          <div className="kpi-l">{t("kpiLow")}</div>
                        </div>
                      </div>
                    </div>

                    <div className={`crack-box${cracksExpanded ? " expanded" : ""}`}>
                      <div className="crack-box-head">
                        <div className="block-title">{t("crackDetails")}</div>
                        {instances.length > 5 && (
                          <button
                            type="button"
                            className="crack-expand"
                            onClick={() => setCracksExpanded((open) => !open)}
                          >
                            {cracksExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                            {cracksExpanded ? t("collapse") : t("expandAll")}
                          </button>
                        )}
                      </div>
                      {instances.length === 0 && <p className="muted">{t("noCracks")}</p>}
                      {instances.length > 0 && (
                        <p className="muted">
                          {t("crackHint")}
                          {!cracksExpanded && instances.length > 5 ? t("crackHintMore", { n: instances.length }) : ""}
                        </p>
                      )}
                      {instances.length > 0 && (
                        <div ref={crackScrollRef} className="crack-scroll">
                          <div className="crack-scroll-inner">
                          {instances.map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              className={`${focusCrack === item.id ? "crack on" : "crack"}${inspectId === item.id ? " zoom" : ""}`}
                              onClick={() => pickCrack(item.id)}
                              onDoubleClick={() => toggleInspect(item.id)}
                            >
                              <div className="crack-left">
                                {item.crop_data ? (
                                  <img src={item.crop_data} alt={t("altCrack", { id: item.id })} />
                                ) : (
                                  <div className="crack-ph" />
                                )}
                                <div>
                                  <div className="crack-id">
                                    <span>#{item.id}</span>
                                    <span className={pillClass(item.level)}>{levelLabel(item.level, t)}</span>
                                  </div>
                                  <div className="crack-meta">
                                    <div>
                                      {t("length")}: <b>{measure(item.length_mm, item.length_px, 1)}</b>
                                    </div>
                                    <div>
                                      {t("width")}: <b>{measure(item.width_avg_mm, item.width_avg_px, 2)}</b>
                                    </div>
                                    <div>
                                      {t("direction")}: <b>{axisLabel(item.axis, t)}</b>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <div className="crack-score">
                                {(item.score ?? 0).toFixed(2)}
                                <div className="bar">
                                  <span style={{ width: `${Math.round((item.score ?? 0) * 100)}%`, background: barColor(item.level) }} />
                                </div>
                              </div>
                            </button>
                          ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="vlm">
                      <div className="vlm-h">
                        <div className="vlm-ico">
                          <Sparkles size={14} />
                        </div>
                        <span>{t("vlmTitle")}</span>
                      </div>
                      {busy ? (
                        <p>{t("vlmWaiting")}</p>
                      ) : (
                        <>
                          <SceneCaption rec={rec} lang={lang} t={t} />
                          <ReviewFields
                            rec={rec}
                            closeup={closeupFields}
                            closeupId={inspectId}
                            closeupNote={closeupNote}
                            t={t}
                          />
                        </>
                      )}
                      {(rec?.scene_reason || rec?.detector || rec?.exif_source) && (
                        <p className="meta">
                          {rec.scene_kind === "hientruong"
                            ? t("routeField")
                            : rec.scene_kind === "cancanh"
                              ? t("routeClose")
                              : rec.detector
                                ? t("modelLine", { name: rec.detector })
                                : ""}
                          {rec.scene_reason ? ` · ${localizeSceneReason(rec.scene_reason, t)}` : ""}
                          {rec.exif_source
                            ? t("gpsLine", {
                                gps: rec.lat != null ? `${rec.lat.toFixed(6)}, ${rec.lon?.toFixed(6)}` : "—",
                                src: rec.exif_source,
                              })
                            : ""}
                          {rec.length_mm != null ? t("lengthMm", { mm: rec.length_mm.toFixed(1) }) : ""}
                        </p>
                      )}
                    </div>
                  </>
                )}

                {tab === "mota" && (
                  <>
                    <SceneCaption rec={rec} lang={lang} t={t} />
                    <ReviewFields
                      rec={rec}
                      closeup={closeupFields}
                      closeupId={inspectId}
                      closeupNote={closeupNote}
                      t={t}
                    />
                  </>
                )}
                {tab === "hoidap" && (
                  <div className="chat">
                    <div className="vlm-h">
                      <div className="vlm-ico">
                        <MessageCircle size={14} />
                      </div>
                      <span>{t("chatTitle", { n: records.length })}</span>
                    </div>
                    <p className="muted">
                      {t("chatHint")}
                      {inspectId != null ? t("chatInspecting", { id: inspectId }) : ""}
                    </p>
                    <div className="chat-log">
                      {chatMsgs.length === 0 && <p className="muted">{t("chatEmpty")}</p>}
                      {chatMsgs.map((msg, i) => (
                        <div key={`${msg.role}-${i}`} className={msg.role === "user" ? "chat-msg me" : "chat-msg ai"}>
                          <b>{msg.role === "user" ? t("you") : "Qwen"}</b>
                          <p>{msg.role === "ai" ? localizeSheet(msg.text, t) : msg.text}</p>
                        </div>
                      ))}
                      {chatBusy ? <p className="muted">{t("chatReading")}</p> : null}
                    </div>
                    <div className="chat-form">
                      <input
                        value={chatInput}
                        onChange={(ev) => setChatInput(ev.target.value)}
                        onKeyDown={(ev) => {
                          if (ev.key === "Enter") {
                            ev.preventDefault();
                            void sendChat();
                          }
                        }}
                        placeholder={records.length ? t("chatPh") : t("chatNeedDetect")}
                        disabled={!records.length || chatBusy}
                      />
                      <button
                        type="button"
                        className="btn btn-blue"
                        disabled={!records.length || chatBusy || !chatInput.trim()}
                        onClick={() => void sendChat()}
                      >
                        {t("ask")}
                      </button>
                    </div>
                  </div>
                )}
                {tab === "baocao" && (
                  <pre className="report">
                    {localizeSheet(bundle?.report || bundle?.problem, t) || t("noReport")}
                  </pre>
                )}
              </div>

              <div className="actions">
                <div className="block-title">{t("proposedActions")}</div>
                <div className="action-row">
                  <div>
                    {instances.length === 0 && <p className="muted">{t("noActions")}</p>}
                    {summarizeActions(instances).map((group) => (
                      <label key={group.action} className="check">
                        <input type="checkbox" disabled checked={group.priority} readOnly />
                        <span>
                          {actionLabel(group.action, t)} — {t("cracksN", { n: group.ids.length })} (
                          {formatIdRange(group.ids, t)})
                        </span>
                      </label>
                    ))}
                  </div>
                  <button type="button" disabled className="btn btn-blue btn-lg">
                    <FileText size={16} />
                    {t("pdf")}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
