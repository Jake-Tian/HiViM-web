

import cv2  # We're using OpenCV to read video, to install !pip install opencv-python
import base64
import time
from openai import OpenAI
import os
from prompts import prompt_generate_episodic_memory, character_matching_information
from general import clean_model_output


def get_response(messages):
    client = OpenAI()

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=messages,
    )
    return response.choices[0].message.content


def generate_messages(video_path, prompt):

    video = cv2.VideoCapture(video_path)
    print(video.get(cv2.CAP_PROP_FRAME_COUNT))

    base64Frames = []
    while video.isOpened():
        success, frame = video.read()
        if not success:
            break
        _, buffer = cv2.imencode(".jpg", frame)
        base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

    content = [
        {
        "type": "text",
        "text": prompt
        }, 
        *[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame}"
                }
            }
            for frame in base64Frames[0::50]
        ]
    ]

    messages = [{
        "role": "user",
        "content": content
    }]
    return messages


if __name__ == "__main__":
    start_time = time.time()

    messages = generate_messages("../data/processed/14_subtitled_tracked.mp4", character_matching_information + prompt_generate_episodic_memory)
    response = get_response(messages)
    print(clean_model_output(response))

    elapsed_time = time.time() - start_time
    print(f"Time taken: {elapsed_time} seconds")