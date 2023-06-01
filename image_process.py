import pika
import json
import bittensor as bt
import asyncio
import threading
import uuid
import time

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
    queue = None # queue of images and responses to be processed (uid, ImageRequest)
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
        self.queue = [] # queue of images and responses to be processed (uid, ImageRequest)
        self.responses = {}  # A dictionary to store the responses

    # add an image to the queue
    def add_image(self, image_request, uid=uuid.uuid4()):
        # check image_request type
        if(type(image_request) != ImageRequest):
            # raise error
            raise TypeError('image_request must be of type ImageRequest')
        
        # Validate that axon isn't None
        if(self.axon == None):
            # raise error
            raise ValueError('Axon is None, cannot add image to queue')

        # add image_request to queue
        self.queue.append((uid, image_request))
        self.responses[uid] = None

        # return uid
        return uid

    async def process_queue(self):
        # get but dont pop from queue
        uid, image_request = self.queue[0]

        # does uid exist on responses even if it is None?
        valid_uid = uid in self.responses
        image_response = self.responses[uid] 

        bt.logging.trace("valid_uid", valid_uid)
        
        # check if image_response is None
        if(image_response == None):

            bt.logging.trace("image_response is None")

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
                num_inference_steps = 30,
                timeout = 30
            )
            
            bt.logging.trace(image_response)

            # add async_image_response to responses
            self.responses[uid] = image_response
            bt.logging.trace("got async image response")
            bt.logging.trace(type(image_response))

            return None

        elif(valid_uid and image_response != None):
            # check if image_response is done processing
            # this is a coroutine, done/done() does not exist on the object
            bt.logging.trace("image_response is not None", type(image_response))
            
            # check if image_response is done processing
            bt.logging.trace(image_response)

            # pop from queue
            self.queue.pop(0)
            # return image_response
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
            miner = Miner(ip=ip[0], port=ip[1])
            self.miners[miner] = []

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
        uid = miner.add_image(image_request, uid)
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
        return miner.get_response(uid)
    
    # add function for when converted to string, this object outputs list of miners and their queue size
    def __str__(self):
        return str([(str(miner), len(miner.queue)) for miner in self.miners])
        


# Setup bittensor
bt.trace()
mg = bt.metagraph(netuid=14, network='test')
mg.sync()

# Setup wallet
wallet = bt.wallet().create_if_non_existent()
ips = load_ips()

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
                num_inference_steps = 30,
                timeout = 30
            )
            model_type = request['request'].get('model_type') or None
            miners.add_image(image_request, model_type=model_type, uid=request["uid"])
            uids.append(request["uid"])

        images = {}
        # wait for response
        while True:
            for request in requests:
                uid = request["uid"]
                miner_response = miners.get_response(uid)
                if(miner_response != None):
                    bt.logging.trace("Got response from miner")
                    if(miner_response.is_success):
                        images[uid] = {
                            "image": miner_response.image,
                            "request": request["request"],
                        }
                        try:
                            uids.remove(uid)
                        except ValueError:
                            bt.logging.trace("Failed to remove uid from uids")
                            pass
                    else:
                        bt.logging.error("Error processing image")
                        bt.logging.error(miner_response.error)
                        try:
                            uids.remove(uid)
                        except ValueError:
                            bt.logging.trace("Failed to remove uid from uids (error)")
                            pass
                        # TODO: loop back and add image to queue again
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
                "seed": image['request']['seed'],

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

    # Start consuming requests from the server
    channel.basic_consume(queue='client_requests', on_message_callback=process_request)

    # Start consuming messages
    channel.start_consuming()


bt.logging.trace("Starting consume thread")
consume_thread = threading.Thread(target=consume_queue)
consume_thread.start()
bt.logging.trace("Started consume thread")

# Start processing the queue
bt.logging.trace("Starting queue processing")
while True:
    miners.process_queue()


