import base64
import os

import cv2
import numpy as np
import requests

# Get OpenAI API Key from environment variable
api_key = os.environ["OPENAI_API_KEY"]
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

metaprompt = """
- For any marks mentioned in your answer, please highlight them with [].
"""


# Function to encode the image
def encode_image_from_file(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def encode_image_from_cv2(image: np.ndarray) -> str:
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")


def prepare_inputs(message: str, image: np.ndarray) -> dict:
    # # Path to your image
    # image_path = "temp.jpg"
    # # Getting the base64 string
    # base64_image = encode_image(image_path)
    base64_image = encode_image_from_cv2(image)

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {"role": "system", "content": [metaprompt]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message,
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            },
        ],
        "max_tokens": 800,
    }

    return payload


def request_gpt4v(message: str, image: np.ndarray) -> str:
    payload = prepare_inputs(message, image)
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    res = response.json()["choices"][0]["message"]["content"]
    return res
