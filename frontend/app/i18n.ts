export type Lang = "vi" | "en";

const vi = {
  brandSub: "VLM – Hệ thống báo cáo vết nứt cơ sở hạ tầng",
  notify: "Thông báo",
  roleAdmin: "Quản trị viên",
  navHome: "Trang chủ",
  navAnalyze: "Phân tích ảnh",
  navVideo: "Video/Camera",
  navReport: "Báo cáo",
  navHistory: "Lịch sử",
  navStats: "Thống kê",
  navSettings: "Cài đặt",
  modelOn: "● Đang hoạt động",
  dropTitle: "Kéo thả ảnh vào đây hoặc chọn file",
  dropHint: "Hỗ trợ: JPG, PNG — chọn nhiều ảnh; có thể chọn thêm lần nữa (Conglo + LCW)",
  altCrack: "Vết nứt #{id}",
  enCaptionFallback: "(Chưa có bản tiếng Anh — đang hiện bản đã dịch từng phần từ tiếng Việt)",
  reasonNameClose: "Tên file gần cận ({name})",
  reasonNameField: "Tên file hiện trường ({name})",
  reasonCvField: "CV hiện trường (score={score}: {why})",
  reasonCvClose: "CV cận cảnh (score={score}: {why})",
  reasonFallbackSize: "Fallback kích thước {size}",
  reasonSkewField: "cấu trúc vùng lệch (hiện trường)",
  reasonUniformClose: "texture đều đầy khung (cận)",
  reasonLightSplit: "chênh sáng trên/dưới",
  reasonLongStructure: "đường kết cấu dài",
  reasonSmoothEdges: "mép mịn phủ khung",
  reasonGraySurface: "bề mặt xám đồng nhất",
  reasonLowCoarse: "ít cấu trúc thô",
  reasonHighCoarse: "cấu trúc thô mạnh",
  reasonSmallCrop: "ảnh nhỏ/crop",
  reasonDefault: "điểm phân loại",
  qRecHigh: "Recall cao: ít bỏ sót vết thật (FN ít)",
  qRecMid: "Recall trung bình: còn bỏ sót một phần",
  qRecLow: "Recall thấp: bỏ sót nhiều pixel nứt",
  qPrecOk: "Precision khá: ít tô thừa",
  qPrecLow: "Precision thấp: nhiều pixel thừa (FP) — LCW hay tô rộng hơn nhãn",
  qPrecVeryLow: "Precision rất thấp: mask dự đoán rộng hơn nhãn nhiều",
  qOverall: "Tổng thể F1={f1}, IoU={iou} (TP {tp}, FP {fp}, FN {fn}).",
  qPrecWarn: "Không kết luận chỉ từ precision.",
  termCrack: "vết nứt",
  termConcrete: "bê tông",
  termBridge: "cầu",
  termPier: "trụ",
  termDeck: "bản mặt cầu",
  termBeam: "dầm",
  termColumn: "cột",
  termAbutment: "mố",
  termSlab: "bản",
  termWall: "tường",
  termSurface: "bề mặt",
  termSpalling: "bong tróc",
  termCorrosion: "ăn mòn",
  termSeepage: "thấm nước",
  termField: "hiện trường",
  termCloseup: "cận cảnh",
  sevLow: "Thấp",
  sevMedium: "Trung bình",
  sevHigh: "Cao",
  sevCritical: "Nghiêm trọng",
  filesChosen: "Đã chọn {n} ảnh: {names}",
  clearFiles: "Xóa danh sách",
  busyAnalyze: "VLM đang kiểm tra…",
  pickImages: "Chọn ảnh",
  addMoreImages: "Thêm ảnh",
  detect: "Phát hiện",
  measuring: "Đang đo…",
  samples: "Ảnh mẫu:",
  condSupported: "Supported",
  condUnresolved: "Unresolved",
  condResolved: "Resolved",
  condRefer: "Refer",
  condGrade: "Mức điều kiện",
  condAssessments: "{n} đánh giá VLM",
  pipeHint: "Bấm từng bước trên pipeline để xem chi tiết.",
  pipeDetect: "DeepInspect",
  pipeAssess: "Assessor",
  pipeSupervisor: "Supervisor",
  pipePm: "PM",
  pipeFinal: "Final",
  pipeSkipped: "bỏ qua",
  pipeDetectHint: "Gợi ý mức từ detector",
  pipeNoAssess: "Không có đánh giá VLM (chế độ nhanh).",
  pipeDecision: "Quyết định",
  pipeAction: "Hành động",
  pipeStatus: "Trạng thái",
  pipeNoNote: "Không có ghi chú ngắn.",
  pipePmSkipHint: "Supervisor đã supported — không gọi PM.",
  captionTitle: "Mô tả hiện trường",
  description: "Mô tả",
  time: "Thời điểm",
  gps: "GPS",
  none: "không có",
  source: "Nguồn ảnh",
  sourceDashcam: "Dashcam",
  sourceSurvey: "Khảo sát mặt đường",
  sourceCctv: "Camera giám sát",
  sourceUav: "UAV",
  sourceUnknown: "Không rõ",
  structureTitle: "Phân tích kết cấu",
  structuralElement: "Cấu kiện (structural_element)",
  defectType: "Loại hư hỏng (defect_type)",
  severityLevel: "Mức độ (severity_level)",
  locationDescription: "Vị trí (location_description)",
  recommendedAction: "Đề xuất (recommended_action)",
  navLidar: "LiDAR 3D",
  navDarwin: "Darwin Map",
  lidarTitle: "LiDAR điểm thật (.las)",
  lidarHint: "Scene 223582 · tree / wires / powerline",
  lidarBuild: "Build viewer",
  lidarBuilding: "Đang nạp điểm…",
  lidarOpen: "Mở 3D",
  lidarEmpty: "Chưa có file .las trong Data/223582",
  lidarReady: "{n} lớp · bấm Build rồi Mở 3D",
  lidarQwen: "Qwen 3D",
  lidarQwenBusy: "Qwen đang sinh scene…",
  lidarQwenOpen: "Mở Qwen HTML",
  viewEval: "Ô 4 (TP/FP/FN)",
  viewDeepLab: "DeepInspect",
  viewOriginal: "Ảnh gốc",
  viewRaw: "Raw",
  zoomIn: "Phóng to",
  zoomOut: "Thu nhỏ",
  resetView: "Khôi phục",
  zoomSelected: "Phóng to vết đang chọn",
  download: "Tải xuống",
  inspecting: "Đang phóng to vết #{id}",
  inspectHint: " — đúp lại hoặc bấm đây để về ảnh đầy đủ",
  altSharp: "Nét vết #{id}",
  altInspect: "Phóng to vết #{id}",
  titleExit: "#{id} — đúp để về ảnh đầy đủ",
  titleZoom: "#{id} — đúp để phóng to",
  closeupTitle: "Ảnh cận #{id}",
  altOriginal: "Ảnh gốc {name}",
  altRaw: "Raw {name}",
  altEval: "Ô 4 {name}",
  altDeepLab: "DeepInspect {name}",
  emptyStage: "Ảnh nhận diện DeepInspect hiện ở đây sau khi bấm Phát hiện. Bấm Ảnh gốc để xem file upload.",
  tabResult: "Kết quả phân tích",
  tabDescribe: "Mô tả chi tiết (VLM)",
  tabChat: "Hỏi đáp",
  tabReport: "Báo cáo",
  tabHistory: "Lịch sử",
  kpiAll: "Vết nứt được phát hiện",
  kpiMid: "Mức độ trung bình",
  kpiLow: "Mức độ nhẹ",
  crackDetails: "Chi tiết từng vết nứt",
  collapse: "Thu gọn",
  expandAll: "Phóng to hết",
  noCracks: "Chưa có vết trên mask.",
  crackHint: "Bấm để khoanh box. Đúp để phóng to.",
  crackHintMore: " Hiện 5/{n} — cuộn để xem tiếp.",
  length: "Chiều dài",
  width: "Chiều rộng",
  direction: "Hướng",
  vlmTitle: "Nhận xét & đề xuất (sinh bởi VLM)",
  vlmWaiting: "Đang chờ VLM sau khi gỡ DeepInspect.",
  routeField: "VLM: hiện trường → LCW",
  routeClose: "VLM: cận cảnh → Conglomerate",
  modelLine: "Model: {name}",
  gpsLine: " · GPS {gps} · nguồn {src}",
  lengthMm: " · dài {mm} mm",
  chatTitle: "Hỏi đáp cả phiên · {n} ảnh",
  chatHint: "Ví dụ: hiện trường nào nguy cơ cao? tại sao mức cao? 2 ảnh ấy là hiện trường gì?",
  chatInspecting: " Đang phóng to vết #{id}.",
  chatEmpty: "Chưa có câu hỏi. Hỏi về mọi ảnh đã phát hiện trong phiên.",
  you: "Bạn",
  chatReading: "Đang đọc phiếu đo…",
  chatPh: "Hỏi về các vết nứt trong phiên…",
  chatNeedDetect: "Cần Phát hiện ảnh trước",
  ask: "Hỏi",
  noReport: "Chưa có báo cáo.",
  proposedActions: "Hành động đề xuất:",
  noActions: "Không có đề xuất nứt.",
  cracksN: "{n} vết",
  pdf: "Tạo báo cáo PDF",
  levelHigh: "Nguy hiểm (Cao)",
  levelMid: "Trung bình",
  levelLow: "Nhẹ",
  axisH: "ngang",
  axisV: "dọc",
  actionWatch: "theo dõi định kỳ",
  actionPriority: "kiểm tra hiện trường ưu tiên",
  actionDetail: "kiểm tra chi tiết",
  actionSeal: "xử lý chống thấm",
  actionStruct: "đánh giá kết cấu tổng thể",
  closeupWait: "Đang chờ Qwen mô tả ảnh cận…",
  closeupDetail: "Mô tả chi tiết",
  closeupRisk: "Mức ảnh hưởng",
  closeupPos: "Vị trí trên bề mặt",
  noVlm: "Chưa có mô tả VLM.",
  reviewObject: "Đối tượng khảo sát / Vị trí",
  reviewCount: "Tổng quan số lượng",
  reviewFocus: "Chi tiết vết nứt trọng điểm (Vết nứt #{id})",
  reviewSize: "Kích thước ước tính: chiều dài {length}; chiều rộng {width}.",
  reviewAxis: "Đặc điểm hình học / Hướng phát triển: {axis}.",
  reviewRisk: "Đánh giá mức độ ảnh hưởng / Rủi ro: {risk}.",
  reviewCloseup: "Mô tả ảnh cận (vết #{id})",
  reviewOthers: "Nhận định tình trạng chung cho các vết nứt phụ",
  reviewActions: "Hành động đề xuất / Khuyến nghị",
  errSize: "Không đọc được kích thước ảnh.",
  errAnalyze: "Không phân tích được.",
  errNeedFile: "Chọn ít nhất một ảnh.",
  errChat: "Chưa hỏi được.",
  noAnswer: "Không có câu trả lời.",
  sharpening: "Đang làm nét rồi phóng 4 lần…",
  sharpOk: "Làm nét vùng rộng + phóng 4 lần",
  sharpFail: "Không chạy được Real-ESRGAN, hiện crop gốc. {err}",
  sharpCrop: "Hiện crop gốc",
  sharpErr: "Không làm nét được.",
  closeupQwen: "Qwen3-VL vừa mô tả crop.",
  closeupCached: "Mô tả ảnh cận (đã lưu).",
  closeupErr: "Qwen chưa mô tả được ảnh cận.",
  closeupBusy: "Qwen đang xem crop…",
  langVi: "Tiếng Việt",
  langEn: "English",
  darwinTitle: "Darwin vệ tinh + LiDAR 3D",
  darwinSub: "Point cloud WebGL · bearing {bearing} · pitch {pitch}",
  darwinPts: " · {n} pts",
  darwinBack: "← Phân tích ảnh",
  darwinHideLidar: "Ẩn LiDAR",
  darwinShowLidar: "Hiện LiDAR",
  darwinZoomLidar: "Zoom LiDAR",
  darwinTopDown: "Nhìn thẳng",
  darwinTilt70: "Nghiêng 70°",
  darwinIntensity: "Intensity (CC)",
  darwinHeight: "Cao độ",
  darwinExag: "Cao ×{n}",
  darwinRebuild: "Rebuild",
  darwinRebuilding: "Đang nạp…",
  darwinHint:
    "LiDAR 3D: quay lại trang sẽ dùng cache RAM (không tải lại 2M điểm).",
  darwinInit: "Đang khởi tạo bản đồ…",
  darwinLoading: "Esri Imagery · đang nạp LiDAR 3D (lần đầu hơi lâu)…",
  darwinCacheAttach: "Bản đồ OK · gắn lại LiDAR từ cache…",
  darwinReady: "LiDAR 3D · {mode} · {n} pts",
  darwinReadyCache: "LiDAR 3D · {mode} · {n} pts · cache RAM",
  darwinRebuildOk: "{mode} · {n} điểm (rebuild)",
  darwinModeIntensity: "Intensity",
  darwinModeHeight: "Cao độ",
  darwinSampling: "Đang sample lại LAS (3D)…",
  darwinZoomGps: "Zoom GPS ảnh",
  darwinGpsPts: " · {n} GPS",
  darwinGpsReady: "GPS ảnh conglo · {n} điểm trên bản đồ",
  darwinGpsNone: "Chưa có GPS từ phiên phân tích",
  darwinGpsPopupCrack: "{n} vết nứt",
  darwinGpsPopupNone: "Không phát hiện nứt",
  darwinGpsAddress: "Địa chỉ",
  darwinLicense: "License data",
  darwinLicenseOrg: "CivilTech Solution",
  gpsOnDarwin: "Đã đọc GPS · xem trên Darwin 3D ({n})",
  countText: "Phát hiện tổng cộng {n} vết nứt.",
  noOthers: "Không có vết nứt phụ.",
  othersText:
    "Vết nứt {ids}: {hi} cao, {mid} trung bình, {lo} nhẹ — mức độ hiện tại chủ yếu trung bình/nhẹ, chưa có dấu hiệu nguy hiểm ngay.",
  noMm: "chưa có tỷ lệ mm",
  notMeasured: "chưa đo",
  axisUnknown: "Chưa rõ hướng",
  axisHFull: "Phương ngang",
  axisVFull: "Phương dọc",
  riskHigh: "Ảnh hưởng đến kết cấu, mức độ nguy hiểm cao",
  riskMid: "Ảnh hưởng cục bộ, mức độ nguy hiểm trung bình",
  riskLow: "Chưa có dấu hiệu nguy hiểm ngay, mức độ nhẹ",
  objColumn: "Cột / bệ bê tông (ảnh hiện trường)",
  objSurface: "Bề mặt bê tông (ảnh cận)",
  fieldPhoto: "ảnh hiện trường",
  closePhoto: "ảnh cận",
  photoTabField: "Ảnh hiện trường",
  photoTabClose: "Ảnh cận cảnh",
  photoTabEmpty: "Không có ảnh trong nhóm này.",
  actDetailCrack: "Kiểm tra chi tiết — vết nứt #{id}",
  actWatchRest: "Theo dõi định kỳ — {n} vết còn lại",
  actSealIf: "Xử lý chống thấm — chỉ khi có dấu hiệu ẩm/thấm",
  actStructNew: "Đánh giá kết cấu tổng thể nếu xuất hiện vết mới",
} as const;

