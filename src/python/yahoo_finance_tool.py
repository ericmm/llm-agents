from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from requests.exceptions import HTTPError, ReadTimeout
from typing import Optional
from urllib3.exceptions import ConnectionError


class YahooFinanceNewsTool2(BaseTool):
  """Tool that searches financial info on Yahoo Finance."""

  name: str = "yahoo_finance"
  description: str = (
    "Useful for when you need to find financial info about an equity or ETF fund. "
    "For the equity, it provides info like exchange, country, industry, sector, price, etc."
    "For the ETF fund, it also provides holdings & corresponding percentages, and sector weightings."
    "Input should be a company or fund ticker only, for example, AAPL for Apple, VOO for Vanguard S&P 500 ETF."
  )

  def _run(
      self,
      query: str,
      run_manager: Optional[CallbackManagerForToolRun] = None,
  ) -> str:
    """Use the Yahoo Finance tool."""
    try:
      import yfinance
    except ImportError:
      raise ImportError(
          "Could not import yfinance python package. "
          "Please install it with `pip install yfinance`."
      )

    try:
      import yahooquery
    except ImportError:
      raise ImportError(
          "Could not import yahooquery  python package. "
          "Please install it with `pip install yahooquery`."
      )

    yf_ticker = None
    try:
      yf_ticker = yfinance.Ticker(query)
      if yf_ticker is None:
        return f"Company ticker {query} not found."
    except (HTTPError, ReadTimeout, ConnectionError):
      return f"Company ticker {query} not found."

    yq_ticker = None
    try:
      yq_ticker = yahooquery.Ticker(query)
    except (HTTPError, ReadTimeout, ConnectionError):
      # do nothing as we have yf_ticker info
      print(f"Company ticker {query} not found by yahooquery.")

    return YahooFinanceNewsTool2._format_results(yf_ticker, yq_ticker)


  @staticmethod
  def _format_results(yf_ticker, yq_ticker) -> str:
    quote_type = yf_ticker.info.get('quoteType', '')
    if quote_type.strip().upper() == 'ETF':
      return YahooFinanceNewsTool2._format_etf(yf_ticker.info, yq_ticker)
    else:
      return YahooFinanceNewsTool2._format_stock(yf_ticker.info)


  @staticmethod
  def _format_stock(info) -> str:
    return f"""symbol: {info.get('symbol', '')}
quoteType: {info.get('quoteType', '')}
shortName: {info.get('shortName', '')}
exchange: {info.get('exchange', '')}
country: {info.get('country', '')}
industry: {info.get('industry', '')}
sector: {info.get('sector', '')}
previousClose: {info.get('previousClose', '')}
open: {info.get('open', '')}
currentPrice: {info.get('currentPrice', '')}
currency: {info.get('currency', '')}
"""

  @staticmethod
  def _format_etf(info, yq_ticker) -> str:
    etf_summary = f"""symbol: {info.get('symbol', '')}
quoteType: {info.get('quoteType', '')}
shortName: {info.get('shortName', '')}
exchange: {info.get('exchange', '')}
fundFamily: {info.get('fundFamily', '')}
previousClose: {info.get('previousClose', '')}
open: {info.get('open', '')}
currency: {info.get('currency', '')}
"""
    symbol = info.get('symbol', '')
    holdings = yq_ticker.fund_holding_info.get(symbol, {}).get("holdings", None) or []

    holdings_info = ""
    if len(holdings) > 0:
      holdings_info +="\nholdings:\n"
      for h in holdings:
        holdings_info += f"{h['symbol']}, {h['holdingPercent']}\n"

    sector_info = YahooFinanceNewsTool2._format_etf_sector(yq_ticker.fund_sector_weightings.to_string())
    return etf_summary + holdings_info + sector_info

  @staticmethod
  def _format_etf_sector(sector_info: str) -> str:
    # remove first two lines
    sector_info = "\n".join(sector_info.split("\n")[2:])

    # remove multiple empty spaces in the middle
    while '  ' in sector_info:
      sector_info = sector_info.replace('  ', ' ')

    # replace single space to comma
    sector_info = sector_info.replace(' ', ', ')
    sector_info = "\nsector weightings:\n" + sector_info
    return sector_info
