import bt
import datetime
import ffn
import math
import pandas as pd
import streamlit as st
import time
import yfinance as yf
# from st_aggrid import AgGrid
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

STRATEGY_EQUALLY_WEIGHTED = "Equally Weighted"
STRATEGY_MARKETCAP_WEIGHTED = "MarketCap Weighted"
STRATEGY_SUPPLIED_WEIGHTS = "Using Weights Above"


def do_fetch_fake_holdings(ticker: str) -> pd.DataFrame:
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
  # csv upload
  if st.session_state.get('holdings', None) is not None:
    st.session_state.page_state = 'DATA_FETCHED'
    st.session_state.enriched = False
    return

  if len(ticker.strip()) == 0:
    st.error("You haven't specify a fund ticker yet")
  else:
    with st.spinner(f"Fetching the fund {ticker}... it may take a few minutes, please kindly be patient."):
      if st.session_state.use_fake:
        data = do_fetch_fake_holdings(ticker)
      else:
        data = do_fetch_holdings(ticker)
    st.session_state.page_state = 'DATA_FETCHED'
    st.session_state.holdings = data
    st.session_state.enriched = False


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
        symbol = soup.a.get_text().replace('N/A', '')

      shares = float(h[2].replace(',', ''))
      weight = float(h[3].replace(',', ''))/100
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
  # uppercase the symbol
  new_data['symbol'] = new_data['symbol'].str.upper()
  # drop the 'checked' column
  new_data = new_data.drop('checked', axis=1)
  new_data.reset_index()
  st.session_state.holdings = new_data
  st.session_state.enriched = False
  st.session_state.result = None


def calc_weight_by_market_cap(selected_df: pd.DataFrame):
  weights = {}
  symbol_col = selected_df['symbol']
  market_cap_col = selected_df['marketCap']
  total_market_cap = 0
  for m in market_cap_col:
    total_market_cap += m
  for idx, s in enumerate(symbol_col):
    weights[s.lower()] = float(market_cap_col[idx] / total_market_cap)
  return weights


def build_benchmark_test(start_date: str):
  s = bt.Strategy(f'Benchmark: {st.session_state.benchmark_ticker}',
                  [bt.algos.RunOnce(),
                   bt.algos.SelectAll(),
                   bt.algos.WeighEqually(),  # only one ticker, so it's 100%
                   bt.algos.Rebalance()])
  data = bt.get(st.session_state.benchmark_ticker, start=start_date)
  return bt.Backtest(s, data)


def build_back_test(selected_df: pd.DataFrame, data: pd.DataFrame, strategies: list[str], rebalance_freq: str):
  tests = []

  run_algo = build_rebalance_freq_algo(rebalance_freq)
  select_all_algo = bt.algos.SelectAll()
  rebalance_algo = bt.algos.Rebalance()
  weighted_algo = None
  for strategy_name in strategies:
    if strategy_name == STRATEGY_EQUALLY_WEIGHTED:
      weighted_algo = bt.algos.WeighEqually()

    elif strategy_name == STRATEGY_MARKETCAP_WEIGHTED:
      weights = calc_weight_by_market_cap(selected_df)
      weighted_algo = bt.algos.WeighSpecified(**weights)

    elif strategy_name == STRATEGY_SUPPLIED_WEIGHTS:
      weights = {}
      # use weights in dataframe
      symbol_col = selected_df['symbol']
      weight_col = selected_df['weight']
      for idx, s in enumerate(symbol_col):
        weights[s.lower()] = weight_col[idx]
      weighted_algo = bt.algos.WeighSpecified(**weights)

    # build strategy
    strategy = bt.Strategy(
        strategy_name,
        [
          run_algo,
          select_all_algo,
          weighted_algo,
          rebalance_algo
        ]
    )
    # create back test using strategy with data
    test = bt.Backtest(strategy, data)
    tests.append(test)

  # add benchmark test
  tests.append(build_benchmark_test(data.index[0]))
  return tests


def build_rebalance_freq_algo(rebalance_freq):
  if rebalance_freq == 'Never':
    return bt.algos.RunOnce()
  elif rebalance_freq == 'Monthly':
    return bt.algos.RunMonthly()
  elif rebalance_freq == 'Quarterly':
    return bt.algos.RunQuarterly()
  else:
    return bt.algos.RunYearly()


