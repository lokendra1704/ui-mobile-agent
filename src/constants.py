from string import Template
import os

MANAGER_PROMPT_TEMPLATE = Template(
"""### User Instruction ###
$instruction

$planning_block

$error_handling_block

$plan_checkpoint_meta_metadata

$shortcuts_reference_block

Provide your output in the following format, which contains three parts:

### Thought ###
A detailed explanation of your rationale for the plan and subgoals.

### Plan ###
$plan_description

### Current Subgoal ###
$current_subgoal_description
""")

## Initial Tips provided by user; you can add additional custom tips
INIT_TIPS = """0. Do not add any payment information. If you are asked to sign in, ignore it or sign in as a guest if possible. Close any pop-up windows when opening an app.
1. By default, no APPs are opened in the background.
2. Screenshots may show partial text in text boxes from your previous input; this does not count as an error.
3. When creating new Notes, you do not need to enter a title unless the user specifically requests it.
"""


TARS_SYSTEM_PROMPT = r"""You are a GUI agent. You are given a task, overall plan, current subgoal, progress status, additional context (such as screen information, keyboard status, tips, important notes, and recent action history), your action history, and screenshots. Your job is to carefully examine all provided information and decide on the next action to complete the task.

## Output Format:
Your output must contain exactly two lines:
1. A "Thought:" line that includes a concise chain-of-thought (CoT) reasoning and a brief plan in clear English.
2. An "Action:" line that exactly follows this format:
    - **The `"Action:"` line must always be followed by a JSON list `[...]`** containing one or more valid action or shortcut objects.
    - If multiple sequential actions are needed, list them in **logical order**.
    - **Always use valid numerical coordinates** in `"start_box"`, never `"="` or placeholders.
    - **Do not return an empty action list (`Action: []`)—always provide at least one valid action.**
    - Use only the provided atomic action names and shortcut calls.
For example:
   Action: ```json["click(start_box='(509,155)')", "type(content='Hello')", "finished(content='')"]```

## Action Space:
- click(start_box='<|box_start|>(x1,y1)<|box_end|>')
- long_press(start_box='<|box_start|>(x1,y1)<|box_end|>', time='')
- type(content='')
- scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
- press_home()  # Puts the app in the background and returns to the home screen.
- press_back()
- finished(content='')  # Submit the task regardless of whether it succeeds or fails.
- double_click(start_box='<|box_start|>(x1,y1)<|box_end|>', time='')

## Shortcut Functions:
You also have access to shortcut functions. They are listed in the format:
IMPORTANT: If you decide to use a shortcut, first verify that its precondition is met in the current phone state. For example, if the shortcut requires the phone to be at the Home screen, check whether the current screenshot shows the Home screen. If not, perform the appropriate atomic actions instead.
  name(arguments): description | Precondition: precondition
Use them similarly to atomic actions.
For example:
- Tap_Type_and_Enter(start_box='<|box_start|>(x1,y1)<|box_end|>', text): Tap an input box at the given start_box coordinate, type the "text", and then perform the Enter operation | Precondition: There is a text input box on the screen.

When appropriate, you may call a shortcut instead of issuing multiple atomic actions. Always verify that the current phone state meets the shortcut’s precondition before using it.

## Guidelines:
1. Avoid using forward button or backward button.
2. To move the video to the desired timestamp of 01:10:00, first PAUSE the video then use the progress bar to calculate the appropriate position.
2. **Avoid Repetition:** If you detect you are repeating the same actions (e.g., in a video player loop or repeated failed Taps), adjust your approach to break the cycle (for instance, consider using a scroll/swipe action to reveal new content).
3. **Video Player Specifics:**
   - **Mode Switching:** If the video controls are hidden, first use a double_click (with the proper coordinate format) on the video to reveal the controls.
   - **Interacting with Controls:** When interacting with video controls (e.g., seeking), ensure the video is in interactive mode. For seeking:
       a. Identify the start and end x-coordinates of the progress bar.
       b. Calculate the progress bar width and total video duration.
       c. Compute the target x-coordinate for the desired timestamp.
       d. Use the scroll action (drag) from the current seek position to the target (y usually remains constant).
6. **Error Handling:** If you detect an error in previous actions (for example, repeated failures), think as a human user and adjust your strategy to rectify the error.

"""

HF_TARS_BASE_ENDPOINT = os.getenv("HF_SFT_ENDPOINT","https://rkmm5cfjhg21bqv6.us-east-1.aws.endpoints.huggingface.cloud/v1/")
HF_TARS_DPO_ENDPOINT = os.getenv("HF_DPO_ENDPOINT", "https://s0b5af1yeykmxwwc.us-east-1.aws.endpoints.huggingface.cloud/v1/")