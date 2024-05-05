from langchain.agents import AgentExecutor, Tool
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.chains import LLMMathChain
from langchain.globals import set_debug
from langchain.memory.buffer_window import ConversationBufferWindowMemory
from langchain.tools.render import render_text_description
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from prompts import AGENT_SYSTEM_PROMPT_TEMPLATE, AGENT_USER_PROMPT_TEMPLATE
from react_output_parser import ReActSingleInputOutputParser2
from yahoo_finance_tool import YahooFinanceNewsTool2
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import (
  create_sync_playwright_browser,
)

set_debug(False)


if __name__ == "__main__":

  llm = ChatOpenAI(model="gpt-3.5-turbo",
                   openai_api_key="your-api-key",
                   openai_api_base="http://127.0.0.1:3456/v1",
                   temperature=0,
                   verbose=True,
                   streaming=True,)

  ddg_search = DuckDuckGoSearchAPIWrapper(region="au-en", max_results=2)
  yahoo_finance_news = YahooFinanceNewsTool2(top_k=2)
  llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)

  sync_browser = create_sync_playwright_browser()
  browser_tools = PlayWrightBrowserToolkit.from_browser(sync_browser=sync_browser).get_tools()

  tools = [
    yahoo_finance_news,
    Tool(
        name="Web Search",
        func=ddg_search.run,
        description="Useful for when you need to search information from the internet (e.g weather, people, etc.), " +
                    "the input must be a single string parameter (search query)",
    ),
    Tool.from_function(
        func=llm_math_chain.run,
        name="Calculator",
        description="Useful for when you need to answer questions about very simple math. " +
                    "This tool is only for math questions and nothing else, " +
                    "the input must be a math expressions, e.g. 123 + 456",
    ),
  ]
  tools.extend(browser_tools)

  agent_prompt = ChatPromptTemplate.from_messages([
    ("system", AGENT_SYSTEM_PROMPT_TEMPLATE),
    ("user", AGENT_USER_PROMPT_TEMPLATE),
  ])
  prompt = agent_prompt.partial(
      tools=render_text_description(tools),
      tool_names=", ".join([t.name for t in tools]),
  )

  llm_with_stop = llm.bind(stop=["\nObservation"])
  agent = (
      {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_log_to_str(x["intermediate_steps"]),
        "chat_history": lambda x: x["chat_history"],
      }
      | prompt
      | llm_with_stop
      | ReActSingleInputOutputParser2()
  )

  memory = ConversationBufferWindowMemory(memory_key="chat_history", k=10)
  agent_executor = AgentExecutor(agent=agent,
                                 tools=tools,
                                 memory=memory,
                                 verbose=True,
                                 handle_parsing_errors=True,)

  while True:
    query = input("Please enter your query (type 'exit' to quit):\n")
    if query.lower() == "exit":
      break
    if len(query.strip()) != 0:
      answer = agent_executor.invoke({"input": query})

      print(answer["output"])

  print("Bye!")
