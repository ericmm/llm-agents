import ffn
import yahooquery
import yfinance
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
    "Input must be a SINGLE equity or fund ticker only, for example, AAPL for Apple, VOO for Vanguard S&P 500 ETF."
    "For the equity, it provides info like exchange, country, industry, sector, price, yearly returns, etc."
    "For the ETF fund, it also provides holdings & corresponding percentages, sector weightings and yearly returns."
  )

  def _run(
      self,
      query: str,
      run_manager: Optional[CallbackManagerForToolRun] = None,
  ) -> str:
    """Use the Yahoo Finance tool."""

    if len(query) > 10 and ',' in query:
      return f"Invalid ticker {query}, must be ONE ticker at a time, e.g. MSFT"

    yf_ticker = None
    try:
      yf_ticker = yfinance.Ticker(query.upper())
      if yf_ticker is None:
        return f"Company ticker {query} not found."
    except (HTTPError, ReadTimeout, ConnectionError):
      return f"Company ticker {query} not found."

    yq_ticker = None
    try:
      yq_ticker = yahooquery.Ticker(query.upper())
    except (HTTPError, ReadTimeout, ConnectionError):
      # do nothing as we have yf_ticker info
      print(f"Company ticker {query} not found by yahooquery.")

    ffn_ticker = None
    try:
      # get the returns data for 10 years
      ffn_ticker = ffn.get(query.lower(), start='2014-01-01')
    except (HTTPError, ReadTimeout, ConnectionError):
      # do nothing as we have yf_ticker info
      print(f"Company ticker {query} not found by ffn.")

    return YahooFinanceNewsTool2._format_results(query, yf_ticker, yq_ticker, ffn_ticker)


  @staticmethod
  def _format_results(query, yf_ticker, yq_ticker, ffn_ticker) -> str:
    quote_type = yf_ticker.info.get('quoteType', '')
    if quote_type.strip().upper() == 'ETF':
      return YahooFinanceNewsTool2._format_etf(query, yf_ticker.info, yq_ticker, ffn_ticker)
    else:
      return YahooFinanceNewsTool2._format_stock(query,yf_ticker.info, ffn_ticker)


  @staticmethod
  def _format_stock(query, info, ffn_ticker) -> str:
    return_info = YahooFinanceNewsTool2._format_return_info(query, ffn_ticker)
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
marketCap: {info.get('marketCap', '0')}
{return_info}
"""

  @staticmethod
  def _format_etf(query, info, yq_ticker, ffn_ticker) -> str:
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
        holdings_info += f"{h['symbol']}: {h['holdingPercent']:.2%}\n"

    sector_info = YahooFinanceNewsTool2._format_etf_sector(query, yq_ticker.fund_sector_weightings)
    return_info = YahooFinanceNewsTool2._format_return_info(query, ffn_ticker)
    return etf_summary + holdings_info + sector_info + return_info

  @staticmethod
  def _format_etf_sector(query, sector_weightings) -> str:
    sector_info = ''
    if sector_weightings is not None:
      sw_series = sector_weightings.get(query, None)
      if sw_series is not None:
        for i in sw_series.index:
          if float(sw_series[i]) > 0:
            sector_info += f'{i}: {sw_series[i]:.2%}\n'

    if len(sector_info) > 0:
      sector_info = "\nsector weightings:\n" + sector_info
    return sector_info


  @staticmethod
  def _format_return_info(query, ffn_ticker) -> str:
    return_info = ''
    if ffn_ticker is not None:
      stats = ffn_ticker.calc_stats().get(query.lower(), None)
      if stats is not None and stats.lookback_returns is not None:
        for k in ['ytd', '1y', '3y', '5y', '10y']:
          return_info +=f'{k}: {stats.lookback_returns[k]:.2%}\n'

    if len(return_info) > 0:
      return '\nreturns:\n' + return_info
    else:
      return return_info
