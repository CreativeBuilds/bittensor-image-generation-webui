from inference import predict_pil, img_path
from PIL import Image


if __name__ == "__main__":
    pil_image = Image.open(img_path)
    prediction = predict_pil(pil_image)
    print("Predicted aesthetic score:", prediction)