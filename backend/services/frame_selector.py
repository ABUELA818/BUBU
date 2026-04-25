import statistics


def select_best_frames(frames: list, top_n: int = 5, min_score: float = 65.0):
    if not frames:
        return None

    good = [f for f in frames if f["score"] >= min_score]
    if len(good) < 2:
        good = sorted(frames, key=lambda x: x["score"], reverse=True)[:2]

    candidates = sorted(good, key=lambda x: x["score"], reverse=True)[:top_n]
    stable     = _remove_outliers(candidates)
    return _weighted_average(stable)


def _remove_outliers(frames: list) -> list:
    if len(frames) <= 2:
        return frames

    sw_values = [f["metrics"]["shoulder_width"] for f in frames]
    median_sw = statistics.median(sw_values)
    threshold = median_sw * 0.10

    stable = [f for f in frames if abs(f["metrics"]["shoulder_width"] - median_sw) <= threshold]
    return stable if len(stable) >= 2 else frames[:2]


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