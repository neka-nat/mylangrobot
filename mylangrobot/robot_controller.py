import os
import time
from typing import Optional

import kinpy as kp
import numpy as np
from pydantic import BaseModel
from pymycobot.mycobot import MyCobot


class MyCobotSettings(BaseModel):
    urdf_path: str = os.path.join(os.path.dirname(__file__), "../data/mycobot/mycobot.urdf")
    end_effector_name: str = "camera_flange"
    port: str = "/dev/ttyACM0"
    baud: int = 115200
    default_speed: int = 40
    default_z_speed: int = 20
    suction_pin: int = 5
    command_timeout: int = 5
    use_gravity_compensation: bool = False
    end_effector_height: float = 0.065  # pump head offset
    object_height: float = 0.01
    release_height: float = 0.05
    positions: dict[str, list[float]] = {
        "home": [0, 20, -130, 20, 0, 0],
        "capture": [0, 0, -30, -60, 0, -45],
        "drop": [-45, 20, -130, 20, 0, 0],
    }


class MyCobotController:
    def __init__(self, **kwargs):
        settings = MyCobotSettings(**kwargs)
        self._mycobot = MyCobot(settings.port, settings.baud)
        self._suction_pin = settings.suction_pin
        self._default_speed = settings.default_speed
        self._default_z_speed = settings.default_z_speed
        self._command_timeout = settings.command_timeout
        self._use_gravity_compensation = settings.use_gravity_compensation
        self._sim = kp.build_serial_chain_from_urdf(open(settings.urdf_path).read(), settings.end_effector_name)
        self._current_position = self._mycobot.get_angles()
        self.positions = settings.positions
        self.capture_coord = self._calc_camera_lens_coords_on_capture_position(settings.urdf_path)
        self.end_effector_height = settings.end_effector_height  # pump head offset
        self.object_height = settings.object_height
        self.release_height = settings.release_height
        self._detections = []

    def _calc_camera_lens_coords_on_capture_position(self, urdf_path: str) -> kp.Transform:
        sim_for_lens = kp.build_serial_chain_from_urdf(open(urdf_path).read(), "camera_lens")
        return sim_for_lens.forward_kinematics(np.deg2rad(self.positions["capture"]))

    def _check_and_correct_object_no(self, object_no: int) -> int:
        """Check if object_no is valid and correct it if not

        When using SOM, there are times when numbers are incorrectly recognized
        if two numerical labels are in succession. In cases where the number of objects fits within two digits,
        for non-existent object_no, adopt the numerical value of the first digit.
        """
        if object_no >= len(self._detections) and object_no < 100:
            object_no = object_no % 10
        return object_no

    def calc_gravity_compensation(self, angles: list) -> np.ndarray:
        if not self._use_gravity_compensation:
            return np.zeros(6)
        k = np.array([0.0, 0.0, -0.15, -0.35, 0.0, 0.0])
        mat = self._sim.jacobian(np.deg2rad(angles))
        d_ang = np.rad2deg(np.dot(mat.T, np.array([0, 0, -9.8, 0, 0, 0]))) * k
        return d_ang

    def set_detections(self, detections: list) -> None:
        self._detections = detections

    def clear_detections(self) -> None:
        self._detections = []

    def current_coords(self) -> kp.Transform:
        return self._sim.forward_kinematics(np.deg2rad(self._current_position))

    def move_to_xy(self, x: float, y: float, speed: Optional[float] = None) -> None:
        """Move to absolute position xy"""
        coords = self.current_coords()
        coords.pos[0] = x
        coords.pos[1] = y
        self.move_to_coords(coords, speed)

    def move_to_z(self, z: float, speed: Optional[float] = None) -> None:
        """Move to absolute position z"""
        coords = self.current_coords()
        coords.pos[2] = z
        self.move_to_coords(coords, speed or self._default_z_speed)

    def move_to_coords(self, coords: kp.Transform, speed: Optional[float] = None) -> None:
        position = self._sim.inverse_kinematics(coords, np.deg2rad(self._current_position))
        self._current_position = np.rad2deg(position)
        self._mycobot.sync_send_angles(
            self._current_position + self.calc_gravity_compensation(self._current_position),
            speed or self._default_speed,
            self._command_timeout,
        )
        print("Current coords: {}".format(self.current_coords()))

    def move_to_object(self, object_no: int, speed: Optional[float] = None) -> None:
        object_no = self._check_and_correct_object_no(object_no)
        print("[MyCobotController] Move to Object No. {}".format(object_no))
        detection = (
            np.array([-self._detections[object_no][0], -self._detections[object_no][1]]) + self.capture_coord.pos[:2]
        )
        print("[MyCobotController] Object pos:", detection[0], detection[1])
        self.move_to_xy(detection[0], detection[1], speed)

    def move_to_place(self, place_name: str, speed: Optional[float] = None) -> None:
        print("[MyCobotController] Move to Place {}".format(place_name))
        self._current_position = self.positions[place_name]
        self._mycobot.sync_send_angles(
            np.array(self._current_position) + self.calc_gravity_compensation(self._current_position),
            speed or self._default_speed,
            self._command_timeout,
        )
        print("Current coords: {}".format(self.current_coords()))

    def grab(self, speed: Optional[float] = None) -> None:
        print("[MyCobotController] Grab to Object")
        current_pos = self.current_coords().pos
        self.move_to_z(self.object_height + self.end_effector_height, speed)
        self._mycobot.set_basic_output(self._suction_pin, 0)
        time.sleep(2)
        self.move_to_z(current_pos[2], speed)

    def release(self, speed: Optional[float] = None) -> None:
        print("[MyCobotController] Release")
        current_pos = self.current_coords().pos
        self.move_to_z(self.release_height + self.end_effector_height, speed)
        self._mycobot.set_basic_output(self._suction_pin, 1)
        time.sleep(1)
        self.move_to_z(current_pos[2], speed)
