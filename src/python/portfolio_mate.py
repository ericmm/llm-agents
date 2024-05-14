import bt
import datetime
import pandas as pd
import streamlit as st
import time
import yfinance as yf
# from st_aggrid import AgGrid
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


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


def on_fetch_holdings(ticker: str, start_date: str):
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
    st.session_state.ticker = ticker.strip().upper()
    st.session_state.start_date = (start_date or datetime.date(2014, 1, 1)).strftime("%Y-%m-%d")


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


def build_benchmark_test():
  s = bt.Strategy(f'Benchmark: {st.session_state.benchmark_ticker}',
                  # [bt.algos.RunOnce(),
                  [bt.algos.RunMonthly(),
                   bt.algos.SelectAll(),
                   bt.algos.WeighEqually(), # only one ticker, so it's 100%
                   bt.algos.Rebalance()])
  data = bt.get(st.session_state.benchmark_ticker,
                start=st.session_state.start_date)
  return bt.Backtest(s, data)


def build_back_test(selected_df: pd.DataFrame, data: pd.DataFrame, strategies: list[str]):
  tests = []
  run_monthly_algo = bt.algos.RunMonthly()
  select_all_algo = bt.algos.SelectAll()
  rebalance_algo = bt.algos.Rebalance()
  weighted_algo = None
  # selectNAlgo = bt.algos.SelectN(2)
  for strategy_name in strategies:
    if strategy_name == "Equally Weighted":
      weighted_algo = bt.algos.WeighEqually()

    elif strategy_name == "MarketCap Weighted":
      weights = calc_weight_by_market_cap(selected_df)
      weighted_algo = bt.algos.WeighSpecified(**weights)

    elif strategy_name == "Using Weights Above":
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
          run_monthly_algo,
          select_all_algo,
          weighted_algo,
          rebalance_algo
        ]
    )
    # create back test using strategy with data
    test = bt.Backtest(strategy, data)
    tests.append(test)

  # add benchmark test
  tests.append(build_benchmark_test())
  return tests


def download_history_data(selected_df: pd.DataFrame):
  symbol_list = selected_df['symbol'].to_list()
  if st.session_state.benchmark_ticker not in symbol_list:
    symbol_list.append(st.session_state.benchmark_ticker)
  comma_sep_symbols = ','.join(symbol_list)
  return bt.get(comma_sep_symbols, start=st.session_state.start_date)


def calc_returns(selected_df: pd.DataFrame, strategies: list[str], benchmark_ticker: str):
  st.session_state.page_state = 'CALC_RETURNS'
  if len(strategies) == 0:
    st.error("Please select at least one strategy.")
    return
  elif len(benchmark_ticker) == 0:
    st.error("Please enter a benchmark ticker.")
    return

  st.session_state.benchmark_ticker = benchmark_ticker.upper()
  data = download_history_data(selected_df)
  tests = build_back_test(selected_df, data, strategies)

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

use_fake = st.checkbox("Use fake holdings", value=True)
st.session_state.use_fake = use_fake == True

cols=st.columns(2)
with cols[0]:
  ticker = st.text_input(label="Fund Ticker", placeholder="Please enter a fund ticker, e.g. SPY")
with cols[1]:
  date = st.date_input(label="Data since (for getting historical price data)",
                       value=datetime.date(2014, 1, 1),
                       min_value=datetime.date(2000, 1, 1),
                       max_value=datetime.date.today(),
                       format="YYYY-MM-DD")

