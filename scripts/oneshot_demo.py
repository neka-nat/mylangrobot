import argparse

import yaml

from mylangrobot.operator import SOMOperator
from mylangrobot.interface import InterfaceType
from mylangrobot.robot_controller import MyCobotSettings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="../configs/settings.yml")
    parser.add_argument("--prompt", type=str, required=True)
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    mycobot_settings = MyCobotSettings(**config["mycobot_settings"])

    som = SOMOperator(
        pixel_size_on_capture_position=config["pixel_size_on_capture_position"],
        interface_type=InterfaceType[config["interface_type"]],
        camera_id=config["camera_id"],
        language=config["language"],
        mycobot_settings=mycobot_settings,
    )
    som.execute_command(args.prompt)
