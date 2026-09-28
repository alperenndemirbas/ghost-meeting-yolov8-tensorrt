from ultralytics import YOLO

# Standart modeli yükle
model = YOLO('yolov8n.pt')

# NVIDIA TensorRT motoruna (.engine) dönüştür
model.export(format='engine', device=0)