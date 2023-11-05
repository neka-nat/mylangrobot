import re
from enum import Enum

mycobot_description = (
    "This is a robotic arm with 6 degrees of freedom that has a suction pump attached to its end effector."
)

mycobot_functions = (
    "* grab(): Turns on the suction pump to grab an object\n"
    "* release(): Turns off the suction pump to release an object\n"
    "* move_to_object(object_no): Given a number of an object, it moves the suction pump to a given position of the object No.\n"
    "* move_to_place(place_name): Given a name of a place, it moves the suction pump to a given position of the place.\n"
    "    The places defines the following:\n"
    "    * 'home': The initial position of the robot\n"
    "    * 'drop': The position where the user receives the object\n"
)

prompt_template = (
    "Imagine we are working with a manipulator robot.\n"
    "{robot_description}\n"
    "I would like you to assist me in sending commands to this robot given a scene and a task. There are {num_objects} objects in the image.\n"
    "At any point, you have access to the following functions:\n"
    "You are allowed to create new functions using these, but you are not allowed to use any other hypothetical functions.\n"
    "{robot_functions}\n"
    "Keep the solutions simple and clear. "
    "You can also ask clarification questions using the tag 'Question - '. Here is an example scenario that illustrates how you can ask clarification questions.\n"
    "Let's assume a scene contains two spheres.\n\n"
    "Me: pick up the sphere.\n"
    "You: Question - there are two spheres. Which one do you want me to pick up?\n"
    "Me: Sphere 1, please.\n\n"
    "Use python code to express your solution or output questions in {language}.\n\n"
    "Let's start!\n\n"
    "{{text}}\n"
    "You: "
)


def get_mycobot_prompt(num_objects: int, language: str = "English") -> str:
    prompt = prompt_template.format(
        robot_description=mycobot_description,
        num_objects=num_objects,
        robot_functions=mycobot_functions,
        language=language,
    )
    return prompt


class ResponseType(Enum):
    CODE = "code"
    QUESTION = "question"


_QUESTIONS = ["Question - ", "質問 - ", "クエスチョン -"]


def parse_response(response: str) -> tuple[str, ResponseType]:
    if any([response.startswith(question) for question in _QUESTIONS]):
        return response.split(" - ")[-1], ResponseType.QUESTION
    else:
        matched = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
        if matched:
            return matched.group(1), ResponseType.CODE
    raise ValueError("Invalid response format", response)
