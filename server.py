from flask import Flask, request, send_from_directory
import requests
import os
import bittensor as bt
import argparse
import uuid
from PIL import Image


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
axon = None
if(args['axon.ip'] == DEFAULT_AXON_IP and args['axon.port'] == DEFAULT_AXON_PORT):
    axon = bt.axon( wallet = wallet, port = args['axon.port'], ip = args['axon.ip']).info()
else:
    axon = [x for x in mg.axons if x.ip == args['axon.ip'] and x.port == args['axon.port']][0]
    
if(axon == None):
    print(mg.axons)
    print('Axon not found, using default axon')
    axon = mg.axons[default_uid]

if(axon == None):
    print('Axon not found, no connection to network')
    exit()

texttoimage = bt.text_to_image( keypair=wallet.hotkey, axon=axon)

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
    try:
        
        while(len(responses) < time_to_loop):
            response = texttoimage.forward(
                text=request_body['text'],
                image=request_body['image'],
                height=request_body['height'],
                width=request_body['width'],
                num_images_per_prompt=request_body['num_images_per_prompt'],
                num_inference_steps=request_body['num_inference_steps'],
                guidance_scale=request_body['guidance_scale'],
                negative_prompt=request_body['negative_prompt'],
                timeout=request_body['timeout']
            )

            responses.append({
                'image': response.image,
                'id': str(uuid.uuid4())
            })
        return {'data': responses}
    except Exception as e:
        print('Error forwarding request: ', e)
        return {'error': "Failed to forward request to network"}


# Start the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8093)
