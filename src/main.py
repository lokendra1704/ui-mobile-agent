import os
import time
from PIL import Image
from dotenv import load_dotenv
from tars import (
    TARS,
    MessageDict,
    TextMessageContent,
    ImageMessageContent,
    ImageURLDict,
)
from utils import get_image_url, get_screenshot, extract_action
from actions import ActionSpace
import argparse


load_dotenv()


def run_task_with_user_plan(user_plan, max_itr=20):
    if not user_plan:
        raise Exception("User plan is not provided.")
    agent = TARS(base_type="sft", system_name="default", user_instruction=user_plan)
    messages = []
    iter = 1
    actionOperator = None
    response = None
    screenshot_file = "./screenshot/screenshot.jpg"
    invalid_last_action = False
    while True:
        get_screenshot(adb_path="adb", save_path=screenshot_file)
        if max_itr is not None and iter >= max_itr:
            print("Max iteration reached. Stopping...")
            break
        if iter == 1:
            width, height = Image.open(screenshot_file).size
            actionOperator = ActionSpace(
                adb_path=os.getenv("ADB_PATH", "adb"),
                image_width=width,
                image_height=height,
            )
            messages.append(
                MessageDict(
                    role="user",
                    content=[
                        TextMessageContent(
                            type="text",
                            text="Here is the initial state of the screen'.",
                        ),
                        ImageMessageContent(
                            type="image_url",
                            image_url=ImageURLDict(url=get_image_url(screenshot_file)),
                        ),
                    ],
                ),
            )
        else:
            if not invalid_last_action:
                messages.append(
                    MessageDict(
                        role="user",
                        content=[
                            TextMessageContent(
                                type="text",
                                text="Here is the screen after last execution of previous action suggested",
                            ),
                            ImageMessageContent(
                                type="image_url",
                                image_url=ImageURLDict(
                                    url=get_image_url(screenshot_file)
                                ),
                            ),
                        ],
                    )
                )
            else:
                messages.append(
                    MessageDict(
                        role="user",
                        content=[
                            TextMessageContent(
                                type="text",
                                text="Invalid Last action, Please try again",
                            )
                        ],
                    )
                )
                invalid_last_action = False
        response = None
        response = agent.inference(messages)
        print("Response: ", response)
        if response is not None:
            messages.append(
                MessageDict(
                    role="assistant",
                    content=[
                        TextMessageContent(type="text", text=response),
                    ],
                )
            )
            action = extract_action(response)
            if not action or (type(action) == dict and "type" not in action):
                invalid_last_action = True
            elif type(action) == dict:
                if action.get("type") == "finished":
                    print("Task completed.")
                    break
                elif action.get("type") == "wait" or action.get("type") == "sleep":
                    time.sleep(action.get("time", 1))
                else:
                    actionOperator.map_generate_action_to_event(action)
        else:
            invalid_last_action = True
        iter += 1


def main():
    parser = argparse.ArgumentParser(description="Run the TARS agent to perform tasks based on user instructions.")
    parser.add_argument("user_query", type=str, help="Task Query")
    args = parser.parse_args()
    user_query = args.user_query
    run_task_with_user_plan(user_query)

if __name__ == "__main__":
    main()
