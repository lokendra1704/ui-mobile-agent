import base64
import time
import subprocess
from PIL import Image
import os
import re
import json
from openai import OpenAI
import logging
from constants import MOONDREAM_PROMPT_TEMPLATE, OPENAI_FIXER_PROMPT, OPENAI_FIXER_SYSTEM_PROMPT

openai_agent = OpenAI(api_key=os.getenv("OPENAI_API_KEY_DZ"))
moondream_agent = OpenAI(
    api_key=os.getenv("MOONDREAM_API_KEY"), base_url=os.getenv("MOONDREAM_API_BASE_URL")
)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def call_openai_chat_completions(max_itr=3, **kwargs):
    while max_itr > 0:
        try:
            start_time = time.time()
            response = openai_agent.chat.completions.create(**{"model":"gpt-4o-mini", **kwargs})
            print("[call_openai_chat_completions] Time taken to get response from OPENAI:", time.time() - start_time)
            return response.choices[0].message.content
        except Exception as e:
            print("Error in Sending request to OpenAI API.", str(e))
            max_itr -= 1
            time.sleep(1)
    raise Exception("Failed to get response from OpenAI API.")
    


def track_usage(res_json, api_key):
    """
    {'id': 'chatcmpl-AbJIS3o0HMEW9CWtRjU43bu2Ccrdu', 'object': 'chat.completion', 'created': 1733455676, 'model': 'gpt-4o-2024-11-20', 'choices': [...], 'usage': {'prompt_tokens': 2731, 'completion_tokens': 235, 'total_tokens': 2966, 'prompt_tokens_details': {'cached_tokens': 0, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 0, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}, 'system_fingerprint': 'fp_28935134ad'}
    """
    model = res_json["model"]
    usage = res_json["usage"]
    if "prompt_tokens" in usage and "completion_tokens" in usage:
        prompt_tokens, completion_tokens = (
            usage["prompt_tokens"],
            usage["completion_tokens"],
        )
    elif "promptTokens" in usage and "completionTokens" in usage:
        prompt_tokens, completion_tokens = (
            usage["promptTokens"],
            usage["completionTokens"],
        )
    elif "input_tokens" in usage and "output_tokens" in usage:
        prompt_tokens, completion_tokens = usage["input_tokens"], usage["output_tokens"]
    else:
        prompt_tokens, completion_tokens = None, None

    prompt_token_price = None
    completion_token_price = None
    if prompt_tokens is not None and completion_tokens is not None:
        if "gpt-4o" in model:
            prompt_token_price = (2.5 / 1000000) * prompt_tokens
            completion_token_price = (10 / 1000000) * completion_tokens
        elif "gemini" in model:
            prompt_token_price = (1.25 / 1000000) * prompt_tokens
            completion_token_price = (5 / 1000000) * completion_tokens
        elif "claude" in model:
            prompt_token_price = (3 / 1000000) * prompt_tokens
            completion_token_price = (15 / 1000000) * completion_tokens
    return {
        "api_key": api_key,
        "id": res_json["id"] if "id" in res_json else None,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "prompt_token_price": prompt_token_price,
        "completion_token_price": completion_token_price,
    }


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_screen_coordinates(x, y, image_width, image_height):
    return (
        get_screen_x_coordinate(x, image_width),
        get_screen_y_coordinate(y, image_height),
    )


def get_screen_x_coordinate(x, image_width):
    print("[get_screen_x_coordinate] With arguments: ", x, image_width)
    return round(image_width * x / 1000)


def emulator_to_ai_x_coordinate(x, image_width):
    return round(x * 1000 / image_width)


def emulator_to_ai_y_coordinate(y, image_height):
    return round(y * 1000 / image_height)


def get_screen_y_coordinate(y, image_height):
    print("[get_screen_x_coordinate] With arguments: ", y, image_height)
    return round(image_height * y / 1000)


def get_image_url(image_path):
    encoded_string = encode_image(image_path)
    return f"data:image/jpeg;base64,{encoded_string}"


def get_screenshot(adb_path, save_path="./screenshot/screenshot.jpg"):
    print("Getting Screenshot...")
    max_retry = 3
    while max_retry > 0:
        try:
            command = adb_path + " shell rm /sdcard/screenshot.png"
            subprocess.run(command, capture_output=True, text=True, shell=True)
            time.sleep(0.5)
            command = adb_path + " shell screencap -p /sdcard/screenshot.png"
            subprocess.run(command, capture_output=True, text=True, shell=True)
            time.sleep(0.5)
            command = adb_path + f" pull /sdcard/screenshot.png {save_path}"
            subprocess.run(command, capture_output=True, text=True, shell=True)
            while not os.path.exists(save_path):
                time.sleep(0.2)
            image = Image.open(save_path)
            image.convert("RGB").save(save_path, "JPEG")
            return save_path
        except Exception as e:
            print(e)
            time.sleep(2)
            max_retry -= 1


