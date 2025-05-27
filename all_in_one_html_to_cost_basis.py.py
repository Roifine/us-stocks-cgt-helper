#!/usr/bin/env python3
"""
All-in-One Script: HTML Trading Statements → Cost Basis Dictionary

This single script contains everything you need:
1. HTML parsing functions
2. Cost basis dictionary creation
3. Automatic file discovery
4. Complete workflow

Just save this file and run: python all_in_one_html_to_cost_basis.py
"""

import pandas as pd
import re
import json
import os
import glob
from datetime import datetime
from bs4 import BeautifulSoup

# For Excel writing - install with: pip install openpyxl
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    openpyxl = None

# For HTML parsing - install with: pip install beautifulsoup4
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

# ============================================================================
# HTML PARSING FUNCTIONS (from html_to_csv.py)
# ============================================================================

def clean_text(text):
    """Clean and normalize text content."""
    if not text:
        return ""
    # Remove HTML tags, extra whitespace, and special characters
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(',', '')  # Remove commas from numbers
    return text

def parse_number(text):
    """Parse numeric values from text, handling negative signs and commas."""
    if not text:
        return 0
    
    clean_text_val = clean_text(text)
    
    # Handle negative values
    is_negative = clean_text_val.startswith('-') or '(' in clean_text_val
    
    # Extract numeric part
    numeric_part = re.sub(r'[^\d.]', '', clean_text_val)
    
    try:
        value = float(numeric_part) if numeric_part else 0
        return -value if is_negative else value
    except ValueError:
        return 0

