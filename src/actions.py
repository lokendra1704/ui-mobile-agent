import time
import subprocess
from utils import get_screen_x_coordinate, get_screen_y_coordinate

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
    
    def scroll(self, x, y, direction):
        x_screen = get_screen_x_coordinate(x, self.image_width)
        y_screen = get_screen_y_coordinate(y, self.image_height)
        if direction == "up":
            command = self.adb_path + f" shell input swipe {x_screen} {y_screen+400} {x_screen} {y_screen} 500"
        elif direction == "down":
            command = self.adb_path + f" shell input swipe {x_screen} {y_screen} {x_screen} {y_screen+400} 500"
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
            self.scroll(action["x"], action["y"], action["direction"])
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
        time.sleep(3)
