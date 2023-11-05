import argparse

from mylangrobot.operator import SOMOperator


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-id", type=int, default=0)
    parser.add_argument("--language", type=str, default="English")
    args = parser.parse_args()

    som = SOMOperator(camera_id=args.camera_id, language=args.language)
    som.run()
