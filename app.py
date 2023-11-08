import autogen

#1 create the model and API key
config_list = [
    {
    'model':'gpt-3.5-turbo-16k',
    'api_key':'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'
    }
]

#2 create an AssistantAgent names "assistant"
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={
        "seed": 41, # seed for caching and reproducibility
        "config_list": config_list,
        "temperature":0, # temperature of sampling, this ideally get changed via an API in the future
    },
)

proof_reader = autogen.AssistantAgent(
    name="proof reader",
    llm_config={
        "seed": 44,
        "config_list": config_list,
        "temperature":0,
    },
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode='NEVER',
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "work_dir":"coding",
        "use_docker": False,
    },
)

user_proxy.initiate_chat(
    assistant,
    message="""Provide a 500 word blog in text format about accessibility and it's importance in eLearning""",
)

#follow up from the first response

user_proxy.send(
    recipient=assistant,
    message="""Please can you write a linkedin marketing message on the blog post and suggest some SEO tags""",
)

user_proxy.send(
    recipient=proof_reader,
    message="please can you go through and check the responses and change any US english to UK english, and pass this back to the Assistant"
)