st.button("Fetch", on_click=on_fetch_holdings, args=(ticker, date))

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
    if st.session_state.get('enriched', False) == False:
      enrich_holdings(selected_holdings)
      st.session_state.enriched = True

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
    selected_df.reset_index(inplace=True)
    # drop the old 'index' column
    selected_df.drop('index', axis=1, inplace=True)

    options = st.multiselect("Select strategy", ("Equally Weighted", "MarketCap Weighted", "Using Weights Above"))
    benchmark_ticker = st.text_input(label="Benchmark Ticker", placeholder="Please enter a benchmark ticker, e.g. MSFT or SPY")
    st.button("Calculate returns", on_click=calc_returns, args=(selected_df,options,benchmark_ticker))

    result = st.session_state.get('result', None)
    if result is not None:
      stats_data = result.stats.T.copy()
      percentage_columns = ['rf', 'total_return', 'cagr', 'max_drawdown', 'mtd',
                            'three_month', 'six_month', 'ytd', 'one_year', 'three_year',
                            'five_year', 'ten_year', 'incep', 'daily_mean', 'daily_vol',
                            'best_day', 'worst_day', 'monthly_mean', 'monthly_vol', 'best_month',
                            'worst_month', 'yearly_mean', 'yearly_vol', 'best_year', 'worst_year',
                            'avg_drawdown', 'avg_up_month', 'avg_down_month', 'win_year_perc', 'twelve_month_win_perc',]
      for col in percentage_columns:
        stats_data[col] = stats_data[col] * 100

      stats_config = {
        'start' : st.column_config.DateColumn(label='Start', format="YYYY-MM-DD",),
        'end' : st.column_config.DateColumn(label='End', format="YYYY-MM-DD",),
        'rf' : st.column_config.NumberColumn(label='Risk-free rate', format="%.2f%%",),
        'total_return' : st.column_config.NumberColumn(label='Total Return', format="%.2f%%",),
        'cagr' : st.column_config.NumberColumn(label='CAGR', format="%.2f%%",),
        'max_drawdown' : st.column_config.NumberColumn(label='Max Drawdown', format="%.2f%%",),
        'calmar' : st.column_config.NumberColumn(label='Calmar Ratio', format="%.2f",),
        'mtd' : st.column_config.NumberColumn(label='MTD', format="%.2f%%",),
        'three_month' : st.column_config.NumberColumn(label='3m', format="%.2f%%",),
        'six_month' : st.column_config.NumberColumn(label='6m', format="%.2f%%",),
        'ytd' : st.column_config.NumberColumn(label='YTD', format="%.2f%%",),
        'one_year' : st.column_config.NumberColumn(label='1y', format="%.2f%%",),
        'three_year' : st.column_config.NumberColumn(label='3Y (ann.)', format="%.2f%%",),
        'five_year' : st.column_config.NumberColumn(label='5Y (ann.)', format="%.2f%%",),
        'ten_year' : st.column_config.NumberColumn(label='10Y (ann.)', format="%.2f%%",),
        'incep' : st.column_config.NumberColumn(label='Since Incep. (ann.)', format="%.2f%%",),
        'daily_sharpe' : st.column_config.NumberColumn(label='Daily Sharpe', format="%.2f",),
        'daily_sortino' : st.column_config.NumberColumn(label='Daily Sortino', format="%.2f",),
        'daily_mean' : st.column_config.NumberColumn(label='Daily Mean (ann.)', format="%.2f%%",),
        'daily_vol' : st.column_config.NumberColumn(label='Daily Vol (ann.)', format="%.2f%%",),
        'daily_skew' : st.column_config.NumberColumn(label='Daily Skew', format="%.2f",),
        'daily_kurt' : st.column_config.NumberColumn(label='Daily Kurt', format="%.2f",),
        'best_day' : st.column_config.NumberColumn(label='Best Day', format="%.2f%%",),
        'worst_day' : st.column_config.NumberColumn(label='Worst Day', format="%.2f%%",),
        'monthly_sharpe' : st.column_config.NumberColumn(label='Monthly Sharpe', format="%.2f",),
        'monthly_sortino' : st.column_config.NumberColumn(label='Monthly Sortino', format="%.2f",),
        'monthly_mean' : st.column_config.NumberColumn(label='Monthly Mean (ann.)', format="%.2f%%",),
        'monthly_vol' : st.column_config.NumberColumn(label='Monthly Vol (ann.)', format="%.2f%%",),
        'monthly_skew' : st.column_config.NumberColumn(label='Monthly Skew', format="%.2f",),
        'monthly_kurt' : st.column_config.NumberColumn(label='Monthly Kurt', format="%.2f",),
        'best_month' : st.column_config.NumberColumn(label='Best Month', format="%.2f%%",),
        'worst_month' : st.column_config.NumberColumn(label='Worst Month', format="%.2f%%",),
        'yearly_sharpe' : st.column_config.NumberColumn(label='Yearly Sharpe', format="%.2f",),
        'yearly_sortino' : st.column_config.NumberColumn(label='Yearly Sortino', format="%.2f",),
        'yearly_mean' : st.column_config.NumberColumn(label='Yearly Mean (ann.)', format="%.2f%%",),
        'yearly_vol' : st.column_config.NumberColumn(label='Yearly Vol (ann.)', format="%.2f%%",),
        'yearly_skew' : st.column_config.NumberColumn(label='Yearly Skew', format="%.2f",),
        'yearly_kurt' : st.column_config.NumberColumn(label='Yearly Kurt', format="%.2f",),
        'best_year' : st.column_config.NumberColumn(label='Best Yearly', format="%.2f%%",),
        'worst_year' : st.column_config.NumberColumn(label='Worst Yearly', format="%.2f%%",),
        'avg_drawdown' : st.column_config.NumberColumn(label='Avg. Drawdown', format="%.2f%%",),
        'avg_drawdown_days' : st.column_config.NumberColumn(label='Avg. Drawdown Days', format="%.2f",),
        'avg_up_month' : st.column_config.NumberColumn(label='Avg. Up Month', format="%.2f%%",),
        'avg_down_month' : st.column_config.NumberColumn(label='Avg. Down Month', format="%.2f%%",),
        'win_year_perc' : st.column_config.NumberColumn(label='Win Year % ', format="%.2f%%",),
        'twelve_month_win_perc' : st.column_config.NumberColumn(label='Win 12m %', format="%.2f%%",),
      }
      st.dataframe(data=stats_data,
                   column_config=stats_config, )

      price_data = result.prices.copy()
      price_data.drop(price_data.columns[len(price_data.columns)-1], axis=1, inplace=True)
      st.line_chart(data=price_data)
      print(result.prices)
  else:
    st.error("No holding is selected")