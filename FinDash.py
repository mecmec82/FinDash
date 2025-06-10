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
        if not info or not info.get('longName'):
            st.warning(f"Could not find valid data for ticker: {ticker_symbol.upper()}. Please check the ticker symbol.")
            return None # Return None if ticker is invalid

        financials = stock.financials # Annual income statement
        balance_sheet = stock.balance_sheet # Annual balance sheet

        # Basic Info
        data["Company"] = info.get("longName", f"{ticker_symbol.upper()}")
        data["Industry"] = info.get("industry", "N/A")
        if info.get("marketCap"):
            data["Market Cap (B)"] = info["marketCap"] / 1_000_000_000

        # Trailing P/E
        if info.get("trailingPE"):
            data["Trailing P/E"] = info["trailingPE"]

        # Sales Growth Calculations
        # yfinance financials are in descending order of year (most recent first)
        if 'Total Revenue' in financials.index:
            revenues = financials.loc['Total Revenue']
            
            # 1-Year Sales Growth
            if len(revenues) >= 2 and revenues.iloc[1] != 0:
                data["1Yr Sales Growth"] = (revenues.iloc[0] - revenues.iloc[1]) / revenues.iloc[1]
            
            # 5-Year Sales Growth (Compound Annual Growth Rate - CAGR)
            # Need at least 5 years of data for 5-year growth (index 0 to 4 inclusive)
            if len(revenues) >= 5 and revenues.iloc[4] > 0 and revenues.iloc[0] > 0:
                try:
                    data["5Yr Sales Growth"] = (revenues.iloc[0] / revenues.iloc[4])**(1/5) - 1
                except ZeroDivisionError:
                    data["5Yr Sales Growth"] = np.nan # Handle cases where oldest revenue is zero
                except Exception as e:
                    st.warning(f"Error calculating 5Yr Sales Growth for {ticker_symbol}: {e}")
                    data["5Yr Sales Growth"] = np.nan
        else:
            st.info(f"Total Revenue data not available for {ticker_symbol}.")

        # Debt to Equity Calculation
        if 'Total Debt' in balance_sheet.index and 'Total Stockholder Equity' in balance_sheet.index:
            total_debt = balance_sheet.loc['Total Debt'].iloc[0] if not balance_sheet.loc['Total Debt'].empty else np.nan
            total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0] if not balance_sheet.loc['Total Stockholder Equity'].empty else np.nan
            
            if pd.notna(total_debt) and pd.notna(total_equity) and total_equity != 0:
                data["Debt to Equity"] = total_debt / total_equity
            elif pd.notna(total_debt) and pd.notna(total_equity) and total_equity == 0:
                data["Debt to Equity"] = float('inf') # Infinite D/E if equity is zero
            else:
                data["Debt to Equity"] = np.nan
        else:
            st.info(f"Debt or Equity data not available for {ticker_symbol}.")

    except Exception as e:
        st.error(f"Failed to fetch or process data for {ticker_symbol.upper()}. Error: {e}")
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
        # Handle infinite D/E gracefully
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
    value="AAPL, MSFT, AMZN", # Default value for convenience
    help="Enter comma-separated stock ticker symbols."
)

# Process input tickers
# Clean up input: remove spaces, split by comma, filter empty strings, convert to uppercase
tickers_to_fetch = [
    ticker.strip().upper() for ticker in ticker_input.split(',') if ticker.strip()
]

if tickers_to_fetch:
    comparison_data_list = []
    invalid_tickers = []

    st.info(f"Attempting to fetch data for: {', '.join(tickers_to_fetch)}")

    with st.spinner("Fetching financial data... This may take a moment per ticker."):
        for ticker in tickers_to_fetch:
            company_data = fetch_company_data(ticker)
            if company_data:
                comparison_data_list.append(company_data)
            else:
                invalid_tickers.append(ticker)

    if invalid_tickers:
        st.warning(f"Could not retrieve data for the following tickers: {', '.join(invalid_tickers)}. They might be invalid or have no available data.")

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
        existing_cols = [col for col in desired_order if col in df.columns]
        df = df[existing_cols]

        st.subheader("Comparison Table")

        # Apply conditional formatting using our helper function
        df_formatted = df.copy()

        format_map = {
            "1Yr Sales Growth": "percent",
            "5Yr Sales Growth": "percent",
            "Debt to Equity": "ratio",
            "PEG Ratio": "ratio",
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
        *   **5Yr Sales Growth:** The Compound Annual Growth Rate (CAGR) of a company's revenue over the past five fiscal years. Indicates consistent long-term growth. Requires 5 years of historical revenue data.
        *   **Debt to Equity:** A ratio indicating the proportion of equity and debt used to finance a company's assets. Lower is generally better (less reliance on debt), but varies significantly by industry (e.g., financial institutions often have higher D/E). An "Inf" value means total equity is zero or negative.
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
        st.warning("No data could be retrieved for the entered tickers. Please ensure they are valid NYSE/NASDAQ symbols.")
else:
    st.info("Please enter one or more ticker symbols to begin the comparison.")