def wait_for_file(filepath, timeout=2, poll_interval=0.1):
    """Poll for a file to appear until a timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(filepath):
            return True
        time.sleep(poll_interval)
    return False

def open_image_with_retry(filepath, max_attempts=3, delay=0.2):
    """Retry opening an image file if it is temporarily unavailable."""
    for attempt in range(max_attempts):
        try:
            return Image.open(filepath)
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} to open image failed: {e}")
            time.sleep(delay)
    raise FileNotFoundError(f"Could not open {filepath} after {max_attempts} attempts.")

def run_command(command, timeout=5):
    """Execute a shell command and log its output. Timeout ensures commands don't hang."""
    logging.info(f"Running command: {command}")
    result = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=timeout)
    if result.returncode != 0:
        logging.error(f"Command failed: {command}\nError: {result.stderr}")
    return result

def get_screenshot(adb_path, save_path="./screenshot/screenshot.jpg", retries=3):
    """Capture a screenshot from an Android device with minimal waiting and robust checks."""
    logging.info("Getting Screenshot...")
    while retries > 0:
        try:
            # Ensure the target directory exists.
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 1. Remove any previous screenshot on the device.
            # run_command(f"{adb_path} shell rm /sdcard/screenshot.png")

            # 2. Capture a new screenshot on the device.
            run_command(f"{adb_path} shell screencap -p /sdcard/screenshot.png")

            # 3. Pull the screenshot from the device to the local machine.
            pull_result = run_command(f"{adb_path} pull /sdcard/screenshot.png {save_path}")
            if pull_result.returncode != 0 or not wait_for_file(save_path):
                raise FileNotFoundError("ADB pull did not retrieve the file successfully.")

            # 4. Open the image with a quick retry mechanism.
            image = open_image_with_retry(save_path)

            # 5. Convert the image to RGB and save it as a JPEG.
            image.convert("RGB").save(save_path, "JPEG")
            logging.info(f"Screenshot saved successfully: {save_path}")
            return save_path

        except Exception as e:
            logging.error(f"Error obtaining screenshot: {e}")
            retries -= 1
            # A short pause before retrying
            time.sleep(0.5)

    raise RuntimeError("Failed to get screenshot after multiple retries.")

def validate_action_from_openai(prompt, system_prompt=OPENAI_FIXER_SYSTEM_PROMPT, screenshot_path=None):
    start_time = time.time()
    response = openai_agent.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": get_image_url(screenshot_path)}},
                {"type": "text", "text": prompt},
            ]},
        ],
    )
    print("[validate_action_from_openai] Time taken to get response from OPENAI:", time.time() - start_time)
    response = response.choices[0].message.content
    return extract_json_object(response)


