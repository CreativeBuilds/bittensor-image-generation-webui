export function GetAspectRatio(ratio: string) {
  const aspectRatioArr = ratio.split(':').map(Number);
  const minWidthHeight = 768;

  let width = minWidthHeight;
  let height = minWidthHeight;

  if (aspectRatioArr.length === 2) {
    const aspectRatioWidth = aspectRatioArr[0];
    const aspectRatioHeight = aspectRatioArr[1];

    if (aspectRatioWidth > aspectRatioHeight) {
      // Increase width while maintaining aspect ratio
      width = Math.max(minWidthHeight, Math.ceil((aspectRatioWidth / aspectRatioHeight) * minWidthHeight));
      height = Math.ceil((width / aspectRatioWidth) * aspectRatioHeight);
    } else if (aspectRatioHeight > aspectRatioWidth) {
      // Increase height while maintaining aspect ratio
      height = Math.max(minWidthHeight, Math.ceil((aspectRatioHeight / aspectRatioWidth) * minWidthHeight));
      width = Math.ceil((height / aspectRatioHeight) * aspectRatioWidth);
    }
  }

  // Ensure the width and height are divisible by 8
  width = Math.ceil(width / 8) * 8;
  height = Math.ceil(height / 8) * 8;

  return { width, height };
}
