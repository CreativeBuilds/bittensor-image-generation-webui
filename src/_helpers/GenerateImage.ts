export interface ImageParams {
  prompt: string;
  height: number;
  width: number;
  negativePrompt: string;
  image?: string;
  strength?: number;
  token: string;
}
const IS_LOCAL = window.location.hostname === '0.0.0.0' || window.location.hostname === 'localhost';
const SITE = IS_LOCAL ? 'http://'+window.location.hostname+':8093' : null;

export function GenerateImage({ prompt, height, width, negativePrompt, image, strength, token }: ImageParams) {
  
  if(IS_LOCAL)
    return fetch('http://0.0.0.0:8093/TextToImage/Forward', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text: prompt,
        image: image || '',
        height: height,
        width: width,
        timeout: 12,
        num_images_per_prompt: 1,
        num_inference_steps: 30,
        guidance_scale: 7.5,
        strength: strength || 0.75,
        negative_prompt: negativePrompt,
        user_token: token
      })
    })
      .then(response => response.json());
  else {
    // going to use a callable function instead
    
  }
}
