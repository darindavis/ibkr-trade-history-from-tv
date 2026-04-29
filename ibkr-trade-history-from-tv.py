r"""
File: ibkr-trade-history-from-tv.py
Desc: Summarize the IBKR trade history exported from TradingView. Specifically for day trades.
Input: CSV export from TradingView (Downloads\interactive-brokers-trade-history.csv)
Output: Excel file in Downloads folder.
Usage: ibkr-trade-history-from-tv.py
Author: Darin Davis, Copyright 2026
History:
    4/28/26: Initial version
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

    # create column reflecting negative quantity for sells
    daily_history['net_qty'] = daily_history['Qty'].where(daily_history['Side'] == 'Buy', -daily_history['Qty'])
    # Syntax: keep original value if condition is True; replace it with other value if condition is False
    # print(history.info())
    # print(daily_history.head())

    # for each unique symbol, sum the number of contracts bought and sold
    net_positions = (daily_history
                    .groupby('Symbol')['net_qty']
                    # Group the DataFrame by the Symbol column; creates a net_qty Series object (not a DataFrame)
                    .sum()  # For each group (each unique Symbol), add all the values in net_qty
                            # Result at this point is a pandas Series, with Index = Symbol, Values = Sum of net_qty
                    .reset_index())
                            # Convert result from Series back into DataFrame. Moves Symbol from the index into a regular column.

    # calc number of contracts bought per ticker
    buy_counts = (daily_history[daily_history['Side'] == 'Buy'] # include only buys
                .groupby('Symbol')['Qty'] # select only the Qty column, changing object from DataFrameGroupBy to SeriesGroupBy
                .sum() # sum the Qty series
                .reset_index(name='buyCount'))

    # add buy_counts as a column to netPostions
    net_positions = net_positions.merge(buy_counts, on='Symbol', how='left') # left join

    # calc number of contracts sold per ticker
    sell_counts = (daily_history[daily_history['Side'] == 'Sell'] # include only sells
                .groupby('Symbol')['Qty'] # select only the Qty column, changing object from DataFrameGroupBy to SeriesGroupBy
                .sum() # sum the Qty series
                .reset_index(name='sellCount'))

    # add sell_counts as a column to netPostions
    net_positions = net_positions.merge(sell_counts, on='Symbol', how='left') # left join

    # summarize the net amounts bought per ticker
    net_amount_buy = (daily_history[daily_history['Side'] == 'Buy'] # include only buys
                .groupby('Symbol')['Net Amount'] # select only the Net Amount column, changing object from DataFrameGroupBy to SeriesGroupBy
                .sum() # sum the Net Amount series
                .reset_index(name='net_amount_buy'))

    # add net_amount_buy as a column to netPostions
    net_positions = net_positions.merge(net_amount_buy, on='Symbol', how='left') # left join

    # summarize the net amounts sold per ticker
    net_amount_sell = (daily_history[daily_history['Side'] == 'Sell'] # include only sells
                .groupby('Symbol')['Net Amount'] # select only the Net Amount column, changing object from DataFrameGroupBy to SeriesGroupBy
                .sum() # sum the Net Amount series
                .reset_index(name='net_amount_sell'))

    # add net_amount_sell as a column to netPostions
    net_positions = net_positions.merge(net_amount_sell, on='Symbol', how='left') # left join

    net_positions['PnL'] = net_positions['net_amount_sell'] - net_positions['net_amount_buy']

    print(net_positions)
    
    total_pnl = net_positions['PnL'].sum()
    print(f"Total PnL: {total_pnl}")

    # check to ensure all contracts closed
    if (net_positions['net_qty'] != 0).any():
        print("The following symbols have non-zero net quantity:")
        print(net_positions[net_positions['net_qty'] != 0].to_string(index=False))
    else:
        print("All positions are flat (net_qty = 0 for all symbols).")

