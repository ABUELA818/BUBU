"""
Fuses measurements from multiple views (front + profile) in 3D space.

Strategy:
  • Front frames  → best for shoulder/hip WIDTH  (x-axis measurements)
  • Profile frames → best for DEPTH / posture verification
  • World landmarks give metric-scale 3D coordinates → use Euclidean 3D distances
  • Consistency between frames is used to derive a confidence score
"""

import math
import statistics


# ── 3D distance helpers ───────────────────────────────────────────────────────

def _dist3d(a: dict, b: dict) -> float:
    return math.sqrt(
        (a["x"] - b["x"]) ** 2 +
        (a["y"] - b["y"]) ** 2 +
        (a["z"] - b["z"]) ** 2
    )


def _midpoint3d(a: dict, b: dict) -> dict:
    return {k: (a[k] + b[k]) / 2 for k in ("x", "y", "z")}


# ── Per-frame 3D metrics ──────────────────────────────────────────────────────

def extract_metrics_3d(world_landmarks: list, real_height_cm: float | None = None) -> dict:
    """
    Extract body metrics from MediaPipe world_landmarks (metric space, meters).
    Falls back to returning empty dict if world_landmarks is absent.
    """
    if not world_landmarks or len(world_landmarks) < 29:
        return {}

    ls  = world_landmarks[11]   # left shoulder
    rs  = world_landmarks[12]   # right shoulder
    lh  = world_landmarks[23]   # left hip
    rh  = world_landmarks[24]   # right hip
    lk  = world_landmarks[25]   # left knee
    rk  = world_landmarks[26]   # right knee
    la  = world_landmarks[27]   # left ankle
    ra  = world_landmarks[28]   # right ankle

    shoulder_width  = _dist3d(ls, rs)
    hip_width       = _dist3d(lh, rh)

    mid_sh  = _midpoint3d(ls, rs)
    mid_hip = _midpoint3d(lh, rh)
    mid_kn  = _midpoint3d(lk, rk)
    mid_an  = _midpoint3d(la, ra)

    torso_height = _dist3d(mid_sh,  mid_hip)
    thigh_length = _dist3d(mid_hip, mid_kn)
    leg_length   = _dist3d(mid_kn,  mid_an)
    body_height  = _dist3d(mid_sh,  mid_an)

    ratio = shoulder_width / hip_width if hip_width > 0 else 0

    metrics = {
        "shoulder_width":     shoulder_width,
        "hip_width":          hip_width,
        "body_height":        body_height,
        "torso_height":       torso_height,
        "thigh_length":       thigh_length,
        "leg_length":         leg_length,
        "shoulder_hip_ratio": ratio,
        "source":             "3d",
    }

    if real_height_cm and body_height > 0:
        # Shoulder-to-ankle span ≈ 87 % of standing height
        scale = (real_height_cm * 0.87) / body_height
        metrics["measurements_cm"] = {
            "shoulder_width_cm": round(shoulder_width * scale, 1),
            "hip_width_cm":      round(hip_width      * scale, 1),
            "torso_height_cm":   round(torso_height   * scale, 1),
            "thigh_length_cm":   round(thigh_length   * scale, 1),
            "leg_length_cm":     round(leg_length     * scale, 1),
        }

    return metrics


# ── Outlier removal ───────────────────────────────────────────────────────────

def _remove_outliers(frames: list, key: str) -> list:
    if len(frames) <= 2:
        return frames
    values  = [f["metrics_3d"][key] for f in frames]
    median  = statistics.median(values)
    allowed = median * 0.12
    stable  = [f for f in frames if abs(f["metrics_3d"][key] - median) <= allowed]
    return stable if len(stable) >= 2 else frames[:2]


# ── Weighted average over a set of frames ─────────────────────────────────────

def _weighted_avg(frames: list, keys: list[str]) -> dict:
    total_w = sum(f["score"] for f in frames)
    return {
        key: sum(f["metrics_3d"][key] * f["score"] for f in frames) / total_w
        for key in keys
    }


# ── Consistency / reprojection-style score ────────────────────────────────────

def _consistency_score(frames: list, key: str) -> float:
    """Returns 0-100: higher = more consistent across frames."""
    if len(frames) < 2:
        return 80.0
    values = [f["metrics_3d"][key] for f in frames]
    std    = statistics.stdev(values)
    med    = statistics.median(values)
    cv     = std / med if med > 0 else 1.0   # coefficient of variation
    return round(max(0.0, min(100.0, (1.0 - cv / 0.10) * 100.0)), 1)


