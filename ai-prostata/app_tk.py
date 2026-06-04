


import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import torch
import os
import pathlib
import warnings

if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

warnings.filterwarnings("ignore", category=FutureWarning, message=".*torch.cuda.amp.autocast.*")

# 1. Modelni yuklash
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
# Model yo'lini tekshirib oling (exp6 yoki exp5)
repo_dir = os.path.dirname(os.path.abspath(__file__))
model = torch.hub.load(repo_dir, 'custom', path='runs/train/exp6/weights/best.pt', source='local', device=device)
print("Model yuklandi. Tkinter oynasi ochilmoqda...")

model.names = ["benign (%)", "grade3 (%)", "grade4 (%)", "grade5 (%)"]

DIAGNOSIS_INFO = {
    "benign (%)": "Sog'lom to'qima: Saraton hujayralari aniqlanmadi.",
    "grade3 (%)": "Gleason Grade 3: Saratonning o'rta darajasi. Hujayralar nisbatan sekin rivojlanmoqda.",
    "grade4 (%)": "Gleason Grade 4: Agressiv o'simta. Saraton hujayralari tartibsiz joylashgan.",
    "grade5 (%)": "Gleason Grade 5: Eng og'ir bosqich. Saraton to'qimalari keng tarqalgan."
}

BENIGN_LABELS = ("benign", "sog", "healthy", "normal")

def is_disease_label(label):
    label = str(label).lower()
    return not any(word in label for word in BENIGN_LABELS)

class ProstateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gleason Grading AI System - Xaydarov Abdurasul")
        self.root.geometry("1200x900")
        self.root.configure(bg="#f8f9fa")

        # Oynani moslashuvchan (flexible) qilish
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1) # Rasm konteyneriga asosiy joyni beramiz

        # 1. Mualliflik yozuvi
        self.author = tk.Label(self.root, text="Created by Xaydarov Abdurasul", 
                               font=("Arial", 11, "italic"), bg="#f8f9fa", fg="#6c757d")
        self.author.grid(row=0, column=0, sticky="ne", padx=30, pady=10)

        # 2. Asosiy Sarlavha
        self.header = tk.Label(self.root, text="Prostata bezi saratoni tashxisi (AI tizimi)", 
                               font=("Helvetica", 26, "bold"), bg="#f8f9fa", fg="#212529")
        self.header.grid(row=1, column=0, pady=10, sticky="ew")

        # 3. Rasmlar uchun asosiy konteyner (Grid ishlatamiz)
        self.main_container = tk.Frame(self.root, bg="#f8f9fa")
        self.main_container.grid(row=2, column=0, sticky="nsew", padx=20)
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=1)
        self.main_container.rowconfigure(0, weight=1)

        # --- Chap panel (Asl rasm) ---
        self.left_frame = tk.Frame(self.main_container, bg="#f8f9fa")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=20)
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.rowconfigure(1, weight=1)

        tk.Label(self.left_frame, text="Asl Gistologik Tasvir", font=("Arial", 14, "bold"), bg="#f8f9fa").grid(row=0, column=0, pady=5)
        
        self.orig_panel = tk.Label(self.left_frame, text="Rasm yuklanmagan", bg="#e9ecef", 
                                   relief="sunken", highlightthickness=1)
        self.orig_panel.grid(row=1, column=0, sticky="nsew")

        # --- O'ng panel (AI Natijasi) ---
        self.right_frame = tk.Frame(self.main_container, bg="#f8f9fa")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=20)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(1, weight=1)

        tk.Label(self.right_frame, text="AI Tahlili (Natija)", font=("Arial", 14, "bold"), bg="#f8f9fa").grid(row=0, column=0, pady=5)
        
        self.res_panel = tk.Label(self.right_frame, text="Natija kutilmoqda", bg="#e9ecef", 
                                  relief="sunken", highlightthickness=1)
        self.res_panel.grid(row=1, column=0, sticky="nsew")

        # 4. Xulosa oynasi
        self.info_box = tk.Label(self.root, text="Tizim tayyor. Iltimos, tahlil uchun rasm yuklang...", 
                                 font=("Arial", 13), bg="#ffffff", fg="#495057",
                                 wraplength=1000, height=4, relief="flat", 
                                 highlightbackground="#dee2e6", highlightthickness=1, padx=20, pady=10)
        self.info_box.grid(row=3, column=0, sticky="ew", padx=100, pady=20)

        # 5. Tugmalar paneli
        self.btn_frame = tk.Frame(self.root, bg="#f8f9fa")
        self.btn_frame.grid(row=4, column=0, pady=20)

        self.btn_load = tk.Button(self.btn_frame, text="📁 Rasm yuklash", command=self.load_image, 
                                  bg="#2ecc71", fg="white", font=("Arial", 14, "bold"), padx=40, pady=12, cursor="hand2")
        self.btn_load.pack(side=tk.LEFT, padx=20)

        self.btn_exit = tk.Button(self.btn_frame, text="❌ Chiqish", command=self.root.quit, 
                                  bg="#e74c3c", fg="white", font=("Arial", 14, "bold"), padx=40, pady=12, cursor="hand2")
        self.btn_exit.pack(side=tk.LEFT, padx=20)

    def format_image(self, img, panel):
        # Panel o'lchamini aniqlaymiz (Flexible bo'lishi uchun)
        self.root.update_idletasks()
        p_width = panel.winfo_width()
        p_height = panel.winfo_height()
        
        if p_width < 10: p_width = 500 # Dastlabki yuklash uchun
        if p_height < 10: p_height = 500

        img.thumbnail((p_width, p_height))
        new_img = Image.new("RGB", (p_width, p_height), (233, 236, 239))
        new_img.paste(img, ((p_width - img.size[0]) // 2, (p_height - img.size[1]) // 2))
        return ImageTk.PhotoImage(new_img)

    def load_image(self):
        file_path = filedialog.askopenfilename()
        if not file_path: return
        try:
            # 1. Asl rasm
            orig_img = Image.open(file_path)
            self.tk_orig = self.format_image(orig_img, self.orig_panel)
            self.orig_panel.config(image=self.tk_orig, text="")

            # 2. AI Tahlili
            model.conf = 0.25 
            results = model(orig_img)
            predictions = results.pandas().xyxy[0]

            results.render()
            res_img = Image.fromarray(results.ims[0])
            self.tk_res = self.format_image(res_img, self.res_panel)
            self.res_panel.config(image=self.tk_res, text="")

            # 3. Tashxis xulosasi
            if not predictions.empty:
                disease_predictions = predictions[predictions['name'].apply(is_disease_label)]
                disease_probability = 0 if disease_predictions.empty else int(round(disease_predictions['confidence'].max() * 100))
                summary = f"AI TAHLILI NATIJASI:\nKasallik mavjudlik ehtimoli: taxminan {disease_probability}%.\n"
                details = ""
                unique_grades = predictions['name'].unique()
                for grade in unique_grades:
                    count = len(predictions[predictions['name'] == grade])
                    max_conf = predictions[predictions['name'] == grade]['confidence'].max()    
                    conf_pct = int(max_conf * 100)
                    summary += f"• {count} ta {grade} ({conf_pct}%) aniqlandi. "
                    details += f"\n- {DIAGNOSIS_INFO.get(grade, '')}"
                color = "#c0392b" if disease_probability > 0 else "#27ae60"
                self.info_box.config(text=summary + details, fg=color)
            else:
                self.info_box.config(text="AI TAHLILI NATIJASI:\nKasallik mavjudlik ehtimoli: taxminan 0%. Aniqlangan soha topilmadi.", fg="#27ae60")
                return

        except Exception as e:
            messagebox.showerror("Xato", f"Xatolik: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProstateApp(root)
    root.lift()
    root.attributes("-topmost", True)
    root.after(1000, lambda: root.attributes("-topmost", False))
    root.mainloop()
