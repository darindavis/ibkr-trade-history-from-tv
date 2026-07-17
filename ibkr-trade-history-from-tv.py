r"""
File: ibkr-trade-history-from-tv.py
Desc: Summarize the IBKR trade history exported from TradingView. Specifically for day trades.
Input: CSV export from TradingView (Downloads\interactive-brokers-trade-history.csv)
Output: Excel file in Downloads folder.
Usage: ibkr-trade-history-from-tv.py
Author: Darin Davis, Copyright 2026
History:
    4/28/26: Initial version
    4/29/26: Refactor aggregations, add date as command line arg
    5/1/26: Fix pandas text wrapping
    5/4/26: Add risk and % return; add save results to CSV
    5/7/26: Add % return for each symbol
    5/12/26: Sort history by increasing 'Time'.
    5/18/26: TV changed the column headers 'Qty' to 'Quantity' and 'Net Amount' to 'Net amount'.
            Report total net P&L for closed positions only.
    7/7/26: Add fees to PnL calculation.
    7/14/26: Fix formatting for total PnL.
    7/16/26: Fix formatting for total PnL (again). Add tip to usage() about distinguishing trades on the same symbol.
"""

"""
                    IMPORTS
"""
import pandas as pd
import sys
from pathlib import Path
from datetime import date, datetime

"""
                    GLOBAL VARIABLES
"""

downloads_folder = Path.home() / "Downloads" # full path to current user's Downloads folder


"""
                    FUNCTIONS
"""

def usage():
    script_name = Path(sys.argv[0]).name
    print("\nUsage:", script_name, "[YYYY-MM-DD] (default = today)")
    tip = r"""
Tip: If there are multiple trades on the same option contract, edit the exported CSV file and add an
integer to the end of the symbol to make it unique. For example, if there are two trades on "SPY 450 call",
change the second one to "SPY 450 call 2". This will allow the script to correctly aggregate the fills
for each unique trade.
"""
    print(tip)

def debug(msg=""):
    debug_flag = True

    if debug_flag:
        line = sys._getframe(1).f_lineno # 1 = caller's line number
        # print(f"DEBUG [{__file__}:{line}] {msg}")
        print(f"DEBUG [{line}] {msg}")


"""
                    MAIN CODE
"""
def main():

    # Force pandas to show all columns and allow wrapping
    pd.set_option('display.max_columns', None)      # Show every column
    pd.set_option('display.width', None)            # Auto-detect terminal width (or set a large number like 2000)
    pd.set_option('display.max_colwidth', None)     # Don't truncate individual cell content
    pd.set_option('display.expand_frame_repr', True)  # wrap text

    this_date = date.today().strftime('%Y-%m-%d') # default date of trades to analyze

    if len(sys.argv) > 1: # check if user provided date
        this_date = sys.argv[1] # first argument after script name
        try:
            test_date = datetime.strptime(this_date, '%Y-%m-%d')
        except:
            print(f"Date must be in format YYYY-MM-DD not {this_date}")
            usage()
            sys.exit(1)


    # define the filename of the trade history file
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


    print(f"\nTrade history for {this_date}")

    # Convert Time column to datetime and sort increasing
    history['Time'] = pd.to_datetime(history['Time'])
    history = history.sort_values(by='Time', ascending=True)

    # filter out all dates except for this_date
    daily_history = history[history['Time'].dt.date == pd.to_datetime(this_date).date()].copy()

    if daily_history.empty:
        print("No trades on this date")
        exit(1)

    # Make Time the leftmost column
    daily_history = daily_history[['Time'] + [c for c in daily_history.columns if c != 'Time']]

    ### create columns for aggregation ###

    # create column reflecting negative quantity for sells
    daily_history['net_qty'] = daily_history['Quantity'].where(daily_history['Side'] == 'Buy', -daily_history['Quantity'])
    # Syntax: keep original value if condition is True; replace it with other value if condition is False
    daily_history['buy_qty'] = daily_history['Quantity'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_qty'] = daily_history['Quantity'].where(daily_history['Side'] == 'Sell', 0)
    daily_history['buy_amt'] = daily_history['Net amount'].where(daily_history['Side'] == 'Buy', 0)
    daily_history['sell_amt'] = daily_history['Net amount'].where(daily_history['Side'] == 'Sell', 0)
    
    # print(daily_history.info())
    print(daily_history.to_string(index=False))

    # for each unique symbol, sum the number and value of contracts bought and sold
    net_positions = (daily_history
                    .groupby('Symbol')
                    .agg(
                        net_qty=('net_qty', 'sum'),
                        buy_qty=('buy_qty', 'sum'),
                        sell_qty=('sell_qty', 'sum'),
                        buy_amt=('buy_amt', 'sum'),
                        sell_amt=('sell_amt', 'sum'),
                        fees=('Commission', 'sum'),
                    )
                    .reset_index())

    # compute PnL for each symbol
    net_positions['PnL'] = net_positions['sell_amt'] - net_positions['buy_amt'] - net_positions['fees']
    net_positions['ReturnPcnt'] = net_positions['PnL'] / net_positions['buy_amt']

    print("\nNet positions:")
    print(net_positions.to_string(
        index=False,
        formatters={
            'ReturnPcnt': lambda x: f'{x*100:.1f}%' # format as a percentage
        }
    ))

    # compute total PnL for all symbols with closed positions
    total_pnl = net_positions.query('net_qty == 0')['PnL'].sum()
    print(f"\nTotal PnL for closed positions: {total_pnl:.2f}")

    # compute total risk for all symbols
    total_risk = net_positions['buy_amt'].sum()
    print(f"Total Risk: {total_risk}")

    # compute % return
    pcnt_return = total_pnl / total_risk
    print(f"Percent Return: {pcnt_return:.1%}")

    # check to ensure all contracts closed
    if (net_positions['net_qty'] != 0).any():
        print("\nThe following symbols have open positions (non-zero net quantity):")
        print(net_positions[net_positions['net_qty'] != 0].to_string(index=False))
    else:
        print("\nAll positions are flat (net_qty = 0 for all symbols).")


    # format as a percentage
    net_positions['ReturnPcnt'] = net_positions['ReturnPcnt'].apply(lambda x: f'{x*100:.1f}%')

   # save results to CSV
    out_file = downloads_folder / f"{this_date} interactive-brokers-trade-history-rpt.csv"
 
    with open(out_file, "w", encoding='utf-8') as f:
        f.write(f"IBKR trades for {this_date}\n")
        daily_history.to_csv(f, index=False, sep=',', lineterminator='\n')

        f.write(f"\nNet positions\n")
        net_positions.to_csv(f, index=False, sep=',', lineterminator='\n')
        f.write(f"\nTotal PnL:,{total_pnl}\n")
        f.write(f"Total Risk:,{total_risk}\n")
        f.write(f"Percent Return:,{pcnt_return:.1%}\n")


if __name__ == "__main__":
    main()