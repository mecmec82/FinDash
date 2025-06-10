import streamlit as st
import pandas as pd

# --- Mock Data ---
# In a real application, you would replace this with data fetched from a financial API.
# Common free APIs include:
# - yfinance (via `pip install yfinance`): Good for basic stock prices, some income/balance sheet.
#   You'd need to calculate sales growth yourself from annual revenue.
# - Alpha Vantage (needs API key): Offers various financial data.
# - Financial Modeling Prep (FMP - needs API key): Offers detailed financials, some ratios.
#
# PEG ratio is particularly tricky to get for free as it requires future EPS growth estimates.
# You might need to calculate it yourself: PEG = (P/E Ratio) / (Annual EPS Growth Rate)
# where EPS Growth Rate is often analyst consensus for next 5 years.

financial_data = {
    "Apple Inc. (AAPL)": {
        "1Yr Sales Growth": 0.08,  # 8%
        "5Yr Sales Growth": 0.12,  # 12%
        "Debt to Equity": 1.70,
        "PEG Ratio": 2.10,
        "Market Cap (B)": 2800,
        "Industry": "Technology",
    },
    "Microsoft Corp. (MSFT)": {
        "1Yr Sales Growth": 0.10,  # 10%
        "5Yr Sales Growth": 0.15,  # 15%
        "Debt to Equity": 0.80,
        "PEG Ratio": 1.85,
        "Market Cap (B)": 2400,
        "Industry": "Technology",
    },
    "Amazon.com Inc. (AMZN)": {
        "1Yr Sales Growth": 0.13,  # 13%
        "5Yr Sales Growth": 0.20,  # 20%
        "Debt to Equity": 0.95,
        "PEG Ratio": 2.50,
        "Market Cap (B)": 1500,
        "Industry": "E-commerce/Cloud",
    },
    "Alphabet Inc. (GOOGL)": {
        "1Yr Sales Growth": 0.07,  # 7%
        "5Yr Sales Growth": 0.10,  # 10%
        "Debt to Equity": 0.05,
        "PEG Ratio": 1.60,
        "Market Cap (B)": 1800,
        "Industry": "Technology",
    },
    "Tesla Inc. (TSLA)": {
        "1Yr Sales Growth": 0.30,  # 30%
        "5Yr Sales Growth": 0.40,  # 40%
        "Debt to Equity": 0.15,
        "PEG Ratio": 3.20,
        "Market Cap (B)": 700,
        "Industry": "Automotive",
    },
    "Johnson & Johnson (JNJ)": {
        "1Yr Sales Growth": 0.03,  # 3%
        "5Yr Sales Growth": 0.05,  # 5%
        "Debt to Equity": 0.45,
        "PEG Ratio": 1.20,
        "Market Cap (B)": 400,
        "Industry": "Healthcare",
    },
    "Coca-Cola Co (KO)": {
        "1Yr Sales Growth": 0.06,
        "5Yr Sales Growth": 0.04,
        "Debt to Equity": 2.05,
        "PEG Ratio": 2.80,
        "Market Cap (B)": 260,
        "Industry": "Beverages",
    },
    "JPMorgan Chase & Co. (JPM)": {
        "1Yr Sales Growth": 0.09,
        "5Yr Sales Growth": 0.08,
        "Debt to Equity": 1.10, # Banks have high D/E, often assessed differently
        "PEG Ratio": 1.50,
        "Market Cap (B)": 480,
        "Industry": "Financial Services",
    }
}

# --- Streamlit App ---

st.set_page_config(layout="wide", page_title="Company Financial Comparator")

st.title("📊 Company Financial Comparator")

st.markdown("""
Compare companies based on key financial metrics.
Select companies from the dropdown below to see their data side-by-side.
""")

company_names = list(financial_data.keys())

selected_companies = st.multiselect(
    "Select Companies to Compare:",
    options=company_names,
    default=company_names[:3], # Default selection
    help="You can select multiple companies."
)

if selected_companies:
    comparison_data = []
    for company in selected_companies:
        data = financial_data[company]
        # Add company name to the data dictionary for the DataFrame row
        data_row = {"Company": company}
        data_row.update(data)
        comparison_data.append(data_row)

    df = pd.DataFrame(comparison_data)

    # Set 'Company' as the index for better presentation
    df.set_index("Company", inplace=True)

    # Reorder columns for better readability if desired
    desired_order = [
        "Industry",
        "Market Cap (B)",
        "1Yr Sales Growth",
        "5Yr Sales Growth",
        "Debt to Equity",
        "PEG Ratio",
    ]
    df = df[desired_order]

    # --- Conditional Formatting for Better Readability ---
    # Apply formatting for percentages and numbers
    # For percentages:
    df["1Yr Sales Growth"] = df["1Yr Sales Growth"].apply(lambda x: f"{x:.2%}")
    df["5Yr Sales Growth"] = df["5Yr Sales Growth"].apply(lambda x: f"{x:.2%}")
    # For numbers (Debt to Equity, PEG Ratio):
    df["Debt to Equity"] = df["Debt to Equity"].apply(lambda x: f"{x:.2f}")
    df["PEG Ratio"] = df["PEG Ratio"].apply(lambda x: f"{x:.2f}")
    # For Market Cap:
    df["Market Cap (B)"] = df["Market Cap (B)"].apply(lambda x: f"${x:,.0f}B")


    st.subheader("Comparison Table")
    st.dataframe(df.transpose(), use_container_width=True) # Transpose for metrics as rows

    st.markdown("---")
    st.subheader("Understanding the Metrics:")
    st.markdown("""
    *   **1Yr Sales Growth:** The percentage increase in a company's revenue over the past 12 months. Higher is generally better for growth.
    *   **5Yr Sales Growth:** The average annual percentage increase in a company's revenue over the past five years. Indicates consistent long-term growth.
    *   **Debt to Equity:** A ratio indicating the proportion of equity and debt used to finance a company's assets. Lower is generally better (less reliance on debt), but varies by industry.
    *   **PEG Ratio (Price/Earnings to Growth Ratio):** A stock's price-to-earnings (P/E) ratio divided by the growth rate of its earnings per share (EPS). A PEG ratio of 1.0 is often considered fair value, while lower values (e.g., < 1) may indicate undervalued stocks and higher values (e.g., > 2) may suggest overvalued stocks relative to their growth.
    """)

    st.info("""
    **Disclaimer:** This application uses mock data for demonstration purposes.
    Real-world financial data varies and should be sourced from reliable providers.
    Financial metrics should always be analyzed in context of industry, company size, and overall economic conditions.
    This is not financial advice.
    """)

else:
    st.info("Please select at least one company to view the comparison.")
