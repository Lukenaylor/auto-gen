import autogen

#1 create the model and API key
config_list = [
    {
    'model':'gpt-3.5-turbo-16k',
    'api_key':'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'
    }
]

llm_config = {
    "seed": 42,  # change the seed for different trials
    "temperature": 0,
    "config_list": config_list,
    "timeout": 300,
}

user_proxy = autogen.UserProxyAgent(
   name="Admin",
   system_message="A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin.",
   code_execution_config=False,
)
instructional_designer = autogen.AssistantAgent(
    name="Instructional_Designer",
    llm_config=llm_config,
    system_message='''You are an experienced eLearning instructional designer that has extensive knowledge about how to deliver engaging content to learners across a range of subjects. You take the information from the Admin. Do not ask others to copy and paste the result. Check the research result returned by the researcher.
If the result indicates there is an error, fix the error and output the fixed response. If the error can't be fixed, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
''',
)
researcher = autogen.AssistantAgent(
    name="Researcher",
    llm_config=llm_config,
    system_message="""You are an experienced eLearning content researcher that has the ability to generate accurate research across a range of subjects that the instructional designer can use to create engaging eLearning content. You follow an approved plan. You are able to find and categorize relavent subject knowledge."""
)
planner = autogen.AssistantAgent(
    name="Planner",
    system_message='''You are an experienced eLearning project manager, that is able to understand technical and non-technical knowledge. Your role is to use information provided by the instructional designer and create a plan that a human eLearning Storyline 360 developer can use to build a WCAG AA compliant course. Revise the plan based on feedback from admin and critic, until admin approval.''',
    llm_config=llm_config,
)
proof_reader = autogen.UserProxyAgent(
    name="Proof_Reader",
    system_message="You are an experienced proof reader with a focus on UK english. Your role is to assess the output provided by the instructional designer and suggest changes to make the elearning course as simple to follow as possible. Your role is to focus on the way the eLearning course is written, not to change the overall content.",
    human_input_mode="NEVER",
    code_execution_config={"last_n_messages": 3, "work_dir": "paper"},
)
critic = autogen.AssistantAgent(
    name="Critic",
    system_message="Critic. Double check plan, claims, and responses from other agents and provide feedback. Check whether the plan includes adding verifiable info such as source URL. At the end of the process, please compile all the responses into one overall, useable text file that can be exported to google docs.",
    llm_config=llm_config,
)
groupchat = autogen.GroupChat(agents=[user_proxy, instructional_designer, researcher, planner, proof_reader, critic], messages=[], max_round=50)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

user_proxy.initiate_chat(
    manager,
    message="""
Please create the storyboard for a 30 minute eLearning course about sanctions regulations. The course should be as engaging as possible for learners and should use the most up to date learning design techniques. Note this storyboard is completely text based and should not assume any prior learner knowledge about the subject. As part of this storyboard, please include a question bank of 20 relavent multi choice questions.
""",
)