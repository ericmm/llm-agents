import pandas as pd
import streamlit as st
import yfinance as yf
#from st_aggrid import AgGrid
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import bt
import time

def do_fetch_fake_holdings(ticker: str) ->  pd.DataFrame:
  # simulate fetch action, for testing only
  print(f'fetch fake data for {ticker}...')
  time.sleep(1)
  return pd.DataFrame([
    {"checked": True,"name": "Microsoft", "symbol": "MSFT", "shares": 100, "weight": 0.1},
    {"checked": True,"name": "Apple", "symbol": "AAPL", "shares": 200, "weight": 0.2},
    {"checked": True,"name": "Nvidia", "symbol": "NVDA", "shares": 300, "weight": 0.3},
    {"checked": True,"name": "Amazon", "symbol": "AMZN", "shares": 400, "weight": 0.4},
  ])


def on_fetch_holdings(ticker: str):
  if len(ticker.strip()) == 0:
    st.error("You haven't specify a fund ticker yet")
  else:
    with st.spinner(f"Fetching the fund {ticker}... it may take a few minutes, please kindly be patient."):
      data = do_fetch_fake_holdings(ticker)
    st.session_state.page_state = 'DATA_FETCHED'
    st.session_state.holdings = data
    st.session_state.ticker = ticker.strip().upper()


def do_fetch_holdings(ticker: str) -> pd.DataFrame:
  print('fetch data...')
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = f'https://www.zacks.com/funds/etf/{ticker.strip().upper()}/holding'
    page.goto(url=url, timeout=180000, wait_until='load')

    holdings = None
    try:
      holdings = page.evaluate("etf_holdings")
    except Exception:
      print(f"Cannot fetch holdings for {ticker}")
      return None

    if holdings is None:
      return None

    data = []
    for h in holdings.get('formatted_data', []):
      name = h[0]
      if '<span' in h[0]:
        h0_soup = BeautifulSoup(h[0], 'html.parser')
        name = h0_soup.span.get('title')

      symbol = h[1]
      if '<a' in h[1]:
        soup = BeautifulSoup(h[1], 'html.parser')
        # some holdings do not have symbols, e.g. 'US Dollars', etc.
        symbol = soup.a.get_text().repalce('N/A', '')

      shares = float(h[2].replace(',',''))
      weight = float(h[3].replace(',',''))/100
      data.append({"checked": True,"name": name, "symbol": symbol, "shares": shares, "weight": weight})

    # Close the browser
    browser.close()

    return pd.DataFrame(data)


def remove_uncheked_holdings(edited_data: pd.DataFrame):
  st.session_state.page_state = 'NEXT_STEP'
  # removing rows which are unchecked
  removed_index_list = edited_data[(edited_data['checked'] == False)].index.tolist()
  new_data = edited_data.drop(index=removed_index_list)
  # removing rows which have empty symbol
  removed_index_list = new_data[(new_data['symbol'] == '')].index.tolist()
  new_data = new_data.drop(index=removed_index_list)
  # drop the 'checked' column
  new_data = new_data.drop('checked', axis=1)
  new_data.reset_index()
  st.session_state.holdings = new_data


def build_back_test(data: pd.DataFrame, strategies: list[str]):
  tests = []
  runMonthlyAlgo = bt.algos.RunMonthly()
  selectAllAlgo = bt.algos.SelectAll()
  rebalanceAlgo = bt.algos.Rebalance()
  for strategy_name in strategies:
    if strategy_name == "Equally Weighted":
      weightedAlgo = bt.algos.WeighEqually()
    elif strategy_name == "MarketCap Weighted":
      #TODO: fix me, we need to define a new algo
      weightedAlgo = bt.algos.WeighInvVol()

    # build strategy
    strategy = bt.Strategy(
        strategy_name,
        [
          runMonthlyAlgo,
          selectAllAlgo,
          weightedAlgo,
          rebalanceAlgo
        ]
    )
    # create back test using strategy with data
    test = bt.Backtest(strategy, data)
    tests.append(test)

  return tests


