import base64
import time
import subprocess
from PIL import Image
import os
import re

def track_usage(res_json, api_key):
    """
    {'id': 'chatcmpl-AbJIS3o0HMEW9CWtRjU43bu2Ccrdu', 'object': 'chat.completion', 'created': 1733455676, 'model': 'gpt-4o-2024-11-20', 'choices': [...], 'usage': {'prompt_tokens': 2731, 'completion_tokens': 235, 'total_tokens': 2966, 'prompt_tokens_details': {'cached_tokens': 0, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 0, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}, 'system_fingerprint': 'fp_28935134ad'}
    """
    model = res_json['model']
    usage = res_json['usage']
    if "prompt_tokens" in usage and "completion_tokens" in usage:
        prompt_tokens, completion_tokens = usage['prompt_tokens'], usage['completion_tokens']
    elif "promptTokens" in usage and "completionTokens" in usage:
        prompt_tokens, completion_tokens = usage['promptTokens'], usage['completionTokens']
    elif "input_tokens" in usage and "output_tokens" in usage:
        prompt_tokens, completion_tokens = usage['input_tokens'], usage['output_tokens']
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
        "id": res_json['id'] if "id" in res_json else None,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "prompt_token_price": prompt_token_price,
        "completion_token_price": completion_token_price
    }

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def get_screen_coordinates(x,y,image_width, image_height):
    return (
        get_screen_x_coordinate(x, image_width),
        get_screen_y_coordinate(y, image_height)
    )

def get_screen_x_coordinate(x, image_width):
    return round(image_width*x/1000)

def get_screen_y_coordinate(y, image_height):
    return round(image_height*y/1000)

def get_image_url(image_path):
    encoded_string = encode_image(image_path)
    return f"data:image/jpeg;base64,{encoded_string}"

def get_screenshot(adb_path, save_path="./screenshot/screenshot.jpg"):
    max_retry = 3
    while max_retry > 0:
        try:
            command = adb_path + " shell rm /sdcard/screenshot.png"
            subprocess.run(command, capture_output=True, text=True, shell=True)
            time.sleep(0.5)
            command = adb_path + " shell screencap -p /sdcard/screenshot.png"
            subprocess.run(command, capture_output=True, text=True, shell=True)
            time.sleep(0.5)
            command = adb_path + " pull /sdcard/screenshot.png ./screenshot/screenshot.png"
            subprocess.run(command, capture_output=True, text=True, shell=True)
            image_path = "./screenshot/screenshot.png"
            image = Image.open(image_path)
            image.convert("RGB").save(save_path, "JPEG")
            os.remove(image_path)
            return
        except Exception as e:
            time.sleep(2)
            max_retry -= 1

def extract_action(agent_response: str):
    action_dict = {}
    agent_response = agent_response.lower()  # Convert to lowercase to avoid case sensitivity issues
    
    # Extract action type and parameters using regex
    click_match = re.search(r"action: click\(start_box='\((\d+),(\d+)\)'\)", agent_response)
    long_press_match = re.search(r"action: long_press\(start_box='\((\d+),(\d+)\)'\)", agent_response)
    type_match = re.search(r"action: type\(content=['\"](.+?)['\"]\)", agent_response)
    scroll_match = re.search(r"action: scroll\(start_box='\((\d+),(\d+)\)', end_box='\((\d+),(\d+)\)'\)", agent_response)
    press_home_match = re.search(r'action: press_home\(\)', agent_response)
    press_back_match = re.search(r'action: press_back\(\)', agent_response)
    finished_match = re.search(r'action: finished\(\)', agent_response)
    wait_match = re.search(r'action: wait\(\)', agent_response)
    double_click_match = re.search(r"action: double_click\(start_box='\((\d+),(\d+)\)'\)", agent_response)
    
    if click_match:
        action_dict["type"] = "click"
        action_dict["x"] = int(click_match.group(1))
        action_dict["y"] = int(click_match.group(2))
    elif scroll_match:
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
    
    return action_dict

if __name__ == "__main__":
    print(extract_action("""
1. To move the video to the desired timestamp of 01:10:00, I need to use the progress bar to calculate the appropriate position. Since the video is currently at 19:22, the next step is to drag the progress bar to the left to reach the target time of 01:10:00.
2. The progress bar is located at the bottom of the video player interface, and the current seek position is indicated by the red marker.
3. By dragging the progress bar to the left, I can adjust the seek position to the desired timestamp, ensuring the video plays from the correct point.
Action: scroll(start_box='(226,222)', end_box='(650,226)')                      
"""))