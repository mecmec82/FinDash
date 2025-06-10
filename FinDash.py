import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import re

# --- Helper Functions for Data Fetching and Calculation ---

@st.cache_data(ttl=3600) # Cache data for 1 hour to reduce API calls
def fetch_company_data(ticker_symbol):
    """
    Fetches and calculates financial data for a given ticker using yfinance.
    """
    data = {
        "Company": f"{ticker_symbol.upper()}", # Default, will be updated with longName
        "Industry": "N/A",
        "Market Cap (B)": np.nan,
        "1Yr Sales Growth": np.nan,
        "5Yr Sales Growth": np.nan,
        "Debt to Equity": np.nan,
        "PEG Ratio": np.nan, # Cannot be reliably calculated with yfinance for forward growth
        "Trailing P/E": np.nan, # Included as a substitute valuation metric
    }

    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # Check if the ticker is valid and info is available
        # Some invalid tickers might still return a Ticker object but with no info
        if not info or not info.get('longName') or 'regularMarketPrice' not in info:
            st.warning(f"Could not find valid data for ticker: {ticker_symbol.upper()}. It might be an invalid symbol or have no available data.")
            return None # Return None if ticker is invalid

        financials = stock.financials # Annual income statement
        balance_sheet = stock.balance_sheet # Annual balance sheet

        # Basic Info
        data["Company"] = info.get("longName", f"{ticker_symbol.upper()}")
        data["Industry"] = info.get("industry", "N/A")
        if info.get("marketCap"):
            data["Market Cap (B)"] = info["marketCap"] / 1_000_000_000 # Convert to billions

        # Trailing P/E
        if info.get("trailingPE"):
            data["Trailing P/E"] = info["trailingPE"]

        # Sales Growth Calculations
        if 'Total Revenue' in financials.index:
            revenues = financials.loc['Total Revenue']
            
            # 1-Year Sales Growth
            if len(revenues) >= 2 and revenues.iloc[1] != 0:
                data["1Yr Sales Growth"] = (revenues.iloc[0] - revenues.iloc[1]) / revenues.iloc[1]
            else:
                st.info(f"Not enough annual revenue data (at least 2 years) for {ticker_symbol} to calculate 1-Year Sales Growth.")
            
            # 5-Year Sales Growth (Compound Annual Growth Rate - CAGR)
            # Need at least 5 years of data for 5-year growth (index 0 to 4 inclusive)
            if len(revenues) >= 5:
                # Revenues are ordered descending by year, so iloc[0] is latest, iloc[4] is 5 years prior
                latest_revenue = revenues.iloc[0]
                revenue_5_years_ago = revenues.iloc[4]
                
                if revenue_5_years_ago > 0: # Ensure no division by zero or negative base for CAGR
                    data["5Yr Sales Growth"] = (latest_revenue / revenue_5_years_ago)**(1/5) - 1
                elif latest_revenue > 0 and revenue_5_years_ago == 0:
                    data["5Yr Sales Growth"] = float('inf') # Infinite growth from zero base
                else:
                    st.info(f"5-Year ago revenue is zero or negative for {ticker_symbol}, cannot calculate 5-Year Sales Growth meaningfully.")
            else:
                st.info(f"Not enough annual revenue data (at least 5 years) for {ticker_symbol} to calculate 5-Year Sales Growth.")
        else:
            st.info(f"Total Revenue data not available in annual financials for {ticker_symbol}.")


        # Debt to Equity Calculation
        total_debt = np.nan
        total_equity = np.nan

        # Attempt to get Total Stockholder Equity
        if 'Total Stockholder Equity' in balance_sheet.index and not balance_sheet.loc['Total Stockholder Equity'].empty:
            total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
        else:
            st.info(f"Total Stockholder Equity data not available for {ticker_symbol}.")

        # Calculate Total Debt from Long Term Debt and Short Term Debt
        long_term_debt = balance_sheet.loc['Long Term Debt'].iloc[0] if 'Long Term Debt' in balance_sheet.index and not balance_sheet.loc['Long Term Debt'].empty else 0
        short_term_debt = balance_sheet.loc['Current Debt'].iloc[0] if 'Current Debt' in balance_sheet.index and not balance_sheet.loc['Current Debt'].empty else \
                         (balance_sheet.loc['Short Term Debt'].iloc[0] if 'Short Term Debt' in balance_sheet.index and not balance_sheet.loc['Short Term Debt'].empty else 0)

        # If we successfully got both, sum them up
        if long_term_debt is not None and short_term_debt is not None:
             total_debt = long_term_debt + short_term_debt
        else:
            st.info(f"Long Term Debt or Short Term Debt data not available for {ticker_symbol}.")

        # Perform Debt to Equity calculation if all components are available
        if pd.notna(total_debt) and pd.notna(total_equity):
            if total_equity != 0:
                data["Debt to Equity"] = total_debt / total_equity
            else:
                data["Debt to Equity"] = float('inf') # Infinite D/E if equity is zero
        else:
            data["Debt to Equity"] = np.nan # Ensure it's NaN if data is truly missing
            
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching or processing data for {ticker_symbol.upper()}. Error: {e}")
        return None # Indicate failure for this ticker

    return data

def format_value(value, metric_type):
    """Formats values for display based on metric type, handling NaNs."""
    if pd.isna(value):
        return "N/A"
    if metric_type == "percent":
        return f"{value:.2%}"
    elif metric_type == "currency_billion":
        return f"${value:,.0f}B"
    elif metric_type == "ratio":
        # Handle infinite D/E or growth gracefully
        if value == float('inf'):
            return "Inf"
        return f"{value:.2f}"
    else: # Default for other numbers
        return str(value)

