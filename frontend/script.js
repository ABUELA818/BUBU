const DEBUG = true;
const input = document.getElementById("imageInput");
const preview = document.getElementById("preview");
const resultDiv = document.getElementById("result");

// =======================
// PREVIEW DE IMAGEN
// =======================
input.onchange = () => {
    const file = input.files[0];

    if (file) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    }
};

// =======================
// SUBIR IMAGEN
// =======================
async function uploadImage() {
    const file = input.files[0];

    if (!file) {
        alert("Selecciona una imagen");
        return;
    }

    const heightInput = document.getElementById("heightInput").value;

    const formData = new FormData();
    formData.append("file", file);
    if (heightInput) {
        formData.append("height_cm", heightInput); 
    }

    resultDiv.innerHTML = "Procesando...";

    try {
        const response = await fetch("http://127.0.0.1:8000/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        // 🔴 AQUÍ VA
        if (data.error) {
            resultDiv.innerHTML = `
                <h3>Problemas detectados</h3>
                <ul>
                    ${data.issues.map(issue => `
                        <li>
                            <strong>${issue.message}</strong><br>
                            <small>${issue.suggestion}</small>
                        </li>
                    `).join("")}
                </ul>
            `;
            return;
        }

        renderResults(data);

        if (data.landmarks && DEBUG) {
            drawPose(data.landmarks, data.metrics?.measurements_cm);
        }

    } catch (error) {
        console.error(error);
        resultDiv.innerHTML = "Error al procesar la imagen";
    }
}

// =======================
// RENDER DE RESULTADOS
// =======================
function renderResults(data) {
    const cm = data.metrics?.measurements_cm;

    const measurementsHTML = cm ? `
        <h3>📏 Medidas corporales</h3>
        <table style="margin:auto; border-collapse:collapse; text-align:left;">
            <tr><th style="padding:6px 16px;">Medida</th><th style="padding:6px 16px;">Valor</th></tr>
            <tr><td style="padding:4px 16px;">Ancho de hombros</td><td><strong>${cm.shoulder_width_cm} cm</strong></td></tr>
            <tr><td style="padding:4px 16px;">Ancho de cadera</td> <td><strong>${cm.hip_width_cm} cm</strong></td></tr>
            <tr><td style="padding:4px 16px;">Largo de torso</td>  <td><strong>${cm.torso_height_cm} cm</strong></td></tr>
            <tr><td style="padding:4px 16px;">Largo de muslo</td>  <td><strong>${cm.thigh_length_cm} cm</strong></td></tr>
            <tr><td style="padding:4px 16px;">Largo de pierna</td> <td><strong>${cm.leg_length_cm} cm</strong></td></tr>
        </table>
    ` : `<p><em>Ingresa tu altura para ver medidas en cm</em></p>`;

    resultDiv.innerHTML = `
        <h3>Tipo de cuerpo: ${data.classification.body_type}</h3>
        <p><strong>Ratio hombro/cadera:</strong> ${data.classification.ratio.toFixed(2)}</p>

        ${measurementsHTML}

        <h3>Recomendaciones</h3>
        <p><strong>Tops:</strong> ${data.recommendations.tops.join(", ")}</p>
        <p><strong>Bottoms:</strong> ${data.recommendations.bottoms.join(", ")}</p>

        <h3>Productos sugeridos</h3>
        <ul>
            ${data.products.map(p => `
                <li>${p.product.name} (score: ${p.score})</li>
            `).join("")}
        </ul>
    `;
}

// =======================
// DIBUJAR POSE
// =======================
function drawPose(landmarks, measurementsCm = null, baseImage = null) {
    const canvas = document.getElementById("canvas");
    const ctx    = canvas.getContext("2d");
    const src    = baseImage || preview;   

    canvas.width  = src.naturalWidth  || src.width  || 250;
    canvas.height = src.naturalHeight || src.height || 400;

    ctx.drawImage(src, 0, 0, canvas.width, canvas.height);

    const W = canvas.width;
    const H = canvas.height;

    // =======================
    // CONEXIONES POR SEGMENTO
    // =======================
    const segments = [
        { color: "#00FFFF", pairs: [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10]] },
        { color: "#FFFFFF", pairs: [[11,12],[11,23],[12,24],[23,24]] },
        { color: "#00FF00", pairs: [[11,13],[13,15],[15,17],[15,19],[15,21],[17,19]] },
        { color: "#FF8800", pairs: [[12,14],[14,16],[16,18],[16,20],[16,22],[18,20]] },
        { color: "#00AAFF", pairs: [[23,25],[25,27],[27,29],[27,31],[29,31]] },
        { color: "#FF00AA", pairs: [[24,26],[26,28],[28,30],[28,32],[30,32]] }
    ];

    segments.forEach(({ color, pairs }) => {
        pairs.forEach(([i, j]) => {
            const p1 = landmarks[i];
            const p2 = landmarks[j];
            if (!p1 || !p2) return;

            const visibility = Math.min(p1.visibility, p2.visibility);
            if (visibility < 0.3) return;

            ctx.globalAlpha = Math.min(visibility, 1);
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.lineCap = "round";

            ctx.beginPath();
            ctx.moveTo(p1.x * W, p1.y * H);
            ctx.lineTo(p2.x * W, p2.y * H);
            ctx.stroke();
        });
    });

    // =======================
    // DIBUJAR PUNTOS
    // =======================
    landmarks.forEach((p, i) => {
        if (p.visibility < 0.3) return;

        const x = p.x * W;
        const y = p.y * H;

        ctx.globalAlpha = Math.min(p.visibility, 1);

        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = "white";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);

        if (i <= 10)                              ctx.fillStyle = "#00FFFF";
        else if (i <= 12 || (i >= 23 && i <= 24)) ctx.fillStyle = "#FFFFFF";
        else if ([13,15,17,19,21].includes(i))    ctx.fillStyle = "#00FF00";
        else if ([14,16,18,20,22].includes(i))    ctx.fillStyle = "#FF8800";
        else if ([25,27,29,31].includes(i))       ctx.fillStyle = "#00AAFF";
        else                                       ctx.fillStyle = "#FF00AA";

        ctx.fill();
    });

    ctx.globalAlpha = 1;

    // =======================
    // ETIQUETAS DE MEDIDAS
    // =======================
    if (!measurementsCm) return;

    const L  = landmarks;
    const LS = 11, RS = 12;
    const LH = 23, RH = 24;
    const LK = 25, RK = 26;
    const LA = 27, RA = 28;

    // Puntos medios de cada segmento
    function midpoint(a, b) {
        return {
            x: (L[a].x + L[b].x) / 2 * W,
            y: (L[a].y + L[b].y) / 2 * H
        };
    }

    const labels = [
        {
            pos: midpoint(LS, RS),
            text: `${measurementsCm.shoulder_width_cm} cm`,
            color: "#00FFFF",
            offsetX: 0,
            offsetY: -18
        },
        {
            pos: midpoint(LH, RH),
            text: `${measurementsCm.hip_width_cm} cm`,
            color: "#FFFF00",
            offsetX: 0,
            offsetY: -18
        },
        {
            // Torso: centro entre hombros y cadera (lado derecho)
            pos: {
                x: L[RS].x * W,
                y: (L[RS].y + L[RH].y) / 2 * H
            },
            text: `torso ${measurementsCm.torso_height_cm} cm`,
            color: "#FFFFFF",
            offsetX: 16,
            offsetY: 0
        },
        {
            // Muslo: centro entre cadera y rodilla (lado derecho)
            pos: {
                x: L[RH].x * W,
                y: (L[RH].y + L[RK].y) / 2 * H
            },
            text: `muslo ${measurementsCm.thigh_length_cm} cm`,
            color: "#FF00AA",
            offsetX: 16,
            offsetY: 0
        },
        {
            // Pierna: centro entre rodilla y tobillo (lado derecho)
            pos: {
                x: L[RK].x * W,
                y: (L[RK].y + L[RA].y) / 2 * H
            },
            text: `pierna ${measurementsCm.leg_length_cm} cm`,
            color: "#00AAFF",
            offsetX: 16,
            offsetY: 0
        }
    ];

    labels.forEach(({ pos, text, color, offsetX, offsetY }) => {
        const x = pos.x + offsetX;
        const y = pos.y + offsetY;

        const fontSize = Math.max(12, Math.round(W * 0.022));
        ctx.font = `bold ${fontSize}px Arial`;

        // Fondo semitransparente
        const textWidth = ctx.measureText(text).width;
        ctx.globalAlpha = 0.65;
        ctx.fillStyle = "#000000";
        ctx.fillRect(x - 4, y - fontSize, textWidth + 8, fontSize + 6);

        // Texto
        ctx.globalAlpha = 1;
        ctx.fillStyle = color;
        ctx.fillText(text, x, y);

        // Línea guía desde el punto al texto
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
    });
}