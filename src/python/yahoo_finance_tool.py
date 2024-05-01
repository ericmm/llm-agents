from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from requests.exceptions import HTTPError, ReadTimeout
from typing import Optional
from urllib3.exceptions import ConnectionError


class YahooFinanceNewsTool2(BaseTool):
  """Tool that searches financial news on Yahoo Finance."""

  name: str = "yahoo_finance_news"
  description: str = (
    "Useful for when you need to find financial news about a public company. "
    "Input should be a company ticker only, for example, AAPL for Apple, MSFT for Microsoft."
  )

  def _run(
      self,
      query: str,
      run_manager: Optional[CallbackManagerForToolRun] = None,
  ) -> str:
    """Use the Yahoo Finance News tool."""
    try:
      import yfinance
    except ImportError:
      raise ImportError(
          "Could not import yfinance python package. "
          "Please install it with `pip install yfinance`."
      )
    company = yfinance.Ticker(query)
    try:
      if company.info is None:
        return f"Company ticker {query} not found."
    except (HTTPError, ReadTimeout, ConnectionError):
      return f"Company ticker {query} not found."
    info = company.info
    return self._format_results(info)

  @staticmethod
  def _format_results(info) -> str:
    return f"""exchange:{info.get('exchange', '')}
quoteType:{info.get('quoteType', '')}
shortName:{info.get('shortName', '')}
longName:{info.get('longName', '')}
symbol:{info.get('symbol', '')}
country:{info.get('country', '')}
industry:{info.get('industry', '')}
sector:{info.get('sector', '')}
previousClose:{info.get('previousClose', '')}
open:{info.get('open', '')}
currentPrice:{info.get('currentPrice', '')}
currency:{info.get('currency', '')}
fundFamily:{info.get('fundFamily', '')}
legalType:{info.get('legalType', '')}
"""
