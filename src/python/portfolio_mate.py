import streamlit as st
import pandas as pd
from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup


data = []
def fetch_fund_holdings(ticker: str) -> pd.DataFrame:
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = f'https://www.zacks.com/funds/etf/{ticker.strip().upper()}/holding'
    page.goto(url=url, timeout=180000, wait_until='load')

    holdings = page.evaluate("etf_holdings")
    if holdings is None:
      return None

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


st.title("Welcome to Portfolio Mate")

ticker = st.text_input(label="Fund Ticker", placeholder="Please enter a fund ticker, e.g. SPY")

st.button("Fetch")

if st.button:
  if len(ticker.strip()) == 0:
    st.error("You haven't specify a fund ticker yet")
  else:
    st.write(f"Fetching the fund {ticker}...")
    st.write("It may take a few minutes, please kindly be patient!")
    data.clear()
    fund_holdings = fetch_fund_holdings(ticker)
    if fund_holdings is not None:
      config = {
        'checked' : st.column_config.CheckboxColumn('Checked'),
        'name' : st.column_config.TextColumn('Name', disabled=True),
        'symbol' : st.column_config.TextColumn('Symbol', disabled=True),
        'shares' : st.column_config.NumberColumn('Shares', disabled=True),
        'weight' : st.column_config.NumberColumn('Weight', disabled=True),
      }
      edited_df = st.data_editor(data=fund_holdings, column_config = config, num_rows='dynamic')
    else:
      st.error("Fetch data failed")

