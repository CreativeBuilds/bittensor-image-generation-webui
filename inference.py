import webdataset as wds
from PIL import Image
import io
import matplotlib.pyplot as plt
import os
import json

from warnings import filterwarnings


# os.environ["CUDA_VISIBLE_DEVICES"] = "0"    # choose GPU if you are on a multi GPU server
import numpy as np
import torch
import pytorch_lightning as pl
import torch.nn as nn
from torchvision import datasets, transforms
import tqdm

from os.path import join
from datasets import load_dataset
import pandas as pdW
from torch.utils.data import Dataset, DataLoader
import json

import clip


from PIL import Image, ImageFile


#####  This script will predict the aesthetic score for this image file:

img_path = "image-2.png"





# if you changed the MLP architecture during training, change it also here:
class MLP(pl.LightningModule):
    def __init__(self, input_size, xcol='emb', ycol='avg_rating'):
        super().__init__()
        self.input_size = input_size
        self.xcol = xcol
        self.ycol = ycol
        self.layers = nn.Sequential(
            nn.Linear(self.input_size, 1024),
            #nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(1024, 128),
            #nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            #nn.ReLU(),
            nn.Dropout(0.1),

            nn.Linear(64, 16),
            #nn.ReLU(),

            nn.Linear(16, 1)
        )

    def forward(self, x):
        return self.layers(x)

    def training_step(self, batch, batch_idx):
            x = batch[self.xcol]
            y = batch[self.ycol].reshape(-1, 1)
            x_hat = self.layers(x)
            loss = F.mse_loss(x_hat, y)
            return loss
    
    def validation_step(self, batch, batch_idx):
        x = batch[self.xcol]
        y = batch[self.ycol].reshape(-1, 1)
        x_hat = self.layers(x)
        loss = F.mse_loss(x_hat, y)
        return loss

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        return optimizer

def normalized(a, axis=-1, order=2):
    import numpy as np  # pylint: disable=import-outside-toplevel

    l2 = np.atleast_1d(np.linalg.norm(a, order, axis))
    l2[l2 == 0] = 1
    return a / np.expand_dims(l2, axis)


# TODO: Retrain the model using ViT-B/32 instead of ViT-L/14
model = MLP(768)  # CLIP embedding dim is 768 for CLIP ViT L 14

s = torch.load("sac+logos+ava1-l14-linearMSE.pth")   # load the model you trained previously or the model available in this repo

model.load_state_dict(s)

model.to("cuda")
model.eval()


device = "cuda" if torch.cuda.is_available() else "cpu"
#RN50x64   
model2, preprocess = clip.load("ViT-L/14", device=device)

import time


def predict_pil(pil_image):
    print(torch.cuda.is_available())
    
    then = time.time()
    image = preprocess(pil_image).unsqueeze(0).to(device)
    print("Time taken to preprocess image:", time.time() - then)

    then = time.time()
    with torch.no_grad():
       image_features = model2.encode_image(image)
    print("Time taken to encode image:", time.time() - then)

    then = time.time()
    im_emb_arr = normalized(image_features.cpu().detach().numpy() )
    print("Time taken to normalize image:", time.time() - then)

    then = time.time()
    prediction = model(torch.from_numpy(im_emb_arr).to(device).type(torch.cuda.FloatTensor))
    print("Time taken to predict:", time.time() - then)
    return prediction.item()

if __name__ == "__main__":
    pil_image = Image.open(img_path)
    prediction = predict_pil(pil_image)
    print("Predicted aesthetic score:", prediction)


