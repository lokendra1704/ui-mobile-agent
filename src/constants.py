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


TARS_SYSTEM_PROMPT = r"""You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task. 

## Output Format
```\nThought: ...
Action: ...\n```

## Action Space
click(start_box='<|box_start|>(x1,y1)<|box_end|>')
long_press(start_box='<|box_start|>(x1,y1)<|box_end|>', time='')
type(content='')
scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
press_home() # Put the app in the background and return to the home screen of mobile.
press_back()
finished(content='') # Submit the task regardless of whether it succeeds or fails.

## Note
- Use English in `Thought` part.

- Write a small plan and finally summarize your next action (with its target element) in one sentence in `Thought` part.

"""

HF_TARS_BASE_ENDPOINT = os.getenv("HF_DPO_ENDPOINT","https://rkmm5cfjhg21bqv6.us-east-1.aws.endpoints.huggingface.cloud/v1/")
HF_TARS_DPO_ENDPOINT = os.getenv("HF_SFT_ENDPOINT", "https://s0b5af1yeykmxwwc.us-east-1.aws.endpoints.huggingface.cloud/v1/")