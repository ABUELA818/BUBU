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

    const formData = new FormData();
    formData.append("file", file);

    resultDiv.innerHTML = "Procesando...";

    try {
        const response = await fetch("http://127.0.0.1:8000/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        renderResults(data);

        if (data.landmarks) {
            drawPose(data.landmarks);
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
    resultDiv.innerHTML = `
        <h3>Tipo de cuerpo: ${data.classification.body_type}</h3>
        <p><strong>Ratio:</strong> ${data.classification.ratio.toFixed(2)}</p>

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
function drawPose(landmarks) {
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");

    // Ajustar tamaño al preview
    canvas.width = preview.width;
    canvas.height = preview.height;

    // Dibujar imagen base
    ctx.drawImage(preview, 0, 0, canvas.width, canvas.height);

    // =======================
    // DIBUJAR PUNTOS
    // =======================
    landmarks.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x * canvas.width, p.y * canvas.height, 4, 0, 2 * Math.PI);
        ctx.fillStyle = "red";
        ctx.fill();
    });

    // =======================
    // CONEXIONES (esqueleto básico)
    // =======================
    const connections = [
        [11, 12], // hombros
        [11, 13], [13, 15], // brazo izq
        [12, 14], [14, 16], // brazo der
        [11, 23], [12, 24], // torso
        [23, 24], // caderas
        [23, 25], [25, 27], // pierna izq
        [24, 26], [26, 28]  // pierna der
    ];

    ctx.strokeStyle = "lime";
    ctx.lineWidth = 2;

    connections.forEach(([i, j]) => {
        const p1 = landmarks[i];
        const p2 = landmarks[j];

        if (p1 && p2) {
            ctx.beginPath();
            ctx.moveTo(p1.x * canvas.width, p1.y * canvas.height);
            ctx.lineTo(p2.x * canvas.width, p2.y * canvas.height);
            ctx.stroke();
        }
    });
}