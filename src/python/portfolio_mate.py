import pandas as pd
import streamlit as st
#from st_aggrid import AgGrid
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time

def fake_fetch(ticker: str) ->  pd.DataFrame:
  # simulate fetch action, for testing only
  time.sleep(3)
  return pd.DataFrame([
    {"checked": True,"name": "Microsoft", "symbol": "MSFT", "shares": 100, "weight": 0.1},
    {"checked": True,"name": "Apple", "symbol": "AAPL", "shares": 200, "weight": 0.2},
    {"checked": True,"name": "Nvidia", "symbol": "NVDA", "shares": 300, "weight": 0.3},
    {"checked": True,"name": "Amazon", "symbol": "AMZN", "shares": 400, "weight": 0.4},
  ])

def fake_holdings(ticker: str):
  if len(ticker.strip()) == 0:
    st.error("You haven't specify a fund ticker yet")
  else:
    with st.spinner(f"Fetching the fund {ticker}... it may take a few minutes, please kindly be patient."):
      data = fetch_fund_holdings(ticker)
    st.session_state.page_state = 'DATA_FETCHED'
    st.session_state.holdings = data
    st.session_state.ticker = ticker.strip().upper()



def fetch_fund_holdings(ticker: str) -> pd.DataFrame:
  print('fetch data...')
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = f'https://www.zacks.com/funds/etf/{ticker.strip().upper()}/holding'
    page.goto(url=url, timeout=180000, wait_until='load')

    holdings = None
    try:
      holdings = page.evaluate("etf_holdings")
    except:
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
        symbol = soup.a.get_text()

      shares = float(h[2].replace(',',''))
      weight = float(h[3].replace(',',''))/100
      data.append({"checked": True,"name": name, "symbol": symbol, "shares": shares, "weight": weight})

    # Close the browser
    browser.close()

    return pd.DataFrame(data)

def next_step(edited_data: pd.DataFrame):
  st.session_state.page_state = 'NEXT_STEP'
  removed_index_list = edited_data[(edited_data['checked'] == False)].index.tolist()
  new_data = edited_data.drop(index=removed_index_list)
  # drop the 'checked' column
  new_data.drop('checked', axis=1, inplace=True)
  new_data.reset_index()
  st.session_state.holdings = new_data


st.title("Welcome to Portfolio Mate")

ticker = st.text_input(label="Fund Ticker", placeholder="Please enter a fund ticker, e.g. SPY")

st.button("Fetch", on_click=fake_holdings, args=(ticker,))

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

    st.button("Next Step", on_click=next_step, args=(edited_df,))
  else:
    st.error("Fetch data failed")

if st.session_state.get('page_state','') == 'NEXT_STEP':
  selected_holdings = st.session_state.holdings
  if selected_holdings is not None:
    config = {
      'name' : st.column_config.TextColumn(label='Name'),
      'symbol' : st.column_config.TextColumn(label='Symbol'),
      'shares' : st.column_config.NumberColumn(label='Shares'),
      'weight' : st.column_config.NumberColumn(label='Weight'),
    }
    selected_df = st.data_editor(data=selected_holdings,
                               hide_index = True,
                               column_config = config,
                               disabled=('name','symbol'))

    st.button("Calculate returns")
  else:
    st.error("No holding is selected")