def download_history_data(selected_df: pd.DataFrame):
  print('Downloading historical data...')
  symbol_list = selected_df['symbol'].to_list()
  if st.session_state.benchmark_ticker not in symbol_list:
    symbol_list.append(st.session_state.benchmark_ticker)
  comma_sep_symbols = ','.join(symbol_list)
  return bt.get(comma_sep_symbols, start=st.session_state.start_date)


def calc_returns(selected_df: pd.DataFrame, strategies: list[str], rebalance_freq: str, benchmark_ticker: str):
  st.session_state.page_state = 'CALC_RETURNS'
  if len(strategies) == 0:
    st.error("Please select at least one strategy.")
    return
  elif len(benchmark_ticker) == 0:
    st.error("Please enter a benchmark ticker.")
    return

  st.session_state.benchmark_ticker = benchmark_ticker.upper()
  data = download_history_data(selected_df)
  tests = build_back_test(selected_df, data, strategies, rebalance_freq)

  # run the back testing and save the result
  st.session_state.result = bt.run(*tests)


def enrich_holdings(selected_holdings):
  symbol_list = selected_holdings['symbol'].str.upper().to_list()
  batch_size = 10
  symbol_batch_list = [symbol_list[i:i + batch_size] for i in range(0, len(symbol_list), batch_size)]

  name_col = []
  country_col = []
  industry_col = []
  sector_col = []
  market_cap_col = []
  return_1y_col = []
  return_3y_col = []
  return_5y_col = []
  return_10y_col = []
  return_col = []
  for symbol_batch in symbol_batch_list:
    batch_tickers = ' '.join(symbol_batch)
    ffn_batch_tickers = ','.join(symbol_batch).lower()
    # batch fetch stock basic info from Yahoo Finance
    print(f'enrich holdings: {batch_tickers}')
    tickers = yf.Tickers(batch_tickers)
    batch_stats = ffn.get(ffn_batch_tickers, start=st.session_state.start_date).calc_stats()
    for symbol in symbol_batch:
      info = tickers.tickers[symbol].info
      if info is not None:
        country_col.append(info['country'])
        industry_col.append(info['industry'])
        sector_col.append(info['sector'])
        market_cap_col.append(info['marketCap'])
        name_col.append(info['shortName'])
        stats = batch_stats.get(symbol.lower(), None)
        populate_returns(stats, return_1y_col, return_3y_col, return_5y_col, return_10y_col, return_col)
      else:
        country_col.append(None)
        industry_col.append(None)
        sector_col.append(None)
        market_cap_col.append(None)
        name_col.append(None)
        return_1y_col.append(None)
        return_3y_col.append(None)
        return_5y_col.append(None)
        return_10y_col.append(None)
        return_col.append(None)

  selected_holdings['amount'] = selected_holdings.apply(lambda row: (row['weight']*st.session_state.amount), axis=1)
  selected_holdings['country'] = country_col
  selected_holdings['industry'] = industry_col
  selected_holdings['sector'] = sector_col
  selected_holdings['marketCap'] = market_cap_col
  selected_holdings['name'] = name_col
  selected_holdings['returns_1y'] = return_1y_col
  selected_holdings['returns_3y'] = return_3y_col
  selected_holdings['returns_5y'] = return_5y_col
  selected_holdings['returns_10y'] = return_10y_col
  selected_holdings['returns'] = return_col


def populate_returns(stats, return_1y_col, return_3y_col, return_5y_col, return_10y_col, return_col):
  if stats is not None and stats.lookback_returns is not None:
    populate_single_return(stats, '1y', return_1y_col)
    populate_single_return(stats, '3y', return_3y_col)
    populate_single_return(stats, '5y', return_5y_col)
    populate_single_return(stats, '10y', return_10y_col)
    populate_single_return(stats, 'incep', return_col)
  else:
    return_1y_col.append(None)
    return_3y_col.append(None)
    return_5y_col.append(None)
    return_10y_col.append(None)
    return_col.append(None)


def populate_single_return(stats, key, col):
  if stats.lookback_returns[key] is not None:
    col.append(float(stats.lookback_returns[key]) * 100)
  else:
    col.append(None)


# Main page start here
st.title("Welcome to Portfolio Mate")

use_fake = st.checkbox("Use fake holdings", value=True)
st.session_state.use_fake = (use_fake is True)

