# this is a server endpoint on a different machine, used to authenticate the user and to forward the request to the local API

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

import firebase_admin

from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import auth
from firebase_admin import storage
from waitress import serve
import requests

DEFAULT_PORT = 8093
DEFAULT_AXON_IP = "127.0.0.1"
DEFAULT_AXON_PORT = 9090
DEFAULT_RESPONSE_TIMEOUT = 60
DEFAULT_INFERENCE_STEPS = 90

FORWARD_TO_IP = "127.0.0.1:8094"
IMAGE_SCORER_IP = "127.0.0.1:8085"

# auth values
DEFAULT_MINIMUM_WTAO_BALANCE = 0
NEEDS_AUTHENTICATION = True
NEEDS_METAMASK_VERIFICATION = False
SAVE_IMAGES = False

app = Flask(__name__, static_folder='build', static_url_path='/')

CORS(app)

cred = credentials.Certificate("firebase-pkey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'image-gen-webui.appspot.com'
})

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
        print("Forwarding request")
        request_body = {**request.json, 'num_images_per_prompt': 1}

        if NEEDS_AUTHENTICATION:
                response = CheckAuthentication(request.json)
                user_id = response['user_id']
                if NEEDS_METAMASK_VERIFICATION:
                    balance = float(response['decoded_token']['balance'])
                else:
                    balance = 0
                if 'error' in response:
                    return response, 400

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
        time_to_loop = 15
        request_body['seed'] = seed 
        request_body['correlation_id'] = correlation_id
        request_body['time_to_loop'] = time_to_loop
        request_body['user_id'] = user_id
        active_users[user_id] = (datetime.datetime.now(), correlation_id)

        doc_data = None

        try:
            if NEEDS_AUTHENTICATION:
                # add request to firestore under generations collection
                db = firestore.client()
                doc_ref = db.collection(u'generations').document(correlation_id)
                image_url = ""
                # if image in request body, upload to firebase storage
                if 'image' in request_body:
                    image = request_body['image']
                    parent_image_url = ""
                    parent_image_hash = ""
                    if(image != "" and SAVE_IMAGES):
                        # ensure image provided is valid
                        try:
                            verify_base64_image(image)
                            decoded_image = base64.b64decode(image)
                            parent_image_hash = hashlib.sha256(decoded_image).hexdigest()

                            # see if image already exists in storage
                            image_doc_ref = db.collection(u'images').document(parent_image_hash)
                            image_doc_snapshot = image_doc_ref.get()
                            exists = image_doc_snapshot.exists
                            if exists:
                                # image already exists, use existing url
                                image_url = image_doc_snapshot.get('url')
                            else:
                                image_name = str(parent_image_hash) + ".png"
                                bucket = storage.bucket()
                                blob = bucket.blob(image_name)
                                image_bytes = io.BytesIO(decoded_image)
                                img = Image.open(image_bytes)
                                # save img to ./images folder
                                # img.save(f"/home/creativebuilds/Projects/image-generation-webui/images/{image_name}", format="JPEG")
                                # save image to firebase storage
                                with io.BytesIO() as output:
                                    img.save(output, format='JPEG')
                                    blob.upload_from_string(output.getvalue(), content_type='image/jpeg')
        
                                parent_image_url = blob.public_url
                                bt.logging.trace(f"Uploaded image to firebase storage with url: {parent_image_url}")
                                request_body['image_url'] = parent_image_url
                                image_doc_ref = db.collection(u'images').document(parent_image_hash)
                                image_doc_ref.set({
                                    u'uploader': user_id,
                                    u'url': parent_image_url,
                                    u'hash': parent_image_hash,
                                })
                        except Exception as e:
                            print(e)
                            active_users[user_id] = (datetime.datetime.now(), correlation_id)
                            return {"error": "Invalid image provided"}, 400
                    elif(image != "" and not SAVE_IMAGES):
                        bt.logging.trace(f"Image provided but SAVE_IMAGES is set to False (skipping upload)")
                    doc_data = {
                        u'uid': user_id,
                        u'prompt': request_body['text'],
                        u'negative_prompt': request_body['negative_prompt'],
                        u'parent_image_url': parent_image_url,
                        u'parent_image_hash': parent_image_hash,
                        u'num_images': 4,
                        u'balance': balance,
                        u'seed': seed,
                        u'children_image_hashes': [],
                        u'children_image_urls': [],
                        u'date': int(time.time() * 1000)
                    }
                    bt.logging.trace(f"Added request to firestore with correlation_id: {correlation_id}")



            # forward the request to the local API
            response = requests.post("http://" + FORWARD_TO_IP + "/TextToImage/Forward", json=request_body)

            if (response.status_code != 200):
                error_msg = response.json()['error']
                print(error_msg)
                return {"error": error_msg}, 400

            response = response.json()
            try:
                if response['error']:
                    return response, 400
            except:
                pass
            all_images = response['data']['images']

            if len(all_images) == 0:
                return {"error": "No images generated"}, 400

            # send to scorer ip
            score_response = requests.post("http://" + IMAGE_SCORER_IP + "/TextToImage/Score", json={"request": request_body, "response": response})
            all_images = score_response.json()['data']['images']
            response['data']['images'] = all_images

            try:
                if doc_data and SAVE_IMAGES:
                    for img_info in all_images:
                        decoded_image = base64.b64decode(img_info['image'])
                        image_hash = hashlib.sha256(decoded_image).hexdigest()

                        # add image to doc data
                        doc_data['children_image_hashes'].append(image_hash)

                        # see if image already exists in storage
                        image_doc_ref = db.collection(u'images').document(image_hash)
                        image_doc_snapshot = image_doc_ref.get()
                        exists = image_doc_snapshot.exists
                        if exists:
                            # image already exists, use existing url
                            image_url = image_doc_snapshot.get('url')
                        else:
                        
                            image_name = str(image_hash) + ".png"
                            bucket = storage.bucket()
                            blob = bucket.blob(image_name)
                            image_bytes = io.BytesIO(decoded_image)

                            # save img to ./images folder
                            img = Image.open(image_bytes)
                            img.save(f"/home/creativebuilds/Projects/image-generation-webui/images/{image_name}", format="JPEG")

                            # save image to firebase storage
                            with io.BytesIO() as output:
                                img.save(output, format='JPEG')
                                blob.upload_from_string(output.getvalue(), content_type='image/jpeg')

                            image_url = blob.public_url

                            # add image to firestore
                            image_doc_ref.set({
                                u'uploader': user_id,
                                u'url': image_url,
                                u'hash': image_hash,
                            })

                        doc_data['children_image_urls'].append(image_url)
                elif doc_data and not SAVE_IMAGES:
                    bt.logging.trace(f"SAVE_IMAGES is set to False (skipping upload)")
            except Exception as e:
                print(e)

            # add request to firestore
            # if doc_data:
                # doc_ref = db.collection(u'requests').document(correlation_id)
                # doc_ref.set(doc_data)
                # bt.logging.trace(f"Added request to firestore with correlation_id: {correlation_id}")

            # Remove user from dict
            del active_users[user_id]
            print("sending back response")
            return response
        except Exception as e:
            print(e)
            print("Something went wrong!")
            del active_users[user_id]
            return {"error": "Something went wrong"}, 400
    return app


if __name__ == '__main__':
    # create the app
    app = create_app(True)

    # run the app
    serve(app, host='0.0.0.0', port=DEFAULT_PORT)