import os
import shutil
from collections import defaultdict
from sklearn.model_selection import train_test_split

# Yo'llar (Sizning papkalaringizga moslangan)
source_images = "datasetPCa/images"
source_labels = "datasetPCa/labels"

output_folder = "../prostate_final_dataset"

# Papkalarni yaratish
for split in ['train', 'val']:
    os.makedirs(os.path.join(output_folder, 'images', split), exist_ok=True)
    os.makedirs(os.path.join(output_folder, 'labels', split), exist_ok=True)

# Fayllarni klasslar bo'yicha guruhlash
image_files = [f for f in os.listdir(source_images) if f.endswith(('.jpg', '.png', '.jpeg'))]
data_by_class = defaultdict(list)

for img_file in image_files:
    label_file = os.path.splitext(img_file)[0] + ".txt"
    label_path = os.path.join(source_labels, label_file)
    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            lines = f.readlines()
            if lines:
                cls = lines[0].split()[0]
                data_by_class[cls].append(img_file)

# 80/20 nisbatda ajratish
train_list, val_list = [], []
for cls, files in data_by_class.items():
    if len(files) > 1:
        tr, vl = train_test_split(files, test_size=0.20, random_state=42)
        train_list.extend(tr)
        val_list.extend(vl)
    else:
        train_list.extend(files)

# Nusxalash funksiyasi
def copy_data(file_list, split_name):
    for img_file in file_list:
        label_file = os.path.splitext(img_file)[0] + ".txt"
        shutil.copy(os.path.join(source_images, img_file), 
                    os.path.join(output_folder, 'images', split_name, img_file))
        shutil.copy(os.path.join(source_labels, label_file), 
                    os.path.join(output_folder, 'labels', split_name, label_file))

copy_data(train_list, 'train')
copy_data(val_list, 'val')

print(f"\nBajarildi! Jami: {len(image_files)} rasm.")
print(f"Train: {len(train_list)} ta, Val: {len(val_list)} ta.")
print(f"Dataset manzil: {os.path.abspath(output_folder)}")

