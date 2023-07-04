import base64
import io
from PIL import Image
from .bittensor import bt

def verify_base64_image(base64_string):
    try:
        # Decode the base64 string
        image_data = base64.b64decode(base64_string)

        # Create a BytesIO object from the decoded image data
        image_buffer = io.BytesIO(image_data)

        # Attempt to open the image using PIL
        img = Image.open(image_buffer)

        # Check if the image can be loaded without errors
        img.verify()

        return True

    except (IOError, SyntaxError) as e:
        bt.logging.error("Invalid image: {}".format(e))
        return False