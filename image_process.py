import pika
import json
import bittensor as bt
import asyncio
import threading
import uuid
import time
import copy
import base64
import asyncio
import hashlib
import os
import argparse
import pydantic
from PIL import Image
from io import BytesIO
import torchvision.transforms as transforms

DEFAULT_NUM_INFERENCE_STEPS = 30
DEFAULT_TIMEOUT = 80

parser = argparse.ArgumentParser()
parser.add_argument( '--netuid', type = int, default = 64 )
parser.add_argument('--subtensor.chain_endpoint', type=str, default='wss://test.finney.opentensor.ai')
parser.add_argument('--subtensor._mock', type=bool, default=False)
parser.add_argument('--ips', type=str, default='ips.txt')

bt.wallet.add_args( parser )
bt.subtensor.add_args( parser )
config = bt.config( parser )

wallet = bt.wallet(config = config )
dendrite = bt.dendrite( wallet = wallet)

class TextToImage( bt.Synapse ):
    images: list[ bt.Tensor ] = []
    text: str = pydantic.Field( ... , allow_mutation = False)
    height: int = pydantic.Field( 512 , allow_mutation = False)
    width: int = pydantic.Field( 512 , allow_mutation = False)
    num_images_per_prompt: int = pydantic.Field( 1 , allow_mutation = False)
    num_inference_steps: int = 20
    guidance_scale: float = 7.5
    negative_prompt: str = pydantic.Field( ... , allow_mutation = False)
    seed: int = pydantic.Field( -1 , allow_mutation = False)

class ImageToImage( TextToImage ):
    image: bt.Tensor = pydantic.Field( ... , allow_mutation = False)
    strength: float = 0.75

transform = transforms.Compose([
    transforms.PILToTensor()
])


def load_ips():
    with open(config.ips) as f:
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

class ImageRequest():
    text = ""
    negative_prompt = "" 
    image = None
    image_str = ""
    width = 512
    height = 512
    gudiance_scale = 7.5
    strength = 0.75
    timeout = 12

    def __init__(self, text, negative_prompt, image, width, height, guidance_scale, strength, timeout = 12, **kwargs):
        self.text = text
        self.negative_prompt = negative_prompt
        if(type(image) == str):
            print("converting image to tensor")
            try:
                self.image_str = image
                print("converting to pil")
                image = self.convert_str_to_pil(image)
                print("converting to tensor")
                image = transform(image)
                print("serializing tensor")
                image = bt.Tensor.serialize(image)
                print("done")
            except Exception as e:
                print("error converting image to tensor")
                print(e)
                image = None
        self.image = image
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.strength = strength
        self.timeout = timeout
    
    def __call__(self):
        return self
    
    def convert_str_to_pil(self, imageasbase64str):
        print("converting image string to bytes")
        imageasbytes = base64.b64decode(imageasbase64str)
        print("converting to BytesIO")
        img = BytesIO(imageasbytes)
        print("opening image")
        image = Image.open(img)
        return image
    
class ImageResponse():
    image = ""
    is_success = False
    def __init__(self, image):
        self.image = image
        self.is_success = True
        if image == None:
            self.is_success = False
            
