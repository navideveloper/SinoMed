import cv2
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model

MODEL_PATH = 'tibbiy_model_pnevmoniya.h5' 
# IMAGE_PATH = 'test-abnormal.png' 
IMAGE_PATH = 'test-normal.png'
IMG_SIZE = (150, 150)

model = load_model(MODEL_PATH)
print("[INFO]: Model muvaffaqiyatli yuklandi!")

img_bgr = cv2.imread(IMAGE_PATH)
if img_bgr is None:
    raise FileNotFoundError(f"Rasm topilmadi: {IMAGE_PATH}")

img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
img_resized = cv2.resize(img_rgb, IMG_SIZE)
img_array = np.expand_dims(img_resized, axis=0) / 255.0

prediction = model.predict(img_array)[0][0]

if prediction > 0.5:
    result_text = f"PNEVMONIYA (Ehtimollik: {prediction*100:.2f}%)"
    text_color = 'red'
else:
    result_text = f"SOG'LOM (Ehtimollik: {(1-prediction)*100:.2f}%)"
    text_color = 'green'

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

heatmap = make_gradcam_heatmap_keras3(img_array, model)

heatmap_resized = cv2.resize(heatmap, (img_bgr.shape[1], img_bgr.shape[0]))
heatmap_uint8 = np.uint8(255 * heatmap_resized)
heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
heatmap_color_rgb = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)

superimposed_img = cv2.addWeighted(img_rgb, 0.6, heatmap_color_rgb, 0.4, 0)

plt.figure(figsize=(12, 6))

plt.subplot(1, 2, 1)
plt.title("Asl Rentgen", fontsize=12)
plt.imshow(img_rgb)
plt.axis('off')

plt.subplot(1, 2, 2)
plt.title("Kasallik Joyi (Grad-CAM)", fontsize=12)
plt.imshow(superimposed_img)
plt.axis('off')

plt.suptitle(result_text, color=text_color, fontsize=16, weight='bold', y=0.98)
plt.tight_layout()
plt.show()