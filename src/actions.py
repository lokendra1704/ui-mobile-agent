import time
import subprocess
from utils import get_screen_x_coordinate, get_screen_y_coordinate, extract_action, emulator_to_ai_x_coordinate, emulator_to_ai_y_coordinate

HARDCODED_AI_COORDINATES = {
    "PHYSICSWALLAH_VIDEO_PLAYER": {
        "START_X": emulator_to_ai_x_coordinate(33, 1080),
        "END_X": emulator_to_ai_x_coordinate(1049, 1080),
        "LENGTH": emulator_to_ai_x_coordinate(1049, 1080) - emulator_to_ai_x_coordinate(33, 1080),
    }
}

def get_final_seek_coordinate(target_time, start_x, length=HARDCODED_AI_COORDINATES["PHYSICSWALLAH_VIDEO_PLAYER"]["LENGTH"]):
    """
    current_time: str: Current time of the video in the format HH:MM:SS
    target_time: str: Target time of the video in the format HH:MM:SS
    """
    current_time = current_time.split(":")
    current_time = int(current_time[0])*3600 + int(current_time[1])*60 + int(current_time[2])
    target_time = target_time.split(":")
    target_time = int(target_time[0])*3600 + int(target_time[1])*60 + int(target_time[2])
    seek_position = start_x + (target_time/current_time)*length
    return seek_position

class ActionSpace:
    def __init__(self, adb_path="adb", image_width=1080, image_height=2400):
        self.adb_path = adb_path
        self.image_width = image_width
        self.image_height = image_height
    
    def click(self, x, y):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        command = self.adb_path + f" shell input tap {x_screen} {y_screen}"
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def type(self, text):
        command = self.adb_path + f" shell input text \"{text}\""
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def press_home(self):
        command = self.adb_path + " shell input keyevent KEYCODE_HOME"
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)
    
    def scroll(self, x, y, x1, y1, duration_in_ms=500):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        x1_screen = get_screen_x_coordinate(x1, self.image_width)
        y1_screen = get_screen_y_coordinate(y1, self.image_height)
        command = self.adb_path + f" shell input swipe {x_screen} {y_screen} {x1_screen} {y1_screen} {duration_in_ms}"
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def press_back(self):
        command = self.adb_path + " shell input keyevent KEYCODE_BACK"
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def long_press(self, x, y):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        command = self.adb_path + f" shell input swipe {x_screen} {y_screen} {x_screen} {y_screen} 1000"
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def press_enter(self):
        command = self.adb_path + " shell input keyevent KEYCODE_ENTER"
        print("Issuing Command: ", command)
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def double_click(self, x, y):
        self.click(x,y)
        time.sleep(0.3)
        self.click(x,y)
    
    def map_generate_action_to_event(self, action):
        print("Performing Action: ", action)
        if action["type"] == "click":
            self.click(action["x"], action["y"])
        elif action["type"] == "type":
            self.type(action["content"])
        elif action["type"] == "press_home":
            self.press_home()
        elif action["type"] == "scroll":
            self.scroll(action["start_x"], action["start_y"], action["end_x"], action["end_y"])
        elif action["type"] == "press_back":
            self.press_back()
        elif action["type"] == "long_press":
            self.long_press(action["x"], action["y"])
        elif action["type"] == "wait":
            print("Waiting...")
        elif action["type"] == "finished":
            print("Task Finished.")
        elif action["type"] == "call_user":
            print("User intervention needed.")
        elif action["type"] == "double_click":
            self.double_click(action["x"], action["y"])
        elif action["type"] == "press_enter":
            self.press_enter()

if __name__ == "__main__":
    print("X 541: ", emulator_to_ai_x_coordinate(541, 1080))
    print("Y 376: ", emulator_to_ai_y_coordinate(376, 2400))
    actionOperator = ActionSpace()
#     action=extract_action("""
# 1. To move the video to the desired timestamp of 01:10:00, I need to use the progress bar to calculate the appropriate position. Since the video is currently at 19:22, the next step is to drag the progress bar to the left to reach the target time of 01:10:00.
# 2. The progress bar is located at the bottom of the video player interface, and the current seek position is indicated by the red marker.
# 3. By dragging the progress bar to the left, I can adjust the seek position to the desired timestamp, ensuring the video plays from the correct point.
# Action: scroll(start_box='(226,222)', end_box='(650,226)')                      
# """)
    action = extract_action("double_click(start_box='(493,155)')")
    # actionOperator.map_generate_action_to_event(action)