class Miner():
    axon = None
    ip = None
    port = None
    queue = None # queue of images and responses to be processed (uid, ImageRequest)
    model_type = "openjourney-v4"
    texttoimage = None
    responses = None

    # set up a miner object
    def __init__(self, ip, port, model_type=None):
        self.ip = ip
        self.port = port
        if(model_type != None):
            self.model_type = model_type
        # find axon within metagraph
        if(len(mg.axons) == 0):
            raise ValueError('No axons in metagraph')
        self.axon = [x for x in mg.axons if x.ip == ip and x.port == port][0]
        # self.texttoimage = bt.text_to_image( keypair=wallet.hotkey, axon=self.axon) # this is a dendrite
        self.queue = [] # queue of images and responses to be processed (uid, ImageRequest)
        self.responses = {}  # A dictionary to store the responses

    def add_image(self, image_request, uid=uuid.uuid4()):
        if(type(image_request) != ImageRequest):
            # raise error
            raise TypeError('image_request must be of type ImageRequest')
        
        if(self.axon == None):
            # raise error
            raise ValueError('Axon is None, cannot add image to queue')

        self.queue.append((uid, image_request))
        self.responses[uid] = (None, image_request)

        return uid

    async def process_queue(self):
        uid, image_request = self.queue[0]

        valid_uid = uid in self.responses
        try:
            image_response = self.responses[uid][0] 
        except:
            image_response = None
            self.responses[uid] = (None, image_request)

        if(image_response == None):
            try:
                # convert image_request.image to a PIL image
                image = Image.open(BytesIO(base64.b64decode(image_request.image)))

                # convert image to tensor
                image_tensor = transform(image)

                synapse = ImageToImage(
                    text = image_request.text,
                    negative_prompt = image_request.negative_prompt,
                    image = bt.Tensor.serialize( image_tensor ),
                    width = image_request.width,
                    height = image_request.height,
                    guidance_scale = image_request.guidance_scale,
                    strength = image_request.strength,
                    num_images_per_prompt = 1,
                    num_inference_steps = DEFAULT_NUM_INFERENCE_STEPS,
                )
            except:
                synapse = TextToImage(
                    text = image_request.text,
                    negative_prompt = image_request.negative_prompt,
                    width = image_request.width,
                    height = image_request.height,
                    guidance_scale = image_request.guidance_scale,
                    num_images_per_prompt = 1,
                    num_inference_steps = DEFAULT_NUM_INFERENCE_STEPS,
                )


            image_response = await dendrite(
                self.axon,
                synapse=synapse,
                timeout=DEFAULT_TIMEOUT
            )

            images = []
            for j, image in enumerate(image_response.images):
                image = transforms.ToPILImage()( bt.Tensor.deserialize( image ) )
                # convert image to base64
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue())
                images.append(img_str.decode('utf-8'))
            
            if len(images) == 0:
                self.responses[uid] = (ImageResponse(None), image_request)
            else:
                self.responses[uid] = (ImageResponse(images[0]), image_request)

            return None

        elif(valid_uid and image_response != None):
            self.queue.pop(0)
            return image_response
        else:
            # return None
            return None

    def get_response(self, uid):
        # check if uid is in self.responses
        if(uid not in self.responses):
            # raise error
            raise ValueError('uid not in self.responses')
        # check if response is None
        if(self.responses[uid] == None):
            return None            
        # return response
        return self.responses[uid]       

    def __str__(self):
        return "Miner: " + self.ip + ":" + str(self.port) 

    # def start_queue_processing(self):
    #     # use a while loop to continuously process queue
    #     while True:
    #         self.process_queue()
    #         # add sleep to prevent the loop from being too fast and consuming too much resources
    #         time.sleep(0.5)

class Miners():
    # miners has an object where each key is a Miner
    miners = {}
    uid_to_miner = {} # a dictionary to store the uid to miner mapping

    # set up a miners object
    def __init__(self, ips):
        for ip in ips:
            try:
                miner = Miner(ip=ip[0], port=ip[1], model_type=ip[2])
                self.miners[miner] = []
            except:
                print("Error connecting to miner: " + ip[0] + ":" + str(ip[1]))
                continue

    # add an image to the queue of the miner with the least images in its queue that matches the model_type if provided
    def add_image(self, image_request, model_type = None, uid = None):
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
            miner = min([miner for miner in self.miners if miner.model_type == model_type], key=lambda miner: len(miner.queue))
        else:
            miner = min(self.miners, key=lambda miner: len(miner.queue))

        # add image_request to miner's queue
        uid = miner.add_image(image_request, uid=uid)
        # add uid to uid_to_miner
        self.uid_to_miner[uid] = miner

        # return uid
        return uid
    
    # process queue for each miner
    def process_queue(self):
        # miners with images in queue
        miners = [miner for miner in self.miners if len(miner.queue) > 0]
        # create tasks
        tasks = [miner.process_queue() for miner in miners]
        # run tasks
        responses = asyncio.run(asyncio.gather(*tasks))
        # return responses
        return responses
    

    def get_response(self, uid):
        # check if uid is in uid_to_miner
        if(uid not in self.uid_to_miner):
            # raise error
            raise ValueError('uid not in uid_to_miner')
        
        # get miner
        miner = self.uid_to_miner[uid]

        # return response
        (response, request) = miner.get_response(uid)
        # check if string includes space in it
        try:
            if(response != None and type(response.image) == str and ' ' in response.image):
                # response is error
                return (((response, request), miner.model_type), True)
        except Exception as e:
            print(e)
            print("FAILED TO CHECK IF RESPONSE IS ERROR")


        return (((response, request), miner.model_type), False)
    
    def remove_response(self, uid):
        # check if uid is in uid_to_miner
        if(uid not in self.uid_to_miner):
            # raise error
            raise ValueError('uid not in uid_to_miner')
        
        # get miner
        miner = self.uid_to_miner[uid]

        # remove response from miner
        miner.responses.pop(uid)

        # remove uid from uid_to_miner
        self.uid_to_miner.pop(uid)
    
    # add function for when converted to string, this object outputs list of miners and their queue size
    def __str__(self):
        return str([(str(miner), len(miner.queue)) for miner in self.miners])
        
