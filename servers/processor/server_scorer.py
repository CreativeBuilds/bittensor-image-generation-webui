from flask import Flask, request
# pip install flask-cors
from flask_cors import CORS
import base64
import io
from PIL import Image
import bittensor as bt

from waitress import serve

from ...inference import predict_pil
from ..._utils._DEFAULTS import *
from ..._utils.handle_outputs import add_prompt_to_file, GetPassedObj, GetBlockedObj

app = Flask(__name__, static_folder='build', static_url_path='/')

CORS(app)

active_users = {}

def create_app():
    app = Flask(__name__)

    CORS(app)

    # API endpoint to forward the request to the local API
    @app.route('/TextToImage/Score', methods=['POST'])
    def forward_request():  

        request_body = request.get_json()['request']

        user_id = request_body['user_id']

        try:
            response = request.get_json()['response']
            all_images = response['data']['images']

            if len(all_images) > 4:

                # determine top 4 images using predict_pil
                image_score_pair = ScoreImagesAesthetic(all_images)
                percentage_blocked = GetPercentBlocked(image_score_pair)


                # if more than 50% of images were blocked, return error
                if percentage_blocked > 0.85:
                    blocked_csv_obj = GetBlockedObj(request_body, percentage_blocked)
                    add_prompt_to_file("blocked", user_id, blocked_csv_obj)
                    return {"error": "Too many images were blocked"}, 400
                
                avg_image_scores, top_4_images_scores, top_4_image_seeds, resolution, image_hashes, parent_hashes, parent_hashes_dedupe, models = ExtractOutCSVInfo(image_score_pair)

                passed_csv_obj = GetPassedObj(request_body, percentage_blocked, avg_image_scores, top_4_images_scores, top_4_image_seeds, resolution, image_hashes, parent_hashes, parent_hashes_dedupe, models)
                add_prompt_to_file("passed", user_id, passed_csv_obj)

                top_4_images_and_scores = image_score_pair[:4]
                top_4_images = [image[0] for image in top_4_images_and_scores]

                # print model and score for each image
                for image in top_4_images_and_scores:
                    score = image[1]
                    bt.logging.trace(f"score: {score} - model: {image[0]['model_type']}")
            else:
                top_4_images = all_images
            
            # update response object to only be the top 4 images
            response['data']['images'] = top_4_images

            return response
        except Exception as e:
            print(e)
            return {"error": "Something went wrong"}, 400

    def GetPercentBlocked(image_score_pair):
        # remove all scores less than 5.0

        image_score_pair_blocked = [pair for pair in image_score_pair if pair[1] < 4.61]
        # get percentage of images that were blocked
        percentage_blocked = len(image_score_pair_blocked) / len(image_score_pair)
        bt.logging.trace(f"percentage blocked: {percentage_blocked}")
        return percentage_blocked

    def ExtractOutCSVInfo(image_score_pair):
        non_blocked = [pair for pair in image_score_pair if pair[1] >= 4.61]
        avg_image_scores = sum([pair[1] for pair in non_blocked]) / len(non_blocked)
                
        image_score_pair.sort(key=lambda x: x[1], reverse=True)

        top_4_images_scores = [pair[1] for pair in image_score_pair[:4]]
        top_4_image_seeds = [pair[0]['seed'] for pair in image_score_pair[:4]]

        resolution = image_score_pair[0][0]['resolution']
        image_hashes = [pair[0]['image_hash'] for pair in image_score_pair[:4]]
        parent_hashes = [pair[0]['parent_hash'] for pair in image_score_pair[:4]]
        # filter hashes for None or ''
        image_hashes = [hash for hash in image_hashes if hash]
        parent_hashes = [hash for hash in parent_hashes if hash]
        # deduplicate hashes
        parent_hashes_dedupe = list(set(parent_hashes))
        models = [pair[0]['model_type'] for pair in image_score_pair[:4]]
        return avg_image_scores,top_4_images_scores,top_4_image_seeds,resolution,image_hashes,parent_hashes,parent_hashes_dedupe,models

    def ScoreImagesAesthetic(all_images):
        image_score_pair = []
        for image in all_images:
            image_bytes = base64.b64decode(image['image'])
            image_pil = Image.open(io.BytesIO(image_bytes))
            score = predict_pil(image_pil)
            image['aesthetic_score'] = score
            print(f"score: {score}")
            image_score_pair.append((image, score))
        return image_score_pair
        
    return app


if __name__ == '__main__':
    # create the app
    app = create_app()

    # run the app
    serve(app, host='0.0.0.0', port=DEFAULT_IMAGE_SCORER_PORT)