cols = st.columns(2)
with cols[0]:
  ticker = st.text_input(label="Fund Ticker",
                         placeholder="Please enter a fund ticker, e.g. SPY")
with cols[1]:
  date = st.date_input(label="Data since (for getting historical price data)",
                       value=datetime.date(2014, 1, 1),
                       min_value=datetime.date(2000, 1, 1),
                       max_value=datetime.date.today(),
                       format="YYYY-MM-DD")
  st.session_state.start_date = (date or datetime.date(2014, 1, 1)).strftime("%Y-%m-%d")

st.button("Fetch", on_click=on_fetch_holdings, args=(ticker,))

uploaded_file = st.file_uploader("Or upload a CSV file with 'symbol,weight' (lower case) header")
if uploaded_file is not None:
  if st.session_state.get('csv_uploaded', False) is False:
    uploaded_df = pd.read_csv(uploaded_file)

    # adding missing columns with default values
    uploaded_df['checked'] = True
    uploaded_df['name'] = uploaded_df['symbol']
    uploaded_df['shares'] = 1
    uploaded_df['weight'] = uploaded_df['weight'] / 100
    # re-order the columns
    uploaded_df = uploaded_df[['checked', 'name', 'symbol', 'shares', 'weight']]
    st.session_state.holdings = uploaded_df

    st.session_state.page_state = 'DATA_FETCHED'
    st.session_state.enriched = False
  st.session_state.csv_uploaded = True
else:
  if st.session_state.get('csv_uploaded', False) is True:
    # user deleted csv file
    st.session_state.holdings = None
    st.session_state.csv_uploaded = False
    st.session_state.enriched = False
st.text("")
st.text("")

print(st.session_state.get('page_state', ''))

if st.session_state.get('page_state', '') == 'DATA_FETCHED':
  fund_holdings = st.session_state.holdings
  if fund_holdings is not None:
    config = {
      'checked': st.column_config.CheckboxColumn(label='Checked'),
      'name': st.column_config.TextColumn(label='Name'),
      'symbol': st.column_config.TextColumn(label='Symbol'),
      'shares': st.column_config.NumberColumn(label='Shares'),
      'weight': st.column_config.NumberColumn(label='Weight'),
    }
    edited_df = st.data_editor(data=fund_holdings,
                               hide_index=False,
                               column_config=config,
                               disabled=('name',),
                               num_rows='dynamic')
    st.session_state.total_weight = edited_df.loc[edited_df['checked'] == True, 'weight'].sum()
    st.text("Tips: You can add new rows (symbol, weight) or edit weights by double click cells. \n     Remember to check the newly added rows.")
    st.text("")

    amt_cols = st.columns(2)
    with amt_cols[0]:
      amount = st.number_input("Amount to Invest", min_value=1.00, max_value=999999999.00, step=10000.00, value=10000.00, format="%.2f")
      st.session_state.amount = amount
    with amt_cols[1]:
      if math.isclose(st.session_state.total_weight, 1.0):
        text = "Total weights (100%)"
      else:
        text = "Total weights (not 100%)❗"
      st.number_input(text, value=st.session_state.total_weight, disabled=True, format="%.6f")
    st.text("")

    st.button("Next Step", on_click=remove_uncheked_holdings, args=(edited_df,))
  else:
    st.error( "No holding is selected, please click 'Fetch' button or upload a CSV file")

