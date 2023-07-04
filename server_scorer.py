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

DEFAULT_PORT = 8095
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

def CheckAuthentication(request_body):
     # extract out user token from request body
    print("Checking authentication", request_body)
    try:
        user_token = request_body['user_token']
    except:
        return {"error": "User not authenticated"}, 400

    decoded_token = auth.verify_id_token(user_token)

    # remove user token from request body
    del request_body['user_token']

    user_id = decoded_token['uid']
    print(decoded_token)

    # check if user is allowed to use the API
    try:
        balance = 0
        # balance = float(decoded_token['balance'])
    except:
        return {"error": "User has not authenticated their metamask"}, 400
    
    if balance < DEFAULT_MINIMUM_WTAO_BALANCE:
        needed = DEFAULT_MINIMUM_WTAO_BALANCE - balance
        return {"error": f"User has insufficient wTAO balance, minimum needed: {DEFAULT_MINIMUM_WTAO_BALANCE} balance: {balance} needed: {needed}"}, 400
    return {"success": "User authenticated", "token": user_token, "decoded_token": decoded_token, "user_id": user_id}

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

# process strings that have , in them, safe for csv
def process_string(string):
    
    # remove newlines
    string = string.replace("\n", "")
    # remove carriage returns
    string = string.replace("\r", "")
    # remove tabs
    string = string.replace("\t", "")

    if "," in string:
        return f"\"{string}\""
    return string

def add_prompt_to_blocked(userid, prompt, negative_prompt, percentage_blocked):
    # make file name if it doesn't exist
    # create directory for outputs under ./outputs
    filename = "blocked.csv"
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    filename = f"outputs/{filename}"
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write("timestamp,userid,percentage_blocked,prompt,negative_prompt\n")
    with open(filename, 'a') as f:
        timestamp_in_milliseconds = int(round(time.time() * 1000))
        f.write(f"{timestamp_in_milliseconds},{userid},{percentage_blocked},{process_string(prompt)},{process_string(negative_prompt)}\n")

def add_prompt_to_passed(userid, prompt, negative_prompt, resolution, average_score, top_4_models, top_4_scores, top_4_seeds, percentage_blocked,image_hashes,parent_hashes ):
    # make file name if it doesn't exist
    # create directory for outputs under ./outputs
    filename = "passed.csv"
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    filename = f"outputs/{filename}"
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write("timestamp,userid,average_score,top_4_models,top_4_scores,top_4_seeds,image_hashes,parent_hashes,percentage_blocked,prompt,negative_prompt,resolution\n")
    with open(filename, 'a') as f:
        timestamp_in_milliseconds = int(round(time.time() * 1000))
        f.write(f"{timestamp_in_milliseconds},{userid},{average_score},{process_string(str(top_4_models))},{process_string(str(top_4_scores))},{process_string(str(top_4_seeds))},{process_string(str(image_hashes))},{process_string(str(parent_hashes))},{percentage_blocked},{process_string(prompt)},{process_string(negative_prompt)},{resolution}\n")

active_users = {}

def create_app():
    app = Flask(__name__)

    CORS(app)

    # API endpoint to forward the request to the local API
    @app.route('/TextToImage/Score', methods=['POST'])
    def forward_request():  

        request_body = request.get_json()['request']

        user_id = request_body['user_id']

        try:
            response = request.get_json()['response']
            all_images = response['data']['images']

            if len(all_images) > 4:
                print("more than 4 images!")
                # determine top 4 images using predict_pil
                image_score_pair = []
                for image in all_images:
                    image_bytes = base64.b64decode(image['image'])
                    image_pil = Image.open(io.BytesIO(image_bytes))
                    score = predict_pil(image_pil)
                    image['aesthetic_score'] = score
                    print(f"score: {score}")
                    image_score_pair.append((image, score))

                # remove all scores less than 5.0
                image_score_pair_blocked = [pair for pair in image_score_pair if pair[1] < 4.61]
                # get percentage of images that were blocked
                percentage_blocked = len(image_score_pair_blocked) / len(image_score_pair)
                bt.logging.trace(f"percentage blocked: {percentage_blocked}")
                # if more than 50% of images were blocked, return error
                if percentage_blocked > 0.85:
                    add_prompt_to_blocked(user_id, request_body['text'], request_body['negative_prompt'], percentage_blocked)
                    return {"error": "Too many images were blocked"}, 400
                
                non_blocked = [pair for pair in image_score_pair if pair[1] >= 4.61]
                avg_image_scores = sum([pair[1] for pair in non_blocked]) / len(non_blocked)
                
                image_score_pair.sort(key=lambda x: x[1], reverse=True)

                top_4_images_scores = [pair[1] for pair in image_score_pair[:4]]
                top_4_image_seeds = [pair[0]['seed'] for pair in image_score_pair[:4]]

                resolution = image_score_pair[0][0]['resolution']
                print(image_score_pair[0][0].keys())
                image_hashes = [pair[0]['image_hash'] for pair in image_score_pair[:4]]
                parent_hashes = [pair[0]['parent_hash'] for pair in image_score_pair[:4]]
                # filter hashes for None or ''
                image_hashes = [hash for hash in image_hashes if hash]
                parent_hashes = [hash for hash in parent_hashes if hash]
                # deduplicate hashes
                parent_hashes_dedupe = list(set(parent_hashes))
                models = [pair[0]['model_type'] for pair in image_score_pair[:4]]

                add_prompt_to_passed(user_id, request_body['text'], request_body['negative_prompt'], resolution, avg_image_scores,models, top_4_images_scores, top_4_image_seeds, percentage_blocked,image_hashes, parent_hashes_dedupe if len(parent_hashes_dedupe) == 1 else parent_hashes)
                # print scores
                for pair in image_score_pair:
                    bt.logging.trace(pair[1], pair[0]['model_type'])
                top_4_images_and_scores = image_score_pair[:4]
                top_4_images = [image[0] for image in top_4_images_and_scores]
                # print model and score for each image
                for image in top_4_images_and_scores:
                    score = image[1]
                    bt.logging.trace(f"score: {score} - model: {image[0]['model_type']}")
            else:
                top_4_images = all_images
            
            # update response object to only be the top 4 images
            response['data']['images'] = top_4_images

            return response
        except Exception as e:
            print(e)
            return {"error": "Something went wrong"}, 400
    return app


if __name__ == '__main__':
    # create the app
    app = create_app()

    # run the app
    serve(app, host='0.0.0.0', port=DEFAULT_PORT)