import io
import os
import numpy as np
import tensorflow as tf
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MODEL_PATH = 'suyak_yoshi_gender_model.keras'
IMG_SIZE = (224, 224)

if not os.path.exists(MODEL_PATH):
    print(f"[ERROR]: Model fayli topilmadi: {MODEL_PATH}")
    model = None
else:
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        print("[INFO]: Suyak yoshini aniqlovchi model muvaffaqiyatli yuklandi!")
    except Exception as e:
        print(f"[ERROR]: Modelni yuklashda xatolik: {e}")
        model = None

# 2. API Endpoint: /api/predict-bone-age
@app.route('/api/predict-bone-age', methods=['POST'])
def predict_bone_age():
    if model is None:
        return jsonify({'error': 'Model serverda yuklanmagan yoki topilmagan.'}), 500

    if 'image' not in request.files:
        return jsonify({'error': 'Rasm yuborilmadi. Kalit so`z "image" bo`lishi kerak.'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Fayl tanlanmagan'}), 400

    is_female_param = request.form.get('is_female', 'false').lower()
    is_female = is_female_param in ['true', '1', 'yes']

    try:
        img_bytes = file.read()
        img_pillow = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        img_resized = img_pillow.resize(IMG_SIZE)
        img_array = np.array(img_resized) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        gender_value = 1.0 if is_female else 0.0
        gender_array = np.array([[gender_value]], dtype='float32')

        preds = model.predict({
            "image_input": img_array, 
            "gender_input": gender_array
        }, verbose=0)
        
        pred_oy = float(preds[0][0])
        pred_oy = max(0, pred_oy)
        oylik_natija = int(round(pred_oy))

        yillar = oylik_natija // 12
        qoldiq_oylar = oylik_naturasi = oylik_natija % 12

        return jsonify({
            'jinsi': 'Ayol' if is_female else 'Erkak',
            'jami_oylik': oylik_natija,
            'formatlangan_yosh': f"{yillar} yosh, {qoldiq_oylar} oy",
            'yosh_yil': round(pred_oy / 12, 1)
        }), 200

    except Exception as e:
        return jsonify({'error': f"Xatolik yuz berdi: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8002, debug=True)