import yfinance as yf

def fetch_yfinance_data(ticker):
    try:
        # Get Ticker object
        stock = yf.Ticker(ticker)

        # Get financial statements (annual)
        income_statement = stock.financials
        balance_sheet = stock.balance_sheet

        # --- Extract/Calculate 1Yr & 5Yr Sales Growth ---
        # This is tricky with yfinance as it gives current/past year's revenue,
        # you'd need to fetch multiple years and calculate growth.
        # Example for 1Yr:
        # revenues = income_statement.loc['Total Revenue']
        # rev_current = revenues.iloc[0]
        # rev_prev = revenues.iloc[1]
        # sales_growth_1yr = (rev_current - rev_prev) / rev_prev if rev_prev != 0 else 0

        # --- Debt to Equity ---
        # total_debt = balance_sheet.loc['Total Debt'].iloc[0]
        # total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0]
        # debt_to_equity = total_debt / total_equity if total_equity != 0 else 0

        # --- PEG Ratio ---
        # yfinance *does not* provide direct PEG or future EPS growth.
        # You'd need a different API for this, or manually estimate.

        # Return a dictionary (partially filled for demonstration)
        return {
            "1Yr Sales Growth": sales_growth_1yr if 'sales_growth_1yr' in locals() else None,
            "5Yr Sales Growth": None, # Needs more complex calculation
            "Debt to Equity": debt_to_equity if 'debt_to_equity' in locals() else None,
            "PEG Ratio": None, # Not available from yfinance directly
            "Market Cap (B)": stock.info.get('marketCap') / 1_000_000_000 if stock.info.get('marketCap') else None,
            "Industry": stock.info.get('industry'),
        }
    except Exception as e:
        st.warning(f"Could not fetch data for {ticker}: {e}")
        return None