const en: Record<keyof typeof vi, string> = {
  brandSub: "VLM – Infrastructure crack reporting system",
  notify: "Notifications",
  roleAdmin: "Administrator",
  navHome: "Home",
  navAnalyze: "Image analysis",
  navVideo: "Video/Camera",
  navReport: "Reports",
  navHistory: "History",
  navStats: "Statistics",
  navSettings: "Settings",
  modelOn: "● Online",
  dropTitle: "Drop images here or choose files",
  dropHint: "Supported: JPG, PNG — multi-select; pick again to add more (Conglo + LCW)",
  altCrack: "Crack #{id}",
  enCaptionFallback: "(No English caption yet — showing partially localized Vietnamese text)",
  reasonNameClose: "Filename looks like a close-up ({name})",
  reasonNameField: "Filename looks like a field scene ({name})",
  reasonCvField: "CV field scene (score={score}: {why})",
  reasonCvClose: "CV close-up (score={score}: {why})",
  reasonFallbackSize: "Size fallback {size}",
  reasonSkewField: "uneven regional structure (field)",
  reasonUniformClose: "uniform full-frame texture (close-up)",
  reasonLightSplit: "top/bottom brightness split",
  reasonLongStructure: "long structural lines",
  reasonSmoothEdges: "smooth edges filling the frame",
  reasonGraySurface: "uniform gray surface",
  reasonLowCoarse: "little coarse structure",
  reasonHighCoarse: "strong coarse structure",
  reasonSmallCrop: "small image/crop",
  reasonDefault: "classifier score",
  qRecHigh: "High recall: few missed true cracks (low FN)",
  qRecMid: "Medium recall: some true cracks still missed",
  qRecLow: "Low recall: many crack pixels missed",
  qPrecOk: "Decent precision: little over-paint",
  qPrecLow: "Low precision: many false pixels (FP) — LCW often paints wider than labels",
  qPrecVeryLow: "Very low precision: prediction mask much wider than labels",
  qOverall: "Overall F1={f1}, IoU={iou} (TP {tp}, FP {fp}, FN {fn}).",
  qPrecWarn: "Do not judge from precision alone.",
  termCrack: "crack",
  termConcrete: "concrete",
  termBridge: "bridge",
  termPier: "pier",
  termDeck: "bridge deck",
  termBeam: "beam",
  termColumn: "column",
  termAbutment: "abutment",
  termSlab: "slab",
  termWall: "wall",
  termSurface: "surface",
  termSpalling: "spalling",
  termCorrosion: "corrosion",
  termSeepage: "seepage",
  termField: "field scene",
  termCloseup: "close-up",
  sevLow: "Low",
  sevMedium: "Medium",
  sevHigh: "High",
  sevCritical: "Critical",
  filesChosen: "Selected {n} images: {names}",
  clearFiles: "Clear list",
  busyAnalyze: "VLM is checking…",
  pickImages: "Choose images",
  addMoreImages: "Add images",
  detect: "Detect",
  measuring: "Measuring…",
  samples: "Samples:",
  condSupported: "Supported",
  condUnresolved: "Unresolved",
  condResolved: "Resolved",
  condRefer: "Refer",
  condGrade: "Condition grade",
  condAssessments: "{n} VLM assessments",
  pipeHint: "Click a pipeline step for details.",
  pipeDetect: "DeepInspect",
  pipeAssess: "Assessor",
  pipeSupervisor: "Supervisor",
  pipePm: "PM",
  pipeFinal: "Final",
  pipeSkipped: "skipped",
  pipeDetectHint: "Detector grade hint",
  pipeNoAssess: "No VLM assessments (fast mode).",
  pipeDecision: "Decision",
  pipeAction: "Action",
  pipeStatus: "Status",
  pipeNoNote: "No short note.",
  pipePmSkipHint: "Supervisor already supported — PM skipped.",
  captionTitle: "Scene description",
  description: "Description",
  time: "Captured",
  gps: "GPS",
  none: "none",
  source: "Image source",
  sourceDashcam: "Dashcam",
  sourceSurvey: "Road survey",
  sourceCctv: "CCTV",
  sourceUav: "UAV",
  sourceUnknown: "Unknown",
  structureTitle: "Structure analysis",
  structuralElement: "Structural element",
  defectType: "Defect type",
  severityLevel: "Severity",
  locationDescription: "Location",
  recommendedAction: "Recommended action",
  navLidar: "LiDAR 3D",
  navDarwin: "Darwin Map",
  lidarTitle: "Real LiDAR points (.las)",
  lidarHint: "Scene 223582 · tree / wires / powerline",
  lidarBuild: "Build viewer",
  lidarBuilding: "Loading points…",
  lidarOpen: "Open 3D",
  lidarEmpty: "No .las files under Data/223582",
  lidarReady: "{n} layers · Build then Open 3D",
  lidarQwen: "Qwen 3D",
  lidarQwenBusy: "Qwen generating…",
  lidarQwenOpen: "Open Qwen HTML",
  viewEval: "Panel 4 (TP/FP/FN)",
  viewDeepLab: "DeepInspect",
  viewOriginal: "Original",
  viewRaw: "Raw",
  zoomIn: "Zoom in",
  zoomOut: "Zoom out",
  resetView: "Reset",
  zoomSelected: "Zoom selected crack",
  download: "Download",
  inspecting: "Zooming crack #{id}",
  inspectHint: " — double-click or press here to return",
  altSharp: "Sharpened crack #{id}",
  altInspect: "Zoom crack #{id}",
  titleExit: "#{id} — double-click to return",
  titleZoom: "#{id} — double-click to zoom",
  closeupTitle: "Close-up #{id}",
  altOriginal: "Original {name}",
  altRaw: "Raw {name}",
  altEval: "Panel 4 {name}",
  altDeepLab: "DeepInspect {name}",
  emptyStage: "The DeepInspect overlay appears here after Detect. Use Original to see the upload.",
  tabResult: "Analysis results",
  tabDescribe: "Detailed description (VLM)",
  tabChat: "Q&A",
  tabReport: "Report",
  tabHistory: "History",
  kpiAll: "Cracks detected",
  kpiMid: "Medium severity",
  kpiLow: "Low severity",
  crackDetails: "Crack details",
  collapse: "Collapse",
  expandAll: "Expand all",
  noCracks: "No cracks on the mask.",
  crackHint: "Click to highlight. Double-click to zoom.",
  crackHintMore: " Showing 5/{n} — scroll for more.",
  length: "Length",
  width: "Width",
  direction: "Direction",
  vlmTitle: "Assessment & recommendations (VLM)",
  vlmWaiting: "Waiting for VLM after unloading DeepInspect.",
  routeField: "VLM: field scene → LCW",
  routeClose: "VLM: close-up → Conglomerate",
  modelLine: "Model: {name}",
  gpsLine: " · GPS {gps} · source {src}",
  lengthMm: " · length {mm} mm",
  chatTitle: "Session Q&A · {n} images",
  chatHint: "e.g. which site is high risk? why is it high? what are those two sites?",
  chatInspecting: " Zooming crack #{id}.",
  chatEmpty: "No questions yet. Ask about any analyzed image in this session.",
  you: "You",
  chatReading: "Reading the measurement sheet…",
  chatPh: "Ask about cracks in this session…",
  chatNeedDetect: "Detect images first",
  ask: "Ask",
  noReport: "No report yet.",
  proposedActions: "Suggested actions:",
  noActions: "No crack actions.",
  cracksN: "{n} cracks",
  pdf: "Create PDF report",
  levelHigh: "High risk",
  levelMid: "Medium",
  levelLow: "Low",
  axisH: "horizontal",
  axisV: "vertical",
  actionWatch: "periodic monitoring",
  actionPriority: "priority field inspection",
  actionDetail: "detailed inspection",
  actionSeal: "waterproofing if needed",
  actionStruct: "overall structural review",
  closeupWait: "Waiting for Qwen to describe the crop…",
  closeupDetail: "Detailed description",
  closeupRisk: "Severity",
  closeupPos: "Position on the surface",
  noVlm: "No VLM description yet.",
  reviewObject: "Survey object / location",
  reviewCount: "Crack count",
  reviewFocus: "Primary crack details (crack #{id})",
  reviewSize: "Estimated size: length {length}; width {width}.",
  reviewAxis: "Geometry / growth direction: {axis}.",
  reviewRisk: "Impact / risk: {risk}.",
  reviewCloseup: "Close-up description (crack #{id})",
  reviewOthers: "Notes on remaining cracks",
  reviewActions: "Recommended actions",
  errSize: "Could not read image size.",
  errAnalyze: "Analysis failed.",
  errNeedFile: "Choose at least one image.",
  errChat: "Could not send the question.",
  noAnswer: "No answer.",
  sharpening: "Sharpening and upscaling ×4…",
  sharpOk: "Wide-area sharpen + 4× upscale",
  sharpFail: "Real-ESRGAN failed, showing original crop. {err}",
  sharpCrop: "Showing original crop",
  sharpErr: "Could not sharpen.",
  closeupQwen: "Qwen3-VL just described the crop.",
  closeupCached: "Close-up description (cached).",
  closeupErr: "Qwen could not describe the crop.",
  closeupBusy: "Qwen is reading the crop…",
  langVi: "Vietnamese",
  langEn: "English",
  darwinTitle: "Darwin Satellite + LiDAR 3D",
  darwinSub: "Point cloud WebGL · bearing {bearing} · pitch {pitch}",
  darwinPts: " · {n} pts",
  darwinBack: "← Image analysis",
  darwinHideLidar: "Hide LiDAR",
  darwinShowLidar: "Show LiDAR",
  darwinZoomLidar: "Zoom LiDAR",
  darwinTopDown: "Top-down",
  darwinTilt70: "Tilt 70°",
  darwinIntensity: "Intensity (CC)",
  darwinHeight: "Elevation",
  darwinExag: "Height ×{n}",
  darwinRebuild: "Rebuild",
  darwinRebuilding: "Loading…",
  darwinHint:
    "3D LiDAR: returning to this page uses the RAM cache (no 2M-point reload).",
  darwinInit: "Initializing map…",
  darwinLoading: "Esri Imagery · loading 3D LiDAR (first load may take a while)…",
  darwinCacheAttach: "Map ready · re-attaching LiDAR from cache…",
  darwinReady: "LiDAR 3D · {mode} · {n} pts",
  darwinReadyCache: "LiDAR 3D · {mode} · {n} pts · RAM cache",
  darwinRebuildOk: "{mode} · {n} points (rebuild)",
  darwinModeIntensity: "Intensity",
  darwinModeHeight: "Elevation",
  darwinSampling: "Re-sampling LAS (3D)…",
  darwinZoomGps: "Zoom photo GPS",
  darwinGpsPts: " · {n} GPS",
  darwinGpsReady: "Conglo photo GPS · {n} points on map",
  darwinGpsNone: "No GPS in the current analyze session",
  darwinGpsPopupCrack: "{n} cracks",
  darwinGpsPopupNone: "No cracks detected",
  darwinGpsAddress: "Address",
  darwinLicense: "License data",
  darwinLicenseOrg: "CivilTech Solution",
  gpsOnDarwin: "GPS captured · view on Darwin 3D ({n})",
  countText: "Detected {n} cracks in total.",
  noOthers: "No secondary cracks.",
  othersText:
    "Cracks {ids}: {hi} high, {mid} medium, {lo} low — mostly medium/low, no immediate danger.",
  noMm: "no mm scale",
  notMeasured: "not measured",
  axisUnknown: "Direction unclear",
  axisHFull: "Horizontal",
  axisVFull: "Vertical",
  riskHigh: "Structural impact, high risk",
  riskMid: "Localized impact, medium risk",
  riskLow: "No immediate danger, low severity",
  objColumn: "Concrete column / pedestal (field photo)",
  objSurface: "Concrete surface (close-up)",
  fieldPhoto: "field photo",
  closePhoto: "close-up",
  photoTabField: "Field photos",
  photoTabClose: "Close-ups",
  photoTabEmpty: "No photos in this group.",
  actDetailCrack: "Detailed inspection — crack #{id}",
  actWatchRest: "Periodic monitoring — {n} remaining cracks",
  actSealIf: "Waterproofing — only if moisture/seepage is present",
  actStructNew: "Overall structural review if new cracks appear",
};

