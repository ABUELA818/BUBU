// ─────────────────────────────────────────────────────────────────────────────
// Virtual Try-On  ·  Camera module  (multi-view 3D capture)
// ─────────────────────────────────────────────────────────────────────────────

const EVALUATE_URL      = "http://127.0.0.1:8000/evaluate-frame";
const ANALYZE_URL       = "http://127.0.0.1:8000/analyze-frames";
const ANALYZE_MULTI_URL = "http://127.0.0.1:8000/analyze-multiview";

// ── Umbrales ──────────────────────────────────────────────────────────────────
const QUALITY_MIN          = 62;
const STABILITY_MIN        = 58;
const CONSECUTIVE_REQUIRED = 4;
const LANDMARK_HISTORY_MAX = 8;
const BURST_TARGET         = 8;
const BURST_MAX_ATTEMPTS   = 18;
const BURST_INTERVAL_MS    = 220;
const EVAL_INTERVAL_MS     = 650;
const STABILITY_LANDMARKS  = [11, 12, 23, 24, 25, 26, 27, 28];

// ── Fases de captura ──────────────────────────────────────────────────────────
const PHASE = Object.freeze({
    IDLE:             "idle",
    FRONT_EVAL:       "front_eval",
    FRONT_BURST:      "front_burst",
    PROFILE_INSTRUCT: "profile_instruct",
    PROFILE_EVAL:     "profile_eval",
    PROFILE_BURST:    "profile_burst",
    ANALYZING:        "analyzing",
    DONE:             "done",
});

// ── Estado global ─────────────────────────────────────────────────────────────
let stream             = null;
let evaluationInterval = null;
let currentPhase       = PHASE.IDLE;
let consecutiveGood    = 0;
let isEvaluating       = false;
let landmarkHistory    = [];
let frontBlobs         = [];
let profileBlobs       = [];
let lastSnapshot       = null;
let lastOrientation    = "unknown";

// ── DOM helpers ───────────────────────────────────────────────────────────────
const $       = id => document.getElementById(id);
const videoEl = ()  => $("cameraFeed");


// ═════════════════════════════════════════════════════════════════════════════
// TABS
// ═════════════════════════════════════════════════════════════════════════════
function switchTab(tab) {
    $("tab-upload").style.display = tab === "upload" ? "block" : "none";
    $("tab-camera").style.display = tab === "camera" ? "block" : "none";

    document.querySelectorAll(".tab-btn").forEach((btn, i) => {
        btn.classList.toggle(
            "active",
            (i === 0 && tab === "upload") || (i === 1 && tab === "camera")
        );
    });

    if (tab !== "camera") stopCamera();
}


// ═════════════════════════════════════════════════════════════════════════════
// INICIO / PARADA DE CÁMARA
// ═════════════════════════════════════════════════════════════════════════════
async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 720 }, height: { ideal: 1280 }, facingMode: "user" }
        });

        const vid = videoEl();
        vid.srcObject     = stream;
        vid.style.display = "block";

        $("startCameraBtn").style.display = "none";
        $("stopCameraBtn").style.display  = "inline-block";

        _resetCaptureState();
        _setPhase(PHASE.FRONT_EVAL);

        setFeedback("Posiciónate dentro de la silueta de frente", "#888888", 0, 0);
        evaluationInterval = setInterval(evaluateFrame, EVAL_INTERVAL_MS);

    } catch (err) {
        alert("No se pudo acceder a la cámara: " + err.message);
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    clearInterval(evaluationInterval);

    const vid = videoEl();
    if (vid) vid.style.display = "none";

    const sb = $("startCameraBtn");
    const eb = $("stopCameraBtn");
    if (sb) sb.style.display = "inline-block";
    if (eb) eb.style.display = "none";

    _setPhase(PHASE.IDLE);
    setFeedback("Cámara detenida", "#555555", 0, 0);
    setProgress(0);
    setBorderColor("#444");
    _showSilhouette("front");
}

function _resetCaptureState() {
    consecutiveGood = 0;
    landmarkHistory = [];
    frontBlobs      = [];
    profileBlobs    = [];
    isEvaluating    = false;
    lastOrientation = "unknown";
}

