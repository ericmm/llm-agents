'''
===========================================
        Module: Prompts collection
===========================================
'''

# parameters: tools, tool_names, chat_history, input
AGENT_SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI personal assistant.
Please think step by step, and answer the questions as best you can. 
You have access to the following tools:

{tools}

To use a tool, you MUST use the following format:
```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: (the input to the action)
Observation: (the result of the action, will be provided by the tool)
```
(this Thought/Action/Action Input/Observation can repeat N times)

If the Observation section is empty or unrelated, please use a different tool in next action until you can answer the question. 

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!
"""

AGENT_USER_PROMPT_TEMPLATE = """Previous conversation history:
{chat_history}

Question: {input}
{agent_scratchpad}"""
