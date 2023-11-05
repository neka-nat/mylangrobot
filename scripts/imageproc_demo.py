import argparse

import cv2
from mylangrobot.operator import SOMOperator


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", type=str)
    parser.add_argument("--prompt", type=str, default="Please pick up the chocolate.")
    args = parser.parse_args()

    image = cv2.imread(args.image_path)
    som = SOMOperator()
    res, res_type, _ = som.process_image(image, args.prompt)
    print(res_type)
    print(res)
