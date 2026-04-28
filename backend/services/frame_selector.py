"""
Frame selection for multi-view capture.
Separates front and profile frames and selects the best from each group.
"""

import statistics


# ── Single-view selection (existing logic, preserved) ─────────────────────────

def select_best_frames(frames: list, top_n: int = 5, min_score: float = 65.0) -> dict | None:
    """Select best frames from a single-view burst and return aggregated metrics."""
    if not frames:
        return None

    good = [f for f in frames if f["score"] >= min_score]
    if len(good) < 2:
        good = sorted(frames, key=lambda x: x["score"], reverse=True)[:2]

    candidates = sorted(good, key=lambda x: x["score"], reverse=True)[:top_n]
    stable     = _remove_outliers(candidates, "shoulder_width")
    return _weighted_average(stable)


# ── Multi-view selection ──────────────────────────────────────────────────────

def select_best_by_view(
    frames:    list,
    top_n:     int   = 6,
    min_score: float = 55.0,
) -> tuple[list, list]:
    """
    Separate frames by orientation and return
      (front_frames, profile_frames)
    Each is a list of the best-scoring frames for that view.

    frames: list of dicts {score, metrics, metrics_3d, landmarks, world_landmarks, orientation}
    """
    front_frames   = [f for f in frames if f.get("orientation") == "front"]
    profile_frames = [f for f in frames if f.get("orientation", "").startswith("profile")]

    front_best   = _pick_best(front_frames,   top_n, min_score)
    profile_best = _pick_best(profile_frames, top_n, min_score)

    return front_best, profile_best


def _pick_best(frames: list, top_n: int, min_score: float) -> list:
    good = [f for f in frames if f["score"] >= min_score]
    if len(good) < 2:
        good = sorted(frames, key=lambda x: x["score"], reverse=True)[:2]

    candidates = sorted(good, key=lambda x: x["score"], reverse=True)[:top_n]
    return _remove_outliers(candidates, "shoulder_width")


# ── Outlier removal ───────────────────────────────────────────────────────────

def _remove_outliers(frames: list, key: str) -> list:
    if len(frames) <= 2:
        return frames

    values   = [f["metrics"][key] for f in frames]
    median   = statistics.median(values)
    allowed  = median * 0.10

    stable = [f for f in frames if abs(f["metrics"][key] - median) <= allowed]
    return stable if len(stable) >= 2 else frames[:2]


# ── Weighted average (legacy single-view path) ────────────────────────────────

def _weighted_average(frames: list) -> dict:
    total_weight = sum(f["score"] for f in frames)
    keys = ["shoulder_width", "hip_width", "body_height", "shoulder_hip_ratio"]

    result = {
        key: sum(f["metrics"][key] * f["score"] for f in frames) / total_weight
        for key in keys
    }
    result["frame_count"] = len(frames)
    result["avg_score"]   = round(total_weight / len(frames), 1)
    return result