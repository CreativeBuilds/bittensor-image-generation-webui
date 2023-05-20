import { GenerateImage } from './GenerateImage';

export interface IImageData {
  image: string;
  id: string;
}

export const SubmitPrompt = ({
  prompt, negativePrompt, ratio,
}: {
  prompt: string;
  negativePrompt: string;
  ratio: { width: number; height: number; };
}, callback: (data: IImageData[]) => void) => {

  const { width, height } = ratio;

  GenerateImage({ prompt, height, width, negativePrompt })
    .then(({ data, error }) => {
      if (error)
        throw new Error(error);
      callback(data);
    })
    .catch(error => {
      console.error(error); // Handle any errors
    });
};
