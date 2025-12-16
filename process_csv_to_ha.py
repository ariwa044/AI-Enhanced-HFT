#!/usr/bin/env python3
"""
BTCUSD M15 CSV to Heiken Ashi Processor
Converts raw OHLC data to Heiken Ashi format compatible with the ensemble system

Usage:
    python process_csv_to_ha.py [input_file] [output_file]
    
Default:
    python process_csv_to_ha.py BTCUSD_M15.csv BTCUSD_15m_HA_data.csv

Input CSV Format:
    DATE, TIME, OPEN, HIGH, LOW, CLOSE, TICKVOL, VOL, SPREAD

Output CSV Format:
    Time, HA_Open, HA_High, HA_Low, HA_Close, Volume
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime

def calculate_heiken_ashi(df):
    """
    Calculate Heiken Ashi values from OHLC data
    
    Heiken Ashi formulas:
    - HA_Close = (Open + High + Low + Close) / 4
    - HA_Open = (Previous HA_Open + Previous HA_Close) / 2
    - HA_High = Max(High, HA_Open, HA_Close)
    - HA_Low = Min(Low, HA_Open, HA_Close)
    """
    
    df = df.copy()
    df_len = len(df)
    
    # Initialize arrays
    ha_open = np.zeros(df_len)
    ha_close = np.zeros(df_len)
    ha_high = np.zeros(df_len)
    ha_low = np.zeros(df_len)
    
    # Calculate HA_Close for all bars
    ha_close = (df['OPEN'].values + df['HIGH'].values + df['LOW'].values + df['CLOSE'].values) / 4
    
    # Calculate HA_Open
    # First bar: average of open and close
    ha_open[0] = (df['OPEN'].iloc[0] + df['CLOSE'].iloc[0]) / 2
    
    # Subsequent bars: average of previous HA_Open and HA_Close
    for i in range(1, df_len):
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
    
    # Calculate HA_High and HA_Low
    for i in range(df_len):
        ha_high[i] = max(df['HIGH'].iloc[i], ha_open[i], ha_close[i])
        ha_low[i] = min(df['LOW'].iloc[i], ha_open[i], ha_close[i])
    
    return ha_open, ha_high, ha_low, ha_close

def process_btcusd_csv(input_file, output_file):
    """
    Process BTCUSD M15 CSV to Heiken Ashi format
    """
    
    print(f"\n{'='*70}")
    print("BTCUSD M15 to Heiken Ashi Converter")
    print(f"{'='*70}\n")
    
    # Load CSV (try different delimiters)
    print(f"[1/5] Loading CSV: {input_file}")
    try:
        # Try tab-delimited first
        df = pd.read_csv(input_file, sep='\t', skipinitialspace=True)
        print(f"  ✓ Loaded {len(df)} rows (tab-delimited)")
    except:
        try:
            # Fall back to comma-delimited
            df = pd.read_csv(input_file, sep=',', skipinitialspace=True)
            print(f"  ✓ Loaded {len(df)} rows (comma-delimited)")
        except FileNotFoundError:
            print(f"  ✗ File not found: {input_file}")
            sys.exit(1)
        except Exception as e:
            print(f"  ✗ Error loading CSV: {e}")
            sys.exit(1)
    
    # Verify columns
    print(f"\n[2/5] Verifying columns")
    required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOL']
    
    # Clean column names: remove angle brackets and whitespace
    df.columns = df.columns.str.replace('<', '').str.replace('>', '').str.strip()
    df_cols = df.columns.str.upper()
    
    has_required = True
    for col in required_cols:
        if col not in df_cols:
            print(f"  ✗ Missing column: {col}")
            has_required = False
    
    if not has_required:
        print(f"\n  Available columns: {df.columns.tolist()}")
        sys.exit(1)
    
    # Normalize column names (uppercase)
    df.columns = df.columns.str.upper()
    print(f"  ✓ Columns verified: {df.columns.tolist()}")
    
    # Create datetime column
    print(f"\n[3/5] Creating datetime column")
    try:
        if 'DATE' in df.columns and 'TIME' in df.columns:
            # Combine DATE and TIME
            df['DateTime'] = pd.to_datetime(df['DATE'].astype(str) + ' ' + df['TIME'].astype(str))
        elif 'DATETIME' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DATETIME'])
        else:
            # Fallback: use index
            print("  ⚠ No DATE/TIME columns found, using index")
            df['DateTime'] = pd.date_range(start='2024-01-01', periods=len(df), freq='15min')
        
        print(f"  ✓ DateTime range: {df['DateTime'].min()} to {df['DateTime'].max()}")
    except Exception as e:
        print(f"  ⚠ Error creating datetime: {e}")
        df['DateTime'] = pd.date_range(start='2024-01-01', periods=len(df), freq='15min')
    
    # Calculate Heiken Ashi
    print(f"\n[4/5] Calculating Heiken Ashi values")
    ha_open, ha_high, ha_low, ha_close = calculate_heiken_ashi(df)
    print(f"  ✓ HA calculation complete")
    
    # Create output dataframe
    output_df = pd.DataFrame({
        'Time': df['DateTime'].values,
        'HA_Open': ha_open,
        'HA_High': ha_high,
        'HA_Low': ha_low,
        'HA_Close': ha_close,
        'Volume': df['VOL'].values
    })
    
    # Save CSV
    print(f"\n[5/5] Saving output: {output_file}")
    try:
        output_df.to_csv(output_file, index=False)
        print(f"  ✓ Saved {len(output_df)} rows")
    except Exception as e:
        print(f"  ✗ Error saving CSV: {e}")
        sys.exit(1)
    
    # Display summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Input file:     {input_file}")
    print(f"Output file:    {output_file}")
    print(f"Rows processed: {len(output_df)}")
    print(f"\nOutput columns:")
    print(f"  {output_df.columns.tolist()}")
    print(f"\nFirst 5 rows:")
    print(output_df.head())
    print(f"\nLast 5 rows:")
    print(output_df.tail())
    print(f"\nHeiken Ashi Statistics:")
    print(f"  HA_Open  - Min: {output_df['HA_Open'].min():.2f}, Max: {output_df['HA_Open'].max():.2f}")
    print(f"  HA_High  - Min: {output_df['HA_High'].min():.2f}, Max: {output_df['HA_High'].max():.2f}")
    print(f"  HA_Low   - Min: {output_df['HA_Low'].min():.2f}, Max: {output_df['HA_Low'].max():.2f}")
    print(f"  HA_Close - Min: {output_df['HA_Close'].min():.2f}, Max: {output_df['HA_Close'].max():.2f}")
    print(f"\nVolume Statistics:")
    print(f"  Min: {output_df['Volume'].min():.0f}")
    print(f"  Max: {output_df['Volume'].max():.0f}")
    print(f"  Mean: {output_df['Volume'].mean():.0f}")
    print(f"\n✅ File processing complete!")
    print(f"{'='*70}\n")
    
    return output_df

if __name__ == "__main__":
    # Get input/output filenames from arguments or use defaults
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        input_file = "BTCUSD_M15.csv"
    
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = "BTCUSD_15m_HA_data.csv"
    
    # Process
    result_df = process_btcusd_csv(input_file, output_file)