def parse_trade_date(date_text):
    """Parse trade date from Interactive Brokers format."""
    if not date_text:
        return None
    
    # Extract date part (before comma if time is included)
    date_part = date_text.split(',')[0].strip()
    
    try:
        # Try to parse the date (format: YYYY-MM-DD)
        return datetime.strptime(date_part, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Alternative format handling
            return datetime.strptime(date_part, '%m/%d/%Y').strftime('%Y-%m-%d')
        except ValueError:
            print(f"Could not parse date: {date_text}")
            return date_text

def parse_ib_html_to_csv(html_file_path, output_csv_path=None):
    """
    Parse Interactive Brokers HTML statement to CSV format.
    
    Args:
        html_file_path (str): Path to the HTML file
        output_csv_path (str): Path for output CSV file (optional)
    
    Returns:
        pandas.DataFrame: Parsed transaction data
    """
    
    print(f"Parsing HTML file: {html_file_path}")
    
    # Read HTML file
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        return None
    
    # Extract transactions using regex (more reliable than BeautifulSoup for this format)
    transactions = []
    
    # Find all summary rows (consolidated transactions)
    summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
    summary_matches = re.findall(summary_row_pattern, html_content)
    
    print(f"Found {len(summary_matches)} summary transactions")
    
    for i, row_html in enumerate(summary_matches):
        try:
            # Extract cell contents using regex
            cell_pattern = r'<td[^>]*>([\s\S]*?)</td>'
            cell_matches = re.findall(cell_pattern, row_html)
            
            if len(cell_matches) < 10:  # Skip malformed rows
                continue
            
            # Clean cell contents
            cells = [clean_text(cell) for cell in cell_matches]
            
            # Map cells to data (based on actual HTML structure):
            # Cell 0: Account ID, Cell 1: Symbol, Cell 2: Trade Date/Time
            # Cell 3: Settle Date, Cell 4: Exchange, Cell 5: Type
            # Cell 6: Quantity, Cell 7: Price, Cell 8: Proceeds
            # Cell 9: Commission, Cell 10: Fee
            
            symbol = cells[1]
            trade_datetime = cells[2]
            trade_date = parse_trade_date(trade_datetime)
            transaction_type = cells[5]
            quantity_text = cells[6]
            price_text = cells[7]
            proceeds_text = cells[8]
            commission_text = cells[9]
            
            # Skip currency transactions (AUD.USD, etc.)
            if '.' in symbol and symbol not in ['U.S', 'S.A']:
                print(f"Skipping currency transaction: {symbol}")
                continue
            
            # Parse numeric values
            quantity = abs(parse_number(quantity_text))
            price = abs(parse_number(price_text))
            proceeds = parse_number(proceeds_text)
            commission = parse_number(commission_text)
            
            # Adjust signs to match your CSV format:
            # BUY: negative proceeds, negative commission
            # SELL: positive proceeds, negative commission
            if transaction_type == 'BUY':
                proceeds = -abs(proceeds)
                commission = -abs(commission)
            elif transaction_type == 'SELL':
                proceeds = abs(proceeds)
                commission = -abs(commission)
            
            # Create transaction record matching your exact CSV format
            transaction = {
                'Symbol': symbol,
                'Trade Date': trade_date,
                'Type': transaction_type,
                'Quantity': quantity,
                'Price (USD)': price,
                'Proceeds (USD)': proceeds,
                'Commission (USD)': commission
            }
            
            transactions.append(transaction)
            print(f"Parsed: {symbol} {transaction_type} {quantity} @ ${price} on {trade_date}")
            
        except Exception as e:
            print(f"Error parsing row {i+1}: {e}")
            continue
    
    if not transactions:
        print("No valid transactions found")
        return None
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Remove duplicates that might have been created during parsing
    print(f"\n🔍 Checking for parsing duplicates...")
    original_count = len(df)
    df = df.drop_duplicates(subset=['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Proceeds (USD)', 'Commission (USD)'], keep='first')
    duplicates_removed = original_count - len(df)
    
    if duplicates_removed > 0:
        print(f"   ✂️  Removed {duplicates_removed} duplicate transactions from parsing")
    else:
        print(f"   ✅ No parsing duplicates found")
    
    # Sort by date
    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
    df = df.sort_values('Trade Date').reset_index(drop=True)
    
    # Generate output filename if not provided
    if output_csv_path is None:
        base_name = os.path.splitext(html_file_path)[0]
        output_csv_path = f"{base_name}_transactions.csv"
    
    # Save to CSV
    try:
        df.to_csv(output_csv_path, index=False)
        print(f"\nTransactions saved to: {output_csv_path}")
    except Exception as e:
        print(f"Error saving CSV: {e}")
    
    # Display summary
    print(f"\n" + "="*60)
    print("TRANSACTION SUMMARY")
    print("="*60)
    print(f"Total transactions: {len(df)}")
    print(f"Date range: {df['Trade Date'].min().strftime('%Y-%m-%d')} to {df['Trade Date'].max().strftime('%Y-%m-%d')}")
    print(f"Unique symbols: {len(df['Symbol'].unique())}")
    
    print(f"\nTransaction types:")
    type_counts = df['Type'].value_counts()
    for tx_type, count in type_counts.items():
        print(f"  {tx_type}: {count}")
    
    print(f"\nSymbol breakdown:")
    symbol_counts = df['Symbol'].value_counts()
    for symbol, count in symbol_counts.items():
        print(f"  {symbol}: {count} transactions")
    
    return df

# ============================================================================
# COST BASIS FUNCTIONS (from cost_base.py)
# ============================================================================

def get_financial_year_dates(fy_string):
    """
    Convert financial year string to start and end dates.
    
    Args:
        fy_string (str): Financial year in format "2024-25" or "2023-24"
    
    Returns:
        tuple: (start_date, end_date) as datetime objects
    """
    try:
        start_year = int(fy_string.split('-')[0])
        start_date = datetime(start_year, 7, 1)  # July 1
        end_date = datetime(start_year + 1, 6, 30)  # June 30 next year
        return start_date, end_date
    except:
        return None, None

def get_financial_year_input():
    """
    Get financial year input from user.
    
    Returns:
        str: Financial year string (e.g., "2024-25") or None for no filtering
    """
    print("\n" + "="*60)
    print("FINANCIAL YEAR SELECTION FOR CGT OPTIMIZATION")
    print("="*60)
    print("Select the financial year you're planning CGT for:")
    print("(Sales from this FY will be EXCLUDED from cost basis to keep them available for optimization)")
    print()
    print("💡 Why this matters:")
    print("   • Keeps your current year's sales available for CGT strategy")
    print("   • Cost basis dictionary shows what shares you can still sell")
    print("   • Helps you choose which shares to sell for best tax outcome")
    print()
    print("Options:")
    print("1. 2023-24 (July 1, 2023 - June 30, 2024)")
    print("2. 2024-25 (July 1, 2024 - June 30, 2025) ← Most common choice")  
    print("3. 2025-26 (July 1, 2025 - June 30, 2026)")
    print("4. No filtering (use all transactions)")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == '1':
                return "2023-24"
            elif choice == '2':
                return "2024-25"
            elif choice == '3':
                return "2025-26"
            elif choice == '4':
                return None
            elif choice.lower() in ['q', 'quit', 'exit']:
                print("Exiting...")
                return None
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4 (or 'q' to quit).")
        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted")
            return None
        except:
            print("❌ Invalid input. Please try again.")

def create_cost_basis_dictionary_from_csv(csv_files, target_financial_year=None):
    """
    Create a dictionary of cost basis for each symbol from buy transactions in CSV files.
    Excludes SELL transactions from the target financial year to keep them available for CGT optimization.
    
    Args:
        csv_files (list or str): List of CSV file paths, or single CSV file path
        target_financial_year (str): Financial year to exclude sales from (e.g., "2024-25")
    
    Returns:
        dict: Dictionary with symbol as key and list of purchase records as value
    """
    
    # Handle single file input
    if isinstance(csv_files, str):
        csv_files = [csv_files]
    
    print(f"Loading buy transactions from {len(csv_files)} CSV file(s)...")
    
    # Load and combine all CSV files
    all_transactions = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['Source_File'] = os.path.basename(csv_file)  # Track source
            all_transactions.append(df)
            print(f"✅ Loaded {len(df)} transactions from {csv_file}")
            
            # Show breakdown of transaction types
            if 'Type' in df.columns:
                type_counts = df['Type'].value_counts()
                for t_type, count in type_counts.items():
                    print(f"   📊 {t_type}: {count} transactions")
            
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
            continue
    
    if not all_transactions:
        print("❌ No CSV files loaded successfully")
        return None
    
    # Combine all transactions
    all_df = pd.concat(all_transactions, ignore_index=True)
    
    print(f"📊 Total transactions loaded: {len(all_df)}")
    
    # Validate expected columns exist
    required_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
    missing_columns = [col for col in required_columns if col not in all_df.columns]
    
    if missing_columns:
        print(f"❌ Missing required columns: {missing_columns}")
        print(f"Available columns: {list(all_df.columns)}")
        return None
    
    # Convert Trade Date to datetime for filtering
    all_df['Trade Date'] = pd.to_datetime(all_df['Trade Date'])
    
    # Apply financial year filtering if specified
    if target_financial_year:
        fy_start, fy_end = get_financial_year_dates(target_financial_year)
        if fy_start and fy_end:
            print(f"\n🗓️ Financial Year Filtering: {target_financial_year}")
            print(f"Excluding SELL transactions from {fy_start.strftime('%d.%m.%Y')} to {fy_end.strftime('%d.%m.%Y')}")
            
            # Count transactions before filtering
            total_before = len(all_df)
            sell_before = len(all_df[all_df['Type'] == 'SELL'])
            buy_before = len(all_df[all_df['Type'] == 'BUY'])
            
            # Filter out SELL transactions from the target financial year
            sell_in_fy = (all_df['Type'] == 'SELL') & (all_df['Trade Date'] >= fy_start) & (all_df['Trade Date'] <= fy_end)
            excluded_sells = all_df[sell_in_fy].copy()
            
            # Keep all BUY transactions and SELL transactions from BEFORE the target FY
            all_df = all_df[~sell_in_fy].copy()
            
            # Show filtering summary
            excluded_count = len(excluded_sells)
            print(f"📊 Filtering Summary:")
            print(f"   Before: {total_before} transactions ({buy_before} BUY, {sell_before} SELL)")
            print(f"   Excluded: {excluded_count} SELL transactions from FY {target_financial_year}")
            print(f"   After: {len(all_df)} transactions")
            
            if excluded_count > 0:
                print(f"\n🚫 Excluded SELL transactions (kept available for CGT optimization):")
                excluded_summary = excluded_sells.groupby('Symbol').agg({
                    'Quantity': 'sum',
                    'Proceeds (USD)': 'sum'
                }).round(2)
                for symbol, row in excluded_summary.iterrows():
                    print(f"   • {symbol}: {abs(row['Quantity']):.2f} units, ${abs(row['Proceeds (USD)']):,.2f}")
        else:
            print(f"❌ Invalid financial year format: {target_financial_year}")
    
    # Filter for BUY transactions only (and any remaining SELL transactions from previous years)
    # But we primarily want BUY transactions for cost basis
    buys_df = all_df[all_df['Type'] == 'BUY'].copy()
    
    # Also process any remaining SELL transactions to subtract from cost basis
    remaining_sells_df = all_df[all_df['Type'] == 'SELL'].copy()
    
    print(f"📈 Buy transactions found: {len(buys_df)}")
    if len(remaining_sells_df) > 0:
        print(f"📉 Sell transactions from previous years: {len(remaining_sells_df)}")
    print(f"🏷️  Unique symbols purchased: {len(buys_df['Symbol'].unique())}")
    
    if len(buys_df) == 0:
        print("❌ No buy transactions found")
        return None
    
    # Show symbol breakdown for purchases
    symbol_counts = buys_df['Symbol'].value_counts()
    print(f"\n📋 Symbols purchased:")
    for symbol, count in symbol_counts.items():
        total_units = buys_df[buys_df['Symbol'] == symbol]['Quantity'].sum()
        print(f"   {symbol}: {count} purchases, {total_units:.2f} total units")
    
    # Remove duplicates from buy transactions before processing
    print(f"\n🔍 Checking for duplicate transactions...")
    buys_df_deduplicated = buys_df.drop_duplicates(
        subset=['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)'], 
        keep='first'
    ).copy()
    
    duplicates_removed = len(buys_df) - len(buys_df_deduplicated)
    if duplicates_removed > 0:
        print(f"   ✂️  Removed {duplicates_removed} duplicate BUY transactions")
        
        # Show which symbols had duplicates
        duplicate_symbols = []
        for symbol in buys_df['Symbol'].unique():
            original_count = len(buys_df[buys_df['Symbol'] == symbol])
            dedup_count = len(buys_df_deduplicated[buys_df_deduplicated['Symbol'] == symbol])
            if original_count != dedup_count:
                duplicate_symbols.append(f"{symbol} ({original_count - dedup_count} duplicates)")
        
        if duplicate_symbols:
            print(f"   📊 Symbols with duplicates: {', '.join(duplicate_symbols)}")
    else:
        print(f"   ✅ No duplicate transactions found")
    
    # Use deduplicated dataframe
    buys_df = buys_df_deduplicated
    
    # Initialize the cost basis dictionary with BUY transactions
    cost_basis_dict = {}
    
    # Process each buy transaction
    for index, row in buys_df.iterrows():
        symbol = row['Symbol']
        quantity = abs(row['Quantity'])  # Ensure positive quantity
        
        # Get price per unit in USD (excluding commission)
        price_per_unit_usd = abs(row['Price (USD)']) if 'Price (USD)' in row else 0
        commission_usd = abs(row['Commission (USD)']) if 'Commission (USD)' in row else 0
        
        # Format date as DD.M.YY (e.g., 25.5.24)
        trade_date = pd.to_datetime(row['Trade Date'])
        try:
            formatted_date = trade_date.strftime("%d.%-m.%y")  # Unix format
        except:
            # Fallback for Windows
            formatted_date = trade_date.strftime("%d.%m.%y").replace('.0', '.')  # Remove leading zero manually
        
        # Create the record dictionary
        record = {
            'units': quantity,
            'price': round(price_per_unit_usd, 2),  # Price per unit in USD
            'commission': round(commission_usd, 2),  # Total commission in USD for this transaction
            'date': formatted_date,
            'source_file': row.get('Source_File', 'unknown')  # Track which file this came from
        }
        
        # Check for duplicates in the cost basis dictionary itself
        if symbol not in cost_basis_dict:
            cost_basis_dict[symbol] = []
        
        # Additional duplicate check at dictionary level
        duplicate_found = False
        for existing_record in cost_basis_dict[symbol]:
            if (existing_record['units'] == record['units'] and 
                existing_record['price'] == record['price'] and 
                existing_record['commission'] == record['commission'] and 
                existing_record['date'] == record['date']):
                duplicate_found = True
                print(f"   🔍 Skipping duplicate: {symbol} {quantity} units @ ${price_per_unit_usd} on {formatted_date}")
                break
        
        if not duplicate_found:
            cost_basis_dict[symbol].append(record)
    
    # Process SELL transactions from previous years (subtract from cost basis using FIFO)
    if len(remaining_sells_df) > 0:
        print(f"\n🔄 Processing {len(remaining_sells_df)} SELL transactions from previous years...")
        
        for index, row in remaining_sells_df.iterrows():
            symbol = row['Symbol']
            units_sold = abs(row['Quantity'])
            sell_date = pd.to_datetime(row['Trade Date'])
            
            if symbol in cost_basis_dict:
                print(f"   📉 {symbol}: Sold {units_sold} units on {sell_date.strftime('%d.%m.%y')}")
                
                # Apply FIFO - remove oldest units first
                remaining_to_remove = units_sold
                records_to_keep = []
                
                for record in cost_basis_dict[symbol]:
                    if remaining_to_remove <= 0:
                        records_to_keep.append(record)
                    elif record['units'] <= remaining_to_remove:
                        # Remove this entire record
                        remaining_to_remove -= record['units']
                        print(f"      ✂️  Removed all {record['units']} units from {record['date']}")
                    else:
                        # Partially remove from this record
                        original_units = record['units']
                        record['units'] -= remaining_to_remove
                        print(f"      ✂️  Removed {remaining_to_remove} units from {record['date']} (kept {record['units']})")
                        remaining_to_remove = 0
                        records_to_keep.append(record)
                
                cost_basis_dict[symbol] = records_to_keep
                
                if remaining_to_remove > 0:
                    print(f"      ⚠️  Warning: Tried to sell {remaining_to_remove} more units than available")
    
    # Remove symbols with no remaining units
    symbols_to_remove = []
    for symbol, records in cost_basis_dict.items():
        total_remaining = sum(record['units'] for record in records)
        if total_remaining <= 0:
            symbols_to_remove.append(symbol)
    
    for symbol in symbols_to_remove:
        print(f"   🗑️  Removed {symbol} - no remaining units after sales")
        del cost_basis_dict[symbol]
    
    # Sort each symbol's records by date (oldest first) and do final deduplication
    for symbol in cost_basis_dict:
        # Sort by date first (handle different date formats)
        def parse_date_for_sorting(date_str):
            try:
                return datetime.strptime(date_str, "%d.%m.%y")
            except:
                try:
                    return datetime.strptime(date_str, "%d.%-m.%y")
                except:
                    # Fallback - assume it's already a reasonable format
                    return datetime.now()
        
        cost_basis_dict[symbol].sort(key=lambda x: parse_date_for_sorting(x['date']))
        
        # Final deduplication check for this symbol
        unique_records = []
        duplicates_found = 0
        
        for record in cost_basis_dict[symbol]:
            # Check if this exact record already exists
            is_duplicate = False
            for existing in unique_records:
                if (existing['units'] == record['units'] and 
                    existing['price'] == record['price'] and 
                    existing['commission'] == record['commission'] and 
                    existing['date'] == record['date']):
                    is_duplicate = True
                    duplicates_found += 1
                    break
            
            if not is_duplicate:
                unique_records.append(record)
        
        if duplicates_found > 0:
            print(f"   🔍 Final cleanup: Removed {duplicates_found} duplicate {symbol} records")
        
        cost_basis_dict[symbol] = unique_records
    
    print(f"✅ Created cost basis dictionary for {len(cost_basis_dict)} symbols")
    
    # Validation summary
    total_unique_purchases = sum(len(records) for records in cost_basis_dict.values())
    total_unique_units = sum(sum(record['units'] for record in records) for records in cost_basis_dict.values())
    
    print(f"📊 Final Summary:")
    print(f"   • Unique purchase transactions: {total_unique_purchases}")
    print(f"   • Total units available: {total_unique_units:,.2f}")
    
    return cost_basis_dict

def create_cgt_analysis_sheets(csv_files, cost_basis_dict, target_financial_year):
    """
    Create CGT analysis sheets:
    1. Sale transactions for current FY (deduplicated)
    
    Args:
        csv_files (list): List of CSV files
        cost_basis_dict (dict): Cost basis dictionary
        target_financial_year (str): Target financial year (e.g., "2024-25")
    
    Returns:
        DataFrame: current_fy_sales_df (deduplicated)
    """
    
    if not target_financial_year:
        print("⚠️ No target financial year specified - skipping CGT analysis sheets")
        return None
    
    print(f"\n🔄 Creating CGT sales analysis for FY {target_financial_year}...")
    
    # Load and combine all CSV files
    all_transactions = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['Source_File'] = os.path.basename(csv_file)
            all_transactions.append(df)
        except Exception as e:
            continue
    
    if not all_transactions:
        return None
    
    all_df = pd.concat(all_transactions, ignore_index=True)
    all_df['Trade Date'] = pd.to_datetime(all_df['Trade Date'])
    
    # Remove duplicates BEFORE filtering for sales
    print(f"   🔍 Removing duplicates from transaction data...")
    original_count = len(all_df)
    all_df = all_df.drop_duplicates(
        subset=['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Proceeds (USD)', 'Commission (USD)'], 
        keep='first'
    )
    duplicates_removed = original_count - len(all_df)
    if duplicates_removed > 0:
        print(f"   ✂️  Removed {duplicates_removed} duplicate transactions")
    
    # Get financial year dates
    fy_start, fy_end = get_financial_year_dates(target_financial_year)
    
    # Extract SELL transactions from current financial year
    current_fy_sales = all_df[
        (all_df['Type'] == 'SELL') & 
        (all_df['Trade Date'] >= fy_start) & 
        (all_df['Trade Date'] <= fy_end)
    ].copy()
    
    if len(current_fy_sales) > 0:
        # Add CGT-relevant columns
        current_fy_sales['Units_Sold'] = abs(current_fy_sales['Quantity'])
        current_fy_sales['Sale_Price_Per_Unit'] = abs(current_fy_sales['Price (USD)'])
        current_fy_sales['Total_Proceeds'] = abs(current_fy_sales['Proceeds (USD)'])
        current_fy_sales['Commission_Paid'] = abs(current_fy_sales['Commission (USD)'])
        current_fy_sales['Net_Proceeds'] = current_fy_sales['Total_Proceeds'] - current_fy_sales['Commission_Paid']
        current_fy_sales['Financial_Year'] = target_financial_year
        
        # Sort by date
        current_fy_sales = current_fy_sales.sort_values('Trade Date').reset_index(drop=True)
        
        # Final deduplication check on the CGT-specific columns
        print(f"   🔍 Final deduplication check on sales data...")
        original_sales_count = len(current_fy_sales)
        current_fy_sales = current_fy_sales.drop_duplicates(
            subset=['Symbol', 'Trade Date', 'Units_Sold', 'Sale_Price_Per_Unit', 'Total_Proceeds'], 
            keep='first'
        ).reset_index(drop=True)
        final_duplicates_removed = original_sales_count - len(current_fy_sales)
        
        if final_duplicates_removed > 0:
            print(f"   ✂️  Removed {final_duplicates_removed} duplicate sales records from CGT sheet")
        
        print(f"   📉 Final result: {len(current_fy_sales)} unique sales in FY {target_financial_year}")
        
        # Show sample of what will be in the sheet
        print(f"\n📋 Sample sales for FY {target_financial_year}:")
        for _, row in current_fy_sales.head(3).iterrows():
            print(f"   • {row['Symbol']}: {row['Units_Sold']:.0f} units @ ${row['Sale_Price_Per_Unit']:.2f} on {row['Trade Date'].strftime('%Y-%m-%d')}")
        if len(current_fy_sales) > 3:
            print(f"   ... and {len(current_fy_sales) - 3} more sales")
    else:
        print(f"   📉 No sales found in FY {target_financial_year}")
    
    return current_fy_sales

def save_cgt_analysis_to_excel(csv_files, cost_basis_dict, transaction_history, target_financial_year):
    """
    Save CGT analysis to Excel file with single sheet: current FY sales.
    
    Args:
        csv_files: List of CSV files
        cost_basis_dict: Cost basis dictionary
        transaction_history: Complete transaction history
        target_financial_year: Target financial year
    """
    
    if not target_financial_year:
        print("⚠️ No target financial year - skipping Excel CGT analysis")
        return
    
    if not EXCEL_AVAILABLE:
        print("⚠️ openpyxl not available - skipping Excel CGT analysis")
        print("Install with: pip install openpyxl")
        return
    
    print(f"\n💾 Creating CGT sales analysis Excel file...")
    
    # Create CGT analysis sheet (just the sales data)
    current_fy_sales_df = create_cgt_analysis_sheets(csv_files, cost_basis_dict, target_financial_year)
    
    # Generate filename
    excel_filename = f"CGT_Sales_FY{target_financial_year}.xlsx"
    
    # Check if we have any data to work with
    if current_fy_sales_df is None or len(current_fy_sales_df) == 0:
        print("⚠️ No sales data available for current FY - creating template Excel file")
    
    try:
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            
            # Sheet 1: Sale transactions for current FY (only sheet needed)
            if current_fy_sales_df is not None and len(current_fy_sales_df) > 0:
                # Select relevant columns for CGT
                cgt_sales_columns = [
                    'Symbol', 'Trade Date', 'Units_Sold', 'Sale_Price_Per_Unit', 
                    'Total_Proceeds', 'Commission_Paid', 'Net_Proceeds', 'Financial_Year'
                ]
                current_fy_sales_df[cgt_sales_columns].to_excel(
                    writer, sheet_name=f'Sales_FY{target_financial_year}', index=False
                )
                print(f"   📊 Created Excel sheet with {len(current_fy_sales_df)} unique sales transactions for FY {target_financial_year}")
            else:
                # Create empty sheet with headers
                empty_df = pd.DataFrame(columns=[
                    'Symbol', 'Trade Date', 'Units_Sold', 'Sale_Price_Per_Unit', 
                    'Total_Proceeds', 'Commission_Paid', 'Net_Proceeds', 'Financial_Year'
                ])
                empty_df.to_excel(writer, sheet_name=f'Sales_FY{target_financial_year}', index=False)
                print(f"   📊 No sales found for FY {target_financial_year} - created empty template")
        
        print(f"\n✅ CGT Sales Analysis saved to: {excel_filename}")
        print(f"📄 Contains: Current financial year sales (deduplicated) ready for CGT reporting")
        
        return excel_filename
        
    except Exception as e:
        print(f"❌ Error creating Excel file: {e}")
        return None

def create_complete_transaction_history(csv_files, target_financial_year=None):
    """
    Create a complete transaction history JSON with ALL transactions (BUY and SELL).
    This is for reference purposes, separate from the cost basis dictionary.
    
    Args:
        csv_files (list): List of CSV file paths
        target_financial_year (str): Financial year info for filename
    
    Returns:
        dict: Complete transaction history organized by symbol
    """
    
    print(f"\n🔄 Creating complete transaction history for reference...")
    
    # Load and combine all CSV files (same as before)
    all_transactions = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['Source_File'] = os.path.basename(csv_file)
            all_transactions.append(df)
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
            continue
    
    if not all_transactions:
        return None
    
    # Combine all transactions
    all_df = pd.concat(all_transactions, ignore_index=True)
    all_df['Trade Date'] = pd.to_datetime(all_df['Trade Date'])
    
    # Remove duplicates
    original_count = len(all_df)
    all_df = all_df.drop_duplicates(
        subset=['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Proceeds (USD)', 'Commission (USD)'], 
        keep='first'
    )
    duplicates_removed = original_count - len(all_df)
    
    if duplicates_removed > 0:
        print(f"   ✂️  Removed {duplicates_removed} duplicate transactions from history")
    
    # Create complete transaction history dictionary
    transaction_history = {}
    
    for index, row in all_df.iterrows():
        symbol = row['Symbol']
        quantity = row['Quantity']  # Keep original sign (positive for BUY, negative for SELL)
        transaction_type = row['Type']
        
        # Get values
        price_per_unit_usd = abs(row['Price (USD)']) if 'Price (USD)' in row else 0
        commission_usd = abs(row['Commission (USD)']) if 'Commission (USD)' in row else 0
        proceeds_usd = row['Proceeds (USD)'] if 'Proceeds (USD)' in row else 0
        
        # Format date
        trade_date = pd.to_datetime(row['Trade Date'])
        try:
            formatted_date = trade_date.strftime("%d.%-m.%y")
        except:
            formatted_date = trade_date.strftime("%d.%m.%y").replace('.0', '.')
        
        # Create transaction record
        transaction_record = {
            'type': transaction_type,
            'units': abs(quantity),  # Always positive for clarity
            'price': round(price_per_unit_usd, 2),
            'commission': round(commission_usd, 2),
            'proceeds': round(proceeds_usd, 2),
            'date': formatted_date,
            'source_file': row.get('Source_File', 'unknown')
        }
        
        # Add to dictionary
        if symbol not in transaction_history:
            transaction_history[symbol] = []
        
        transaction_history[symbol].append(transaction_record)
    
    # Sort each symbol's transactions by date
    for symbol in transaction_history:
        transaction_history[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%y") if '.' in x['date'] else datetime.now())
    
    print(f"✅ Created complete transaction history for {len(transaction_history)} symbols")
    
    # Show summary
    total_transactions = sum(len(records) for records in transaction_history.values())
    buy_count = 0
    sell_count = 0
    
    for records in transaction_history.values():
        for record in records:
            if record['type'] == 'BUY':
                buy_count += 1
            elif record['type'] == 'SELL':
                sell_count += 1
    
    print(f"   📊 Total: {total_transactions} transactions ({buy_count} BUY, {sell_count} SELL)")
    
    return transaction_history

def save_cost_basis_dictionary(cost_basis_dict, output_file_path):
    """
    Save the cost basis dictionary to a JSON file for easy access.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
        output_file_path (str): Path where to save the JSON file
    """
    try:
        # Create a clean version without source_file info for the JSON
        clean_dict = {}
        for symbol, records in cost_basis_dict.items():
            clean_dict[symbol] = []
            for record in records:
                clean_record = {
                    'units': record['units'],
                    'price': record['price'],
                    'commission': record['commission'],
                    'date': record['date']
                }
                clean_dict[symbol].append(clean_record)
        
        with open(output_file_path, 'w') as f:
            json.dump(clean_dict, f, indent=2)
        print(f"📊 Cost basis dictionary saved to: {output_file_path}")
    except Exception as e:
        print(f"❌ Error saving JSON file: {e}")

def save_complete_transaction_history(transaction_history, target_financial_year=None):
    """
    Save the complete transaction history to a JSON file.
    
    Args:
        transaction_history (dict): Complete transaction history dictionary
        target_financial_year (str): Financial year for filename
    """
    
    if target_financial_year:
        json_output = f"complete_transaction_history_FY{target_financial_year}.json"
    else:
        json_output = "complete_transaction_history.json"
    
    try:
        with open(json_output, 'w') as f:
            json.dump(transaction_history, f, indent=2)
        print(f"📄 Complete transaction history saved to: {json_output}")
        return json_output
    except Exception as e:
        print(f"❌ Error saving transaction history: {e}")
        return None
    """
    Save the cost basis dictionary to a JSON file for easy access.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
        output_file_path (str): Path where to save the JSON file
    """
    try:
        # Create a clean version without source_file info for the JSON
        clean_dict = {}
        for symbol, records in cost_basis_dict.items():
            clean_dict[symbol] = []
            for record in records:
                clean_record = {
                    'units': record['units'],
                    'price': record['price'],
                    'commission': record['commission'],
                    'date': record['date']
                }
                clean_dict[symbol].append(clean_record)
        
        with open(output_file_path, 'w') as f:
            json.dump(clean_dict, f, indent=2)
        print(f"Cost basis dictionary saved to: {output_file_path}")
    except Exception as e:
        print(f"Error saving JSON file: {e}")

def display_transaction_history_sample(transaction_history):
    """
    Display a sample of the complete transaction history.
    
    Args:
        transaction_history (dict): Complete transaction history dictionary
    """
    
    if not transaction_history:
        return
    
    print("\n" + "="*60)
    print("COMPLETE TRANSACTION HISTORY SAMPLE")
    print("="*60)
    
    # Show first symbol as example
    sample_symbol = list(transaction_history.keys())[0]
    sample_records = transaction_history[sample_symbol]
    
    print(f"📋 Example for {sample_symbol}:")
    for i, record in enumerate(sample_records[:3], 1):  # Show first 3 transactions
        transaction_type = record['type']
        units = record['units']
        price = record['price']
        commission = record['commission']
        date = record['date']
        proceeds = record.get('proceeds', 0)
        
        if transaction_type == 'BUY':
            print(f"   {i}. 📈 BUY {units} units @ ${price} + ${commission} commission on {date}")
        else:
            print(f"   {i}. 📉 SELL {units} units @ ${price} (${proceeds} proceeds) on {date}")
    
    if len(sample_records) > 3:
        print(f"   ... and {len(sample_records) - 3} more transactions")
    
    print(f"\n💡 The complete history JSON includes:")
    print(f"   • Transaction type (BUY/SELL)")
    print(f"   • Units, price, commission for each transaction")
    print(f"   • Proceeds for SELL transactions")
    print(f"   • Source file tracking")
    print(f"   • All transactions deduplicated")

def display_cost_basis_summary(cost_basis_dict):
    """
    Display a summary of the cost basis dictionary.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
    """
    print("\n" + "="*60)
    print("COST BASIS SUMMARY")
    print("="*60)
    
    for symbol, records in cost_basis_dict.items():
        total_units = sum(record['units'] for record in records)
        total_cost = sum(record['units'] * record['price'] for record in records)
        total_commission = sum(record['commission'] for record in records)
        avg_price = total_cost / total_units if total_units > 0 else 0
        
        print(f"\n{symbol}:")
        print(f"  Total Units: {total_units:,.2f}")
        print(f"  Total Cost: ${total_cost:,.2f} USD (excluding commission)")
        print(f"  Total Commission: ${total_commission:,.2f} USD")
        print(f"  Total Cost (incl. commission): ${total_cost + total_commission:,.2f} USD")
        print(f"  Average Price: ${avg_price:.2f} USD per unit")
        print(f"  Number of Purchases: {len(records)}")
        
        # Show individual purchase records
        print("  Purchase History:")
        for i, record in enumerate(records, 1):
            source_info = f" (from {record['source_file']})" if 'source_file' in record else ""
            print(f"    {i}. {record['units']:,.2f} units @ ${record['price']:.2f} USD + ${record['commission']:.2f} commission on {record['date']}{source_info}")
    """
    Display a summary of the cost basis dictionary.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
    """
    print("\n" + "="*60)
    print("COST BASIS SUMMARY")
    print("="*60)
    
    for symbol, records in cost_basis_dict.items():
        total_units = sum(record['units'] for record in records)
        total_cost = sum(record['units'] * record['price'] for record in records)
        total_commission = sum(record['commission'] for record in records)
        avg_price = total_cost / total_units if total_units > 0 else 0
        
        print(f"\n{symbol}:")
        print(f"  Total Units: {total_units:,.2f}")
        print(f"  Total Cost: ${total_cost:,.2f} USD (excluding commission)")
        print(f"  Total Commission: ${total_commission:,.2f} USD")
        print(f"  Total Cost (incl. commission): ${total_cost + total_commission:,.2f} USD")
        print(f"  Average Price: ${avg_price:.2f} USD per unit")
        print(f"  Number of Purchases: {len(records)}")
        
        # Show individual purchase records
        print("  Purchase History:")
        for i, record in enumerate(records, 1):
            source_info = f" (from {record['source_file']})" if 'source_file' in record else ""
            print(f"    {i}. {record['units']:,.2f} units @ ${record['price']:.2f} USD + ${record['commission']:.2f} commission on {record['date']}{source_info}")

# ============================================================================
# WORKFLOW FUNCTIONS
# ============================================================================

def find_html_files():
    """Find all HTML files in the current directory."""
    html_files = glob.glob("*.htm") + glob.glob("*.html")
    return sorted(html_files)

def find_parsed_csv_files():
    """Find all parsed CSV files from previous runs."""
    csv_files = glob.glob("*parsed*.csv") + glob.glob("*_transactions.csv")
    return sorted(csv_files)

def step1_parse_html_files():
    """Step 1: Parse HTML files to CSV."""
    print("="*70)
    print("STEP 1: PARSING HTML FILES TO CSV")
    print("="*70)
    
    html_files = find_html_files()
    
    if not html_files:
        print("❌ No HTML files found in current directory")
        print("Please place your Interactive Brokers HTML statements in this directory")
        return []
    
    print(f"📄 Found {len(html_files)} HTML files:")
    for file in html_files:
        print(f"   • {file}")
    
    csv_files_created = []
    
    for html_file in html_files:
        print(f"\n🔄 Processing {html_file}...")
        
        # Generate output CSV filename
        base_name = os.path.splitext(html_file)[0]
        csv_output = f"{base_name}_parsed.csv"
        
        # Parse HTML to CSV
        df = parse_ib_html_to_csv(html_file, csv_output)
        
        if df is not None:
            csv_files_created.append(csv_output)
            print(f"✅ Created: {csv_output}")
            
            # Show sample of parsed data
            buy_transactions = df[df['Type'] == 'BUY']
            if len(buy_transactions) > 0:
                print(f"   📊 Found {len(buy_transactions)} BUY transactions")
                print(f"   🏷️  Symbols: {', '.join(buy_transactions['Symbol'].unique())}")
        else:
            print(f"❌ Failed to parse {html_file}")
    
    print(f"\n✅ Step 1 Complete: Created {len(csv_files_created)} CSV files")
    return csv_files_created

def step2_create_cost_basis():
    """Step 2: Create cost basis dictionary from CSV files."""
    print("\n" + "="*70)
    print("STEP 2: CREATING COST BASIS DICTIONARY & TRANSACTION HISTORY")
    print("="*70)
    
    # Find all available CSV files
    csv_files = find_parsed_csv_files()
    
    if not csv_files:
        print("❌ No parsed CSV files found")
        print("Please run Step 1 first to parse HTML files")
        return None, None
    
    print(f"📄 Found {len(csv_files)} CSV files:")
    for file in csv_files:
        print(f"   • {file}")
    
    # Get financial year input from user
    target_fy = get_financial_year_input()
    
    if target_fy:
        print(f"\n🎯 Target Financial Year: {target_fy}")
        print(f"📋 Strategy: SELL transactions from FY {target_fy} will be excluded from cost basis")
        print(f"   This keeps those shares available for CGT optimization")
    else:
        print(f"\n📋 No financial year filtering - processing all transactions")
    
    # Create cost basis dictionary (for CGT calculations)
    print(f"\n🔄 Creating cost basis dictionary for CGT calculations...")
    cost_basis_dict = create_cost_basis_dictionary_from_csv(csv_files, target_fy)
    
    # Create complete transaction history (for reference)
    print(f"\n🔄 Creating complete transaction history for reference...")
    transaction_history = create_complete_transaction_history(csv_files, target_fy)
    
    if cost_basis_dict is None or transaction_history is None:
        print("❌ Failed to create dictionaries")
        return None, None
    
    # Display cost basis summary
    display_cost_basis_summary(cost_basis_dict)
    
    # Display transaction history sample
    display_transaction_history_sample(transaction_history)
    
    # Save both files
    print(f"\n💾 Saving files...")
    
    # Save cost basis dictionary
    if target_fy:
        cost_basis_json = f"cost_basis_dictionary_FY{target_fy}.json"
    else:
        cost_basis_json = "cost_basis_dictionary.json"
    
    save_cost_basis_dictionary(cost_basis_dict, cost_basis_json)
    
    # Save complete transaction history
    history_json = save_complete_transaction_history(transaction_history, target_fy)
    
    # Create CGT analysis Excel file with the new sheets
    excel_filename = save_cgt_analysis_to_excel(csv_files, cost_basis_dict, transaction_history, target_fy)
    
    print(f"\n✅ Step 2 Complete:")
    print(f"   📊 Cost basis dictionary: {cost_basis_json}")
    print(f"   📋 Complete history: {history_json}")
    if excel_filename:
        print(f"   📈 CGT analysis: {excel_filename}")
    
    return cost_basis_dict, transaction_history

def step3_validate_results(cost_basis_dict):
    """Step 3: Validate the results."""
    print("\n" + "="*70)
    print("STEP 3: VALIDATION & SUMMARY")
    print("="*70)
    
    if cost_basis_dict is None:
        print("❌ No cost basis dictionary to validate")
        return False
    
    # Validation checks
    total_symbols = len(cost_basis_dict)
    total_purchases = sum(len(records) for records in cost_basis_dict.values())
    total_units = sum(sum(record['units'] for record in records) for records in cost_basis_dict.values())
    total_cost = sum(sum(record['units'] * record['price'] + record['commission'] for record in records) for records in cost_basis_dict.values())
    
    print(f"📊 VALIDATION SUMMARY:")
    print(f"   • Total symbols: {total_symbols}")
    print(f"   • Total purchase transactions: {total_purchases}")
    print(f"   • Total units purchased: {total_units:,.2f}")
    print(f"   • Total cost (incl. commission): ${total_cost:,.2f} USD")
    
    # Check for potential issues
    issues = []
    
    for symbol, records in cost_basis_dict.items():
        # Check for negative units or prices
        for record in records:
            if record['units'] <= 0:
                issues.append(f"{symbol}: Negative or zero units ({record['units']})")
            if record['price'] <= 0:
                issues.append(f"{symbol}: Negative or zero price (${record['price']})")
    
    if issues:
        print(f"\n⚠️  POTENTIAL ISSUES FOUND ({len(issues)}):")
        for issue in issues[:10]:  # Show first 10 issues
            print(f"   • {issue}")
        if len(issues) > 10:
            print(f"   • ... and {len(issues) - 10} more issues")
    else:
        print(f"\n✅ No validation issues found!")
    
    # Show date range
    all_dates = []
    for records in cost_basis_dict.values():
        for record in records:
            try:
                date_obj = datetime.strptime(record['date'], "%d.%m.%y")
                all_dates.append(date_obj)
            except:
                pass
    
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        print(f"\n📅 Date range: {min_date.strftime('%d.%m.%y')} to {max_date.strftime('%d.%m.%y')}")
        print(f"   ({(max_date - min_date).days} days)")
    
    return len(issues) == 0

def main():
    """Main workflow function."""
    print("🚀 ALL-IN-ONE HTML TO COST BASIS CONVERTER")
    print("="*70)
    print("This script will:")
    print("1. Parse HTML trading statements to CSV format")
    print("2. Create a cost basis dictionary from buy transactions")
    print("3. Filter out sales from your target financial year (for CGT optimization)")
    print("4. Create Excel file with current FY sales (deduplicated)")
    print("5. Validate and summarize the results")
    print()
    
    # Check dependencies
    missing_deps = []
    if not BS4_AVAILABLE:
        missing_deps.append("beautifulsoup4 (for HTML parsing)")
    if not EXCEL_AVAILABLE:
        missing_deps.append("openpyxl (for Excel files)")
    
    if missing_deps:
        print("⚠️ Missing optional dependencies:")
        for dep in missing_deps:
            print(f"   • {dep}")
        print("\nInstall with:")
        print("   pip install beautifulsoup4 openpyxl")
        print("\nContinuing with available features...\n")
    
    # Check if we should skip Step 1
    existing_csv = find_parsed_csv_files()
    if existing_csv:
        print(f"🔍 Found {len(existing_csv)} existing parsed CSV files:")
        for file in existing_csv:
            print(f"   • {file}")
        
        try:
            response = input("\nSkip HTML parsing and use existing CSV files? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                csv_files = existing_csv
                print("✅ Using existing CSV files")
            else:
                csv_files = step1_parse_html_files()
        except KeyboardInterrupt:
            print("\n\n⚠️ Process interrupted by user")
            return None
    else:
        csv_files = step1_parse_html_files()
    
    # Step 2: Create cost basis dictionary and complete transaction history
    cost_basis_dict, transaction_history = step2_create_cost_basis()
    
    # Step 3: Validate results
    validation_passed = step3_validate_results(cost_basis_dict)
    
    # Final summary
    print("\n" + "="*70)
    print("WORKFLOW COMPLETE")
    print("="*70)
    
    if cost_basis_dict:
        print("✅ SUCCESS! Your CGT analysis files are ready.")
        print("\n📄 Files created:")
        print("   📊 cost_basis_dictionary_FY*.json - For CGT calculations")
        print("     (Optimized for your target financial year)")
        print("   📋 complete_transaction_history_FY*.json - Complete reference")
        print("     (All BUY and SELL transactions with transaction types)")
        print("   📈 CGT_Sales_FY*.xlsx - Excel file with current FY sales")
        print("     • Deduplicated sales transactions ready for CGT reporting")
        
        if existing_csv or csv_files:
            print("   • *_parsed.csv - Raw trading data in CSV format")
        
        print("\n📋 How to use:")
        print("1. 📊 Use cost_basis_dictionary for CGT optimization")
        print("2. 📋 Use complete_transaction_history for record keeping") 
        print("3. 📈 Use CGT_Sales Excel file for current year CGT reporting")
        print("4. Current financial year sales are excluded from cost basis")
        print("5. All files are deduplicated and ready to use")
        
        if transaction_history:
            total_transactions = sum(len(records) for records in transaction_history.values())
            print(f"\n📈 Quick Stats:")
            print(f"   • Cost basis available for {len(cost_basis_dict)} symbols")
            print(f"   • Complete history: {total_transactions} total transactions")
        
        if not validation_passed:
            print("\n⚠️  Some validation issues were found - please review them above")
    else:
        print("❌ FAILED - Please check the error messages above")
    
    return cost_basis_dict

if __name__ == "__main__":
    # Run the complete workflow
    try:
        result = main()
        print(f"\n🎉 Script completed {'successfully' if result else 'with errors'}!")
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your HTML files and try again")