#!/usr/bin/env python3
"""
Simple Test Script for Cost Basis Processing
This script bypasses Streamlit and directly tests the CSV processing logic
"""

import pandas as pd
import glob
import os
import json
import tempfile
from datetime import datetime

# Import the processing functions
try:
    from complete_unified_with_aud import (
        apply_hybrid_fifo_processing_with_aud,
        RBAAUDConverter,
        robust_date_parser
    )
    print("✅ Successfully imported processing functions")
    
    # Try to import format_date_for_output, but don't fail if it's not available
    try:
        from complete_unified_with_aud import format_date_for_output
    except ImportError:
        format_date_for_output = None
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

def create_mock_rba_rates():
    """Create mock RBA exchange rate data"""
    print("💱 Creating mock RBA exchange rates...")
    
    # Create temp rates folder
    rates_folder = "temp_rates"
    os.makedirs(rates_folder, exist_ok=True)
    
    # Generate realistic rates
    dates = pd.date_range('2020-01-01', '2025-12-31', freq='D')
    base_rates = {2020: 0.69, 2021: 0.75, 2022: 0.71, 2023: 0.67, 2024: 0.66, 2025: 0.65}
    
    rates_data = []
    for date in dates:
        base_rate = base_rates.get(date.year, 0.67)
        import hashlib
        daily_seed = int(hashlib.md5(date.strftime('%Y-%m-%d').encode()).hexdigest()[:8], 16)
        variation = (daily_seed % 400 - 200) / 10000
        rate = base_rate * (1 + variation)
        rates_data.append({'Date': date.strftime('%Y-%m-%d'), 'AUD_USD_Rate': f"{rate:.4f}"})
    
    # Split into two files
    mid_point = len(rates_data) // 2
    file1 = os.path.join(rates_folder, "FX_2018-2022.csv")
    file2 = os.path.join(rates_folder, "FX_2023-2025.csv")
    
    pd.DataFrame(rates_data[:mid_point]).to_csv(file1, index=False)
    pd.DataFrame(rates_data[mid_point:]).to_csv(file2, index=False)
    
    return rates_folder