def download_history_data(selected_df: pd.DataFrame):
  symbol_list = selected_df['symbol'].to_list()
  comma_sep_symbols = ','.join(symbol_list)
  # TODO: fix me, fetch batch by batch
  return bt.get(comma_sep_symbols, start='2014-01-01')


def calc_returns(selected_df: pd.DataFrame, strategies: list[str]):
  st.session_state.page_state = 'CALC_RETURNS'
  if len(strategies) == 0:
    st.error("Please select at least one strategy.")

  data = download_history_data(selected_df)
  tests = build_back_test(data, strategies)

  # run the back testing and save the result
  st.session_state.result = bt.run(*tests)



def enrich_holdings(selected_holdings):
  symbol_list = selected_holdings['symbol'].to_list()
  batch_size = 10
  symbol_batch_list = [symbol_list[i:i + batch_size] for i in range(0, len(symbol_list), batch_size)]

  country_col = []
  industry_col = []
  sector_col = []
  market_cap_col = []
  for symbol_batch in symbol_batch_list:
    batch_tickers = ' '.join(symbol_batch)
    # batch fetch stock basic info from Yahoo Finance
    tickers = yf.Tickers(batch_tickers)
    for symbol in symbol_batch:
      info = tickers.tickers[symbol].info
      if info is not None:
        country_col.append(info['country'])
        industry_col.append(info['industry'])
        sector_col.append(info['sector'])
        market_cap_col.append(info['marketCap'])
      else:
        country_col.append(None)
        industry_col.append(None)
        sector_col.append(None)
        market_cap_col.append(None)

  selected_holdings['country'] = country_col
  selected_holdings['industry'] = industry_col
  selected_holdings['sector'] = sector_col
  selected_holdings['marketCap'] = market_cap_col


# Main page start here
st.title("Welcome to Portfolio Mate")

ticker = st.text_input(label="Fund Ticker", placeholder="Please enter a fund ticker, e.g. SPY")

st.button("Fetch", on_click=on_fetch_holdings, args=(ticker,))

print(st.session_state.get('page_state',''))

if st.session_state.get('page_state','') == 'DATA_FETCHED':
  fund_holdings = st.session_state.holdings
  if fund_holdings is not None:
    config = {
      'checked' : st.column_config.CheckboxColumn(label='Checked'),
      'name' : st.column_config.TextColumn(label='Name'),
      'symbol' : st.column_config.TextColumn(label='Symbol'),
      'shares' : st.column_config.NumberColumn(label='Shares'),
      'weight' : st.column_config.NumberColumn(label='Weight'),
    }
    edited_df = st.data_editor(data=fund_holdings,
                               hide_index = False,
                               column_config = config,
                               disabled=('name','symbol'),
                               num_rows='dynamic')

    st.button("Next Step", on_click=remove_uncheked_holdings, args=(edited_df,))
  else:
    st.error("Fetch data failed")

if (st.session_state.get('page_state','') == 'NEXT_STEP'
    or st.session_state.get('page_state','') == 'CALC_RETURNS'):
  selected_holdings = st.session_state.holdings
  if selected_holdings is not None:
    enrich_holdings(selected_holdings)

    config = {
      'name' : st.column_config.TextColumn(label='Name'),
      'symbol' : st.column_config.TextColumn(label='Symbol'),
      'shares' : st.column_config.NumberColumn(label='Shares'),
      'weight' : st.column_config.NumberColumn(label='Weight'),
      'country' : st.column_config.TextColumn(label='Country'),
      'industry' : st.column_config.TextColumn(label='Industry'),
      'sector' : st.column_config.TextColumn(label='Sector'),
      'marketCap' : st.column_config.NumberColumn(label='MarketCap'),
    }
    selected_df = st.data_editor(data=selected_holdings,
                               hide_index = True,
                               column_config = config,)

    options = st.multiselect("Select strategy", ("Equally Weighted", "MarketCap Weighted"))
    st.button("Calculate returns", on_click=calc_returns, args=(selected_df,options,))

    result = st.session_state.get('result', None)
    if result is not None:
      #TODO: fix display
      st.dataframe(result)
  else:
    st.error("No holding is selected")