export type Msg = keyof typeof vi;

export type TFn = (key: Msg, vars?: Record<string, string | number>) => string;

export function makeT(lang: Lang): TFn {
  const dict = lang === "en" ? en : vi;
  return (key, vars) => {
    let text = dict[key] || vi[key];
    if (vars) {
      for (const [name, value] of Object.entries(vars)) {
        text = text.replaceAll(`{${name}}`, String(value));
      }
    }
    return text;
  };
}

export function levelLabel(level: string | undefined, t: TFn) {
  if (level === "cao") return t("levelHigh");
  if (level === "trung bình") return t("levelMid");
  if (level === "nhẹ") return t("levelLow");
  return "—";
}

export function axisLabel(axis: string | undefined, t: TFn) {
  const raw = (axis || "").toLowerCase();
  if (raw.startsWith("ngang") || raw.startsWith("horiz")) return t("axisH");
  if (raw.startsWith("dọc") || raw.startsWith("doc") || raw.startsWith("vert")) return t("axisV");
  return axis || "—";
}

export function actionLabel(action: string | undefined, t: TFn) {
  const text = action || "theo dõi định kỳ";
  const raw = text.toLowerCase();
  const id = text.match(/#\s*(\d+)/)?.[1];
  const rest = text.match(/(\d+)\s+vết còn lại/i)?.[1];
  if (raw.includes("ưu tiên") || raw.includes("priority")) return t("actionPriority");
  if ((raw.includes("chi tiết") || raw.includes("detailed")) && id) return t("actDetailCrack", { id });
  if (raw.includes("chi tiết") || raw.includes("detailed")) return t("actionDetail");
  if (raw.includes("ẩm") || raw.includes("seepage")) return t("actSealIf");
  if (raw.includes("chống thấm") || raw.includes("waterproof")) return t("actionSeal");
  if (raw.includes("vết mới") || raw.includes("new crack")) return t("actStructNew");
  if (raw.includes("kết cấu") || raw.includes("structural")) return t("actionStruct");
  if ((raw.includes("theo dõi") || raw.includes("monitor")) && rest) return t("actWatchRest", { n: rest });
  if (raw.includes("theo dõi") || raw.includes("monitor")) return t("actionWatch");
  return localizeSheet(text, t);
}

const REASON_CODE_KEYS: Record<string, Msg> = {
  skew_field: "reasonSkewField",
  uniform_close: "reasonUniformClose",
  light_split: "reasonLightSplit",
  long_structure: "reasonLongStructure",
  smooth_edges: "reasonSmoothEdges",
  gray_surface: "reasonGraySurface",
  low_coarse: "reasonLowCoarse",
  high_coarse: "reasonHighCoarse",
  small_crop: "reasonSmallCrop",
  default: "reasonDefault",
};

export function localizeSceneReason(reason: string | undefined, t: TFn): string {
  if (!reason) return "";
  let s = localizeSheet(reason, t);
  const nameClose = s.match(/^name_close:(.+)$/i);
  if (nameClose) return t("reasonNameClose", { name: nameClose[1] });
  const nameField = s.match(/^name_field:(.+)$/i);
  if (nameField) return t("reasonNameField", { name: nameField[1] });
  const fallback = s.match(/^fallback_size:(.+)$/i);
  if (fallback) return t("reasonFallbackSize", { size: fallback[1] });
  const cv = s.match(/^cv_(field|close):([^:]+):(.*)$/i);
  if (cv) {
    const kind = cv[1].toLowerCase();
    const score = cv[2];
    const why = cv[3]
      .split(",")
      .map((code) => {
        const key = REASON_CODE_KEYS[code.trim()];
        return key ? t(key) : code.trim();
      })
      .filter(Boolean)
      .join(", ");
    return kind === "field"
      ? t("reasonCvField", { score, why: why || t("reasonDefault") })
      : t("reasonCvClose", { score, why: why || t("reasonDefault") });
  }
  return s;
}

export function localizeSeverity(level: string | undefined, t: TFn): string {
  const raw = String(level || "").trim().toLowerCase();
  if (!raw) return t("none");
  if (raw === "low" || raw === "thấp" || raw === "nhe" || raw === "nhẹ") return t("sevLow");
  if (raw === "medium" || raw === "trung bình" || raw === "trung binh" || raw === "moderate")
    return t("sevMedium");
  if (raw === "high" || raw === "cao") return t("sevHigh");
  if (raw === "critical" || raw === "nghiêm trọng" || raw === "nghiem trong") return t("sevCritical");
  return localizeSheet(level, t);
}

export function localizeSheet(text: string | undefined, t: TFn): string {
  if (!text) return "";
  let s = text;
  s = s.replace(/Phát hiện tổng cộng\s+(\d+)\s+vết nứt\.?/gi, (_, n) => t("countText", { n }));
  s = s.replace(
    /Vết nứt\s+([^:]+):\s*(\d+)\s+cao,\s*(\d+)\s+trung\s*bình,\s*(\d+)\s+nhẹ\s*—\s*mức độ hiện tại chủ yếu trung bình\/nhẹ, chưa có dấu hiệu nguy hiểm ngay\./gi,
    (_, ids, hi, mid, lo) => t("othersText", { ids, hi, mid, lo }),
  );
  s = s.replace(/Không có vết nứt phụ\.?/gi, t("noOthers"));
  s = s.replace(/Cột\s*\/\s*bệ bê tông \(ảnh hiện trường\)/gi, t("objColumn"));
  s = s.replace(/Bề mặt bê tông \(ảnh cận\)/gi, t("objSurface"));
  s = s.replace(/Kiểm tra chi tiết\s*—\s*vết nứt\s*#(\d+)/gi, (_, id) => t("actDetailCrack", { id }));
  s = s.replace(/Theo dõi định kỳ\s*—\s*(\d+)\s+vết còn lại/gi, (_, n) => t("actWatchRest", { n }));
  s = s.replace(/Xử lý chống thấm\s*—\s*chỉ khi có dấu hiệu ẩm\/thấm/gi, t("actSealIf"));
  s = s.replace(/Đánh giá kết cấu tổng thể nếu xuất hiện vết mới/gi, t("actStructNew"));
  s = s.replace(/Đánh giá kết cấu tổng thể/gi, t("actionStruct"));
  s = s.replace(/Theo dõi định kỳ/gi, t("actionWatch"));
  s = s.replace(/Kiểm tra chi tiết/gi, t("actionDetail"));
  s = s.replace(/Kiểm tra hiện trường ưu tiên/gi, t("actionPriority"));
  s = s.replace(/Ảnh hưởng đến kết cấu, mức độ nguy hiểm cao/gi, t("riskHigh"));
  s = s.replace(/Ảnh hưởng cục bộ, mức độ nguy hiểm trung bình/gi, t("riskMid"));
  s = s.replace(/Chưa có dấu hiệu nguy hiểm ngay, mức độ nhẹ/gi, t("riskLow"));
  s = s.replace(/chưa có tỷ lệ mm/gi, t("noMm"));
  s = s.replace(/\bchưa đo\b/gi, t("notMeasured"));
  s = s.replace(/Phương ngang/gi, t("axisHFull"));
  s = s.replace(/Phương dọc/gi, t("axisVFull"));
  s = s.replace(/Chưa rõ hướng/gi, t("axisUnknown"));
  s = s.replace(/\(ảnh hiện trường\)/gi, `(${t("fieldPhoto")})`);
  s = s.replace(/\(ảnh cận\)/gi, `(${t("closePhoto")})`);
  s = s.replace(/\bbản mặt cầu\b/gi, t("termDeck"));
  s = s.replace(/\bbê tông\b/gi, t("termConcrete"));
  s = s.replace(/\bvết nứt\b/gi, t("termCrack"));
  s = s.replace(/\bbong tróc\b/gi, t("termSpalling"));
  s = s.replace(/\băn mòn\b/gi, t("termCorrosion"));
  s = s.replace(/\bthấm nước\b/gi, t("termSeepage"));
  s = s.replace(/\bthấm\b/gi, t("termSeepage"));
  s = s.replace(/\bhiện trường\b/gi, t("termField"));
  s = s.replace(/\bcận cảnh\b/gi, t("termCloseup"));
  s = s.replace(/\bmố cầu\b/gi, t("termAbutment"));
  s = s.replace(/\bmố\b/gi, t("termAbutment"));
  s = s.replace(/\btrụ cầu\b/gi, t("termPier"));
  s = s.replace(/\btrụ\b/gi, t("termPier"));
  s = s.replace(/\bdầm\b/gi, t("termBeam"));
  s = s.replace(/\bcột\b/gi, t("termColumn"));
  s = s.replace(/\bbản\b/gi, t("termSlab"));
  s = s.replace(/\btường\b/gi, t("termWall"));
  s = s.replace(/\bcầu\b/gi, t("termBridge"));
  s = s.replace(/\bbề mặt\b/gi, t("termSurface"));
  s = s.replace(/cấu trúc vùng lệch \(hiện trường\)/gi, t("reasonSkewField"));
  s = s.replace(/texture đều đầy khung \(cận\)/gi, t("reasonUniformClose"));
  s = s.replace(/chênh sáng trên\/dưới/gi, t("reasonLightSplit"));
  s = s.replace(/đường kết cấu dài/gi, t("reasonLongStructure"));
  s = s.replace(/mép mịn phủ khung/gi, t("reasonSmoothEdges"));
  s = s.replace(/bề mặt xám đồng nhất/gi, t("reasonGraySurface"));
  s = s.replace(/ít cấu trúc thô/gi, t("reasonLowCoarse"));
  s = s.replace(/cấu trúc thô mạnh/gi, t("reasonHighCoarse"));
  s = s.replace(/ảnh nhỏ\/crop/gi, t("reasonSmallCrop"));
  s = s.replace(/tên file gần cận \(([^)]+)\)/gi, (_, name) => t("reasonNameClose", { name }));
  s = s.replace(/tên file hiện trường \(([^)]+)\)/gi, (_, name) => t("reasonNameField", { name }));
  s = s.replace(
    /CV hiện trường \(score=([^)]+)\)/gi,
    (_, rest) => t("reasonCvField", { score: rest, why: "" }).replace(": ", ": "),
  );
  s = s.replace(
    /CV cận cảnh \(score=([^)]+)\)/gi,
    (_, rest) => t("reasonCvClose", { score: rest, why: "" }),
  );
  s = s.replace(/Recall cao: ít bỏ sót vết thật \(FN ít\)/gi, t("qRecHigh"));
  s = s.replace(/Recall trung bình: còn bỏ sót một phần/gi, t("qRecMid"));
  s = s.replace(/Recall thấp: bỏ sót nhiều pixel nứt/gi, t("qRecLow"));
  s = s.replace(/Precision khá: ít tô thừa/gi, t("qPrecOk"));
  s = s.replace(
    /Precision thấp: nhiều pixel thừa \(FP\) — LCW hay tô rộng hơn nhãn/gi,
    t("qPrecLow"),
  );
  s = s.replace(
    /Precision rất thấp: mask dự đoán rộng hơn nhãn nhiều/gi,
    t("qPrecVeryLow"),
  );
  s = s.replace(
    /Tổng thể F1=([0-9.]+), IoU=([0-9.]+) \(TP (\d+), FP (\d+), FN (\d+)\)\./gi,
    (_, f1, iou, tp, fp, fn) => t("qOverall", { f1, iou, tp, fp, fn }),
  );
  s = s.replace(/Không kết luận chỉ từ precision\./gi, t("qPrecWarn"));
  return s;
}

export const LANG_KEY = "infravision-lang";