# ── Main fusion function ──────────────────────────────────────────────────────

KEYS_3D = [
    "shoulder_width", "hip_width", "body_height",
    "torso_height",   "thigh_length", "leg_length",
]


def fuse_views(
    front_frames:   list,
    profile_frames: list,
    real_height_cm: float | None = None,
) -> dict:
    """
    front_frames / profile_frames:
        list of dicts { score, metrics_3d, landmarks, world_landmarks }

    Returns:
        {
          metrics, measurements_cm (if height given),
          confidence: 'ok' | 'low_confidence' | 'invalid_capture',
          consistency_score, issues, views_used
        }
    """
    issues         = []
    views_used     = []
    fused_metrics  = {}
    confidence     = "low_confidence"

    # ── Front view ────────────────────────────────────────────────────────────
    if front_frames:
        clean_front = _remove_outliers(front_frames, "shoulder_width")
        avg_f       = _weighted_avg(clean_front, KEYS_3D)
        cons_sw     = _consistency_score(clean_front, "shoulder_width")
        fused_metrics.update(avg_f)
        views_used.append("front")

        if len(clean_front) >= 3 and cons_sw >= 70:
            confidence = "ok"
        else:
            issues.append({
                "code":    "low_front_consistency",
                "message": "Poca estabilidad en vista frontal — mantén la postura fija",
            })
    else:
        issues.append({
            "code":    "no_front_frames",
            "message": "No se obtuvieron frames frontales válidos",
        })
        confidence = "invalid_capture"
        return {
            "confidence": confidence,
            "issues":     issues,
            "views_used": views_used,
        }

    # ── Profile view (optional enrichment) ───────────────────────────────────
    if profile_frames:
        clean_prof = _remove_outliers(profile_frames, "body_height")
        avg_p      = _weighted_avg(clean_prof, KEYS_3D)
        views_used.append("profile")

        # Profile is better for depth — use its body_height and leg segments
        # (less shoulder/hip distortion from side angle)
        # Blend: front gets 70 % weight for widths, profile 30 % for heights
        if fused_metrics:
            for k in ("body_height", "torso_height", "thigh_length", "leg_length"):
                fused_metrics[k] = 0.5 * fused_metrics[k] + 0.5 * avg_p[k]
    else:
        issues.append({
            "code":    "no_profile_frames",
            "message": "Sin vista de perfil — medidas de profundidad estimadas",
        })
        if confidence == "ok":
            confidence = "low_confidence"

    # ── Derived ratio ─────────────────────────────────────────────────────────
    if fused_metrics.get("hip_width", 0) > 0:
        fused_metrics["shoulder_hip_ratio"] = (
            fused_metrics["shoulder_width"] / fused_metrics["hip_width"]
        )

    fused_metrics["source"] = "3d_fused"

    # ── Scale to real cm ──────────────────────────────────────────────────────
    measurements_cm = None
    body_h = fused_metrics.get("body_height", 0)
    if real_height_cm and body_h > 0:
        scale = (real_height_cm * 0.87) / body_h
        measurements_cm = {
            "shoulder_width_cm": round(fused_metrics["shoulder_width"] * scale, 1),
            "hip_width_cm":      round(fused_metrics["hip_width"]      * scale, 1),
            "torso_height_cm":   round(fused_metrics["torso_height"]   * scale, 1),
            "thigh_length_cm":   round(fused_metrics["thigh_length"]   * scale, 1),
            "leg_length_cm":     round(fused_metrics["leg_length"]     * scale, 1),
        }

    # ── Consistency score (global) ────────────────────────────────────────────
    all_frames     = front_frames + (profile_frames or [])
    cons_global    = _consistency_score(all_frames, "shoulder_width") if len(all_frames) >= 2 else 80.0

    return {
        "metrics":           fused_metrics,
        "measurements_cm":   measurements_cm,
        "confidence":        confidence,
        "consistency_score": cons_global,
        "issues":            issues,
        "views_used":        views_used,
        "frame_count":       len(all_frames),
        "front_count":       len(front_frames),
        "profile_count":     len(profile_frames) if profile_frames else 0,
    }