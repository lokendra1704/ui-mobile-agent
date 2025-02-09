import time
import subprocess
from utils import get_screen_x_coordinate, get_screen_y_coordinate, extract_action

class ActionSpace:
    def __init__(self, adb_path="adb", image_width=1080, image_height=2400):
        self.adb_path = adb_path
        self.image_width = image_width
        self.image_height = image_height
    
    def click(self, x, y):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        command = self.adb_path + f" shell input tap {x_screen} {y_screen}"
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def type(self, text):
        command = self.adb_path + f" shell input text \"{text}\""
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def press_home(self):
        command = self.adb_path + " shell input keyevent KEYCODE_HOME"
        subprocess.run(command, capture_output=True, text=True, shell=True)
    
    def scroll(self, x, y, x1, y1):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        x1_screen = get_screen_x_coordinate(x1, self.image_width)
        y1_screen = get_screen_y_coordinate(y1, self.image_height)
        command = self.adb_path + f" shell input swipe {x_screen} {y_screen} {x1_screen} {y1_screen} 500"
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def press_back(self):
        command = self.adb_path + " shell input keyevent KEYCODE_BACK"
        subprocess.run(command, capture_output=True, text=True, shell=True)

    def long_press(self, x, y):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        command = self.adb_path + f" shell input swipe {x_screen} {y_screen} {x_screen} {y_screen} 1000"
        subprocess.run(command, capture_output=True, text=True, shell=True)
    
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
            self.click(action["x"], action["y"])
            time.sleep(1)
            self.click(action["x"], action["y"])
        time.sleep(3)

if __name__ == "__main__":
    actionOperator = ActionSpace()
    action=extract_action("""
1. To move the video to the desired timestamp of 01:10:00, I need to use the progress bar to calculate the appropriate position. Since the video is currently at 19:22, the next step is to drag the progress bar to the left to reach the target time of 01:10:00.
2. The progress bar is located at the bottom of the video player interface, and the current seek position is indicated by the red marker.
3. By dragging the progress bar to the left, I can adjust the seek position to the desired timestamp, ensuring the video plays from the correct point.
Action: scroll(start_box='(226,222)', end_box='(650,226)')                      
""")
    actionOperator.map_generate_action_to_event(action)