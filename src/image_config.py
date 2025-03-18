from PIL import Image

image_path = "/Users/arx/Documents/mocomoco/businessCard/jpg/IMG_0795.jpg"

try:
    with Image.open(image_path) as img:
        print("Format:", img.format)
        print("Size:", img.size)
        print("Mode:", img.mode)
except Exception as e:
    print("Error:", e)
