#!/usr/bin/env python3
"""
Quick Debug Script - Check Missing Cost Basis Issues
Run this to identify where the problem is occurring
"""

import pandas as pd
import glob
import os
from datetime import datetime

def debug_missing_symbols():
    """Debug why symbols are missing from cost basis"""
    
    missing_symbols = ['CYBR', 'TAL', 'PD', 'FRSH', 'PAYO', 'HUBS', 'HOOD', 'FROG', 'NVDA', 'TSM']
    partial_symbols = ['LRN', 'ESTC']
    
    print("🔍 DEBUGGING MISSING COST BASIS")
    print("=" * 50)
    
    # Check 1: Find symbols in manual CSV files
    print("\n1️⃣ Checking Manual CSV Files:")
    manual_files = [f for f in glob.glob("*.csv") if 'manual' in f.lower()]
    manual_files.extend(glob.glob("csv_folder/*.csv"))
    
    symbol_found_in = {}
    
    for csv_file in manual_files:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                print(f"\n📄 {csv_file}:")
                print(f"   Shape: {df.shape}")
                
                if 'Symbol' in df.columns:
                    found_symbols = []
                    for symbol in missing_symbols + partial_symbols:
                        if symbol in df['Symbol'].values:
                            found_symbols.append(symbol)
                            if symbol not in symbol_found_in:
                                symbol_found_in[symbol] = []
                            symbol_found_in[symbol].append(csv_file)
                    
                    if found_symbols:
                        print(f"   ✅ Found: {found_symbols}")
                    else:
                        print(f"   ❌ None of the missing symbols found")
                        
                    # Show all symbols for reference
                    all_symbols = sorted(df['Symbol'].unique())
                    print(f"   📊 All symbols in file: {all_symbols}")
                else:
                    print(f"   ⚠️ No 'Symbol' column found")
                    print(f"   📋 Columns: {list(df.columns)}")
                    
            except Exception as e:
                print(f"   ❌ Error reading {csv_file}: {e}")
    
    # Check 2: Summary of found symbols
    print(f"\n2️⃣ Symbol Location Summary:")
    for symbol in missing_symbols + partial_symbols:
        if symbol in symbol_found_in:
            print(f"   ✅ {symbol}: Found in {symbol_found_in[symbol]}")
        else:
            print(f"   ❌ {symbol}: NOT FOUND in any manual CSV")
    
    # Check 3: Check specific examples
    print(f"\n3️⃣ Detailed Check for Key Symbols:")
    
    # Check CYBR specifically
    for csv_file in manual_files:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                if 'Symbol' in df.columns:
                    cybr_rows = df[df['Symbol'] == 'CYBR']
                    if len(cybr_rows) > 0:
                        print(f"\n📊 CYBR transactions in {csv_file}:")
                        for _, row in cybr_rows.iterrows():
                            print(f"   {row.get('Date', 'No Date')} | {row.get('Activity_Type', row.get('Type', 'No Type'))} | {row.get('Quantity', 0)} units @ ${row.get('Price_USD', row.get('Price', 0))}")
            except:
                continue
    
    # Check 4: Date cutoff analysis
    print(f"\n4️⃣ Date Cutoff Analysis:")
    cutoff_date = datetime(2024, 6, 30)
    print(f"   📅 Using cutoff: {cutoff_date.strftime('%Y-%m-%d')}")
    
    for csv_file in manual_files:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                if 'Symbol' in df.columns and 'Date' in df.columns:
                    # Try to parse dates
                    df['parsed_date'] = pd.to_datetime(df['Date'], format='%d.%m.%y', errors='coerce')
                    if df['parsed_date'].isna().all():
                        df['parsed_date'] = pd.to_datetime(df['Date'], errors='coerce')
                    
                    buy_transactions = df[df.get('Activity_Type', df.get('Type', '')) == 'PURCHASED']
                    sell_transactions = df[df.get('Activity_Type', df.get('Type', '')) == 'SOLD']
                    
                    if len(buy_transactions) > 0:
                        buys_before_cutoff = len(buy_transactions[buy_transactions['parsed_date'] <= cutoff_date])
                        buys_after_cutoff = len(buy_transactions[buy_transactions['parsed_date'] > cutoff_date])
                        print(f"   📈 {csv_file}: {buys_before_cutoff} BUYs before cutoff, {buys_after_cutoff} after")
                    
                    if len(sell_transactions) > 0:
                        sells_before_cutoff = len(sell_transactions[sell_transactions['parsed_date'] <= cutoff_date])
                        sells_after_cutoff = len(sell_transactions[sell_transactions['parsed_date'] > cutoff_date])
                        print(f"   📉 {csv_file}: {sells_before_cutoff} SELLs before cutoff, {sells_after_cutoff} after")
                        
            except Exception as e:
                print(f"   ❌ Date parsing error for {csv_file}: {e}")

def check_current_working_directory():
    """Check what files are in current directory"""
    print(f"\n5️⃣ Current Working Directory Check:")
    print(f"   📁 Current directory: {os.getcwd()}")
    
    # List all CSV files
    all_files = glob.glob("*.csv") + glob.glob("csv_folder/*.csv")
    print(f"   📄 CSV files found: {len(all_files)}")
    for f in all_files:
        size_kb = os.path.getsize(f) / 1024 if os.path.exists(f) else 0
        print(f"      • {f} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    check_current_working_directory()
    debug_missing_symbols()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"1. If symbols are found in CSV files but missing from cost basis:")
    print(f"   → Problem is in the CSV loading or hybrid filtering logic")
    print(f"2. If symbols are NOT found in CSV files:")
    print(f"   → Need to add missing transaction data")
    print(f"3. If dates are being filtered incorrectly:")
    print(f"   → Need to fix the hybrid processing cutoff logic")