function _setPhase(phase) {
    currentPhase = phase;

    const phaseLabel = $("phaseLabel");
    const phaseMap = {
        [PHASE.IDLE]:             { text: "",                      color: "#555" },
        [PHASE.FRONT_EVAL]:       { text: "FASE 1 · Vista frontal", color: "#00FF88" },
        [PHASE.FRONT_BURST]:      { text: "FASE 1 · Capturando…",  color: "#00AAFF" },
        [PHASE.PROFILE_INSTRUCT]: { text: "TRANSICIÓN",            color: "#FFAA00" },
        [PHASE.PROFILE_EVAL]:     { text: "FASE 2 · Vista de perfil", color: "#00FF88" },
        [PHASE.PROFILE_BURST]:    { text: "FASE 2 · Capturando…",  color: "#00AAFF" },
        [PHASE.ANALYZING]:        { text: "Analizando…",           color: "#888" },
        [PHASE.DONE]:             { text: "✅ Listo",               color: "#00FF88" },
    };
    if (phaseLabel && phaseMap[phase]) {
        phaseLabel.textContent  = phaseMap[phase].text;
        phaseLabel.style.color  = phaseMap[phase].color;
    }

    // Switch silhouette
    if (phase === PHASE.PROFILE_EVAL || phase === PHASE.PROFILE_BURST) {
        _showSilhouette("profile");
    } else {
        _showSilhouette("front");
    }
}

function _showSilhouette(view) {
    const front   = $("silhouetteFront");
    const profile = $("silhouetteProfile");
    if (front)   front.style.display   = view === "front"   ? "block" : "none";
    if (profile) profile.style.display = view === "profile" ? "block" : "none";
}


// ═════════════════════════════════════════════════════════════════════════════
// EVALUACIÓN EN TIEMPO REAL
// ═════════════════════════════════════════════════════════════════════════════
async function evaluateFrame() {
    const evalPhases = [PHASE.FRONT_EVAL, PHASE.PROFILE_EVAL];
    if (!evalPhases.includes(currentPhase) || isEvaluating) return;

    const vid = videoEl();
    if (!vid || vid.readyState < 2) return;

    isEvaluating = true;

    try {
        const phase    = currentPhase === PHASE.FRONT_EVAL ? "front" : "profile";
        const blob     = await captureBlob(vid, 0.88);
        const formData = new FormData();
        formData.append("file",  blob, "frame.jpg");
        formData.append("phase", phase);

        const res  = await fetch(EVALUATE_URL, { method: "POST", body: formData });
        const data = await res.json();

        const score       = data.score       || 0;
        const feedback    = data.feedback    || { message: "Analizando...", color: "#888888" };
        const landmarks   = data.landmarks;
        const orientation = data.orientation || "unknown";

        lastOrientation = orientation;

        // ── Estabilidad ───────────────────────────────────────────────────
        let stability = 0;
        if (landmarks) {
            landmarkHistory.push(landmarks);
            if (landmarkHistory.length > LANDMARK_HISTORY_MAX) landmarkHistory.shift();
            stability = computeStability(landmarkHistory);
        }

        setFeedback(feedback.message, feedback.color, score, stability);
        setBorderColor(feedback.color);

        // ── ¿Frame válido para esta fase? ─────────────────────────────────
        const qualityOk = score >= QUALITY_MIN && stability >= STABILITY_MIN;

        // Orientation check
        let orientOk = false;
        if (phase === "front") {
            orientOk = orientation === "front" || orientation === "unknown";
        } else {
            orientOk = orientation === "profile_right" || orientation === "profile_left";
            if (orientation === "front") {
                setFeedback("Gírate 90° de lado — perfil completo", "#FF8800", score, stability);
            }
        }

        const frameOk = qualityOk && orientOk;

        if (frameOk) {
            consecutiveGood++;
            lastSnapshot = captureCanvas(vid);
        } else {
            consecutiveGood = 0;
            if (stability < STABILITY_MIN && landmarkHistory.length > 2) {
                landmarkHistory.shift();
            }
        }

        setProgress(consecutiveGood, CONSECUTIVE_REQUIRED);

        if (consecutiveGood >= CONSECUTIVE_REQUIRED) {
            consecutiveGood = 0;
            clearInterval(evaluationInterval);

            if (currentPhase === PHASE.FRONT_EVAL) {
                _setPhase(PHASE.FRONT_BURST);
                await _doBurst(vid, "front");
            } else {
                _setPhase(PHASE.PROFILE_BURST);
                await _doBurst(vid, "profile");
            }
        }

    } catch (e) {
        console.warn("Error evaluando frame:", e);
    } finally {
        isEvaluating = false;
    }
}