# --- Streamlit App Layout ---

st.set_page_config(layout="wide", page_title="Dynamic Financial Company Comparator")

st.title("📊 Dynamic Company Financial Comparator")

st.markdown("""
Enter one or more company stock ticker symbols (e.g., `AAPL, MSFT, AMZN`) in the input box below.
Separate multiple tickers with commas.
""")

# Input for ticker symbols
ticker_input = st.text_input(
    "Enter Ticker Symbols (e.g., AAPL, MSFT, GOOGL):",
    value="AAPL, MSFT, AMZN, KO", # Default value for convenience, including KO
    help="Enter comma-separated stock ticker symbols (e.g., AAPL, MSFT, GOOGL)."
)

# Process input tickers
# Clean up input: remove spaces, split by comma, filter empty strings, convert to uppercase
tickers_to_fetch = [
    ticker.strip().upper() for ticker in ticker_input.split(',') if ticker.strip()
]

if tickers_to_fetch:
    comparison_data_list = []
    invalid_tickers = []
    missing_data_messages = st.empty() # Placeholder for info messages

    st.info(f"Attempting to fetch data for: {', '.join(tickers_to_fetch)}")

    with st.spinner("Fetching financial data... This may take a moment per ticker."):
        # Use a temporary list for messages to display at the end
        temp_messages = []
        # Redirect st.info from fetch_company_data to our list
        # This is a bit advanced, but allows us to capture messages
        # and display them all at once after the spinner is gone.
        original_st_info = st.info
        def capture_info_message(message):
            temp_messages.append(message)
        st.info = capture_info_message # Temporarily replace st.info

        for ticker in tickers_to_fetch:
            company_data = fetch_company_data(ticker)
            if company_data:
                comparison_data_list.append(company_data)
            else:
                invalid_tickers.append(ticker)
        
        st.info = original_st_info # Restore original st.info after fetching
    
    # Display captured messages
    if temp_messages:
        with missing_data_messages.container():
            st.markdown("##### Data Availability Notes:")
            for msg in temp_messages:
                st.info(msg)


    if invalid_tickers:
        st.warning(f"Could not retrieve data for the following tickers: {', '.join(invalid_tickers)}. They might be invalid, or `yfinance` had issues fetching their data.")

    if comparison_data_list:
        df = pd.DataFrame(comparison_data_list)

        # Set 'Company' as the index for better presentation
        df.set_index("Company", inplace=True)

        # Reorder columns for better readability
        desired_order = [
            "Industry",
            "Market Cap (B)",
            "1Yr Sales Growth",
            "5Yr Sales Growth",
            "Debt to Equity",
            "PEG Ratio", # Will be N/A
            "Trailing P/E",
        ]
        # Filter for columns that actually exist in the fetched data
        existing_cols = [col for col in df.columns if col in desired_order]
        df = df[existing_cols] # Apply desired_order for existing columns

        st.subheader("Comparison Table")

        # Apply conditional formatting using our helper function
        df_formatted = df.copy()

        format_map = {
            "1Yr Sales Growth": "percent",
            "5Yr Sales Growth": "percent",
            "Debt to Equity": "ratio",
            "PEG Ratio": "ratio", # Will show N/A
            "Trailing P/E": "ratio",
            "Market Cap (B)": "currency_billion",
        }

        for col, fmt_type in format_map.items():
            if col in df_formatted.columns:
                df_formatted[col] = df_formatted[col].apply(lambda x: format_value(x, fmt_type))

        st.dataframe(df_formatted.transpose(), use_container_width=True) # Transpose for metrics as rows

        st.markdown("---")
        st.subheader("Understanding the Metrics:")
        st.markdown("""
        *   **1Yr Sales Growth:** The percentage increase in a company's revenue over the past 12 months (latest fiscal year vs. previous fiscal year). Higher is generally better for growth.
        *   **5Yr Sales Growth:** The Compound Annual Growth Rate (CAGR) of a company's revenue over the past five fiscal years. Indicates consistent long-term growth. Requires at least 5 years of historical annual revenue data.
        *   **Debt to Equity:** A ratio indicating the proportion of equity and debt used to finance a company's assets, calculated as (Long Term Debt + Short Term Debt) / Total Stockholder Equity. Lower is generally better (less reliance on debt), but varies significantly by industry (e.g., financial institutions often have higher D/E). An "Inf" value means total equity is zero or negative.
        *   **PEG Ratio (Price/Earnings to Growth Ratio):** A stock's price-to-earnings (P/E) ratio divided by the growth rate of its earnings per share (EPS).
            *   **⚠️ IMPORTANT NOTE ON PEG RATIO:** This metric **cannot be reliably calculated using `yfinance`** because it fundamentally requires *future* earnings per share (EPS) growth estimates (typically a 5-year forecasted growth from analysts), which `yfinance` does not provide. Therefore, it will always show "N/A" for live fetched companies in this application.
        *   **Trailing P/E (Price/Earnings Ratio):** The stock's current share price divided by its earnings per share (EPS) over the past 12 months. This is included here as a readily available fundamental valuation metric.
        """)

        st.info("""
        **Disclaimer:**
        *   Data is fetched using `yfinance` and may have limitations, be delayed, or occasional inaccuracies.
        *   **PEG Ratio** is not available via `yfinance` as it requires future earnings growth estimates.
        *   Financial metrics should always be analyzed in context of industry, company size, and overall economic conditions.
        *   This application is for informational purposes only and is not financial advice.
        """)

    else:
        st.warning("No data could be retrieved for the entered tickers. Please ensure they are valid NYSE/NASDAQ symbols and have available financial data.")
else:
    st.info("Please enter one or more ticker symbols to begin the comparison.")
