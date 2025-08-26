import torch
import torchvision
from ultralytics import YOLO

print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
model = YOLO("yolov5s.pt")
