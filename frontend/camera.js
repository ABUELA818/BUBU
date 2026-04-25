const EVALUATE_URL = "http://127.0.0.1:8000/evaluate-frame";
const ANALYZE_URL  = "http://127.0.0.1:8000/analyze-frames";

// ── Umbrales ─────────────────────────────────────────────────────────────────
const QUALITY_MIN          = 62;   // score mínimo de calidad por frame
const STABILITY_MIN        = 60;   // score mínimo de estabilidad (quietud)
const CONSECUTIVE_REQUIRED = 4;    // frames consecutivos buenos + estables antes de capturar
const LANDMARK_HISTORY_MAX = 8;    // ventana de landmarks para calcular varianza
const BURST_TARGET         = 8;    // frames útiles que queremos obtener
const BURST_MAX_ATTEMPTS   = 18;   // intentos máximos antes de rendirse
const BURST_INTERVAL_MS    = 220;  // ms entre cada frame del burst (más lento = más nítido)
const EVAL_INTERVAL_MS     = 700;  // ms entre evaluaciones en tiempo real

// Landmarks clave para el cálculo de estabilidad
const STABILITY_LANDMARKS  = [11, 12, 23, 24, 25, 26, 27, 28];

// ── Estado ───────────────────────────────────────────────────────────────────
let stream             = null;
let evaluationInterval = null;
let consecutiveGood    = 0;
let isCapturing        = false;
let isBurstMode        = false;
let isEvaluating       = false;
let lastSnapshot       = null;
let landmarkHistory    = [];   // ventana deslizante de sets de landmarks


// ── DOM helpers ───────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const videoEl = () => $("cameraFeed");


// ── TABS ─────────────────────────────────────────────────────────────────────
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


// ── INICIO / PARADA DE CÁMARA ─────────────────────────────────────────────────
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

        consecutiveGood  = 0;
        landmarkHistory  = [];
        isCapturing      = true;
        isBurstMode      = false;

        setFeedback("Posiciónate dentro de la silueta", "#888888", 0, 0);
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

    isCapturing     = false;
    isBurstMode     = false;
    landmarkHistory = [];

    setFeedback("Cámara detenida", "#555555", 0, 0);
    setProgress(0);
    setBorderColor("#444");
}


// ── EVALUACIÓN EN TIEMPO REAL ─────────────────────────────────────────────────
async function evaluateFrame() {
    if (!isCapturing || isBurstMode || isEvaluating) return;

    const vid = videoEl();
    if (!vid || vid.readyState < 2) return;

    isEvaluating = true;

    try {
        const blob     = await captureBlob(vid, 0.88);
        const formData = new FormData();
        formData.append("file", blob, "frame.jpg");

        const res  = await fetch(EVALUATE_URL, { method: "POST", body: formData });
        const data = await res.json();

        const score     = data.score    || 0;
        const feedback  = data.feedback || { message: "Analizando...", color: "#888888" };
        const landmarks = data.landmarks;

        // ── Estabilidad ──────────────────────────────────────────────────────
        let stability = 0;
        if (landmarks) {
            // Acumular historial de landmarks
            landmarkHistory.push(landmarks);
            if (landmarkHistory.length > LANDMARK_HISTORY_MAX) {
                landmarkHistory.shift();
            }
            stability = computeStability(landmarkHistory);
        }

        setFeedback(feedback.message, feedback.color, score, stability);
        setBorderColor(feedback.color);

        const frameOk = score >= QUALITY_MIN && stability >= STABILITY_MIN;

        if (frameOk) {
            consecutiveGood++;
            lastSnapshot = captureCanvas(vid);   // guarda el frame más reciente y estable
        } else {
            consecutiveGood = 0;
            if (stability < STABILITY_MIN) {
                if (landmarkHistory.length > 2) landmarkHistory.shift();
            }
        }

        setProgress(consecutiveGood, CONSECUTIVE_REQUIRED);

        if (consecutiveGood >= CONSECUTIVE_REQUIRED) {
            consecutiveGood = 0;
            startBurst(vid);
        }

    } catch (e) {
        console.warn("Error evaluando frame:", e);
    } finally {
        isEvaluating = false;
    }
}


