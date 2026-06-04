import io
import base64
import cv2
import numpy as np
import tensorflow as tf
from flask import Flask, request, jsonify
from flask_cors import CORS
from tensorflow.keras.models import load_model

app = Flask(__name__)
CORS(app)  # Front-end yoki boshqa joydan so'rov yuborishda muammo bo'lmasligi uchun

# 1. Modelni yuklash
MODEL_PATH = 'tibbiy_model_pnevmoniya.h5'
IMG_SIZE = (150, 150)

try:
    model = load_model(MODEL_PATH)
    print("[INFO]: Model muvaffaqiyatli yuklandi!")
except Exception as e:
    print(f"[ERROR]: Modelni yuklashda xatolik: {e}")

# 2. Grad-CAM funksiyasi
def make_gradcam_heatmap_keras3(img_array, model):
    conv_layers = [layer for layer in model.layers if "conv2d" in layer.name]
    if not conv_layers:
        raise ValueError("Model ichida Conv2D qatlami topilmadi!")
    last_conv_layer = conv_layers[-1]
    
    inputs = tf.keras.Input(shape=(IMG_SIZE[0], IMG_SIZE[1], 3))
    x = inputs
    
    conv_out = None
    for layer in model.layers:
        x = layer(x)
        if layer.name == last_conv_layer.name:
            conv_out = x
            
    grad_model = tf.keras.Model(inputs, [conv_out, x])

    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        class_channel = preds[:, 0]

    grads = tape.gradient(class_channel, last_conv_layer_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-10)
    return heatmap.numpy()

# 3. API Endpoit: /api/ predict
@app.route('/api/', methods=['POST'])
def predict_pnevmoniya():
    # So'rovda rasm borligini tekshirish
    if 'image' not in request.files:
        return jsonify({'error': 'Rasm yuborilmadi. Kalit so`z "image" bo`lishi kerak.'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Fayl tanlanmagan'}), 400

    try:
        # Rasmni xotiradan (in-memory) o'qish (Fayl tizimiga saqlab o'tirmaymiz)
        in_memory_file = io.BytesIO()
        file.save(in_memory_file)
        data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
        img_bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return jsonify({'error': 'Yuborilgan fayl yaroqli rasm emas.'}), 400

        # Rasmni model uchun tayyorlash
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, IMG_SIZE)
        img_array = np.expand_dims(img_resized, axis=0) / 255.0

        # Bashorat qilish
        prediction = float(model.predict(img_array)[0][0]) # JSON uchun floatga o'tkazamiz

        if prediction > 0.5:
            status = "PNEVMONIYA"
            probability = prediction * 100
        else:
            status = "SOG'LOM"
            probability = (1 - prediction) * 100

        # Grad-CAM Heatmap yaratish
        heatmap = make_gradcam_heatmap_keras3(img_array, model)
        heatmap_resized = cv2.resize(heatmap, (img_bgr.shape[1], img_bgr.shape[0]))
        heatmap_uint8 = np.uint8(255 * heatmap_resized)
        heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        
        # Heatmapni asl rasm ustiga chizish (BGR formatida, chunki OpenCVda saqlaymiz)
        superimposed_img = cv2.addWeighted(img_bgr, 0.6, heatmap_color, 0.4, 0)

        # Tayyor rasmni Base64 string ko'rinishiga o'tkazish
        _, buffer = cv2.imencode('.png', superimposed_img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        img_data_url = f"data:image/png;base64,{img_base64}"

        # JSON javob qaytarish
        return jsonify({
            'status': status,
            'probability': round(probability, 2),
            'heatmap_image': img_data_url
        }), 200

    except Exception as e:
        return jsonify({'error': f"Xatolik yuz berdi: {str(e)}"}), 500

if __name__ == '__main__':
    # Siz so'ragandek 127.0.0.1:8001 portida ishga tushirish
    app.run(host='127.0.0.1', port=8001, debug=True)