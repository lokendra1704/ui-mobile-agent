from openai import OpenAI
import json
import os
from time import sleep
from typing import List, TypedDict, Literal, Union
from constants import TARS_SYSTEM_PROMPT, HF_TARS_BASE_ENDPOINT, HF_TARS_DPO_ENDPOINT
from utils import track_usage, encode_image

class TextMessageContent(TypedDict):
    type: Literal["text"]
    text: str

class ImageURLDict(TypedDict):
    url: str

class ImageMessageContent(TypedDict):
    type: Literal["image_url"]
    image_url: ImageURLDict

class MessageDict(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: Union[List[Union[TextMessageContent, ImageMessageContent]], TextMessageContent, ImageMessageContent]

SYSTEM_PROMPTS = {
    "default": TARS_SYSTEM_PROMPT,
}

class TARS:
    def __init__(self, user_instruction, system_name, base_type="dpo", api_key = os.getenv("HF_API_KEY"), model="tgi"):
        url = HF_TARS_DPO_ENDPOINT if base_type == "dpo" else HF_TARS_BASE_ENDPOINT
        print(f"Using {base_type}:{url} endpoint.")
        self.client = OpenAI(base_url=url, api_key=api_key)
        self.model = model
        self.system_name = system_name
        self.user_instruction = user_instruction
        self.system_prompt = SYSTEM_PROMPTS.get(system_name, None)
        self.messages = []

    def __fix_message_serizalization__(self, messages: List[MessageDict]):
        for i in range(len(messages)):
            message = messages[i]
            if type(message["content"]) != list:
                messages[i]["content"] = [message["content"]]
        return messages

    def __inference__(self, messages: List[MessageDict]=[], usage_tracking_jsonl=None, **kwargs):
        """
        Inference language models with retry mechanism.
        System name is used to fetch system prompt (first message to system) from system_message dictionary.
        If system_name is not provided, messages list is used as it is.
        If system_name is provided, A system message is placed before all messages in the list.
        In case system_name is provided and messages list's first message is also system message, it is replaced with system message from system_message dictionary.
        """
        messages = self.__fix_message_serizalization__(messages)
        if not self.__validate_messages__(messages):
            raise Exception("Invalid messages.")
        max_retry = 5
        sleep_sec = 20
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **kwargs,
                )
                if usage_tracking_jsonl:
                    usage = track_usage(response, api_key="hf-inference-endpoint")
                    with open(usage_tracking_jsonl, "a") as f:
                        f.write(json.dumps(usage) + "\n")
                return response.choices[0].message.content
            except Exception as e:
                print("Error in Sending request to OpenAI API.",)
            print(f"Sleep {sleep_sec} before retry...")
            sleep(sleep_sec)
            max_retry -= 1
            if max_retry < 0:
                print(f"Failed after {max_retry} retries...")
                return None
            
    def __prune_message__(self, messages: List[MessageDict]):
        """
        Prune the messages to remove the irrelevant messages to avoid hitting the maximum context limit of LLM/VLM.
        Irrelevant message is defined as:
            - All the ImageMessageContent before last assistant message.
        """
        last_assistant_message_index = None
        pruned_messages = []
        for i in range(len(messages)-1, -1, -1):
            if messages[i]['role'] == "system" or messages[i]["role"] == "assistant":
                last_assistant_message_index = i
                break
        if last_assistant_message_index is not None:
            for message in messages[:last_assistant_message_index+1]:
                if message['role'] == "user":
                    if type(message["content"]) == list:
                        current_message = []
                        for content in message["content"]:
                            if content["type"] != "image_url":
                                current_message.append(content)
                        pruned_messages.append({"role": "user", "content": current_message})
                    else:
                        if message["content"]["type"] != "image_url":
                            pruned_messages.append(message)
                else:
                    pruned_messages.append(message)
            return pruned_messages
        else:
            return messages
        
    def inference(self, messages: List[MessageDict]=[], usage_tracking_jsonl=None, **kwargs):
        """
        Public method to perform inference.
        """
        if not messages:
            raise Exception("Messages are not provided.")
        system_prompt = None
        formatted_system_prompt = None
        user_instruction = self.user_instruction
        if self.system_prompt is not None:
            system_prompt = self.system_prompt
        elif self.system_name is not None:
            system_prompt = f"{self.system_name}\n{user_instruction}" if SYSTEM_PROMPTS.get(self.system_name, None) else None
        elif kwargs.get("system_prompt", None):
            system_prompt = kwargs["system_prompt"]
        else:
            raise Exception("System prompt is not provided.")
        formatted_system_prompt = f"{system_prompt}\n## User Instruction\n{user_instruction}"
        self.system_prompt = formatted_system_prompt
        messages = [
            MessageDict(role="system", content=[TextMessageContent(type="text", text=formatted_system_prompt)]),
            *messages[-3:],
            # *self.__prune_message__(messages)
        ]
        if kwargs is None:
            kwargs = {}
        if kwargs.get("max_tokens", None) is None:
            kwargs["max_tokens"] = 2048
        if kwargs.get("temperature", None) is None:
            kwargs["temperature"] = 0.0
        return self.__inference__(messages=messages, usage_tracking_jsonl=usage_tracking_jsonl, **kwargs)
    
    def __validate_messages__(self, messages: List[MessageDict]):
        try:
            if not messages:
                raise Exception("Messages are not provided.")
            if type(messages) != list:
                raise Exception("Messages should be a list.")
            if messages[-1]["role"] != "user":
                raise Exception("Last message should be user message.")
            for i in range(len(messages)-1):
                role = messages[i]["role"]
                next_role = messages[i+1]["role"]
                if role == next_role:
                    raise Exception("Consecutive messages should have different roles.")
            return True
        except Exception as e:
            print(e)
            return False
    
def test():
        tars_instance = TARS(
            base_type="dpo",
            system_name="default",
            user_instruction="Open Youtube and search for 'How to make a cake'.",
        )
        screenshot_path = "/Users/lokendrabairwa/Pictures/screenshot.png"
        encoded_string = encode_image(screenshot_path)
        messages = [
            MessageDict(role="user", content=[
                TextMessageContent(type="text", text="Here is the initial state of the screen'."),
                ImageMessageContent(type="image_url", image_url=ImageURLDict(url=f"data:image/png;base64,{encoded_string}")),
            ]),
        ]
        response = tars_instance.inference(
            messages=messages,
            max_tokens=100,
            temperature=0.0,
        )
        print(response)

def raw_test():
    instruction = "Pause Video Player"
    screenshot_path = "/Users/lokendrabairwa/Pictures/screenshot.png"
    client = OpenAI(
        base_url=HF_TARS_DPO_ENDPOINT, 
    )
    encoded_string = encode_image(screenshot_path)

    response = client.chat.completions.create(
        model="tgi",
        messages=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": SYSTEM_PROMPTS["default"]},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"### User Instruction ###\n{instruction}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}},
                ],
            },
        ],
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    test()
    # raw_test()