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
import datetime

from waitress import serve
import sys



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

DEFAULT_PORT = 8094
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
        request_body = {**request.json, 'num_images_per_prompt': 1}
        try:    
            correlation_id = request_body['correlation_id']
            del request_body['correlation_id']
        except:
            correlation_id = str(uuid.uuid4())


        try:    
            time_to_loop = request_body['time_to_loop']
            del request_body['time_to_loop']
        except:
            time_to_loop = 4

        try:    
            seed = request_body['seed']
            del request_body['seed']
        except:
            seed = random.randint(0, 1000000000)
        
        print('Forwarding request to local API...')
        
        # use miners to add image to queue and wait for response
        # create a uids array with length of time_to_loop made up of miners.add_image(ImageRequest(**request_body))
        requests = []

        # Create a correlation ID to match requests with responses

        

        for i in range(time_to_loop):
            requests.append({
                "uid": str(uuid.uuid4()),
                "request": {**request_body, "seed": seed + i},
                "request_id": correlation_id,
                "image": None,
            })

        try:
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
        except:
            print("RabbitMQ connection failed")
            # exit python file
            sys.exit()

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

        

          # Get the response from the dictionary
        response = response_dict[correlation_id]

        

        # Clean up the event and dictionary for this request
        del response_dict[correlation_id]
        del response_events[correlation_id]

        # Close the RabbitMQ connection
        connection.close() 

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
    serve(app, host='0.0.0.0', port=DEFAULT_PORT)

    # Wait for Flask thread to complete (optional)