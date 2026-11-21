
from pathlib import Path

if __package__:
    from .inference import load_model
else:
    from inference import load_model


def main():
    prototype_dir = Path(__file__).resolve().parent
    model = load_model()

    print("IA chargée avec succès !")
    print("Classes détectées :", model.names)

    model.predict(
        source=str(prototype_dir / "Image0775_jpg.rf.zixLWQaadRkNFH9RAH1P.jpg"),
        conf=0.5,
        save=True,
    )
    model.predict(
        source=str(prototype_dir / "test.mp4"),
        conf=0.5,
        save=True,
        show=True,
    )

    print("Analyse terminée !")


if __name__ == "__main__":
    main()