// ═════════════════════════════════════════════════════════════════════════════
// BURST CAPTURE
// ═════════════════════════════════════════════════════════════════════════════
async function _doBurst(vid, view) {
    // Countdown
    for (let i = 3; i >= 1; i--) {
        setFeedback(`¡No te muevas! Capturando en ${i}...`, "#00FF88", 100, 100);
        setBorderColor("#00FF88");
        await sleep(1000);
    }

    setFeedback("Capturando frames…", "#00AAFF", 100, 100);

    const blobs    = [];
    let   attempts = 0;

    while (blobs.length < BURST_TARGET && attempts < BURST_MAX_ATTEMPTS) {
        attempts++;
        await sleep(BURST_INTERVAL_MS);

        const canvas = captureCanvas(vid);
        const blob   = await canvasToBlob(canvas, 0.92);
        const fd     = new FormData();
        fd.append("file", blob, "burst.jpg");

        try {
            const res  = await fetch(EVALUATE_URL, { method: "POST", body: fd });
            const data = await res.json();
            const q    = data.score || 0;

            setFeedback(
                `Frame ${blobs.length + 1}/${BURST_TARGET} (intento ${attempts})`,
                q >= 50 ? "#00AAFF" : "#FFAA00",
                q, 100
            );

            if (q >= 50) {
                blobs.push(blob);
                lastSnapshot = canvas;
            }
        } catch {
            blobs.push(blob);
            lastSnapshot = canvas;
        }
    }

    if (blobs.length === 0) {
        setFeedback("No se obtuvieron frames útiles — intenta de nuevo", "#FF4444", 0, 0);
        setTimeout(stopCamera, 2500);
        return;
    }

    if (view === "front") {
        frontBlobs = blobs;
        await _transitionToProfile(vid);
    } else {
        profileBlobs = blobs;
        _setPhase(PHASE.ANALYZING);
        await sendMultiview();
        stopCamera();
    }
}


// ═════════════════════════════════════════════════════════════════════════════
// TRANSICIÓN A PERFIL
// ═════════════════════════════════════════════════════════════════════════════
async function _transitionToProfile(vid) {
    _setPhase(PHASE.PROFILE_INSTRUCT);
    setBorderColor("#FFAA00");

    // Countdown to turn
    const seconds = 5;
    for (let i = seconds; i >= 1; i--) {
        setFeedback(
            `✅ Frente listo · Gírate 90° a tu derecha en ${i}s`,
            "#FFAA00", 100, 100
        );
        await sleep(1000);
    }

    // Reset state for profile phase
    consecutiveGood = 0;
    landmarkHistory = [];

    _setPhase(PHASE.PROFILE_EVAL);
    setFeedback("Mantén el perfil — quédate quieto/a", "#888888", 0, 0);
    setProgress(0);
    evaluationInterval = setInterval(evaluateFrame, EVAL_INTERVAL_MS);
}


