from actions import ActionSpace
import time
import os
import datetime
import json
from typing import Optional
import re
from constants import VIDEO_CONTROLLER_SYSTEM_PROMPT, VIDEO_PLAYER_IMAGE_ANALYZER_PROMPT, VIDEO_CONTROLLER_PROMPT_TEMPLATE, CHECK_PAUSED_PROMPT, CHECK_PLAYING_PROMPT, OPENAI_PLAY_PAUSE_PROMPT
from utils import call_openai_chat_completions, get_screenshot, get_image_url, extract_json_object, run_functions_in_parallel, quick_state_validation, timestamp_to_seconds, emulator_to_ai_y_coordinate, emulator_to_ai_x_coordinate

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
        # video_progress_bar_current_coordinates: Optional[tuple] = None,
    ):
        # Static attributes
        self.total_video_duration = total_video_duration
        self.pause_or_play_button_coordinates = pause_or_play_button_coordinates
        self.video_progress_bar_bbox_coordinates = [
            [emulator_to_ai_x_coordinate(28, 1080), emulator_to_ai_y_coordinate(545, 2400)],
            [emulator_to_ai_x_coordinate(1050, 1080), emulator_to_ai_y_coordinate(545, 2400)]
        ] # Change it using appium or other methods.
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
        # self.video_progress_bar_current_coordinates = [[28, 545], [1050, 545]] 

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
            # f"video_progress_bar_current_coordinates={self.video_progress_bar_current_coordinates})"
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
            # if parsed_json.get("video_progress_bar_current_coordinates", None): 
            #     self.video_progress_bar_current_coordinates = parsed_json.get("video_progress_bar_current_coordinates", None)
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
        print("[make_video_player_interactive] Making Video Player Interactive by clicking randomly...")
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
            print("[While-Loop] Ensuring Video is Paused...Current Stat: Visibility: Pause Button", self.is_pause_button_visible, "Visibility: Play Button", self.is_play_button_visible)
            self.make_video_player_interactive(player_coordinates)
            time.sleep(0.5)
            self.click_play_pause_button(player_coordinates)
            time.sleep(1.5)
            print("[While-loop][After Attempt to make interactive] Attempted, now checking the latest state")
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
        # pause_visible, play_visible = run_functions_in_parallel([
        #         lambda: quick_state_validation(CHECK_PAUSED_PROMPT, screenshot_file_path, prompt_type="qa"),
        #         lambda: quick_state_validation(CHECK_PLAYING_PROMPT, screenshot_file_path, prompt_type="qa"),
        #     ])
        pause_visible = None
        play_visible = None
        response = call_openai_chat_completions(
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OPENAI_PLAY_PAUSE_PROMPT},
                        {"type": "image_url", "image_url": {"url": get_image_url(screenshot_file_path)}},
                    ],
                }
            ]
        )
        parsed_response = extract_json_object(response)
        if parsed_response:
            print("[check_player_interactivity][Results]", parsed_response)
            pause_visible = parsed_response.get("is_pause_icon_visible", None)
            play_visible = parsed_response.get("is_play_icon_visible", None)
        else:
            raise Exception("Error in check_player_interactivity.")
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

    def _seek_actions_(self, current_timestamp=None, desired_timestamp=None, diff=None):
        """
        Given the current and desired timestamps (in seconds),
        returns a list of actions to move the video player to the desired time.
        
        Tools available:
        - scroll()                # For large jumps (≥ 100 seconds difference)
        - forward()               # Jumps forward by 10 seconds
        - backward()              # Jumps backward by 10 seconds
        - play_for_seconds(seconds=)  # Fine adjustment (seconds should be less than 3)
        
        Logic:
        - If |difference| >= 100 seconds, use scroll() to jump roughly to the desired time.
        - Otherwise, use forward() or backward() for 10-second increments.
        - Then, if there's a remaining difference less than 3 seconds, use play_for_seconds().
        - If the remaining difference is 3 seconds or more (rare case), add one more forward/backward.
        
        Examples:
        1. current=3600, desired=3690  (diff = +90 sec)
            → 9 forward() actions.
        2. current=3600, desired=3612  (diff = +12 sec)
            → 1 forward() action, then play_for_seconds(seconds=2).
        3. current=3600, desired=3540  (diff = -60 sec)
            → 6 backward() actions.
        """
        current_timestamp = timestamp_to_seconds(current_timestamp)
        desired_timestamp = timestamp_to_seconds(desired_timestamp)
        actions = []
        diff = diff if diff else desired_timestamp - current_timestamp

        if abs(diff) >= 100:
            # For large jumps, assume scroll() brings you roughly to the desired time.
            actions.append("scroll()")
        else:
            # For small differences, use forward/backward in 10-second increments.
            steps = int(abs(diff) // 10)  # Number of full 10-second steps.
            remainder = abs(diff) % 10    # Remaining seconds after full steps.
            if diff > 0:
                for _ in range(steps):
                    actions.append("forward()")
            elif diff < 0:
                for _ in range(steps):
                    actions.append("backward()")
            # Fine adjustment: if remainder is non-zero.
            if remainder > 0:
                play_for_seconds_steps = int(remainder // 3)
                seconds_remainder = remainder % 3
                for _ in range(play_for_seconds_steps):
                    actions.append("play_for_seconds(seconds=3)")
                if seconds_remainder < 3 and seconds_remainder > 0:
                    actions.append(f"play_for_seconds(seconds={seconds_remainder})")
        for action in actions:
            if "forward" in action :
                adb_agent.click(
                    emulator_to_ai_x_coordinate(850, 1080),
                    emulator_to_ai_y_coordinate(380, 2400)
                )
            elif "backward" in action:
                adb_agent.click(
                    emulator_to_ai_x_coordinate(240, 1080),
                    emulator_to_ai_y_coordinate(380, 2400)
                )
            elif "play_for_seconds" in action:
                seconds = re.search(r"play_for_seconds\(seconds=(\d+)\)", action).group(1)
                if seconds:
                    seconds = int(seconds)
                else:
                    raise Exception("Invalid action format.")
                adb_agent.click(
                    emulator_to_ai_x_coordinate(540, 1080),
                    emulator_to_ai_y_coordinate(380, 2400)
                )
                time.sleep(seconds)
                adb_agent.click(
                    emulator_to_ai_x_coordinate(540, 1080),
                    emulator_to_ai_y_coordinate(380, 2400)
                )
            time.sleep(2)
        return True

    def predict_x_coordinate(self, timestamp, progress_range=None, video_duration=None):
        """
        Given a progress bar range, a desired timestamp, and the total video duration,
        predict the x-coordinate on the progress bar.

        Args:
            progress_range (tuple): A tuple (start_x, end_x) representing the progress bar's x-axis boundaries.
            timestamp (float): The desired timestamp in seconds.
            video_duration (float): The total duration of the video in seconds.

        Returns:
            float: The predicted x-coordinate corresponding to the timestamp.
        """
        if progress_range is None:
            progress_range = self.get_video_progress_bar_x_coordinates()
        if video_duration is None:
            video_duration = timestamp_to_seconds(self.total_video_duration)
        start_x, end_x = progress_range
        progress_width = end_x - start_x
        proportion = timestamp / video_duration
        x_coordinate = start_x + proportion * progress_width
        return x_coordinate

    def get_video_progress_bar_x_coordinates(self):
        if self.video_progress_bar_bbox_coordinates:
            return ( self.video_progress_bar_bbox_coordinates[0][0], self.video_progress_bar_bbox_coordinates[1][0] )
        else:
            return None

    def jump_to_approximate_timestamp(self, timestamp):
        """
        ASSUMES THE VIDEO IS PAUSED.
        Given a timestamp, jump to the corresponding time in the video.
        """
        target_x_coordinate = self.predict_x_coordinate(timestamp)
        adb_agent.click(target_x_coordinate, self.video_progress_bar_bbox_coordinates[0][1])
        return True
    
    def seek(self, timestamp):
        try:
            target_timestamp_seconds = timestamp_to_seconds(timestamp)
            while True: # TODO; Add a timeout or max_iter
                self.update_video_player_state(ensure_pause=False)
                current_timestamp = timestamp_to_seconds(self.current_video_timestamp)
                if abs(current_timestamp - target_timestamp_seconds) <= 0:
                    break
                elif abs(current_timestamp - target_timestamp_seconds) <= 100:
                    self._seek_actions_(current_timestamp, target_timestamp_seconds)
                    # break
                else:
                    self.jump_to_approximate_timestamp(target_timestamp_seconds)
        except Exception as e:
            print("Error in seek: ", e)
            return False


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
        elif "seek" in action:
            timestamp = re.search(r"seek_video\(to_timestamp='(.+?)'\)", action).group(1)
            video_controller.seek(timestamp)
        action_logs.append(action)
    print("Completed the task.")
    return True
    
if __name__ == "__main__":
    # user_task = "Seek forward the video progress bar to 01:10:00"
    # operate_video_player(user_task)
    video_controller = VideoController(pause_or_play_button_coordinates=(501, 157))

    