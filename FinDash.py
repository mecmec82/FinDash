import streamlit as st
import pandas as pd
import yfinance as yf
import re
import numpy as np

# --- Configuration & Data Definitions ---

# Companies to pre-populate in the multiselect for easy demonstration
# Include display names and tickers
STOCKS_TO_COMPARE = [
    {"display_name": "Apple Inc. (AAPL)", "ticker": "AAPL"},
    {"display_name": "Microsoft Corp. (MSFT)", "ticker": "MSFT"},
    {"display_name": "Amazon.com Inc. (AMZN)", "ticker": "AMZN"},
    {"display_name": "Alphabet Inc. (GOOGL)", "ticker": "GOOGL"},
    {"display_name": "Tesla Inc. (TSLA)", "ticker": "TSLA"},
    {"display_name": "Johnson & Johnson (JNJ)", "ticker": "JNJ"},
    {"display_name": "Coca-Cola Co (KO)", "ticker": "KO"},
    {"display_name": "JPMorgan Chase & Co. (JPM)", "ticker": "JPM"},
]

# --- Helper Functions for Data Fetching and Calculation ---

@st.cache_data(ttl=3600) # Cache data for 1 hour to reduce API calls
def fetch_company_data(ticker_symbol):
    """Fetches financial data for a given ticker using yfinance."""
    data = {
        "Company": f"{ticker_symbol}", # Will be updated with proper name
        "Industry": "N/A",
        "Market Cap (B)": np.nan,
        "1Yr Sales Growth": np.nan,
        "5Yr Sales Growth": np.nan,
        "Debt to Equity": np.nan,
        "PEG Ratio": np.nan, # Cannot be reliably calculated with yfinance
        "Trailing P/E": np.nan, # Included as a substitute for PEG, since PEG is not available
    }

    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        financials = stock.financials # Annual income statement
        balance_sheet = stock.balance_sheet # Annual balance sheet

        # Basic Info
        data["Company"] = info.get("longName", f"{ticker_symbol}")
        data["Industry"] = info.get("industry", "N/A")
        if info.get("marketCap"):
            data["Market Cap (B)"] = info["marketCap"] / 1_000_000_000

        # Trailing P/E (as a proxy/substitute for PEG due to data limitations)
        if info.get("trailingPE"):
            data["Trailing P/E"] = info["trailingPE"]

        # 1Yr Sales Growth
        if 'Total Revenue' in financials.index and len(financials.columns) >= 2:
            current_year_revenue = financials.loc['Total Revenue'].iloc[0]
            previous_year_revenue = financials.loc['Total Revenue'].iloc[1]
            if previous_year_revenue != 0:
                data["1Yr Sales Growth"] = (current_year_revenue - previous_year_revenue) / previous_year_revenue

        # 5Yr Sales Growth (Compound Annual Growth Rate - CAGR)
        if 'Total Revenue' in financials.index and len(financials.columns) >= 5:
            # yfinance returns financials in descending order of year (most recent first)
            # So, financials.loc['Total Revenue'].iloc[0] is most recent
            # financials.loc['Total Revenue'].iloc[4] is 5 years ago
            latest_revenue = financials.loc['Total Revenue'].iloc[0]
            oldest_revenue_5yr = financials.loc['Total Revenue'].iloc[4]
            # Ensure revenue isn't zero or negative to avoid div by zero or complex logs
            if oldest_revenue_5yr > 0 and latest_revenue > 0:
                data["5Yr Sales Growth"] = (latest_revenue / oldest_revenue_5yr)**(1/5) - 1

        # Debt to Equity
        if 'Total Debt' in balance_sheet.index and 'Total Stockholder Equity' in balance_sheet.index:
            total_debt = balance_sheet.loc['Total Debt'].iloc[0]
            total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
            if total_equity != 0: # Avoid division by zero
                data["Debt to Equity"] = total_debt / total_equity

    except Exception as e:
        st.warning(f"Could not fetch complete data for {ticker_symbol}. Error: {e}")
        # Return partial data or data with NaNs for metrics that failed
        return data

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
        return f"{value:.2f}"
    else: # Default for other numbers
        return str(value)

