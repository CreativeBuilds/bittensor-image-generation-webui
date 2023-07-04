# How do the servers work in this project?

Do to reasons with issues of blocking, seperate functionalities have been split up into their own files and may run on seperate servers.

Folders within `./servers/` represent a distinct, unique, server. Server files within a folder run on the same server but are different processes.

### Endpoint Server

`./servers/endpoint` is the **gateway** it is the entrypoint for all api calls into the system.

The endpoint/gateway first validates requests, and then forwards the request to the rabbit server `servers/endpoint/server_rabbit.py`.

`servers/endpoint/server_rabbit.py` is responsible for pushing and pulling requests to and from the local RabbitMQ server.

RabbitMQ requests are picked up by process #3, `servers/endpoint/image_process.py`

`./servers/endpoint/image_process.py` is the file which handles requesting images from miners on the bittensor network.

Images are sent back through the pipeline back to the **gateway** which then sends them to a *second server*.

## Processor Server

`./servers/processor` is the second server and runs with access to cuda/gpu inference. 

`./servers/processor/server_scorer.py` runs an aesthetic model, grading each image and assigning a score for how aesthetically pleasing the image is. The top 4 images are then sent back to the **gateway** which completes the request, sending the image back to the client who requested them.

Also note the server_scorer file saves locally a list of all prompts/seeds/scores inside of `./outputs/passed.csv` and `./outputs/blocked.csv`

Blocked requests are those which do not pass the nsfw image filter built into stable diffusion and result in most images returning black.