// ═════════════════════════════════════════════════════════════════════════════
// ENVÍO AL BACKEND
// ═════════════════════════════════════════════════════════════════════════════
async function sendMultiview() {
    const heightCam = $("heightInputCam")?.value;
    const formData  = new FormData();

    frontBlobs.forEach((b, i) => formData.append("front_files",   b, `front_${i}.jpg`));
    profileBlobs.forEach((b, i) => formData.append("profile_files", b, `profile_${i}.jpg`));
    if (heightCam) formData.append("height_cm", heightCam);

    setFeedback("Fusionando vistas 3D…", "#888888", 100, 100);

    try {
        const res  = await fetch(ANALYZE_MULTI_URL, { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) {
            $("result").innerHTML = `<p style="color:#FF4444">⚠️ ${data.error}</p>`;
            return;
        }

        renderResults(data);

        if (data.landmarks && lastSnapshot && typeof DEBUG !== "undefined" && DEBUG) {
            drawPose(data.landmarks, data.measurements_cm, lastSnapshot);
        }

        const qi = $("qualityInfo");
        if (qi) {
            const conf    = data.confidence || {};
            const confColor = conf.level === "ok" ? "#00FF88"
                            : conf.level === "low_confidence" ? "#FFAA00"
                            : "#FF4444";
            const views   = (data.views_used || ["front"]).join(" + ");
            qi.innerHTML = `
                📊 Frames: <strong>${data.frame_count}</strong> &nbsp;|&nbsp;
                Vistas: <strong>${views}</strong> &nbsp;|&nbsp;
                Calidad: <strong>${data.quality_score}%</strong> &nbsp;|&nbsp;
                Consistencia: <strong>${data.consistency_score ?? "—"}%</strong>
                <br>
                <span style="color:${confColor}; font-weight:bold;">
                    ${conf.level?.toUpperCase() ?? ""} · ${conf.message ?? ""}
                </span>
                ${(conf.issues || []).length > 0 ? `
                  <ul style="text-align:left; color:#aaa; font-size:11px; margin-top:4px;">
                    ${conf.issues.map(i => `<li>${i.message}</li>`).join("")}
                  </ul>` : ""}
            `;
        }

    } catch (e) {
        console.error("Error enviando burst:", e);
        $("result").innerHTML = `<p style="color:#FF4444">Error al procesar los frames</p>`;
    }
}


// ═════════════════════════════════════════════════════════════════════════════
// ESTABILIDAD
// ═════════════════════════════════════════════════════════════════════════════
function computeStability(history) {
    if (history.length < 3) return 0;

    let totalStd = 0;
    let count    = 0;

    for (const idx of STABILITY_LANDMARKS) {
        const xValues = history.map(lms => lms[idx].x);
        const yValues = history.map(lms => lms[idx].y);
        totalStd += stdDev(xValues) + stdDev(yValues);
        count    += 2;
    }

    const avgStd = totalStd / count;
    const score  = Math.max(0, Math.min(100, (1 - avgStd / 0.018) * 100));
    return Math.round(score);
}

function stdDev(values) {
    const mean     = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    return Math.sqrt(variance);
}


// ═════════════════════════════════════════════════════════════════════════════
// UI HELPERS
// ═════════════════════════════════════════════════════════════════════════════
function setFeedback(msg, color, quality, stability) {
    const fe = $("feedbackText");
    const se = $("scoreText");
    if (fe) { fe.textContent = msg; fe.style.color = color; }
    if (se) {
        se.textContent = quality > 0
            ? `Cal: ${Math.round(quality)}%  |  Est: ${Math.round(stability)}%`
            : "—";
        se.style.color = color;
    }
}

function setBorderColor(color) {
    const c = $("cameraContainer");
    if (c) c.style.borderColor = color;
}

function setProgress(current, required = CONSECUTIVE_REQUIRED) {
    const bar = $("captureProgress");
    const lbl = $("progressLabel");
    if (!bar) return;

    const pct = Math.min(100, Math.round((current / required) * 100));
    bar.style.width      = `${pct}%`;
    bar.style.background = pct >= 100 ? "#00FF88" : pct > 50 ? "#FFAA00" : "#FF4444";

    if (lbl) {
        lbl.textContent = pct >= 100
            ? "✅ Listo para capturar"
            : `Frames estables: ${current}/${required}`;
    }
}


// ═════════════════════════════════════════════════════════════════════════════
// UTILIDADES
// ═════════════════════════════════════════════════════════════════════════════
function captureCanvas(vid) {
    const c = document.createElement("canvas");
    c.width  = vid.videoWidth;
    c.height = vid.videoHeight;
    c.getContext("2d").drawImage(vid, 0, 0);
    return c;
}

function captureBlob(vid, quality = 0.88) {
    return canvasToBlob(captureCanvas(vid), quality);
}

function canvasToBlob(canvas, quality = 0.88) {
    return new Promise(r => canvas.toBlob(r, "image/jpeg", quality));
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}