# --- Streamlit App Layout ---

st.set_page_config(layout="wide", page_title="Financial Company Comparator")

st.title("📊 Company Financial Comparator (Powered by `yfinance`)")

st.markdown("""
Compare companies based on key financial metrics.
Select companies from the dropdown below to fetch their latest data.
""")

# Prepare options for the multiselect from our predefined list
company_options = [item["display_name"] for item in STOCKS_TO_COMPARE]

# Default selection (e.g., first 3 companies)
default_selection_display_names = [item["display_name"] for item in STOCKS_TO_COMPARE[:3]]

selected_display_names = st.multiselect(
    "Select Companies to Compare:",
    options=company_options,
    default=default_selection_display_names,
    help="You can select multiple companies. Data is fetched using `yfinance`."
)

if selected_display_names:
    comparison_data_list = []
    # Extract tickers from selected display names
    selected_tickers = []
    for display_name in selected_display_names:
        match = re.search(r'\((.*?)\)', display_name)
        if match:
            selected_tickers.append(match.group(1)) # Get ticker inside parentheses
        else:
            # Fallback if format is just ticker (though our list is consistent)
            selected_tickers.append(display_name)


    with st.spinner("Fetching financial data... This may take a moment."):
        for ticker in selected_tickers:
            company_data = fetch_company_data(ticker)
            if company_data:
                comparison_data_list.append(company_data)

    if comparison_data_list:
        df = pd.DataFrame(comparison_data_list)

        # Set 'Company' as the index for better presentation
        df.set_index("Company", inplace=True)

        # Reorder columns for better readability
        # The order of these columns also determines the order of rows when transposed
        desired_order = [
            "Industry",
            "Market Cap (B)",
            "1Yr Sales Growth",
            "5Yr Sales Growth",
            "Debt to Equity",
            "PEG Ratio", # Will mostly be N/A
            "Trailing P/E", # Included as a substitute
        ]
        # Filter for columns that actually exist in the fetched data
        existing_cols = [col for col in desired_order if col in df.columns]
        df = df[existing_cols]

        st.subheader("Comparison Table")

        # Apply conditional formatting using our helper function
        # Create a copy to avoid SettingWithCopyWarning
        df_formatted = df.copy()

        # Define which columns get which format type
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
        *   **1Yr Sales Growth:** The percentage increase in a company's revenue over the past 12 months. Higher is generally better for growth.
        *   **5Yr Sales Growth:** The Compound Annual Growth Rate (CAGR) of a company's revenue over the past five years. Indicates consistent long-term growth.
        *   **Debt to Equity:** A ratio indicating the proportion of equity and debt used to finance a company's assets. Lower is generally better (less reliance on debt), but varies significantly by industry (e.g., banks often have higher D/E).
        *   **PEG Ratio (Price/Earnings to Growth Ratio):** A stock's price-to-earnings (P/E) ratio divided by the growth rate of its earnings per share (EPS).
            *   **⚠️ IMPORTANT NOTE ON PEG RATIO:** This metric **cannot be reliably calculated using `yfinance`** because it requires *future* earnings per share (EPS) growth estimates (typically 5-year forecasted growth from analysts), which `yfinance` does not provide. It will show "N/A" for fetched companies.
        *   **Trailing P/E (Price/Earnings Ratio):** The stock's current share price divided by its earnings per share (EPS) over the past 12 months. Included here as a fundamental valuation metric, as PEG is unavailable.
        """)

        st.info("""
        **Disclaimer:**
        *   Data is fetched using `yfinance` and may have limitations or occasional inaccuracies.
        *   **PEG Ratio** is not available via `yfinance` as it requires future earnings growth estimates.
        *   Financial metrics should always be analyzed in context of industry, company size, and overall economic conditions.
        *   This application is for informational purposes only and is not financial advice.
        """)

    else:
        st.warning("No data available for the selected companies. Please try again or select different companies.")
else:
    st.info("Please select at least one company to view the comparison.")
