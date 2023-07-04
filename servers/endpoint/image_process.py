import pika
import json
import threading
import time
import copy
import base64
import hashlib
import os
import sys

from ..._utils.bittensor import bt
from ...classes.ImageRequest import ImageRequest
from ...classes.Miners import Miners
from ..._utils._DEFAULTS import DEFAULT_NUM_INFERENCE_STEPS, DEFAULT_TIMEOUT
from ..._utils.load_ips import load_ips

# get actual dir of "../../ips.txt"
dir_path = os.path.dirname(os.path.realpath(__file__))
ips = load_ips(os.path.join(dir_path, "../../ips.txt"))

# Setup miners
miners = Miners(ips)


# Connect to RabbitMQ on a separate thread
def consume_queue():
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    bt.logging.trace("Connected to RabbitMQ")
    

    def process_request(channel, method, properties, body):
        # Process the requests
        requests = json.loads(body)
        bt.logging.trace("Received requests")
        bt.logging.trace(requests)
        # Perform the image processing on the request

        uids = []
        for request in requests:
            image_request = ImageRequest(
                text=request['request']['text'],
                negative_prompt=request['request']['negative_prompt'],
                image = request['request']['image'],
                width = request['request']['width'],
                height = request['request']['height'],
                guidance_scale = request['request']['guidance_scale'],
                strength = request['request']['strength'],
                seed = request['request']['seed'],
                num_images_per_prompt = 1,
                num_inference_steps = DEFAULT_NUM_INFERENCE_STEPS,
                timeout = DEFAULT_TIMEOUT
            )
            model_type = request['request'].get('model_type') or None
            miners.add_image(image_request, model_type=model_type, uid=request["uid"])
            uids.append(request["uid"])

        images = {}
        # wait for response
        cloned_requests = copy.deepcopy(requests)
        while True:
            for request in cloned_requests:
                uid = request["uid"]
                ((miner_response, miner_request), model_type) = miners.get_response(uid)
                if(miner_response != None):
                    if(miner_response.is_success):
                        try:
                            decoded_image = base64.b64decode(miner_response.image)
                            image_hash = hashlib.sha256(decoded_image).hexdigest()
                        except:
                            image_hash = ''
                        try:
                            parent_image = miner_request.image
                            if(parent_image == None or parent_image == ''):
                                parent_hash = ''
                            else:
                                parent_hash = hashlib.sha256(base64.b64decode(parent_image)).hexdigest()
                        except:
                            parent_hash = ''
                        images[uid] = {
                            "image": miner_response.image,
                            "image_hash": image_hash,
                            "parent_hash": parent_hash,
                            "request": request["request"],
                            "model_type": model_type,
                        }
                        try:
                            # find uid 
                            
                            uids.remove(uid)
                            # remove it from requests
                        except ValueError:
                            bt.logging.trace("Failed to remove uid from uids")
                            pass
                        try:
                            cloned_requests.remove(request)
                        except ValueError:
                            bt.logging.trace("Failed to remove request from cloned_requests")
                            pass
                    else:
                        bt.logging.error("Error processing image")
                        bt.logging.error(miner_response)
                        
                        # remove response in miners
                        miners.remove_response(uid)

                        image_request = ImageRequest(
                            text=request['request']['text'],
                            negative_prompt=request['request']['negative_prompt'],
                            image = request['request']['image'],
                            width = request['request']['width'],
                            height = request['request']['height'],
                            guidance_scale = request['request']['guidance_scale'],
                            strength = request['request']['strength'],
                            seed = request['request']['seed'],
                            num_images_per_prompt = 1,
                            num_inference_steps = DEFAULT_NUM_INFERENCE_STEPS,
                            timeout = DEFAULT_TIMEOUT
                        )

                        # if msg includes cannot identify image file
                        position = -1
                        try:
                            position = miner_response.return_message.index("cannot identify image file")
                        except ValueError:
                            pass

                        if (position > -1):
                            # remove image from request
                            image_request.image = ''
                        # add image back to queue
                        bt.logging.trace("Adding image back to queue")
                        # wait 0.5 seconds
                        time.sleep(0.5)
                        miners.add_image(image_request, model_type=model_type, uid=uid)

            if(len(uids) == 0):
                break


            time.sleep(0.1)

        # Create the response
        bt.logging.trace("Creating response")
        response = []
        for uid in images:
            image = images[uid]
            response.append({
                "uid": uid,
                "image": image['image'],
                "image_hash": image['image_hash'],
                "parent_hash": image['parent_hash'],
                "seed": image['request']['seed'],
                "model_type": image['model_type'],
                "resolution": f"{image['request']['width']}x{image['request']['height']}",
            })


        bt.logging.trace("Sending response")
        bt.logging.trace(properties.reply_to)

        # Send the response back to the server using the provided correlation ID and reply_to queue
        
        body = {"images": response, "request_id": requests[0]["request_id"], "request": requests[0]["request"]}

        # create json dump
        json_dump = json.dumps(body)

        channel.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            body=json_dump,
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id
            )
        )

        # Acknowledge the request message
        channel.basic_ack(delivery_tag=method.delivery_tag)

    # create channel if doesnt exist
    channel.queue_declare(queue='client_requests', durable=True)

    # Start consuming requests from the server
    channel.basic_consume(queue='client_requests', on_message_callback=process_request)

    # Start consuming messages
    try:
        channel.start_consuming()
    except:
        bt.logging.error("Error consuming messages")
        # Close the connection
        connection.close()
        # Exit the program
        sys.exit(1)


bt.logging.trace("Starting consume thread")
consume_thread = threading.Thread(target=consume_queue)
consume_thread.start()
bt.logging.trace("Started consume thread")

# Start processing the queue
bt.logging.trace("Starting queue processing")
while True:
    miners.process_queue()
    time.sleep(0.5)


