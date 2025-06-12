import yfinance as yf
import sys
import time # Import time for adding delays

def calculate_peg_ratio(price, eps, growth_rate):
    """
    Calculates the PEG (Price/Earnings to Growth) ratio.

    Args:
        price (float): The current stock price.
        eps (float): The Earnings Per Share (usually trailing 12 months or forward).
        growth_rate (float): The annual EPS growth rate as a percentage (e.g., 15 for 15%).
                             Note: This function expects it as a whole number, not a decimal.

    Returns:
        float: The calculated PEG ratio, or None if calculation is not possible.
    """
    if price <= 0:
        return None
    if eps <= 0:
        return None
    if growth_rate <= 0:
        return None

    try:
        pe_ratio = price / eps
        peg_ratio = pe_ratio / growth_rate
        return peg_ratio
    except ZeroDivisionError:
        return None
    except Exception as e:
        return None

def get_stock_data(ticker_symbol):
    """
    Fetches stock data (price, EPS, growth rate) using yfinance.
    Includes enhanced debugging output to identify missing data points.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT').

    Returns:
        tuple: (company_name, price, eps, growth_rate_percent) or (None, None, None, None) if data is not found/invalid.
    """
    ticker = yf.Ticker(ticker_symbol)
    
    # Add a small delay to avoid potential rate limiting, especially when fetching multiple tickers quickly.
    time.sleep(0.5) # Wait for 0.5 seconds between requests

    try:
        info = ticker.info

        # --- DEBUGGING START ---
        # Check if the info dictionary is populated at all
        if not info or len(info) < 50: # A rough heuristic for sufficient data (info dict usually has many keys)
            print(f"DEBUG: Info dictionary for '{ticker_symbol}' is empty or incomplete (length: {len(info) if info else 0}). This is a major issue.", file=sys.stderr)
            return None, None, None, None

        company_name = info.get('longName', ticker_symbol)
        
        price = info.get('currentPrice')
        if price is None:
             price = info.get('regularMarketPrice') # Fallback for real-time price
             if price is None:
                 print(f"DEBUG: For {ticker_symbol}, 'currentPrice' and 'regularMarketPrice' are both None. Price is missing.", file=sys.stderr)

        eps = info.get('trailingEps') 
        if eps is None:
            eps = info.get('forwardEps') # Try forwardEps as a fallback
            if eps is None:
                print(f"DEBUG: For {ticker_symbol}, 'trailingEps' and 'forwardEps' are both None. EPS is missing.", file=sys.stderr)

        growth_rate_decimal = info.get('nextFiveYearsEarningsGrowth') 
        if growth_rate_decimal is None:
            print(f"DEBUG: For {ticker_symbol}, 'nextFiveYearsEarningsGrowth' is None. This is often the reason PEG fails.", file=sys.stderr)

        growth_rate_percent = None
        if growth_rate_decimal is not None:
            growth_rate_percent = growth_rate_decimal * 100 # Convert 0.15 to 15

        # Final check before returning None for any missing critical piece
        if price is None:
            print(f"DEBUG: Final check for {ticker_symbol}: Price is definitively None.", file=sys.stderr)
            return company_name, None, None, None
        if eps is None:
            print(f"DEBUG: Final check for {ticker_symbol}: EPS is definitively None.", file=sys.stderr)
            return company_name, None, None, None
        if growth_rate_percent is None:
            print(f"DEBUG: Final check for {ticker_symbol}: Growth Rate is definitively None.", file=sys.stderr)
            return company_name, None, None, None # Crucial for PEG calculation

        # --- DEBUGGING END ---
        
        return company_name, price, eps, growth_rate_percent

    except Exception as e:
        print(f"ERROR: An exception occurred while fetching data for '{ticker_symbol}': {e}", file=sys.stderr)
        print("This could indicate a network issue or a breaking change in yfinance/Yahoo Finance structure.", file=sys.stderr)
        return None, None, None, None

def main():
    """
    Main function to run the PEG ratio calculator for top S&P 500 companies.
    """
    print("--- PEG Ratio Calculator for Top 10 S&P 500 Companies ---")
    print("Fetching data from Yahoo Finance using 'yfinance'.")
    print("Note: The 'Next 5 Years Earnings Growth' estimate is crucial for PEG and may not be available for all stocks.")
    print("If data is missing, check your internet connection and the yfinance library's status.")
    print("-" * 70)

    top_sp500_tickers = [
        "MSFT",  # Microsoft
        "NVDA",  # Nvidia
        "AAPL",  # Apple Inc.
        "AMZN",  # Amazon
        "GOOGL", # Alphabet Inc. (Class A)
        "GOOG",  # Alphabet Inc. (Class C)
        "META",  # Meta Platforms
        "AVGO",  # Broadcom
        "BRK.B", # Berkshire Hathaway
        "TSLA",  # Tesla, Inc.
    ]

    results = []

    for ticker_symbol in top_sp500_tickers:
        print(f"Processing {ticker_symbol}...", end=' ')
        company_name, price, eps, growth_rate = get_stock_data(ticker_symbol)

        if price is None or eps is None or growth_rate is None:
            results.append({
                "Ticker": ticker_symbol,
                "Company Name": company_name if company_name else "N/A",
                "Status": "Data Missing/Invalid",
                "PEG Ratio": "N/A",
                "P/E Ratio": "N/A",
                "Growth Rate": "N/A"
            })
            print("Skipped (Data Missing)")
            continue

        peg_ratio = calculate_peg_ratio(price, eps, growth_rate)
        pe_ratio = price / eps if eps > 0 else "N/A" # Calculate P/E even if PEG fails due to growth rate

        results.append({
            "Ticker": ticker_symbol,
            "Company Name": company_name,
            "Status": "Success",
            "PEG Ratio": f"{peg_ratio:.2f}" if peg_ratio is not None else "Cannot Calculate",
            "P/E Ratio": f"{pe_ratio:.2f}" if pe_ratio != "N/A" else "N/A",
            "Growth Rate": f"{growth_rate:.2f}%"
        })
        print("Done")

    print("\n" + "=" * 70)
    print("--- Summary of PEG Ratios for Top S&P 500 Companies ---")
    print("=" * 70)

    print(f"{'Ticker':<8} | {'Company Name':<25} | {'P/E Ratio':<12} | {'Growth Rate':<15} | {'PEG Ratio':<12} | {'Status':<15}")
    print("-" * 105)
    for result in results:
        print(f"{result['Ticker']:<8} | {result['Company Name']:<25} | {result['P/E Ratio']:<12} | {result['Growth Rate']:<15} | {result['PEG Ratio']:<12} | {result['Status']:<15}")

    print("\nInterpretation:")
    print("  - PEG < 1: Potentially undervalued relative to growth.")
    print("  - PEG = 1: Fairly valued.")
    print("  - PEG > 1: Potentially overvalued relative to growth.")
    print("  - 'Cannot Calculate' may be due to negative EPS or negative/zero growth rate.")
    print("\n--- End of Report ---")

if __name__ == "__main__":
    main()
