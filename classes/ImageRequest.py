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
        return self
