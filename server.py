from flask import Flask, request, send_from_directory
import requests
import os
import bittensor as bt
import argparse
import uuid
from PIL import Image
import time
import asyncio
import jsonify
import multiprocessing
import queue

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

parser = argparse.ArgumentParser()

DEFAULT_PORT = 8093
DEFAULT_AXON_IP = "127.0.0.1"
DEFAULT_AXON_PORT = 9090

parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port number (default: {})'.format(DEFAULT_PORT))
parser.add_argument('--axon.ip', type=str, default=DEFAULT_AXON_IP, help='Axon IP address (default: {})'.format(DEFAULT_AXON_IP))
parser.add_argument('--axon.port', type=int, default=DEFAULT_AXON_PORT, help='Axon port number (default: {})'.format(DEFAULT_AXON_PORT))

args = vars(parser.parse_args())

app = Flask(__name__, static_folder='build', static_url_path='/')
use_local_api = False
default_uid = 4

mg = bt.metagraph(netuid=14, network='test')
mg.sync()

wallet = bt.wallet().create_if_non_existent()

ips = load_ips()

class ImageRequest():
    text = ""
    negative_prompt = "" 
    image = ""
    width = 512
    height = 512
    gudiance_scale = 7.5
    strength = 0.75
    timeout = 12

    def __init__(self, text, negative_prompt, image, width, height, guidance_scale, strength, timeout = 12, **kwargs):
        self.text = text
        self.negative_prompt = negative_prompt
        self.image = image
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.strength = strength
        self.timeout = timeout
    
    def __call__(self):
        print("Calling image request", self)
        return self

class Miner():
    axon = None
    ip = None
    port = None
    queue = None # queue of images and responses to be processed (uid, ImageRequest, ImageResponse)
    model_type = "prompthero/openjourney"
    texttoimage = None
    responses = None

    # set up a miner object
    def __init__(self, ip, port, model_type=None):
        self.ip = ip
        self.port = port
        if(model_type != None):
            self.model_type = model_type
        # find axon within metagraph
        self.axon = [x for x in mg.axons if x.ip == ip and x.port == port][0]
        self.texttoimage = bt.text_to_image( keypair=wallet.hotkey, axon=self.axon)
        self.queue = multiprocessing.Queue()
        self.responses = {}  # A dictionary to store the responses

    # add an image to the queue
    def add_image(self, image_request):
        # check image_request type
        if(type(image_request) != ImageRequest):
            # raise error
            raise TypeError('image_request must be of type ImageRequest')
        
        # Validate that axon isn't None
        if(self.axon == None):
            # raise error
            raise ValueError('Axon is None, cannot add image to queue')

        uid = uuid.uuid4()

        # add image_request to queue
        self.queue.put((uid, image_request, None))
        self.responses[uid] = None

        # return uid
        return uid

    def process_queue(self):
        while not self.queue.empty():
            bt.logging.trace("Queue not empty, processing queue")
            uid, image_request, image_response = self.queue.get()

            bt.logging.trace("Processing image request", image_request)
            
            # check if image_response is None
            if(image_response == None):
                # Call axon to process image_request
                image_response = self.texttoimage.forward(
                    text = image_request.text,
                    negative_prompt = image_request.negative_prompt,
                    image = image_request.image,
                    width = image_request.width,
                    height = image_request.height,
                    guidance_scale = image_request.guidance_scale,
                    strength = image_request.strength,
                    num_images_per_prompt = 1,
                    num_inference_steps = 90,
                    timeout = 12
                )

                self.responses[uid] = image_response

    def start_queue_processing(self):
        # use a while loop to continuously process queue
        while True:
            self.process_queue()
            # add sleep to prevent the loop from being too fast and consuming too much resources
            time.sleep(0.5)

class Miners():
    # miners has an object where each key is a Miner
    miners = {}

    # set up a miners object
    def __init__(self, ips):
        for ip in ips:
            miner = Miner(ip=ip[0], port=ip[1])
            self.miners[miner] = []
            multiprocessing.Process(target=miner.start_queue_processing).start()

    # add an image to the queue of the miner with the least images in its queue that matches the model_type if provided
    def add_image(self, image_request, model_type = None):
        # check image_request type
        if(type(image_request) != ImageRequest):
            # raise error
            raise TypeError('image_request must be of type ImageRequest')
        
        # check model_type type
        if(model_type != None and type(model_type) != str):
            # raise error
            raise TypeError('model_type must be of type str')
        

        # find the miner with the least images in its queue that matches the model_type if provided
        miner = None
        if(model_type != None):
            miner = min([miner for miner in self.miners if miner.model_type == model_type], key=lambda miner: miner.queue.qsize())
        else:
            miner = min(self.miners, key=lambda miner: miner.queue.qsize())

        # add image_request to miner's queue
        uid = miner.add_image(image_request)

        # return uid
        return uid


miners = Miners(ips)

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
    time_to_loop = 4
    request_body = {**request.json, 'num_images_per_prompt': 1}
    print('Forwarding request to local API...')
    responses = []

    # use miners to add image to queue and wait for response
    # create a uids array with length of time_to_loop made up of miners.add_image(ImageRequest(**request_body))
    uids = []
    errs = 0
    for i in range(time_to_loop):
        try:
            image_request = ImageRequest(**request_body)
            uid = miners.add_image(image_request)
            print('Added image to queue', uid)
            uids.append(uid)
        except Exception as e:
            # re increment i
            i -= 1
            errs += 1
            if(errs > 3):
                print(e)
                print('The error above was from adding image to queue')
                return {'error': 'Error adding image to queue'}, 500

    async def process_uid(uid):
        response = None
        start_time = time.time()
        while response is None and time.time() - start_time < 16:
            for miner in miners.miners:
                if uid in miner.responses and miner.responses[uid] is not None:
                    response = miner.responses[uid]
                    break
            if response is not None:
                break
        print('Received response from local API'. response)
        return response

    async def process_uids(uids):
        tasks = []
        for uid in uids:
            tasks.append(asyncio.create_task(process_uid(uid)))
        responses = await asyncio.gather(*tasks)
        return responses
    
    # Use asyncio to process uids asynchronously
    responses = asyncio.run(process_uids(uids))

    # convert responses from (uid, request, response) to {uid, image: response.image}
    responses = [{'uid': response[0], 'image': response[2].image} for response in responses]
    
    if responses is not None:
        # Do something with the responses
        print('Received responses from API')
        return jsonify(responses)



# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8093)
