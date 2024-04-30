from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain.chains import LLMMathChain
from langchain.globals import set_debug
from langchain.memory.buffer_window import ConversationBufferWindowMemory
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from prompts import AGENT_PROMPT_TEMPLATE

set_debug(True)


if __name__ == "__main__":

  llm = ChatOpenAI(model="gpt-3.5-turbo",
                   openai_api_key="your-api-key",
                   openai_api_base="http://127.0.0.1:3040/v1",
                   temperature=0,
                   verbose=True,
                   streaming=True,)

  ddg_search = DuckDuckGoSearchAPIWrapper(region="au-en", max_results=1)
  llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)

  tools = [
    Tool(
        name="Web Search",
        func=ddg_search.run,
        description="Useful for when you need to search information from the internet (e.g weather, people, stock, etc.), " +
                    "the input must be a single string parameter (search query)",
    ),
    Tool.from_function(
        func=llm_math_chain.run,
        name="Calculator",
        description="Useful for when you need to answer questions about very simple math. " +
                    "This tool is only for math questions and nothing else. ",
    ),
  ]

  agent_prompt = ChatPromptTemplate.from_messages(
      [("user", AGENT_PROMPT_TEMPLATE)]
  )
  agent = create_react_agent(llm, tools, agent_prompt)

  memory = ConversationBufferWindowMemory(memory_key="chat_history", k=10)
  agent_executor = AgentExecutor(agent=agent,
                                 tools=tools,
                                 verbose=True,
                                 memory=memory,
                                 handle_parsing_errors=True)

  while True:
    query = input("Please enter your query (type 'exit' to quit):\n")
    if query.lower() == "exit":
      break
    if len(query.strip()) != 0:
      answer = agent_executor.invoke({"input": query})

      print(answer["output"])

  print("Bye!")