def load_csv_files_simple(financial_year="2024-25"):
    """Load CSV files using simple logic"""
    print(f"\n📁 LOADING CSV FILES FOR FY {financial_year}")
    print("=" * 50)
    
    # Find CSV files
    all_csv_files = []
    all_csv_files.extend(glob.glob("*.csv"))
    all_csv_files.extend(glob.glob("csv_folder/*.csv"))
    
    # Filter transaction files
    transaction_files = []
    for csv_file in all_csv_files:
        if 'sales_only' in csv_file.lower():
            continue
        if any(keyword in csv_file.lower() for keyword in ['report', 'output', 'cgt_', 'result']):
            continue
        transaction_files.append(csv_file)
    
    print(f"📄 Found {len(transaction_files)} CSV files:")
    for f in transaction_files:
        print(f"   • {f}")
    
    # Date calculations
    fy_year = int(financial_year.split('-')[0])
    cutoff_date = datetime(fy_year, 6, 30)
    target_fy_start = datetime(fy_year, 7, 1)
    target_fy_end = datetime(fy_year + 1, 6, 30)
    
    print(f"\n📅 Date filtering:")
    print(f"   Cutoff: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"   Target FY: {target_fy_start.strftime('%Y-%m-%d')} to {target_fy_end.strftime('%Y-%m-%d')}")
    
    all_transactions = []
    
    for csv_file in transaction_files:
        print(f"\n🔄 Processing: {os.path.basename(csv_file)}")
        
        try:
            df = pd.read_csv(csv_file)
            print(f"   📊 Raw shape: {df.shape}")
            print(f"   📋 Columns: {list(df.columns)}")
            
            standardized = None
            
            # Format 1: Manual CSV (Date, Activity_Type, Symbol, Quantity, Price_USD)
            if all(col in df.columns for col in ['Date', 'Activity_Type', 'Symbol', 'Quantity', 'Price_USD']):
                print(f"   📝 Format: Manual CSV")
                
                df_copy = df.copy()
                df_copy['Date'] = pd.to_datetime(df_copy['Date'], format='%d.%m.%y', errors='coerce')
                
                sell_transactions = df_copy[df_copy['Activity_Type'] == 'SOLD']
                buy_transactions = df_copy[df_copy['Activity_Type'] == 'PURCHASED']
                
                print(f"   📈 Raw BUYs: {len(buy_transactions)}")
                print(f"   📉 Raw SELLs: {len(sell_transactions)}")
                
                # Hybrid filtering
                sell_before_cutoff = sell_transactions[sell_transactions['Date'] <= cutoff_date]
                sell_in_target_fy = sell_transactions[
                    (sell_transactions['Date'] >= target_fy_start) & 
                    (sell_transactions['Date'] <= target_fy_end)
                ]
                
                print(f"   📉 SELLs before cutoff: {len(sell_before_cutoff)}")
                print(f"   📉 SELLs in target FY: {len(sell_in_target_fy)}")
                
                # Combine
                df_filtered = pd.concat([
                    buy_transactions, 
                    sell_before_cutoff, 
                    sell_in_target_fy
                ], ignore_index=True)
                df_filtered = df_filtered.drop_duplicates()
                
                print(f"   📊 After filtering: {len(df_filtered)} transactions")
                
                if len(df_filtered) > 0:
                    standardized = pd.DataFrame()
                    standardized['Symbol'] = df_filtered['Symbol']
                    standardized['Date'] = df_filtered['Date'].astype(str)
                    standardized['Activity'] = df_filtered['Activity_Type'].map({'PURCHASED': 'PURCHASED', 'SOLD': 'SOLD'})
                    standardized['Quantity'] = pd.to_numeric(df_filtered['Quantity'], errors='coerce').abs()
                    standardized['Price'] = pd.to_numeric(df_filtered['Price_USD'], errors='coerce').abs()
                    standardized['Commission'] = 30.0
                    standardized['Source'] = f'CSV_{os.path.basename(csv_file)}'
                    
                    # DEBUG: Check date conversion for target symbols
                    target_symbols = ['CYBR', 'TAL', 'PD', 'FRSH', 'PAYO', 'HUBS', 'HOOD', 'FROG', 'NVDA', 'TSM']
                    for symbol in target_symbols:
                        symbol_rows = standardized[standardized['Symbol'] == symbol]
                        if len(symbol_rows) > 0:
                            print(f"      🔍 {symbol} date check:")
                            for _, row in symbol_rows.head(2).iterrows():  # Check first 2 rows
                                print(f"         {row['Activity']}: Date='{row['Date']}'")
                                # Test date parsing
                                try:
                                    test_date = robust_date_parser(row['Date'])
                                    print(f"         → Parsed as: {test_date} (year: {test_date.year})")
                                except Exception as e:
                                    print(f"         → Parse error: {e}")
            
            # Format 2: Parsed CSV (Symbol, Trade Date, Type, Quantity, Price (USD))
            elif all(col in df.columns for col in ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)']):
                print(f"   📝 Format: Parsed CSV")
                
                df_copy = df.copy()
                df_copy['Trade Date'] = pd.to_datetime(df_copy['Trade Date'])
                
                sell_transactions = df_copy[df_copy['Type'] == 'SELL']
                buy_transactions = df_copy[df_copy['Type'] == 'BUY']
                
                print(f"   📈 Raw BUYs: {len(buy_transactions)}")
                print(f"   📉 Raw SELLs: {len(sell_transactions)}")
                
                # Hybrid filtering
                sell_before_cutoff = sell_transactions[sell_transactions['Trade Date'] <= cutoff_date]
                sell_in_target_fy = sell_transactions[
                    (sell_transactions['Trade Date'] >= target_fy_start) & 
                    (sell_transactions['Trade Date'] <= target_fy_end)
                ]
                
                print(f"   📉 SELLs before cutoff: {len(sell_before_cutoff)}")
                print(f"   📉 SELLs in target FY: {len(sell_in_target_fy)}")
                
                # Combine
                df_filtered = pd.concat([
                    buy_transactions, 
                    sell_before_cutoff, 
                    sell_in_target_fy
                ], ignore_index=True)
                df_filtered = df_filtered.drop_duplicates()
                
                print(f"   📊 After filtering: {len(df_filtered)} transactions")
                
                if len(df_filtered) > 0:
                    standardized = pd.DataFrame()
                    standardized['Symbol'] = df_filtered['Symbol']
                    standardized['Date'] = df_filtered['Trade Date'].astype(str)
                    standardized['Activity'] = df_filtered['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
                    standardized['Quantity'] = pd.to_numeric(df_filtered['Quantity'], errors='coerce').abs()
                    standardized['Price'] = pd.to_numeric(df_filtered['Price (USD)'], errors='coerce').abs()
                    standardized['Commission'] = pd.to_numeric(df_filtered.get('Commission (USD)', 0), errors='coerce').abs()
                    standardized['Source'] = f'CSV_{os.path.basename(csv_file)}'
                    
                    # DEBUG: Check date conversion for target symbols
                    target_symbols = ['CYBR', 'TAL', 'PD', 'FRSH', 'PAYO', 'HUBS', 'HOOD', 'FROG', 'NVDA', 'TSM']
                    for symbol in target_symbols:
                        symbol_rows = standardized[standardized['Symbol'] == symbol]
                        if len(symbol_rows) > 0:
                            print(f"      🔍 {symbol} date check:")
                            for _, row in symbol_rows.head(2).iterrows():  # Check first 2 rows
                                print(f"         {row['Activity']}: Date='{row['Date']}'")
                                # Test date parsing
                                try:
                                    test_date = robust_date_parser(row['Date'])
                                    print(f"         → Parsed as: {test_date} (year: {test_date.year})")
                                except Exception as e:
                                    print(f"         → Parse error: {e}")
            
            else:
                print(f"   ❌ Unknown format - skipping")
                continue
            
            # Final cleanup and add to collection
            if standardized is not None and len(standardized) > 0:
                # Clean up
                before_cleanup = len(standardized)
                standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
                after_cleanup = len(standardized)
                
                if before_cleanup != after_cleanup:
                    print(f"   ⚠️ Dropped {before_cleanup - after_cleanup} rows with missing data")
                
                # Check for target symbols
                target_symbols = ['CYBR', 'TAL', 'PD', 'FRSH', 'PAYO', 'HUBS', 'HOOD', 'FROG', 'NVDA', 'TSM']
                found_symbols = []
                for symbol in target_symbols:
                    symbol_data = standardized[standardized['Symbol'] == symbol]
                    if len(symbol_data) > 0:
                        buy_count = len(symbol_data[symbol_data['Activity'] == 'PURCHASED'])
                        sell_count = len(symbol_data[symbol_data['Activity'] == 'SOLD'])
                        found_symbols.append(f"{symbol}({buy_count}B,{sell_count}S)")
                
                if found_symbols:
                    print(f"   🎯 Target symbols found: {found_symbols}")
                
                all_transactions.append(standardized)
                print(f"   ✅ Added {len(standardized)} transactions")
            
            else:
                print(f"   ❌ No valid transactions after processing")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            print(f"   🔧 Traceback: {traceback.format_exc()}")
    
    return all_transactions

def test_cost_basis_creation():
    """Test the complete cost basis creation process"""
    print(f"\n🧪 TESTING COST BASIS CREATION")
    print("=" * 50)
    
    # Step 1: Load CSV files
    transactions_list = load_csv_files_simple()
    
    if not transactions_list:
        print("❌ No transactions loaded")
        return
    
    # Step 2: Combine transactions
    combined_df = pd.concat(transactions_list, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], keep='first')
    
    print(f"\n📊 COMBINED DATA SUMMARY:")
    print(f"   Total transactions: {len(combined_df)}")
    print(f"   Unique symbols: {combined_df['Symbol'].nunique()}")
    print(f"   BUY transactions: {len(combined_df[combined_df['Activity'] == 'PURCHASED'])}")
    print(f"   SELL transactions: {len(combined_df[combined_df['Activity'] == 'SOLD'])}")
    
    # Check for target symbols in combined data
    target_symbols = ['CYBR', 'TAL', 'PD', 'FRSH', 'PAYO', 'HUBS', 'HOOD', 'FROG', 'NVDA', 'TSM']
    print(f"\n🎯 TARGET SYMBOLS CHECK:")
    for symbol in target_symbols:
        symbol_data = combined_df[combined_df['Symbol'] == symbol]
        if len(symbol_data) > 0:
            buy_count = len(symbol_data[symbol_data['Activity'] == 'PURCHASED'])
            sell_count = len(symbol_data[symbol_data['Activity'] == 'SOLD'])
            print(f"   ✅ {symbol}: {buy_count} BUYs, {sell_count} SELLs")
            
            # Show first purchase example WITH RAW DATE
            purchases = symbol_data[symbol_data['Activity'] == 'PURCHASED']
            if len(purchases) > 0:
                first_purchase = purchases.iloc[0]
                print(f"      Example: {first_purchase['Quantity']} @ ${first_purchase['Price']} on '{first_purchase['Date']}' from {first_purchase['Source']}")
                
                # Test date parsing on this specific date
                try:
                    parsed_date = robust_date_parser(first_purchase['Date'])
                    print(f"      Date parsing: '{first_purchase['Date']}' → {parsed_date} (year: {parsed_date.year})")
                except Exception as e:
                    print(f"      Date parsing ERROR: {e}")
        else:
            print(f"   ❌ {symbol}: NOT FOUND")
    
    # Step 3: Set up AUD converter
    rates_folder = create_mock_rba_rates()
    
    try:
        aud_converter = RBAAUDConverter()
        rba_files = [
            os.path.join(rates_folder, "FX_2018-2022.csv"),
            os.path.join(rates_folder, "FX_2023-2025.csv")
        ]
        aud_converter.load_rba_csv_files(rba_files)
        
        if aud_converter.exchange_rates:
            print(f"\n✅ AUD converter ready with {len(aud_converter.exchange_rates)} rates")
        else:
            print(f"\n❌ AUD converter failed to load rates")
            return
            
    except Exception as e:
        print(f"\n❌ AUD converter error: {e}")
        return
    
    # Step 4: Apply FIFO processing (NO cutoff date to avoid filtering)
    print(f"\n🔄 APPLYING FIFO PROCESSING...")
    
    # ENHANCED DEBUG: Check dates before FIFO processing
    print(f"\n📅 DATE QUALITY CHECK:")
    target_symbols = ['CYBR', 'TAL', 'PD', 'FRSH', 'PAYO', 'HUBS', 'HOOD', 'FROG', 'NVDA', 'TSM']
    
    for symbol in target_symbols:
        symbol_data = combined_df[combined_df['Symbol'] == symbol]
        if len(symbol_data) > 0:
            print(f"   📊 {symbol}:")
            for _, row in symbol_data.iterrows():
                date_str = row['Date']
                try:
                    parsed_date = robust_date_parser(date_str)
                    if parsed_date.year > 1900:
                        print(f"      ✅ {row['Activity']} on {date_str} → {parsed_date.strftime('%Y-%m-%d')}")
                    else:
                        print(f"      ❌ {row['Activity']} on {date_str} → FAILED PARSING (year {parsed_date.year})")
                except Exception as e:
                    print(f"      ❌ {row['Activity']} on {date_str} → ERROR: {e}")
    
    try:
        cost_basis_dict, fifo_log, conversion_errors = apply_hybrid_fifo_processing_with_aud(
            combined_df, aud_converter, None  # No cutoff filtering
        )
        
        print(f"\n📊 FIFO PROCESSING RESULTS:")
        print(f"   Cost basis symbols: {len(cost_basis_dict)}")
        print(f"   Conversion errors: {len(conversion_errors)}")
        
        # Check for target symbols in cost basis
        print(f"\n🎯 COST BASIS CHECK FOR TARGET SYMBOLS:")
        for symbol in target_symbols:
            if symbol in cost_basis_dict:
                records = cost_basis_dict[symbol]
                total_units = sum(r['units'] for r in records)
                total_cost_aud = sum(r['units'] * r.get('price_aud', r['price']) + r.get('commission_aud', r['commission']) for r in records)
                print(f"   ✅ {symbol}: {len(records)} records, {total_units:.2f} units, ${total_cost_aud:.2f} AUD")
                
                # Show first record as example
                if records:
                    first_record = records[0]
                    print(f"      Example: {first_record['units']} units @ ${first_record.get('price_aud', first_record['price']):.2f} AUD from {first_record['date']}")
            else:
                print(f"   ❌ {symbol}: NO COST BASIS CREATED")
        
        # Step 5: Show any conversion errors
        if conversion_errors:
            print(f"\n⚠️ CONVERSION ERRORS:")
            for error in conversion_errors[:10]:  # Show more errors
                print(f"   • {error}")
        
        # ADDITIONAL DEBUG: Check what data actually went into FIFO for missing symbols
        print(f"\n🔧 DETAILED DEBUG FOR MISSING SYMBOLS:")
        for symbol in target_symbols:
            if symbol not in cost_basis_dict:
                symbol_data = combined_df[combined_df['Symbol'] == symbol]
                if len(symbol_data) > 0:
                    purchases = symbol_data[symbol_data['Activity'] == 'PURCHASED']
                    print(f"   🔍 {symbol} debug:")
                    print(f"      Total rows in combined_df: {len(symbol_data)}")
                    print(f"      Purchase rows: {len(purchases)}")
                    
                    if len(purchases) > 0:
                        for idx, purchase in purchases.iterrows():
                            print(f"         Purchase {idx}: {purchase['Quantity']} @ ${purchase['Price']} on '{purchase['Date']}'")
                            
                            # Try the exact same date parsing that FIFO uses
                            try:
                                parsed_date = robust_date_parser(purchase['Date'])
                                print(f"         → robust_date_parser: {parsed_date}")
                                
                                try:
                                    formatted_date = format_date_for_output(purchase['Date'])
                                    print(f"         → format_date_for_output: {formatted_date}")
                                except:
                                    print(f"         → format_date_for_output: function not available")
                                
                                if parsed_date.year <= 1900:
                                    print(f"         ❌ PROBLEM: Invalid year {parsed_date.year}")
                                
                            except Exception as e:
                                print(f"         ❌ Date parsing failed: {e}")
                    else:
                        print(f"      ❌ No purchase records found!")
                else:
                    print(f"   ❌ {symbol}: No data in combined_df")
        
        # Clean up temp files
        import shutil
        shutil.rmtree(rates_folder, ignore_errors=True)
        
        print(f"\n🎉 TEST COMPLETE!")
        return cost_basis_dict
        
    except Exception as e:
        print(f"\n❌ FIFO processing error: {e}")
        import traceback
        print(f"🔧 Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    print("🧪 STARTING COST BASIS TEST")
    print("This script will test the CSV loading and cost basis creation process")
    print("without Streamlit complexity")
    print()
    
    cost_basis_dict = test_cost_basis_creation()
    
    if cost_basis_dict:
        print(f"\n✅ SUCCESS: Cost basis created for {len(cost_basis_dict)} symbols")
        print(f"Symbols: {sorted(cost_basis_dict.keys())}")
    else:
        print(f"\n❌ FAILED: No cost basis created")
        print(f"Check the debug output above to see where the process failed")