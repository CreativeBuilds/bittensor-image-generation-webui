import bittensor as bt

# Setup bittensor
bt.trace()

# st = bt.subtensor(chain_endpoint="test.finney.opentensor.ai:443")

mg = bt.metagraph(netuid=14, network='test')
mg.sync()

# Setup wallet
wallet = bt.wallet().create_if_non_existent()