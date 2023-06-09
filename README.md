# Bittensor-Image-Generation-WebUI

### Getting Started

To locally host, first `git clone https://github.com/creativebuilds/bittensor-image-generation-webui`

Then install venv if you haven't already with `sh setup.sh`

**Make sure to enable the virtual environment after running setup.sh**

Once your virtual environment is up and running, install requirements for python and node with `sh install.sh` alternatively run `pip install -r requirements.txt` and `npm install`

#### Booting a testnet image miner

In order to use this repo you'll need to run your own Text2Image miner locally.

Navigate to your bittensor folder `~/.bittensor/bittensor` on linux (if on windows you'll need to use WSL)

Pull the latest changes from github `git pull`

Swap the activate branch from master to `fast_text_prompting` with `git checkout fast_text_prompting`

Install the new version with `pip install -e .`

Once you're installed you'll need to run the miner with `python neurons/text_to_image/miners/neuron.py --subtensor.chain_endpoint wss://test.finney.opentensor.ai  --logging.debug --neuron.model_name prompthero/openjourney --netuid 14` if your coldkey and/or hotkey are not named `default` pass in the arguments `--wallet.name coldkeyname --wallet.hotkey hotkeyname`

Replace `prompthero/openjourney` with any stable diffusion model on huggingface.

#### Booting the website

Now that your miner is running, it's time to build and launch the website. In the `bittensor-image-generation-webui` directory run the following.

`npm run build` - alternatively if you're actively making changes you can run `nodemon` which will rerun this command on any `/src` file changes.

Next serve the files you just built with `python server.py` 

Some arguments you can pass into `python server.py` include `--port [your port]` if you wish to set a specific port. Default is 8093. `--axon.ip [axon ip]` and `--axon.port [axon port]` if you are connecting to a remote axon that isn't locally hosted.

If everything was run correctly, you should now see the site at http://0.0.0.0:8093

**Happy image generating!**

