import { GenerateImage } from './api';

export interface IImageData {
  image: string;
  id: string;
}

export const SubmitPrompt = async ({
  prompt, negativePrompt, ratio, image, token
}: {
  prompt: string;
  negativePrompt: string;
  ratio: { width: number; height: number; };
  image?: string;
  token: string;

}, callback: (data: {
  images: IImageData[]
}) => void) => {

  const { width, height } = ratio;

  return GenerateImage({ prompt, height, width, negativePrompt, image, strength: image ? 0.75 : undefined, token })
    .then(({ data, error }) => {
      if (error)
        throw new Error(error);
      callback(data);
    })
};
