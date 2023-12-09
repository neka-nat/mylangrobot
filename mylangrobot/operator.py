import time
from typing import Callable, Optional

import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from .annotator import Annotator
from .gpt4v import request_gpt4v
from .interface import Audio, InterfaceType, Terminal
from .prompt import ResponseType, get_mycobot_prompt, parse_response
from .robot_controller import MyCobotController, MyCobotSettings


class SOMOperator:
    def __init__(
        self,
        pixel_size_on_capture_position: float = 0.43 * 1.0e-3,  # [m/pixel]
        interface_type: InterfaceType = InterfaceType.AUDIO,
        camera_id: int = 0,
        language: str = "English",
        mycobot_settings: Optional[MyCobotSettings] = None,
        capture_image_callback: Optional[Callable] = None,
        annotate_image_callback: Optional[Callable] = None,
    ):
        self._cap = cv2.VideoCapture(camera_id)
        if interface_type == InterfaceType.TERMINAL:
            self._interface = Terminal()
        elif interface_type == InterfaceType.AUDIO:
            self._interface = Audio()
        else:
            raise ValueError("Invalid interface type {}.".format(interface_type))
        self._annotator = Annotator()
        self._robot_controller = MyCobotController(**(mycobot_settings or MyCobotSettings()).dict())
        self._language = language
        self._pixel_size_on_capture_position = pixel_size_on_capture_position
        self._current_frame = None
        self._cam_center = None
        self.capture_image_callback = capture_image_callback or (lambda _: self.save_current_image("capture.png"))
        self.annotate_image_callback = annotate_image_callback or (lambda x: cv2.imwrite("annotated.png", x))

    def __del__(self):
        self._cap.release()

    def calibration(self):
        first_pos = None
        second_pos = None

        def callback(event, x, y, flags, param):
            nonlocal first_pos, second_pos
            if event != cv2.EVENT_LBUTTONDOWN:
                return
            if first_pos is None:
                first_pos = np.array([x, y])
                print("First position: {}".format(first_pos))
            elif second_pos is None:
                second_pos = np.array([x, y])
                print("Second position: {}".format(second_pos))

        print("Start calibration ...")
        print("Move to capture position ...")
        self._robot_controller.move_to_place("capture")
        time.sleep(1)
        self.update_current_frame()
        cv2.namedWindow("image")
        cv2.setMouseCallback("image", callback)
        cv2.moveWindow("image", 100, 200)
        print(
            "Place a ruler and click on the image so that the two points on the ruler shown in the image are 100mm apart."
        )
        while first_pos is None or second_pos is None:
            cv2.imshow("image", self._current_frame)
            # ESC key
            if cv2.waitKey(20) & 0xFF == 27:
                break
        cv2.destroyAllWindows()
        self._pixel_size_on_capture_position = 0.1 / np.linalg.norm(first_pos - second_pos)
        print(
            "Calibration finished. Pixel size on capture position: {} [m/pixel]".format(
                self._pixel_size_on_capture_position
            )
        )

    def function_map(self) -> dict:
        return {
            "grab": lambda: self._robot_controller.grab(),
            "release": lambda: self._robot_controller.release(),
            "move_to_object": lambda object_no: self._robot_controller.move_to_object(object_no),
            "move_to_place": lambda place_name: self._robot_controller.move_to_place(place_name),
        }

    def update_current_frame(self):
        print("[SOMOperator] Capture camera ...")
        ret, frame = self._cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame")
        self._current_frame = frame
        self._current_frame = cv2.rotate(self._current_frame, cv2.ROTATE_180)
        # Since the robot body is on the bottom of the image and the end effector is on the right,
        # crop the bottom and right sides of the image.
        height, width, _ = self._current_frame.shape
        self._cam_center = np.array([height / 2, width / 2])
        self._current_frame = self._current_frame[: -(height // 4), : -(width // 8), :]

    def run(self):
        chat_history = []
        while True:
            res = self.run_once(chat_history)
            if res is not None:
                chat_history.append(res)
                print(chat_history)

    def run_once(self, chat_history: Optional[list] = None) -> Optional[tuple[str, str]]:
        if chat_history is None:
            chat_history = []
        input_text = self._interface.input(prefix="Me: ")
        if chat_history:
            input_text = "\n".join([f"Me: {q}\nYou: {a}" for q, a in chat_history]) + "\n" + input_text
        return self.execute_command(input_text)

    def execute_command(self, input_text: str) -> Optional[tuple[str, str]]:
        self._robot_controller.move_to_place("capture")
        time.sleep(1)
        self.update_current_frame()
        self.capture_image_callback(self._current_frame)
        res, response_type, obj_centers = self.process_image(self._current_frame, self._cam_center, input_text)
        if response_type == ResponseType.QUESTION:
            self._interface.output(res)
            return (input_text, res)
        elif response_type == ResponseType.CODE:
            self._robot_controller.move_to_place("home")
            self._robot_controller.set_detections(obj_centers)
            exec(res, self.function_map(), {})
            self._robot_controller.clear_detections()
            return (input_text, "<Execute code>")
        return None

    def process_image(self, image: np.ndarray, cam_center: np.ndarray, text: str) -> tuple[str, ResponseType, list]:
        """Process image and return response text and response type.

        Note:
            The input image should be in BGR format.
        """
        annotated_image, detections = self._annotator.get_annotated_image(image)
        self.annotate_image_callback(annotated_image)
        prompt = get_mycobot_prompt(len(detections.mask), self._language).format(text=text)
        res = request_gpt4v(prompt, annotated_image)
        res, response_type = parse_response(res)
        print("[SOMOperator]", response_type, res)
        # calculate center of masks
        centers = []
        if response_type == ResponseType.CODE:
            for mask in detections.mask:
                center = np.mean(np.where(mask == True), axis=1)
                centers.append(self._pixel_size_on_capture_position * (center - cam_center))
        return res, response_type, centers

    def save_current_image(self, filename: str):
        cv2.imwrite(filename, self._current_frame)
