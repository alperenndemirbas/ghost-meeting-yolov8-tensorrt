# 👻 Ghost Meeting — Görüntü İşleme ve Donanım Performans Testi (PoC)

Bu proje, **TD SYNNEX** staj sunumu kapsamında geliştirilmiş bir kavram kanıtlama (Proof of Concept) uygulamasıdır. 

Temel amacı; gerçek zamanlı bir görüntü işleme (Computer Vision) senaryosu üzerinden yapay zeka modellerinin çalışma mantığını göstermek ve **standart işlemci (CPU)** ile **NVIDIA GPU (TensorRT Engine)** arasındaki çıkarım gecikmesini (Inference Latency - `ms`) ve `FPS` farkını somut olarak kıyaslamaktır.

---

## 🎯 Projenin Amacı ve Çalışma Mantığı

Sistem, kamera görüntülerini gerçek zamanlı işleyerek toplantı odasındaki insanları tespit eder ve odanın doluluk durumunu belirler:

* **Donanım Kıyaslaması (CPU vs. GPU):** Kullanıcı arayüzü üzerinden işlem yükü anlık olarak **CPU (`yolov8n.pt`)** veya **GPU (`yolov8n.engine` - TensorRT)** üzerine aktarılabilir. Her bir kare (frame) için modelin karar verme süresi milisaniye (`ms`) cinsinden ekrana yansıtılarak donanım hızlandırmanın etkisi canlı olarak gözlemlenir.
* **Akıllı Durum Yönetimi:** Anlık yanlış algılamaları önlemek için 3 saniyelik bir zamanlayıcı (debounce) mekanizması bulunur. Odada 3 saniye boyunca insan algılanırsa durum **"Oda Müsait Değil"**, kimse algılanmazsa **"Oda Müsait"** olarak güncellenir.

---

## 🔮 Gelecek Vizyonu ve Geliştirme Planları

Bu temel prototip, ilerleyen aşamalarda çok modüllü (Multimodal) bir akıllı ofis asistanına dönüştürülmek üzere tasarlanmıştır:

* **Sesli Etkileşim ve LLM Entegrasyonu:** Odada 3 saniye boyunca bir kişi tespit edildiğinde sistem sesli olarak *"Oda sizin için rezerve edilsin mi?"* sorusunu yöneltecektir. Kullanıcının verdiği sesli yanıt (Örn: *"Evet, 1 saatliğine rezerve et"*) Büyük Dil Modeli (LLM) tarafından işlenerek anlamlandırılacaktır.
* **Yüz Tanıma (Face Recognition) ile Kimlik Doğrulama:** Rezervasyon onaylandığında yüz tanıma algoritması devreye girerek içerideki kişinin kim olduğunu tespit edecek ve odayı doğrudan o personelin adına, istenen süre boyunca sistemde rezerve edecektir.
* **Sesli Çıkış Komutu:** Toplantı planlanandan erken bittiğinde, kullanıcı odadan çıkarken sisteme seslenerek rezervasyonu sonlandırabilecek ve odayı anında tekrar **"Oda Müsait"** durumuna çekebilecektir.

---

## 🛠️ Kullanılan Teknolojiler

* **Model & Optimizasyon:** YOLOv8n (Ultralytics), NVIDIA TensorRT, CUDA
* **Görüntü İşleme:** OpenCV, PyAV
* **Arayüz & Canlı Akış:** Streamlit, Streamlit-WebRTC

---

## 🚀 Kurulum ve Çalıştırma

Model ağırlık dosyaları (`.pt` ve `.engine`) boyutları nedeniyle bu repoya dahil edilmemiştir. Projeyi yerel ortamınızda çalıştırmak için:

1. **Gerekli kütüphaneleri yükleyin:**
   ```bash
   pip install -r requirements.txt

2. **Model dosyalarını hazırlayın:**

    CPU testi için standart yolov8n.pt modelini, GPU testi için ise TensorRT formatına dönüştürülmüş yolov8n.engine dosyasını ana dizine ekleyin.

3. **Uygulamayı başlatın:**
    ```bash
    streamlit run app.py