from typing import Callable, Dict, Optional, Union, Tuple, List, Any
from autogen import oai
from autogen import Agent, ConversableAgent

from autogen.token_count_utils import count_token

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


class CompressionAgent(ConversableAgent):
    """(Experimental) Compression agent, designed to compress a list of messages.

    CompressionAgent is a subclass of ConversableAgent configured with a default system message.
    The default system message is designed to compress chat history.
    `human_input_mode` is default to "NEVER"
    and `code_execution_config` is default to False.
    This agent doesn't execute code or function call by default.
    """

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant that will compress messages.
Rules:
1. Please summarize each of the message and reserve the titles: ##USER##, ##ASSISTANT##, ##FUNCTION_CALL##, ##FUNCTION_RETURN##, ##SYSTEM##, ##<Name>(<Title>)## (e.g. ##Bob(ASSISTANT)##).
2. Context after ##USER##, ##ASSISTANT## (and ##<Name>(<Title>)##): compress the content and reserve important information. If there is big chunk of code, please use ##CODE## to indicate and summarize what the code is doing with as few words as possible and include details like exact numbers and defined variables.
3. Context after ##FUNCTION_CALL##: Keep the exact content if it is short. Otherwise, summarize/compress it and reserve names (func_name, argument names).
4. Context after ##FUNCTION_RETURN## (or code return): Keep the exact content if it is short. Summarize/compress if it is too long, you should note what the function has achieved and what the return value is.
"""

    def __init__(
        self,
        name: str = "compressor",
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        llm_config: Optional[Union[Dict, bool]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        code_execution_config: Optional[Union[Dict, bool]] = False,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            llm_config (dict): llm inference configuration.
                Please refer to [Completion.create](/docs/reference/oai/completion#create)
                for available options.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            **kwargs,
        )

        self._reply_func_list.clear()
        self.register_reply([Agent, None], CompressionAgent.generate_compressed_reply)

    def generate_compressed_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None, List]]:
        """Compress a list of messages into one message.

        The first message (the initial prompt) will not be compressed.
        The rest of the messages will be compressed into one message, the model is asked to distinuish the role of each message: USER, ASSISTANT, FUNCTION_CALL, FUNCTION_RETURN.
        Check out the DEFAULT_SYSTEM_MESSAGE prompt above.

        TODO: model used in compression agent is different from assistant agent: For example, if original model used by is gpt-4; we start compressing at 70% of usage, 70% of 8092 = 5664; and we use gpt 3.5 here max_toke = 4096, it will raise error. choosinng model automatically?
        """
        # Uncomment the following line to check the content to compress
        print(colored("*" * 30 + "Start compressing the following content:" + "*" * 30, "magenta"), flush=True)

        # 1. use passed-in config and messages
        # in function on_oai_limit of conversable agent, we will pass in llm_config from "config" parameter.
        llm_config = self.llm_config if config is None else config
        if llm_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        # 2. stop if there is only one message in the list
        if len(messages) <= 1:
            print(f"Warning: the first message contains {count_token(messages)} tokens, which will not be compressed.")
            return False, None

        # 3. put all history into one, except the first one
        compressed_prompt = "Below is the compressed content from the previous conversation, evaluate the process and continue if necessary:\n"
        chat_to_compress = "To be compressed:\n"
        start_index = 1
        for m in messages[start_index:]:
            if m.get("role") == "function":
                chat_to_compress += f"##FUNCTION_RETURN## (from function \"{m['name']}\"): \n{m['content']}\n"
            else:
                if "name" in m:
                    # {"name" : "Bob", "role" : "assistant"} -> ##Bob(ASSISTANT)##
                    chat_to_compress += f"##{m['name']}({m['role'].upper()})## {m['content']}\n"
                elif m["content"] is not None:
                    if compressed_prompt in m["content"]:
                        # remove the compressed_prompt from the content
                        tmp = m["content"].replace(compressed_prompt, "")
                        chat_to_compress += f"{tmp}\n"
                    else:
                        chat_to_compress += f"##{m['role'].upper()}## {m['content']}\n"

                if "function_call" in m:
                    if (
                        m["function_call"].get("name", None) is None
                        or m["function_call"].get("arguments", None) is None
                    ):
                        chat_to_compress += f"##FUNCTION_CALL## {m['function_call']}\n"
                    else:
                        chat_to_compress += f"##FUNCTION_CALL## \nName: {m['function_call']['name']}\nArgs: {m['function_call']['arguments']}\n"

        chat_to_compress = [{"role": "user", "content": chat_to_compress}]
        # Uncomment the following line to check the content to compress
        print(chat_to_compress[0]["content"])

        # 4. ask LLM to compress
        try:
            response = oai.ChatCompletion.create(
                context=None, messages=self._oai_system_message + chat_to_compress, **llm_config
            )
        except Exception as e:
            print(f"Warning: Failed to compress the content due to {e}.")
            return False, None
        compressed_message = oai.ChatCompletion.extract_text_or_function_call(response)[0]
        print(
            colored(
                "*" * 30 + "Content after compressing: (type=" + str(type(compressed_message)) + ")" + "*" * 30,
                "magenta",
            ),
            flush=True,
        )
        print(compressed_message, colored("\n" + "*" * 80, "magenta"))

        assert isinstance(compressed_message, str), f"compressed_message should be a string: {compressed_message}"
        # 5. add compressed message to the first message and return
        return True, [
            messages[0],
            {
                "content": compressed_prompt + compressed_message,
                "role": "system",
            },
        ]