if (st.session_state.get('page_state', '') == 'NEXT_STEP'
    or st.session_state.get('page_state', '') == 'CALC_RETURNS'):
  selected_holdings = st.session_state.holdings
  if selected_holdings is not None:
    if st.session_state.get('enriched', False) is False:
      enrich_holdings(selected_holdings)
      st.session_state.enriched = True

    amt_cols2 = st.columns(2)
    with amt_cols2[0]:
      amount = st.number_input("Amount to Invest", value=st.session_state.amount, format="%.2f", disabled=True)
    with amt_cols2[1]:
      st.number_input("Total weights", value=st.session_state.total_weight, disabled=True, format="%.6f")

    config = {
      'name': st.column_config.TextColumn(label='Name'),
      'symbol': st.column_config.TextColumn(label='Symbol'),
      'shares': None,
      'weight': st.column_config.NumberColumn(label='Weight'),
      'amount': st.column_config.NumberColumn(label='Amount to Inv.', format="$%.2f"),
      'country': st.column_config.TextColumn(label='Country'),
      'industry': st.column_config.TextColumn(label='Industry'),
      'sector': st.column_config.TextColumn(label='Sector'),
      'marketCap': st.column_config.NumberColumn(label='MarketCap'),
      'returns_1y': st.column_config.NumberColumn(label='1Y (%)', format="%.2f%%"),
      'returns_3y': st.column_config.NumberColumn(label='3Y (%)', format="%.2f%%"),
      'returns_5y': st.column_config.NumberColumn(label='5Y (%)', format="%.2f%%"),
      'returns_10y': st.column_config.NumberColumn(label='10Y (%)', format="%.2f%%"),
      'returns': st.column_config.NumberColumn(label='since ' + st.session_state.start_date, format="%.2f%%"),
    }

    selected_df = st.data_editor(data=selected_holdings,
                                 hide_index=True,
                                 disabled=('name', 'symbol'),
                                 column_config=config, )
    selected_df.reset_index(inplace=True)
    # drop the old 'index' column
    selected_df.drop('index', axis=1, inplace=True)

    cols2 = st.columns(3)
    with cols2[0]:
      strategies = st.multiselect("Select one or more strategies", (STRATEGY_EQUALLY_WEIGHTED, STRATEGY_MARKETCAP_WEIGHTED, STRATEGY_SUPPLIED_WEIGHTS), default=(STRATEGY_EQUALLY_WEIGHTED, STRATEGY_MARKETCAP_WEIGHTED, STRATEGY_SUPPLIED_WEIGHTS))
    with cols2[1]:
      rebalance_freq = st.selectbox("Rebalance Frequency", ("Never", "Monthly", "Quarterly", "Annually"), index=3, )
    with cols2[2]:
      benchmark_ticker = st.text_input(label="Benchmark Ticker", value="MSFT")
    st.button("Calculate returns", on_click=calc_returns, args=(selected_df, strategies, rebalance_freq, benchmark_ticker))

    result = st.session_state.get('result', None)
    if result is not None:
      stats_data = result.stats.T.copy()
      columns_to_keep = ['start', 'end', 'rf', 'cagr', 'max_drawdown', 'one_year', 'three_year','five_year','ten_year', 'incep', 'total_return']
      stats_data = stats_data[columns_to_keep]
      stats_data['total_return_amt'] = stats_data.apply(lambda row: (row['total_return']*st.session_state.amount), axis=1)
      percentage_columns = ['rf', 'total_return', 'cagr', 'max_drawdown', 'one_year',
                            'three_year', 'five_year', 'ten_year', 'incep' ]
      for col in percentage_columns:
        stats_data[col] = stats_data[col] * 100

      stats_config = {
        'start' : st.column_config.DateColumn(label='Start', format="YYYY-MM-DD",),
        'end' : st.column_config.DateColumn(label='End', format="YYYY-MM-DD",),
        'rf' : st.column_config.NumberColumn(label='Risk-free rate', format="%.2f%%",),
        'total_return' : st.column_config.NumberColumn(label='Total Return %', format="%.2f%%",),
        'total_return_amt' : st.column_config.NumberColumn(label='Total Return $', format="$%.2f",),
        'cagr' : st.column_config.NumberColumn(label='CAGR', format="%.2f%%",),
        'max_drawdown' : st.column_config.NumberColumn(label='Max Drawdown', format="%.2f%%",),
        'calmar' : st.column_config.NumberColumn(label='Calmar Ratio', format="%.2f",),
        'one_year' : st.column_config.NumberColumn(label='1Y', format="%.2f%%",),
        'three_year' : st.column_config.NumberColumn(label='3Y (ann.)', format="%.2f%%",),
        'five_year' : st.column_config.NumberColumn(label='5Y (ann.)', format="%.2f%%",),
        'ten_year' : st.column_config.NumberColumn(label='10Y (ann.)', format="%.2f%%",),
        'incep' : st.column_config.NumberColumn(label='Since Incep. (ann.)', format="%.2f%%",),
      }
      st.dataframe(data=stats_data, column_config=stats_config, )
      st.line_chart(data=result.prices)
  else:
    st.error("No holding is selected, please click 'Fetch' button or upload a CSV file")
