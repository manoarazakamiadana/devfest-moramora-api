
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

# Télécharger automatiquement le modèle
weights = hf_hub_download(
    repo_id="jashwanthpeddisetty0712/violation-detection-yolov8",
    filename="best.pt"
)

# Charger le modèle
model = YOLO(weights)

print("IA chargée avec succès !")
print("Classes détectées :", model.names)

# Tester sur une image
results = model.predict(
    source="Image0775_jpg.rf.zixLWQaadRkNFH9RAH1P.jpg",
    conf=0.5,
    save=True
)

results = model.predict(
    source="test.mp4",
    conf=0.5,
    save=True,
    show=True
)

print("Analyse terminée !")