def extract_action(agent_response: str):
    action_dict = {}
    agent_response = (
        agent_response.lower()
    )  # Convert to lowercase to avoid case sensitivity issues

    # Extract action type and parameters using regex
    click_match = re.search(
        r"click\(start_box(.*?)(\d+),(\d+)\)(.*?)\)", agent_response
    )
    long_press_match = re.search(
        r"long_press\(start_box='\((\d+),(\d+)\)'\)", agent_response
    )
    type_match = re.search(r"type\(content=['\"](.+?)['\"]\)", agent_response)
    scroll_match = re.search(
        r"scroll\(start_box='\((\d+),(\d+)\)', end_box='\((\d+),(\d+)\)'\)",
        agent_response,
    )
    handover_to_video_operator_match = re.search(
        r"handover_to_video_operator\(start_box='\((\d+),(\d+)\)'\)", agent_response
    )
    press_home_match = re.search(r"press_home\(\)", agent_response)
    press_back_match = re.search(r"press_back\(\)", agent_response)
    finished_match = re.search(r"finished\(.*?\)", agent_response)
    wait_match = re.search(r"wait\(\)", agent_response)
    double_click_match = re.search(
        r"double_click\(start_box='\((\d+),(\d+)\)'\)", agent_response
    )

    if scroll_match:
        action_dict["type"] = "scroll"
        action_dict["start_x"] = int(scroll_match.group(1))
        action_dict["start_y"] = int(scroll_match.group(2))
        action_dict["end_x"] = int(scroll_match.group(3))
        action_dict["end_y"] = int(scroll_match.group(4))
    elif type_match:
        action_dict["type"] = "type"
        action_dict["content"] = type_match.group(1)
    elif wait_match:
        action_dict["type"] = "wait"
    elif finished_match:
        action_dict["type"] = "finished"
    elif long_press_match:
        action_dict["type"] = "long_press"
        action_dict["x"] = int(long_press_match.group(1))
        action_dict["y"] = int(long_press_match.group(2))
    elif press_back_match:
        action_dict["type"] = "press_back"
    elif press_home_match:
        action_dict["type"] = "press_home"
    elif double_click_match:
        action_dict["type"] = "double_click"
        action_dict["x"] = int(double_click_match.group(1))
        action_dict["y"] = int(double_click_match.group(2))
    elif press_back_match:
        action_dict["type"] = "press_enter"
    elif click_match:
        action_dict["type"] = "click"
        action_dict["x"] = int(click_match.group(2))
        action_dict["y"] = int(click_match.group(3))
    elif handover_to_video_operator_match:
        action_dict["type"] = "handover_to_video_operator"
        action_dict["x"] = int(handover_to_video_operator_match.group(1))
        action_dict["y"] = int(handover_to_video_operator_match.group(2))
    return action_dict


def make_valid_filename(input_string: str):
    sanitized = input_string.strip()
    sanitized = re.sub(r'[<>:"/\\|?*]', "", sanitized)
    sanitized = re.sub(r"\s+", "_", sanitized)
    return sanitized


def query_moondream(messages, max_retry=3, retry_interval=0.5):
    if not messages:
        return None
    while max_retry > 0:
        try:
            start_time = time.time()
            response = moondream_agent.chat.completions.create(
                model=os.getenv("MOONDREAM_MODEL_NAME"), messages=messages
            )
            print("[query_moondream] Time taken to get response:", time.time() - start_time)
            return response.choices[0].message.content
        except Exception as e:
            print(
                f"[query_moondream][{max_retry}] Failed to Query Moondream API:", str(e)
            )
            max_retry -= 1
            time.sleep(retry_interval)


def quick_state_validation(element_description, image_path, prompt_type="quick_check"):
    get_screenshot(os.getenv("ADB_PATH", "adb"), save_path=image_path)
    if not element_description or not image_path:
        raise Exception("Element description and image path are required.")
    if prompt_type == "quick_check":
        query = MOONDREAM_PROMPT_TEMPLATE.substitute(
                            description=element_description,
                        )
    else:
        query = element_description
    response = query_moondream(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": get_image_url(image_path),
                        },
                    }
                ],
            }
        ]
    )
    print(f"[QUICK CHECK VALIDATION][]: QUERY: {query} ----------------RESPONSE: {response}")
    if response and type(response) == str:
        return "y" in response.lower()

def extract_json_object(text, json_type="dict"):
    """
    Extracts a JSON object from a text string.

    Parameters:
    - text (str): The text containing the JSON data.
    - json_type (str): The type of JSON structure to look for ("dict" or "list").

    Returns:
    - dict or list: The extracted JSON object, or None if parsing fails.
    """
    try:
        if "//" in text:
            # Remove comments starting with //
            text = re.sub(r'//.*', '', text)
        if "# " in text:
            # Remove comments starting with #
            text = re.sub(r'#.*', '', text)
        # Try to parse the entire text as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        pass  # Not a valid JSON, proceed to extract from text

    # Define patterns for extracting JSON objects or arrays
    json_pattern = r"({.*?})" if json_type == "dict" else r"(\[.*?\])"

    # Search for JSON enclosed in code blocks first
    code_block_pattern = r"```json\s*(.*?)\s*```"
    code_block_match = re.search(code_block_pattern, text, re.DOTALL)
    if code_block_match:
        json_str = code_block_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass  # Failed to parse JSON inside code block

    # Fallback to searching the entire text
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue  # Try the next match

    # If all attempts fail, return None
    return None

def replace_action(original_string: str, corrected_json: dict) -> str:
    # Extract the corrected action from the JSON
    corrected_action = corrected_json.get("corrected_action", "")
    
    # Regular expression to find the existing Action statement
    action_pattern = re.compile(r"(Action:\s*)(.*)")
    
    # Replace the existing action with the corrected one
    def replace_match(match):
        return f"{match.group(1)}{corrected_action}"
    
    return action_pattern.sub(replace_match, original_string)

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Any

