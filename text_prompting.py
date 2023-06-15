import bittensor as bt

bt.trace()

wallet = bt.wallet().create_if_non_existent()

mg = bt.metagraph(netuid=1)
mg.sync()

# Get axons

axons = mg.axons

a = axons[891]

# Create a new text_prompting dendrite
tp = bt.text_prompting(axon = a, keypair = wallet.hotkey)

call = tp.forward(prompt=[["system", "user"], ["You are a completion agent, you are designed to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics. As a language model, you are able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand.", "What is your purpose?"]], timeout=30)

print(call)