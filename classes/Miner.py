from ImageRequest import ImageRequest
from .._utils._DEFAULTS import *
from .._utils.bittensor import wallet, mg, bt

import uuid


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
        self.texttoimage = bt.text_to_image( keypair=wallet.hotkey, axon=self.axon)
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

            image_response = self.texttoimage.forward(
                text = image_request.text,
                negative_prompt = image_request.negative_prompt,
                image = image_request.image,
                width = image_request.width,
                height = image_request.height,
                guidance_scale = image_request.guidance_scale,
                strength = image_request.strength,
                num_images_per_prompt = 1,
                num_inference_steps = DEFAULT_NUM_INFERENCE_STEPS,
                timeout = DEFAULT_TIMEOUT
            )
            
            bt.logging.trace(image_response)
            self.responses[uid] = (image_response, image_request)

            return None

        elif(valid_uid and image_response != None):
            bt.logging.trace(image_response)
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
