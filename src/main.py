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
from utils import get_screenshot, extract_action, validate_action_from_openai, make_valid_filename
from actions import ActionSpace
import argparse
import json
from constants import OPENAI_FIXER_PROMPT
import datetime
import uuid

load_dotenv()

def append_to_message(messages_list:list, new_message, log_file_name):
    messages_list.append(new_message)
    with open(f"log/{log_file_name}", "w") as f:
        json.dump(messages_list, f, indent=4)

def run_task_with_user_plan(user_plan, max_itr=20, llm_type="dpo", parent_dir="."):
    if not user_plan:
        raise Exception("User plan is not provided.")
    agent = TARS(base_type=llm_type if llm_type else "dpo", system_name="default", user_instruction=user_plan)
    messages = []
    iter = 1
    actionOperator = None
    response = None
    invalid_last_action = False
    screenshot_dir = os.path.join(parent_dir, f"screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    while True:
        screenshot_paths = [os.path.join(screenshot_dir, f"screenshot_{iter}_1.jpg"), ]
        for screenshot_path in screenshot_paths:
            get_screenshot(adb_path="adb", save_path=screenshot_path)
            time.sleep(1)
        if max_itr is not None and iter >= max_itr:
            print("Max iteration reached. Stopping...")
            break
        if iter == 1:
            width, height = Image.open(screenshot_paths[0]).size
            actionOperator = ActionSpace(
                adb_path=os.getenv("ADB_PATH", "adb"),
                image_width=width,
                image_height=height,
            )
            append_to_message(
                messages,
                MessageDict(
                    role="user",
                    content=[
                        TextMessageContent(
                            type="text",
                            text="Here are two screenshots of the UI clicked with 1s time interval. First screenshot is the initial screen and second screenshot is the screen after one second. This will help you understand dynamic changes in the screen.",
                        ),
                        *[
                            ImageMessageContent(
                                type="image_url",
                                image_url=ImageURLDict(url=screenshot_path),
                            )
                            for screenshot_path in screenshot_paths
                        ],
                    ],
                ),
                agent.message_log_file_name,
            )
        else:
            if not invalid_last_action:
                append_to_message(
                    messages,
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
                                    url=screenshot_paths[0]
                                ),
                            ),
                        ],
                    ),
                    agent.message_log_file_name,
                )
            else:
                append_to_message(
                    messages,
                    MessageDict(
                        role="user",
                        content=[
                            TextMessageContent(
                                type="text",
                                text="Invalid Last action, Please try again",
                            )
                        ],
                    ),
                    agent.message_log_file_name,
                )
                invalid_last_action = False
        response = None
        response = agent.inference(messages)
        print("TARS Response: ", response)
        print("------------------------------------")
        if response is not None:
            fixed_answer = validate_action_from_openai(OPENAI_FIXER_PROMPT , f"TARS_RESPONSE: {response}\nFIXED_OUTPUT: Thought:")
            openai_response = f"Thought: {fixed_answer}"
            if openai_response!=response:
                response = openai_response
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
            append_to_message(
                messages,
                MessageDict(
                    role="assistant",
                    content=[
                        TextMessageContent(type="text", text=response),
                    ],
                ),
                agent.message_log_file_name,
            )
        else:
            invalid_last_action = True
        iter += 1


def main():
    parser = argparse.ArgumentParser(description="Run the TARS agent to perform tasks based on user instructions.")
    parser.add_argument("user_query", type=str, help="Task Query")
    parser.add_argument("--llm_type", type=str, default="dpo", help="dpo/sft: DPO-trained llm or SFT-trained llm")
    parser.add_argument("--max_itr", type=int, default=10, help="Maximum number of iterations to run the task")
    args = parser.parse_args()
    user_query = args.user_query
    llm_type = args.llm_type
    max_itr = args.max_itr
    run_task_with_user_plan(user_query, max_itr=max_itr, llm_type=llm_type)

if __name__ == "__main__":
    user_plan = [
        # "Click on first video in the list",
        "Pause the video",
        "Seek forward the video progress bar to 01:10:00",
        "Play the video",
    ]
    current_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    TASK_DIR = f"./tasks/{current_time}"
    for i,plan in enumerate(user_plan):
        CURRENT_TASK_DIR = os.path.join(TASK_DIR, f"{make_valid_filename(plan)[:30]}_{uuid.uuid4().hex[0:5]}")
        print(f"*********************Running Task {i+1}: {plan}********************")
        run_task_with_user_plan(plan, max_itr=20, llm_type="dpo", parent_dir=CURRENT_TASK_DIR)
        print("$$$$$$$$$$$$$$$$$$$$ Finished STEP $$$$$$$$$$$$$$$$$$$$$$")