// ── ESTABILIDAD: varianza posicional entre frames ─────────────────────────────
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

    // Persona quieta: avgStd < 0.004
    // Persona moviéndose: avgStd > 0.020
    // Convertir a score 0-100 (mayor quietud = mayor score)
    const score = Math.max(0, Math.min(100, (1 - avgStd / 0.018) * 100));
    return Math.round(score);
}

function stdDev(values) {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    return Math.sqrt(variance);
}


// ── BURST CAPTURE ─────────────────────────────────────────────────────────────
async function startBurst(vid) {
    if (isBurstMode) return;
    isBurstMode = true;
    clearInterval(evaluationInterval);

    // Cuenta regresiva real (1 segundo por número)
    for (let i = 3; i >= 1; i--) {
        setFeedback(`¡No te muevas! Capturando en ${i}...`, "#00FF88", 100, 100);
        setBorderColor("#00FF88");
        await sleep(1000);
    }

    setFeedback("Capturando frames...", "#00AAFF", 100, 100);

    const blobs    = [];
    let   attempts = 0;

    // Captura condicional: solo acepta frames donde los landmarks son estables
    // respecto al historial acumulado antes del burst
    const referenceHistory = [...landmarkHistory];

    // REEMPLAZA todo el bloque dentro del while de startBurst
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
            const quality = data.score || 0;

            setFeedback(
                `Frame ${blobs.length + 1}/${BURST_TARGET} (intento ${attempts}/${BURST_MAX_ATTEMPTS})`,
                quality >= 50 ? "#00AAFF" : "#FFAA00",
                quality,
                100   // estabilidad ya fue validada antes del burst, no re-evaluar
            );

            // Umbral permisivo: solo rechazar frames con pose completamente rota
            if (quality >= 50) {
                blobs.push(blob);
                lastSnapshot = canvas;
            }

        } catch (e) {
            // Si falla la evaluación del frame, incluirlo igual
            // (el selector de backend descartará los malos)
            blobs.push(blob);
            lastSnapshot = canvas;
        }
    }

    if (blobs.length === 0) {
        setFeedback("No se obtuvieron frames útiles — intenta de nuevo", "#FF4444", 0, 0);
        setTimeout(stopCamera, 2000);
        return;
    }

    setFeedback(`Analizando ${blobs.length} frames seleccionados...`, "#00AAFF", 100, 100);
    await sendBurst(blobs);
    stopCamera();
}


// ── ENVÍO AL BACKEND ──────────────────────────────────────────────────────────
async function sendBurst(blobs) {
    const heightCam = $("heightInputCam")?.value;
    const formData  = new FormData();

    blobs.forEach((blob, i) => formData.append("files", blob, `frame_${i}.jpg`));
    if (heightCam) formData.append("height_cm", heightCam);

    try {
        const res  = await fetch(ANALYZE_URL, { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) {
            $("result").innerHTML = `<p style="color:#FF4444">⚠️ ${data.error}</p>`;
            return;
        }

        renderResults(data);

        if (data.landmarks && lastSnapshot && DEBUG) {
            drawPose(data.landmarks, data.metrics?.measurements_cm, lastSnapshot);
        }

        const qi = $("qualityInfo");
        if (qi) {
            qi.innerHTML = `
                📊 Frames capturados: <strong>${data.frame_count}</strong> &nbsp;|&nbsp;
                Frames usados: <strong>${data.frames_used}</strong> &nbsp;|&nbsp;
                Calidad promedio: <strong>${data.quality_score}%</strong>
            `;
        }

    } catch (e) {
        console.error("Error enviando burst:", e);
        $("result").innerHTML = `<p style="color:#FF4444">Error al procesar los frames</p>`;
    }
}


// ── UI ────────────────────────────────────────────────────────────────────────
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


// ── UTILIDADES ────────────────────────────────────────────────────────────────
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