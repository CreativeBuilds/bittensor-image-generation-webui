const express = require('express');
const axios = require('axios');

const app = express();
const port = 8093;

// Serve the ./build folder
app.use(express.static('build'));
app.use(express.json());

// API endpoint to forward the request to the local API
app.post('/TextToImage/Forward', async (req, res) => {
  const timeToLoop = 4;
  const requestBody = {...req.body, num_images_per_prompt: 1};
  const localApiUrl = 'http://0.0.0.0:8092/TextToImage/Forward/?hotkey=asdasdasd';

  const responses = [];

  for (let i = 0; i < timeToLoop; i++) {
    const response = await axios.post(localApiUrl, requestBody);
    responses.push(response.data);
    }

  res.send(responses);
});

// Start the server
app.listen(port, () => {
  console.log(`API server is running on http://0.0.0.0:${port}`);
});
