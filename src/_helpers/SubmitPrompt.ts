import { GenerateImage } from './GenerateImage';

export interface IImageData {
  image: string;
  id: string;
}

export const SubmitPrompt = ({
  prompt, negativePrompt, ratio, image
}: {
  prompt: string;
  negativePrompt: string;
  ratio: { width: number; height: number; };
  image?: string;

}, callback: (data: {
  images: IImageData[]
}) => void) => {

  const { width, height } = ratio;

  console.log('SubmitPrompt', { prompt, negativePrompt, width, height, image });

  GenerateImage({ prompt, height, width, negativePrompt, image, strength: image ? 0.75 : undefined })
    .then(({ data, error }) => {
      if (error)
        throw new Error(error);
      callback(data);
    })
    .catch(error => {
      console.error(error); // Handle any errors
    });
};
