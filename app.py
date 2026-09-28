import cv2
import time
import av
import streamlit as st
from ultralytics import YOLO
from streamlit_webrtc import webrtc_streamer

# --- 1. ARAYÜZ AYARLARI ---
st.set_page_config(page_title="Ghost Meeting Architecture PoC", layout="wide")
st.title("👻 Ghost Meeting")

# --- 2. DONANIM VE MODEL SEÇİMİ ---
donanim = st.radio(
    "İşlem Yükü Hangi Donanıma Verilsin?",
    ("GPU (NVIDIA TensorRT Engine)", "CPU (Standart İşlemci)"),
    index=0
)

@st.cache_resource
def load_selected_model(secim):
    if "GPU" in secim:
        return YOLO('yolov8n.engine', task='detect'), "cuda"
    else:
        m = YOLO('yolov8n.pt')
        m.to('cpu')
        return m, "cpu"

model, device_type = load_selected_model(donanim)

# --- 3. GÖRÜNTÜ İŞLEME VE DURUM YÖNETİMİ ---
class GhostMeetingProcessor:
    def __init__(self):
        self.dolu_baslangic = None
        self.bos_baslangic = None
        self.BEKLEME_SURESI = 3.0
        self.oda_durumu = "Oda Musait"
        self.durum_rengi = (0, 255, 0)
        self.onceki_zaman = time.time()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        su_an = time.time()

        # Toplam Kare FPS
        gecen_sure = su_an - self.onceki_zaman
        fps = 1 / gecen_sure if gecen_sure > 0 else 0
        self.onceki_zaman = su_an

        # Çıkarım Gecikmesi (Latency / ms)
        t_baslangic = time.perf_counter()
        if device_type == "cuda":
            results = model(img, classes=[0], verbose=False)
        else:
            results = model(img, classes=[0], device='cpu', verbose=False)
        t_bitis = time.perf_counter()
        latency_ms = (t_bitis - t_baslangic) * 1000

        kisi_sayisi = 0
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                
                if conf > 0.50:
                    kisi_sayisi += 1
                    x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                    
                    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    etiket = f"Kisi: %{int(conf * 100)}"
                    (w, h), _ = cv2.getTextSize(etiket, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(img, (x1, y1 - h - 10), (x1 + w, y1), (255, 0, 0), -1)
                    cv2.putText(img, etiket, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Karar Mekanizması
        if kisi_sayisi > 0:
            self.bos_baslangic = None
            if self.dolu_baslangic is None:
                self.dolu_baslangic = su_an
            elif su_an - self.dolu_baslangic > self.BEKLEME_SURESI:
                self.oda_durumu = "Oda Musait Degil"
                self.durum_rengi = (0, 0, 255)
        else:
            self.dolu_baslangic = None
            if self.bos_baslangic is None:
                self.bos_baslangic = su_an
            elif su_an - self.bos_baslangic > self.BEKLEME_SURESI:
                self.oda_durumu = "Oda Musait"
                self.durum_rengi = (0, 255, 0)

        # Metrik Çıktıları
        cv2.putText(img, f"Kisi Sayisi: {kisi_sayisi}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(img, self.oda_durumu, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.durum_rengi, 2)
        cv2.putText(img, f"FPS: {int(fps)}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        latency_renk = (0, 255, 0) if latency_ms < 15 else (0, 0, 255)
        cv2.putText(img, f"Inference Latency: {latency_ms:.1f} ms ({device_type.upper()})", (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, latency_renk, 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- 4. KAMERA BAŞLATICI ---
webrtc_streamer(
    key="ghost_meeting_poc",
    video_processor_factory=GhostMeetingProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={
        "video": {"frameRate": {"ideal": 30, "max": 60}, "width": 640, "height": 480},
        "audio": False
    }
)