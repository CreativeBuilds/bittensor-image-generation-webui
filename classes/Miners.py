import ImageRequest
import Miner
import asyncio

class Miners():
    
    miners = {} # miners has an object where each key is a Miner
    uid_to_miner = {} # a dictionary to store the uid to miner mapping

    # set up a miners object
    def __init__(self, ips):
        for ip in ips:
            miner = Miner(ip=ip[0], port=ip[1], model_type=ip[2])
            self.miners[miner] = [] # TODO: why is this an array, does it serve a purpose? Should miners be an array of miners instead of an object?

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
        (response, request) = miner.get_response(uid)
        return ((response, request), miner.model_type)
    
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
 