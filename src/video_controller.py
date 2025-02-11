from actions import ActionSpace
import time
import os
import datetime
import json
from typing import Optional
from constants import VIDEO_CONTROLLER_SYSTEM_PROMPT, VIDEO_PLAYER_IMAGE_ANALYZER_PROMPT, VIDEO_CONTROLLER_PROMPT_TEMPLATE
from utils import call_openai_chat_completions, get_screenshot, get_image_url, extract_json_object, run_functions_in_parallel, quick_state_validation

TEMP_PARENT_DIR = "video_analyzer"

adb_agent = ActionSpace()

VIDEO_PLAYER_STATES = [
    "INTERACTIVE_PLAYING",
    "NON_INTERACTIVE_PLAYING",
    "INTERACTIVE_PAUSED",
    "NON_INTERACTIVE_PAUSED",
    "NON_INTERACTIVE_WITH_PROGRESS_BAR"   
]

"""
(can be TODO: make state machine for video player)
Video Player States:
- INTERACTIVE_PLAYING: Mostly Intial State; ; lasts for 3 seconds
- NON_INTERACTIVE_PLAYING: After 3 seconds of inactivity, the player becomes non-interactive.
- INTERACTIVE_PAUSED: lasts indefinitely if nothing else is clicked, but if any playback controls are clicked, it becomes non-interactive after 3 seconds of last action.
- NON_INTERACTIVE_PAUSED: When in INTERACTIVE_PAUSED state, and any playback control is clicked (except play), then after few seconds of inactivity, it becomes NON_INTERACTIVE_PAUSED.
- NON_INTERACTIVE_WITH_PROGRESS_BAR: When in NON_INTERACTIVE_PAUSED state, and play is clicked, then it becomes NON_INTERACTIVE_WITH_PROGRESS_BAR.
"""


"""
Interactive: Shows Playback controls.

When Player is interactive and playing, click on safe click coordinates pauses the video.
When Player is non-interactive, click on safe click coordinates makes it interactive.
"""

def analyze_video_player_using_llm(screenshot_file_path=None, parent_dir=TEMP_PARENT_DIR):
    if not screenshot_file_path:
        screenshot_file_path = os.path.join(parent_dir, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".jpg")
    os.makedirs(parent_dir, exist_ok=True)
    if not os.path.exists(screenshot_file_path):
        get_screenshot("adb", screenshot_file_path)
    return call_openai_chat_completions(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are an expert image analyzer"},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VIDEO_PLAYER_IMAGE_ANALYZER_PROMPT},
                    {"type": "image_url", "image_url": {"url": get_image_url(screenshot_file_path)}},
                ],
            }
        ]
    )

