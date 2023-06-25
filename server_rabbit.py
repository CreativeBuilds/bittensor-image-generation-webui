from flask import Flask, request, send_from_directory
# pip install flask-cors
from flask_cors import CORS
import os
import bittensor as bt
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


import firebase_admin

from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import auth
from firebase_admin import storage
from waitress import serve
import requests


cred = credentials.Certificate("firebase-pkey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'image-gen-webui.appspot.com'
})

bt.trace()

def load_ips():
    with open("ips.txt") as f:
        lines = f.readlines()
    ips = []
    for line in lines:
        line = line.strip()
        parts = line.split(",")
        ip_port = parts[0].split(":")
        ip = ip_port[0]
        port = int(ip_port[1])
        if len(ip_port) > 2:
            model_type = ip_port[2]
        elif len(parts) > 1:
            model_type = parts[1]
        else:
            model_type = None
        ips.append((ip, port, model_type))
    return ips

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

# parser = argparse.ArgumentParser()

DEFAULT_PORT = 8093
DEFAULT_AXON_IP = "127.0.0.1"
DEFAULT_AXON_PORT = 9090
DEFAULT_RESPONSE_TIMEOUT = 60
DEFAULT_INFERENCE_STEPS = 90

# auth values
DEFAULT_MINIMUM_WTAO_BALANCE = 0
NEEDS_AUTHENTICATION = True
NEEDS_METAMASK_VERIFICATION = False
SAVE_IMAGES = True

# parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port number (default: {})'.format(DEFAULT_PORT))
# parser.add_argument('--axon.ip', type=str, default=DEFAULT_AXON_IP, help='Axon IP address (default: {})'.format(DEFAULT_AXON_IP))
# parser.add_argument('--axon.port', type=int, default=DEFAULT_AXON_PORT, help='Axon port number (default: {})'.format(DEFAULT_AXON_PORT))

# args = vars(parser.parse_args())

args = {}

app = Flask(__name__, static_folder='build', static_url_path='/')
use_local_api = False
default_uid = 4

mg = bt.metagraph(netuid=14, network='test')
mg.sync()

wallet = bt.wallet().create_if_non_existent()

ips = load_ips()     
response_dict = {}
response_events = {}
active_users = {}

measurement_id = "G-033RPYKJ8J"

def firebase_log_event_for_cid(event, cid, params):

    user_id = cid

    query_params = {
        'v': 2,
        'tid': measurement_id,
        '_dbg': 1,
        'uid': user_id,
        'dr': "https://tao.studio",
        'source': "https://tao.studio",
        'en': event,
        'ep': params,
    }

    query_string = "&".join([f"{key}={value}" for key, value in query_params.items()])

    url = f"https://www.google-analytics.com/g/collect?{query_string}"
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-length': '0',
        'Content-Type': 'text/plain;charset=UTF-8',
        'origin': 'http://localhost:3000',
        'pragma': 'no-cache',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'dummy',
    }

    response = requests.post(url, headers=headers)
    if response.status_code == 204:
        print('Event sent successfully')
    elif response.status_code == 200:
        print('Event sent successfully')
    else:
        print('Failed to send event:', response.text)

    return response



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

bt.trace()

