# This file runs on the same server as server_rabbit and image_process.py
# it is used to score the images from server_rabbit and send the results to server_wrapper.py on another server

from flask import Flask, request, send_from_directory
# pip install flask-cors
from flask_cors import CORS
import os
import uuid
import threading
import random
import pika
import json
import base64
import io
from PIL import Image
import hashlib
import datetime
import time
import bittensor as bt

from waitress import serve
import requests

from inference import predict_pil


DEFAULT_PORT = 8093
DEFAULT_AXON_IP = "127.0.0.1"
DEFAULT_AXON_PORT = 9090
DEFAULT_RESPONSE_TIMEOUT = 60
DEFAULT_INFERENCE_STEPS = 90

FORWARD_TO_IP = "127.0.0.1:8094"

# auth values
DEFAULT_MINIMUM_WTAO_BALANCE = 0
NEEDS_AUTHENTICATION = True
NEEDS_METAMASK_VERIFICATION = False
SAVE_IMAGES = False

app = Flask(__name__, static_folder='build', static_url_path='/')

CORS(app)


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

        print("Valid image!")
        return True

    except (IOError, SyntaxError) as e:
        print("Invalid image:", e)
        return False


active_users = {}

def create_app(is_local):
    # if local serve static folder
    is_local = True
    if is_local:
        app = Flask(__name__, static_folder='build', static_url_path='/')
    else:
        app = Flask(__name__)

    CORS(app)

    if is_local:
        # Serve the ./build folder
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve(path):
            if path != "" and os.path.exists("build/" + path):
                return send_from_directory('build', path)
            else:
                return send_from_directory('build', 'index.html')

    # API endpoint to forward the request to the local API
    @app.route('/TextToImage/Forward', methods=['POST'])
    def forward_request():  

        request_body = {**request.json, 'num_images_per_prompt': 1}

        # check to see if user is already in queue
        # if user is in queue, return error
        if (active_users.get(user_id) != None):
            # if request is older than 1m, pass else return error
            then = active_users[user_id][0]
            if datetime.datetime.now() - then > datetime.timedelta(minutes=1):
                del active_users[user_id]
            else:
                return {"error": "User already in queue"}, 400
        
        def random_seed(min,max):
            return random.randint(min,max)

        correlation_id = str(uuid.uuid4())
        seed = random_seed(0, 1000000000)
        time_to_loop = 40
        request_body['seed'] = seed
        request_body['correlation_id'] = correlation_id
        request_body['time_to_loop'] = time_to_loop
        active_users[user_id] = (datetime.datetime.now(), correlation_id)

        try:

            # forward the request to the local API
            response = requests.post("http://" + FORWARD_TO_IP + "/TextToImage/Forward", json=request_body)

            response = response.json()
            print(dir(response))

            print("trying to get images from response")
            all_images = response['data']['images']
            print('got all images', type(all_images))

            if len(all_images) > 4:
                print("more than 4 images!")
                # determine top 4 images using predict_pil
                image_score_pair = []
                for image in all_images:
                    image_bytes = base64.b64decode(image['image'])
                    image_pil = Image.open(io.BytesIO(image_bytes))
                    score = predict_pil(image_pil)
                    print(f"score: {score}")
                    image_score_pair.append((image, score))
                image_score_pair.sort(key=lambda x: x[1], reverse=True)
                # print scores
                for pair in image_score_pair:
                    print(pair[1])
                top_4_images_and_scores = image_score_pair[:4]
                top_4_images = [image[0] for image in top_4_images_and_scores]
            else:
                top_4_images = all_images
                # print model and score for each image
                for image in top_4_images_and_scores:
                    score = image[1]
                    print(f"score: {score} - model: {image[0]['model_type']}")
                print('got 4 images in total')
            
            # update response object to only be the top 4 images
            response['data']['images'] = top_4_images

            return response
        except Exception as e:
            print(e)
            return {"error": "Something went wrong"}, 400
    return app


if __name__ == '__main__':
        # create the app
    app = create_app(True)

    # run the app
    serve(app, host='0.0.0.0', port=DEFAULT_PORT)