# Setup bittensor
bt.trace()

# st = bt.subtensor(chain_endpoint="test.finney.opentensor.ai:443")

mg = bt.metagraph(netuid=64, network='test')
mg.sync()

# Setup wallet
wallet = bt.wallet().create_if_non_existent()
ips = load_ips()

# Setup miners
miners = Miners(ips)


# Connect to RabbitMQ on a separate thread
def consume_queue():
    try:
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        bt.logging.trace("Connected to RabbitMQ")
        

        def process_request(channel, method, properties, body):
            # Process the requests
            requests = json.loads(body)
            bt.logging.trace("Received requests")
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
                    (((miner_response, miner_request), model_type), failed) = miners.get_response(uid)
                    if(failed):
                        # remove uid from uids
                        uids.remove(uid)
                        print("Failed", uid, miner_response.image, miner_response.return_message)
                        # remvoe it from requests
                        cloned_requests.remove(request)
                        
                    elif(miner_response != None):
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
                        elif miner_response.image is None:
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
                                # if miner request has image and image is None set position to 0
                                if(miner_request.image != None and miner_response.image == None):
                                    position = 0
                            except ValueError:
                                pass

                            if (position > -1):
                                # remove image from request
                                image_request.image = ''
                            # add image back to queue
                            bt.logging.trace("Adding image back to queue")
                            # wait 0.5 seconds
                            miners.add_image(image_request, model_type=model_type, uid=uid)

                # process images for best 4 images
                # scores = {}
                # bt.logging.trace("Predicting images")
                # for uid in images:
                #     image = images[uid]
                #     # base64 decode image
                #     pil_image = Image.open(io.BytesIO(base64.b64decode(image['image'])))

                #     # run in new thread
                #     predicted_image = predict_pil(pil_image)
                    
                #     scores[uid] = (uid, predicted_image) 
                #     bt.logging.trace(f"{uid}: {scores[uid][1]:.2f}")
                # # get top 4 images
                # top_4 = heapq.nlargest(4, scores.values(), key=lambda x: x[1])
                # # get top 4 images
                # for uid, score in top_4:
                #     top_images[uid] = (images[uid], score)
                if(len(uids) == 0):
                # process images for best 4 images
                # scores = {}
                # bt.logging.trace("Predicting images")
                # for uid in images:
                #     image = images[uid]
                #     # base64 decode image
                #     pil_image = Image.open(io.BytesIO(base64.b64decode(image['image'])))

                #     # run in new thread
                #     predicted_image = predict_pil(pil_image)
                    
                #     scores[uid] = (uid, predicted_image) 
                #     bt.logging.trace(f"{uid}: {scores[uid][1]:.2f}")
                # # get top 4 images
                # top_4 = heapq.nlargest(4, scores.values(), key=lambda x: x[1])
                # # get top 4 images
                # for uid, score in top_4:
                #     top_images[uid] = (images[uid], score)
                    break


                time.sleep(0.1)

            # Create the response
            bt.logging.trace("Creating response")
            response = []
            for uid in images:
                image = images[uid]
                # image = top_images[uid][0]
                # score = top_images[uid][1]
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
    
        channel.start_consuming()
    # on disconnect
    except Exception as e:
    #    kill application
        bt.logging.error("Disconnected from server")
        print("Disconnected from server")
        bt.logging.error(e)
        time.sleep(0.5)
        os._exit(1)        
    


bt.logging.trace("Starting consume thread")
consume_thread = threading.Thread(target=consume_queue)
consume_thread.start()
bt.logging.trace("Started consume thread")

# Start processing the queue
bt.logging.trace("Starting queue processing")
while True:
    try:
        miners.process_queue()
        # check if consume thread is alive
        if(not consume_thread.is_alive()):
            bt.logging.error("Consume thread is dead")
            time.sleep(0.5)
            os._exit(1)
        time.sleep(0.5)
        print("processing queue loop done")
    except Exception as e:
        bt.logging.error("Error processing queue")
        bt.logging.error(e)
        time.sleep(0.5)
        pass


print("done processing queue")

