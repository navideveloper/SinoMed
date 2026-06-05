import tensorflow as tf
import numpy as np
import os
from PIL import Image

model_fayli = 'suyak_yoshi_gender_model.keras'

if not os.path.exists(model_fayli):
    exit()

model = tf.keras.models.load_model(model_fayli)

def suyak_yoshini_aniqla(rasm_manzili, is_female=False):
    img_pillow = Image.open(rasm_manzili).convert('RGB')
    img_resized = img_pillow.resize((224, 224))
    img_array = np.array(img_resized) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    gender_value = 1.0 if is_female else 0.0
    gender_array = np.array([[gender_value]], dtype='float32')

    pred_oy = model.predict({
        "image_input": img_array, 
        "gender_input": gender_array
    }, verbose=0)[0][0]
    
    pred_oy = max(0, float(pred_oy))
    
    return {
        "oylik": int(round(pred_oy)),
    }

MALE = False
FEMALE = True
TEST_GENDER = FEMALE
TEST_IMAGE = 'test-rasm.png'
TEST_AGE = 11*12+3
natija = suyak_yoshini_aniqla(TEST_IMAGE, is_female=TEST_GENDER)
FARQ = (natija['oylik'] - TEST_AGE)

print(f"\rFarq: {"+" if FARQ>=0 else ""}{FARQ} oy")
