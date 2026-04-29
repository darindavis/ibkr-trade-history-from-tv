r"""
File: ibkr-trade-history-from-tv.py
Desc: Summarize the IBKR trade history exported from TradingView. Specifically for day trades.
Input: CSV export from TradingView (Downloads\interactive-brokers-trade-history.csv)
Output: Excel file in Downloads folder.
Usage: ibkr-trade-history-from-tv.py
Author: Darin Davis, Copyright 2026
History:
    4/28/26: Initial version
    4/29/26: Refactor aggregations
"""

"""
                    IMPORTS
"""
import pandas as pd
import sys
from pathlib import Path

"""
                    GLOBAL VARIABLES
"""
# full path to current user's Downloads folder
downloads_folder = Path.home() / "Downloads"

"""
                    FUNCTIONS
"""

def usage():
    print("\nUsage:", sys.argv[0])


"""
                    MAIN CODE
"""
if __name__ == "__main__":

    in_file = downloads_folder / "interactive-brokers-trade-history.csv"

    # load the history file into a dataframe
    try:
        if in_file.exists():
            # print(f"File '{in_file}' exists!")
            if in_file.is_file():
                # print("It's a regular file.")
                history = pd.read_csv(in_file)
        else:
            print(f"File '{in_file}' does not exist.")

    except Exception as e:
        print(f"Error: {e}")


    # Convert Time column to datetime
    history['Time'] = pd.to_datetime(history['Time'])

    this_date = '2026-04-28' # date of trades to analyze

    # filter out all dates except for this_date
    daily_history = history[history['Time'].dt.date == pd.to_datetime(this_date).date()].copy()

    ### create columns for aggregation ###

    # create column reflecting negative quantity for sells
    daily_history['net_qty'] = daily_history['Qty'].where(daily_history['Side'] == 'Buy', -daily_history['Qty'])
    # Syntax: keep original value if condition is True; replace it with other value if condition is False
    daily_history['buy_qty'] = daily_history['Qty'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_qty'] = daily_history['Qty'].where(daily_history['Side'] == 'Sell', 0)
    daily_history['buy_amt'] = daily_history['Net Amount'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_amt'] = daily_history['Net Amount'].where(daily_history['Side'] == 'Sell', 0)
    # print(daily_history.info())
    # print(daily_history.head())

    # for each unique symbol, sum the number and value of contracts bought and sold
    net_positions = (daily_history
                    .groupby('Symbol')
                    .agg(
                        net_qty=('net_qty', 'sum'),
                        buy_qty=('buy_qty', 'sum'),
                        sell_qty=('sell_qty', 'sum'),
                        buy_amt=('buy_amt', 'sum'),
                        sell_amt=('sell_amt', 'sum'),
                    )
                    .reset_index())

    # compute PnL for each symbol
    net_positions['PnL'] = net_positions['sell_amt'] - net_positions['buy_amt']

    print(net_positions)

    # compute total PnL for all symbols
    total_pnl = net_positions['PnL'].sum()
    print(f"Total PnL: {total_pnl}")

    # check to ensure all contracts closed
    if (net_positions['net_qty'] != 0).any():
        print("The following symbols have non-zero net quantity:")
        print(net_positions[net_positions['net_qty'] != 0].to_string(index=False))
    else:
        print("All positions are flat (net_qty = 0 for all symbols).")

