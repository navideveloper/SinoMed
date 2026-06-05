# API natijasidagi chiziqlarni chizish bo'yicha qo'llanma

Bu qo'llanma SinoMed AI Prostata API javobini qabul qiladigan frontend yoki boshqa tizimlar uchun. Maqsad: `/predict` endpointidan kelgan `detections` ro'yxati asosida rasm ustiga aniqlangan sohalar atrofida chiziq, label va confidence chizish.

## Endpoint

```http
POST /predict
Content-Type: multipart/form-data
X-API-Key: <api-key>
```

Request body:

```text
file=<gistologik rasm>
```

API key sozlanmagan bo'lsa `X-API-Key` yuborish shart emas.

## Response formati

```json
{
  "filename": "sample.jpg",
  "image_width": 1280,
  "image_height": 960,
  "disease_probability_percent": 51,
  "conclusion": "Kasallik mavjudlik ehtimoli: taxminan 51%.",
  "detections_count": 2,
  "detections": [
    {
      "label": "grade3 (%)",
      "confidence": 0.5123,
      "confidence_percent": 51,
      "box": [120.5, 88.0, 430.2, 310.8]
    }
  ],
  "inference_time_ms": 184
}
```

`box` tartibi:

```text
[xmin, ymin, xmax, ymax]
```

Bu koordinatalar original rasm piksel o'lchamiga nisbatan keladi. Masalan response ichida `image_width=1280`, `image_height=960` bo'lsa, `box` ham shu original o'lcham koordinatalarida.

## Chizish algoritmi

1. Foydalanuvchi yuklagan rasmni ekranga chiqaring.
2. Rasm ustiga `canvas` yoki SVG layer qo'ying.
3. Canvas o'lchamini ekranda ko'rinayotgan rasm o'lchamiga teng qiling.
4. Original API koordinatalarini ekrandagi rasm o'lchamiga scale qiling.
5. Har bir detection uchun rectangle, label va confidence chizing.

Scale formulasi:

```text
scaleX = displayedImageWidth / response.image_width
scaleY = displayedImageHeight / response.image_height

drawX = xmin * scaleX
drawY = ymin * scaleY
drawWidth = (xmax - xmin) * scaleX
drawHeight = (ymax - ymin) * scaleY
```

## JavaScript canvas namunasi

```html
<div class="preview">
  <img id="sourceImage" alt="Tahlil qilingan rasm">
  <canvas id="overlay"></canvas>
</div>
```

```css
.preview {
  position: relative;
  display: inline-block;
  max-width: 100%;
}

.preview img {
  display: block;
  max-width: 100%;
  height: auto;
}

.preview canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
```

```js
function drawDetections(imageEl, canvasEl, apiResponse) {
  const displayedWidth = imageEl.clientWidth;
  const displayedHeight = imageEl.clientHeight;

  canvasEl.width = displayedWidth;
  canvasEl.height = displayedHeight;

  const ctx = canvasEl.getContext("2d");
  ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

  const scaleX = displayedWidth / apiResponse.image_width;
  const scaleY = displayedHeight / apiResponse.image_height;

  for (const detection of apiResponse.detections) {
    const [xmin, ymin, xmax, ymax] = detection.box;

    const x = xmin * scaleX;
    const y = ymin * scaleY;
    const width = (xmax - xmin) * scaleX;
    const height = (ymax - ymin) * scaleY;

    const color = getDetectionColor(detection.label);
    const text = `${detection.label} ${detection.confidence_percent}%`;

    ctx.lineWidth = 3;
    ctx.strokeStyle = color;
    ctx.strokeRect(x, y, width, height);

    ctx.font = "14px Arial";
    const labelWidth = ctx.measureText(text).width + 12;
    const labelHeight = 22;
    const labelY = Math.max(0, y - labelHeight);

    ctx.fillStyle = color;
    ctx.fillRect(x, labelY, labelWidth, labelHeight);

    ctx.fillStyle = "#ffffff";
    ctx.fillText(text, x + 6, labelY + 15);
  }
}

function getDetectionColor(label) {
  const normalized = String(label).toLowerCase();

  if (normalized.includes("benign")) return "#16a34a";
  if (normalized.includes("grade3")) return "#f59e0b";
  if (normalized.includes("grade4")) return "#ef4444";
  if (normalized.includes("grade5")) return "#7c2d12";

  return "#2563eb";
}
```

Rasm yuklangandan va API javobi kelgandan keyin:

```js
const imageEl = document.getElementById("sourceImage");
const canvasEl = document.getElementById("overlay");

imageEl.onload = () => drawDetections(imageEl, canvasEl, apiResponse);
imageEl.src = URL.createObjectURL(selectedFile);
```

Resize bo'lganda chiziqlarni qayta chizish kerak:

```js
window.addEventListener("resize", () => {
  drawDetections(imageEl, canvasEl, apiResponse);
});
```

## APIga fayl yuborish namunasi

```js
async function predictImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("https://sinomed.prapi.starify.uz/predict", {
    method: "POST",
    headers: {
      "X-API-Key": "your-api-key"
    },
    body: formData
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}
```

API key ishlatilmasa `headers` qismini olib tashlang.

## Muhim holatlar

- `detections_count = 0` bo'lsa rasmga chiziq chizilmaydi, faqat `conclusion` ko'rsatiladi.
- `box` qiymatlari original rasm koordinatalarida keladi; ekrandagi rasm kichraygan/kattalashgan bo'lsa scale qilish shart.
- Rasm CSS orqali `object-fit: contain` bilan letterbox qilib ko'rsatilsa, bo'sh joy offsetlarini ham hisobga oling.
- Agar frontend rasmni crop qilsa, API koordinatalari crop qilingan rasmga mos kelmaydi. APIga yuborilgan aynan o'sha rasmni ekranda ko'rsating.
- Juda katta rasm yuborilsa API `413` qaytarishi mumkin.
- Model yuklanmagan bo'lsa API `503` qaytaradi.

## Tavsiya etilgan UI

- Original rasmni ko'rsating.
- Har bir `grade` uchun rangni ajrating.
- `confidence_percent`ni label ichida ko'rsating.
- Umumiy natija sifatida `conclusion` va `disease_probability_percent`ni alohida panelda ko'rsating.
- Chiziqlarni o'chirib-yoqish uchun toggle qo'shish foydali.