def datetime_to_ms(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)  # UTC datetime for the epoch
    delta = dt - epoch  # Time difference between dt and the epoch
    ms = int(delta.total_seconds() * 1000)  # Convert to milliseconds
    return ms

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
        bt.logging.trace("Inside forward request")
        time_to_loop = 8
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
            return {"error": "User already in queue"}, 400

        print('Forwarding request to local API...')
        def random_seed(min,max):
            return random.randint(min,max)

        # use miners to add image to queue and wait for response
        # create a uids array with length of time_to_loop made up of miners.add_image(ImageRequest(**request_body))
        requests = []
        seed = random_seed(0, 1000000000)

        # Create a correlation ID to match requests with responses
        correlation_id = str(uuid.uuid4())
        doc_data = None

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
                # current time since epoch in milliseconds
                current_time = int(time.time() * 1000)
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
                        return {"error": "Invalid image provided"}, 400
                elif(image != "" and not SAVE_IMAGES):
                    bt.logging.trace(f"Image provided but SAVE_IMAGES is set to False (skipping upload)")
                doc_data = {
                    u'uid': user_id,
                    u'prompt': request_body['text'],
                    u'negative_prompt': request_body['negative_prompt'],
                    u'parent_image_url': parent_image_url,
                    u'parent_image_hash': parent_image_hash,
                    u'num_images': time_to_loop,
                    u'balance': balance,
                    u'seed': seed,
                    u'children_image_hashes': [],
                    u'children_image_urls': [],
                    u'date': int(time.time() * 1000)
                }
                bt.logging.trace(f"Added request to firestore with correlation_id: {correlation_id}")

        active_users[user_id] = (datetime.datetime.now(), correlation_id)

        for i in range(time_to_loop):
            requests.append({
                "uid": str(uuid.uuid4()),
                "request": {**request_body, "seed": seed + i},
                "request_id": correlation_id,
                "image": None,
            })

        # Connect to RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

         # Declare a queue for responses from clients
        channel.queue_declare(queue=correlation_id)

        
        # Create a new response event for this request
        response_event = threading.Event()
        response_events[correlation_id] = response_event

        # Set consume flag
        consume_flag = threading.Event()

       # Function to start consuming messages
        def start_consuming(channel):
            while not consume_flag.is_set():
                channel.connection.process_data_events()

            channel.stop_consuming()

        # Create a correlation dictionary to store the response
        response_dict[correlation_id] = []

        # Callback function to process the response
        def process_response(channel, method, properties, body):
            bt.logging.trace("Processed response")
            global response_dict
            response_dict[correlation_id] = json.loads(body)
            response_event.set()

        bt.logging.trace("Correlation ID: " + correlation_id)

        # Set up the response callback
        channel.basic_consume(
            queue=correlation_id,
            on_message_callback=process_response,
            auto_ack=True
        )

        # Send requests as a single message
        message = json.dumps(requests)
        channel.basic_publish(  
            exchange='',
            routing_key='client_requests',
            body=message,
            properties=pika.BasicProperties(
                correlation_id=correlation_id,
                reply_to=correlation_id
            )
        )

        # run consume in a thread
        consume_thread = threading.Thread(target=start_consuming, args=(channel,))
        consume_thread.start()
        
        
         # Wait for the single response containing all requests
        bt.logging.trace("Waiting for callback event")
        response_event.wait()
        bt.logging.trace("Received callback event")

        consume_flag.set() # stops the consume thread
        
        # Close thread
        consume_thread.join()

        # Remove user from dict
        del active_users[user_id]

          # Get the response from the dictionary
        response = response_dict[correlation_id]

        try:
            if doc_data and SAVE_IMAGES:
                for img_info in response['images']:
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
        if doc_data:
            doc_ref = db.collection(u'requests').document(correlation_id)
            doc_ref.set(doc_data)
            bt.logging.trace(f"Added request to firestore with correlation_id: {correlation_id}")

        # Clean up the event and dictionary for this request
        del response_dict[correlation_id]
        del response_events[correlation_id]
        bt.logging.trace("Received response!")

        # Close the RabbitMQ connection
        connection.close()

        parent_image_hash = ""
        if image != "":
            verify_base64_image(image)
            decoded_image = base64.b64decode(image)
            parent_image_hash = hashlib.sha256(decoded_image).hexdigest()


        event = 'image_generation'
        cid = user_id # 'your_client_id' 
        params = {
            'negative_prompt': request_body['negative_prompt'],
            'prompt': request_body['text'],
            'seed': seed,
            'image_hash': parent_image_hash,
            'width': request_body['width'],
            'height': request_body['height'],
        }   

        # firebase_log_event_for_cid(event, cid, params)

        # Return the response as JSON
        return {"data": response}
        
        
    return app

# Global dictionary variable
ips = load_ips()

# app = create_app(False)

if __name__ == '__main__':
    # Start Flask thread
    app = create_app(False)
    # bt.logging.trace("Starting Flask thread")
    print("Starting server")

    # flask_thread = threading.Thread(target=app.run, kwargs={'host':'0.0.0.0', 'port': 8093})
    # flask_thread.start()
    serve(app, host='0.0.0.0', port=8093)

    # Wait for Flask thread to complete (optional)