def run_functions_in_parallel(funcs: List[Callable[[], Any]]) -> List[Any]:
    """
    Runs a list of synchronous functions in parallel using asyncio and ThreadPoolExecutor.
    Returns the results in a list, maintaining the order.

    :param funcs: List of callable functions with no arguments.
    :return: List of results from the functions.
    """
    async def run_in_executor(func):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)

    async def main():
        tasks = [run_in_executor(func) for func in funcs]
        return await asyncio.gather(*tasks)

    try:
        loop = asyncio.get_running_loop()
        future = asyncio.ensure_future(main())
        return future.result() if future.done() else future
    except RuntimeError:
        return asyncio.run(main())
    
def timestamp_to_seconds(timestamp: str) -> int:
    """
    Convert a timestamp in "hh:mm:ss" or "mm:ss" format to total seconds.
    
    Args:
        timestamp (str): A string representing the timestamp.
    
    Returns:
        int: The total number of seconds.
    
    Raises:
        ValueError: If the timestamp format is not valid.
    """
    try:
        if type(timestamp) is str and ":" in timestamp:
            parts = timestamp.split(":")
            
            if len(parts) == 2:
                # Format: mm:ss
                minutes, seconds = parts
                total_seconds = int(minutes) * 60 + int(seconds)
            elif len(parts) == 3:
                # Format: hh:mm:ss
                hours, minutes, seconds = parts
                total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            else:
                raise ValueError("Timestamp format must be either 'mm:ss' or 'hh:mm:ss'")
            
            return total_seconds
        elif type(timestamp) is str:
            return int(timestamp)
        elif type(timestamp) is int:
            return timestamp
        else:
            raise ValueError("Invalid timestamp format. Must be a string in 'mm:ss' or 'hh:mm:ss' format.")
    except Exception as e:
        raise ValueError(f"Error converting timestamp to seconds: {str(e)}")


if __name__ == "__main__":
    # response = quick_state_validation(
    #     "What are the timestamp of the video?",
    #     "/Users/lokendrabairwa/talkshopclub/ui-mobile-agent/tasks/2025_02_10_04_07_24/Seek_forward_the_video_progres_683bd/screenshots/screenshot_2_1.jpg",
    #     prompt_type="qa"
    # )
#     tars_response = """
# Thought: Since the video has not yet started playing, it is likely that the page has not fully loaded. To ensure the video is ready for interaction, I need to wait for the page to load completely before attempting to play the video again. This will help avoid any potential issues with the video not playing or the interface not responding.\nWait for the page to load completely before proceeding to play the video.\nAction: double_click(start_box='(511,156)')
# """
#     response = openai_agent.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": [{"type": "text", "text": OPENAI_FIXER_PROMPT}]},
#             {"role": "user", "content": [{"type": "text", "text": tars_response}]},
#         ],
#     )
#     response_json = response.choices[0].message.content
#     try:
#         response_dict = extract_json_object(response_json)
#         print(response_dict)
#         print("New Response")
#         print(replace_action(tars_response, response_dict))
#     except Exception as e:
#         print("error", e)
    # image_path = "/Users/lokendrabairwa/talkshopclub/ui-mobile-agent/video_analyzer/2025-02-11_10-05-03.jpg"
    # print(
    #     run_functions_in_parallel([
    #         lambda: quick_state_validation("is pause button visible here? reply with y if visible else n", image_path, prompt_type="qa"),
    #         lambda: quick_state_validation("is play button visible here? reply with y if visible else n", image_path, prompt_type="qa"),
    #     ])
    # )
    screenshot_path = "/Users/lokendrabairwa/talkshopclub/ui-mobile-agent/video_analyzer/temp.jpg"
    get_screenshot(os.getenv("ADB_PATH", "adb"), save_path=screenshot_path)
    response = """Thought: To proceed with the task of clicking on the first video, I need to interact with the video titled \"Vector & Three-Dimensional Geometry 03: Important Questions.\" This involves tapping on the video thumbnail to open it and begin playback. The video is clearly identifiable by its title and thumbnail, making it straightforward to locate and select.\nAction: click(start_box='(237,196)')
"""
    openai_response = validate_action_from_openai(
        OPENAI_FIXER_PROMPT.substitute(
            tars_response=response,
            user_instruction="Play the first video",
        ),
        screenshot_path=screenshot_path,
    )
    print(openai_response)