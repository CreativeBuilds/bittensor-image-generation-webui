import os
import time
from .process_string import process_string

OUTPUTS_DIR = "../outputs"
FILENAME_TEMPLATE = "{type}.csv"


def initialize_file(filepath, header):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write(header)


def write_entry(filepath, fields):
    timestamp_in_milliseconds = int(round(time.time() * 1000))
    line = ','.join(map(process_string, fields))
    entry = f"{timestamp_in_milliseconds},{line}\n"

    with open(filepath, 'a') as f:
        f.write(entry)


def add_prompt_to_file(prompt_type, userid, prompt_obj):
    if prompt_type not in ("blocked", "passed"):
        raise ValueError("Invalid prompt type.")

    filename = FILENAME_TEMPLATE.format(type=prompt_type)
    current_directory = os.path.dirname(os.path.realpath(__file__))
    filepath = os.path.join(current_directory, OUTPUTS_DIR, filename)

    header = f"timestamp,userid,{','.join(prompt_obj)}\n"
    initialize_file(filepath, header)

    ranks = [prompt_obj[key].get("rank") for key in prompt_obj]
    if len(set(ranks)) != len(ranks):
        raise ValueError("Ranks must be unique.")

    sorted_fields = sorted(prompt_obj.items(), key=lambda x: x[1].get("rank", float("inf")))

    fields = [userid] + [item[1]["value"] for item in sorted_fields]
    write_entry(filepath, fields)

def GetPassedObj(request_body, percentage_blocked, avg_image_scores, top_4_images_scores, top_4_image_seeds, resolution, image_hashes, parent_hashes, parent_hashes_dedupe, models):
    prompt_obj = {
                "text": {
                    "value": request_body['text'],
                    "rank": 1
                },
                "negative_prompt": {
                    "value": request_body['negative_prompt'],
                    "rank": 2
                },
                "resolution": {
                    "value": resolution,
                    "rank": 3
                },
                "avg_image_scores": {
                    "value": avg_image_scores,
                    "rank": 4
                },
                "top_4_images_scores": {
                    "value": top_4_images_scores,
                    "rank": 5
                },
                "top_4_image_seeds": {
                    "value": top_4_image_seeds,
                    "rank": 6
                },
                "percentage_blocked": {
                    "value": percentage_blocked,
                    "rank": 7
                },
                "image_hashes": {
                    "value": image_hashes,
                    "rank": 8
                },
                "parent_hashes": {
                    "value": parent_hashes_dedupe if len(parent_hashes_dedupe) == 1 else parent_hashes,
                    "rank": 9
                },
                "models": {
                    "value": models,
                    "rank": 10
                }
            }
    
    return prompt_obj

def GetBlockedObj(request_body, percentage_blocked):
    prompt_obj = {
                    "text": {
                        "value": request_body['text'],
                        "rank": 1
                    },
                    "negative_prompt": {
                        "value": request_body['negative_prompt'],
                        "rank": 2
                    },
                    "percentage_blocked": {
                        "value": percentage_blocked,
                        "rank": 3
                    }
                }
    
    return prompt_obj
