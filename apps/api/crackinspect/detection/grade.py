from __future__ import annotations

def grade_from_ratio(ratio: float, has_crack: bool) -> tuple[int, str, str]:
    if not has_crack or ratio < 0.001:
        return 0, "cấp 0", "không cần xử lý nứt"
    if ratio < 0.02:
        return 1, "cấp 1", "theo dõi định kỳ"
    if ratio < 0.05:
        return 2, "cấp 2", "theo dõi định kỳ"
    if ratio < 0.10:
        return 3, "cấp 3", "theo dõi và trám trét định kỳ"
    return 4, "cấp 4", "ưu tiên khảo sát và xử lý, không kết luận sụp đổ"