class VideoController:
    def __init__(
        self,
        total_video_duration: Optional[str] = None,
        pause_or_play_button_coordinates: Optional[tuple] = None,
        video_progress_bar_bbox_coordinates: Optional[tuple] = None,
        forward_button_coordinates: Optional[tuple] = None,
        backward_button_coordinates: Optional[tuple] = None,
        is_pause_button_visible: Optional[bool] = None,
        is_play_button_visible: Optional[bool] = None,
        is_forward_button_visible: Optional[bool] = None,
        is_backward_button_visible: Optional[bool] = None,
        is_video_progress_bar_visible: Optional[bool] = None,
        current_video_timestamp: Optional[str] = None,
        video_progress_bar_current_coordinates: Optional[tuple] = None,
    ):
        # Static attributes
        self.total_video_duration = total_video_duration
        self.pause_or_play_button_coordinates = pause_or_play_button_coordinates
        self.video_progress_bar_bbox_coordinates = video_progress_bar_bbox_coordinates
        self.forward_button_coordinates = forward_button_coordinates
        self.backward_button_coordinates = backward_button_coordinates

        # Dynamic attributes
        self.is_video_paused_or_playing = None
        self.is_pause_button_visible = is_pause_button_visible
        self.is_play_button_visible = is_play_button_visible
        self.is_forward_button_visible = is_forward_button_visible
        self.is_backward_button_visible = is_backward_button_visible
        self.is_video_progress_bar_visible = is_video_progress_bar_visible
        self.current_video_timestamp = current_video_timestamp
        self.video_progress_bar_current_coordinates = video_progress_bar_current_coordinates

        #Initialize
        self.ensure_video_paused(self.pause_or_play_button_coordinates)
        self.update_video_player_state(ensure_pause=False)

    def __repr__(self):
        return (
            f"VideoController("
            f"total_video_duration={self.total_video_duration}, "
            f"pause_or_play_button_coordinates={self.pause_or_play_button_coordinates}, "
            f"video_progress_bar_bbox_coordinates={self.video_progress_bar_bbox_coordinates}, "
            f"forward_button_coordinates={self.forward_button_coordinates}, "
            f"backward_button_coordinates={self.backward_button_coordinates}, "
            f"is_pause_button_visible={self.is_pause_button_visible}, "
            f"is_play_button_visible={self.is_play_button_visible}, "
            f"is_forward_button_visible={self.is_forward_button_visible}, "
            f"is_backward_button_visible={self.is_backward_button_visible}, "
            f"is_video_progress_bar_visible={self.is_video_progress_bar_visible}, "
            f"current_video_timestamp={self.current_video_timestamp}, "
            f"video_progress_bar_current_coordinates={self.video_progress_bar_current_coordinates})"
        )
        
    def update_video_player_state(self, ensure_pause=True):
        """
        Captures all the possible information of the video player and generates the following dictionary. The default values are for NON_INTERACTIVE_PLAYING.
        NOTE: All COORDINATES ARE AI_VERSION. (NOT RELATIVE TO SCREEN)
        - Only mark ensure pause false when you are sure that the video is paused.
        """
        ## Ensure paused
        if ensure_pause:
            self.ensure_video_paused(self.pause_or_play_button_coordinates)
        parsed_information = analyze_video_player_using_llm()
        parsed_json = extract_json_object(parsed_information)
        if parsed_json:
            # Set all dynamic attributes
            if parsed_json.get("total_video_duration", None): 
                self.total_video_duration = parsed_json.get("total_video_duration", None)
            if parsed_json.get("video_progress_bar_bbox_coordinates", None): 
                self.video_progress_bar_bbox_coordinates = parsed_json.get("video_progress_bar_bbox_coordinates", None)
            if parsed_json.get("forward_button_coordinates", None): 
                self.forward_button_coordinates = parsed_json.get("forward_button_coordinates", None)
            if parsed_json.get("backward_button_coordinates", None): 
                self.backward_button_coordinates = parsed_json.get("backward_button_coordinates", None)
            if parsed_json.get("is_forward_button_visible", False): 
                self.is_forward_button_visible = parsed_json.get("is_forward_button_visible", False)
            if parsed_json.get("is_backward_button_visible", False): 
                self.is_backward_button_visible = parsed_json.get("is_backward_button_visible", False)
            if parsed_json.get("is_video_progress_bar_visible", False): 
                self.is_video_progress_bar_visible = parsed_json.get("is_video_progress_bar_visible", False)
            if parsed_json.get("current_video_timestamp", "00:00:00"): 
                self.current_video_timestamp = parsed_json.get("current_video_timestamp", "00:00:00")
            if parsed_json.get("video_progress_bar_current_coordinates", None): 
                self.video_progress_bar_current_coordinates = parsed_json.get("video_progress_bar_current_coordinates", None)
        return True

    def click_play_pause_button(self, coordinates=None):
        player_coordinates = coordinates if coordinates else self.pause_or_play_button_coordinates
        adb_agent.scroll(
            player_coordinates[0],
            player_coordinates[1],
            player_coordinates[0],
            player_coordinates[1],
            duration_in_ms=250
        )
        return True

    def make_video_player_interactive(self, player_coordinates=None):
        """
        This function makes the video player interactive.
        """
        player_coordinates = player_coordinates if player_coordinates else self.pause_or_play_button_coordinates
        adb_agent.click(player_coordinates[0], player_coordinates[1]-50)

    def is_video_playing(self, player_coordinates):
        """
        This function checks if the video is playing or paused.
        """
        self.update_video_player_state(player_coordinates) # Better to check this everytime the function is invoked, we don't know how much stale the values are.
        while not self.is_pause_button_visible and not self.is_play_button_visible:
            self.make_video_player_interactive(player_coordinates)
            self.update_video_player_state(player_coordinates)
        return self.is_pause_button_visible

    def is_video_paused(self, player_coordinates):
        """
        This function checks if the video is playing or paused.
        """
        self.update_video_player_state(player_coordinates) 
        while not self.is_pause_button_visible and not self.is_play_button_visible:
            self.make_video_player_interactive(player_coordinates)
            self.update_video_player_state(player_coordinates)
        return self.is_play_button_visible

    def ensure_video_paused(self, player_coordinates=None):
        """
        This function ensures that the video is paused.
        """
        if not player_coordinates:
            player_coordinates = self.pause_or_play_button_coordinates
        self.check_player_interactivity()
        if self.is_play_button_visible:
            pass
        elif self.is_pause_button_visible:
            # For more fail-safe approach, we can do wait->make_video_player_interactive->click_play_pause_button
            time.sleep(3.5)
            self.make_video_player_interactive(player_coordinates)
            time.sleep(0.2)
            self.click_play_pause_button(player_coordinates)
        # Other ifs
        while not self.is_pause_button_visible and not self.is_play_button_visible:
            print("[While-Loop] Ensuring Video is Paused...")
            self.make_video_player_interactive(player_coordinates)
            time.sleep(0.5)
            self.click_play_pause_button(player_coordinates)
            self.check_player_interactivity()
        # SET RELEVANT STATES TO PAUSED
        self.is_play_button_visible = True
        self.is_pause_button_visible = False
        self.is_backward_button_visible = True
        self.is_forward_button_visible = True
        self.is_video_progress_bar_visible = True
        self.is_video_paused_or_playing = "PAUSED"
        return True
    
    def ensure_video_playing(self, player_coordinates=None):
        if not player_coordinates:
            player_coordinates = self.pause_or_play_button_coordinates
        self.check_player_interactivity()
        if self.is_pause_button_visible:
            pass
        elif self.is_play_button_visible:
            self.click_play_pause_button(player_coordinates)
        while not self.is_pause_button_visible and not self.is_play_button_visible:
            print("[While-Loop] Ensuring Video is Playing...")
            self.make_video_player_interactive(player_coordinates)
            time.sleep(0.5)
            self.click_play_pause_button(player_coordinates)
            self.check_player_interactivity()
        # Set the relevants states to playing
        self.is_play_button_visible = False
        self.is_pause_button_visible = False
        self.is_backward_button_visible = False
        self.is_forward_button_visible = False
        self.is_video_progress_bar_visible = False
        self.is_video_paused_or_playing = "PLAYING"
        return True
    
    def get_action_logs(self):
        return self.action_logs

    def check_player_interactivity(self, screenshot_file_path=None, parent_dir=TEMP_PARENT_DIR):
        """
        This function checks if the player is interactive or not by sending the picture to moondream/openai.
        """
        if not screenshot_file_path:
            screenshot_file_path = os.path.join(parent_dir, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".jpg")
        os.makedirs(parent_dir, exist_ok=True)
        if not os.path.exists(screenshot_file_path):
            get_screenshot("adb", screenshot_file_path)
        pause_visible, play_visible = run_functions_in_parallel([
                lambda: quick_state_validation("is pause button visible here? reply with y if visible else n", screenshot_file_path, prompt_type="qa"),
                lambda: quick_state_validation("is play button visible here? reply with y if visible else n", screenshot_file_path, prompt_type="qa"),
            ])
        self.is_pause_button_visible = pause_visible
        self.is_play_button_visible = play_visible
        if self.is_play_button_visible:
            # Because pause/play button gets visible with other buttons.
            self.is_backward_button_visible = True
            self.is_forward_button_visible = True
        return pause_visible or play_visible

    def confirm_video_player_is_interactive(self, player_coordinates=None):
        """
        This is same to ensure_video_paused, because to make sure video player is interactive, we need to ensure it is paused first.
        """
        return self.ensure_video_paused(player_coordinates)


def get_next_action(video_controller_obj, action, actions_taken = ["pause_video"],):
    messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": VIDEO_CONTROLLER_SYSTEM_PROMPT},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VIDEO_CONTROLLER_PROMPT_TEMPLATE.substitute(
                        user_instruction=action,
                        actions_taken = json.dumps(actions_taken),
                        video_player_state=video_controller_obj.__repr__(),
                    )},
                ],
            }
        ]
    print(messages)
    return call_openai_chat_completions(
        messages=messages
    )

def operate_video_player(user_query, coordinates=(501, 157)):
    video_controller = VideoController(pause_or_play_button_coordinates=coordinates)
    action = None
    action_logs = ["pause_video"]
    while not action or (action and "finished" not in action):
        action_json = get_next_action(video_controller, user_query, action_logs)
        action = extract_json_object(action_json).get("action", None)
        action = action.lower() if action else ""
        if "play" in action:
            video_controller.ensure_video_playing()
        elif "pause" in action:
            video_controller.ensure_video_paused()
        elif "finished" in action:
            break
        action_logs.append(action)
    print("Completed the task.")
    return True
    
if __name__ == "__main__":
    user_task = "Play the video player"
    operate_video_player(user_task)

    