#!/usr/bin/env python3
"""
Enhanced Unified Cost Basis Creator with Built-in FIFO Processing

This script combines data from multiple sources and applies proper FIFO accounting:
1. HTML-parsed CSV files (from Interactive Brokers)
2. Manual CSV files (from other sources)
3. Applies FIFO (First In, First Out) for sales
4. Creates accurate cost basis dictionary accounting for all historical sales

Key Features:
- Robust date parsing for mixed formats
- Automatic FIFO processing for sales
- Detailed transaction logging
- Commission handling ($30 default for manual transactions)
- Comprehensive validation and reporting
"""

import pandas as pd
import numpy as np
import json
import os
import glob
from datetime import datetime
import warnings
import re

def robust_date_parser(date_str):
    """
    Parse dates in multiple formats and return in DD.M.YY format.
    Handles various date formats including US and Australian formats.
    """
    if not date_str or pd.isna(date_str):
        return None
    
    # Convert to string and clean
    date_str = str(date_str).strip()
    
    # List of formats to try
    formats_to_try = [
        "%d.%m.%y",     # 25.5.24
        "%d.%-m.%y",    # 25.5.24 (Unix style)
        "%d/%m/%y",     # 25/5/24
        "%d/%-m/%y",    # 25/5/24 (Unix style)
        "%m/%d/%Y",     # 5/25/2024 (US format)
        "%d/%m/%Y",     # 25/5/2024 (AU format)
        "%m/%d/%y",     # 5/25/24 (US format short)
        "%d/%m/%y",     # 25/5/24 (AU format short)
        "%Y-%m-%d",     # 2024-05-25 (ISO format)
        "%m-%d-%Y",     # 05-25-2024
        "%d-%m-%Y",     # 25-05-2024
    ]
    
    parsed_date = None
    
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    
    # If standard parsing fails, try pandas parsing
    if parsed_date is None:
        try:
            # Use pandas to parse the date (try Australian format first)
            parsed_date = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            if pd.isna(parsed_date):
                # Try with month first (US format)
                parsed_date = pd.to_datetime(date_str, dayfirst=False, errors='coerce')
        except:
            pass
    
    # If still no luck, try regex-based intelligent parsing
    if parsed_date is None or pd.isna(parsed_date):
        # Extract numbers from the string
        numbers = re.findall(r'\d+', date_str)
        if len(numbers) >= 3:
            try:
                num1, num2, num3 = int(numbers[0]), int(numbers[1]), int(numbers[2])
                
                # Determine which number is the year
                if num3 > 31:  # num3 is full year (e.g., 2024)
                    year = num3
                    # For US vs AU format ambiguity, use context clues
                    if num1 > 12:  # num1 must be day (AU format: DD/MM/YYYY)
                        day, month = num1, num2
                    elif num2 > 12:  # num2 must be day (US format: MM/DD/YYYY)
                        month, day = num1, num2
                    else:  # Ambiguous case
                        # For cases like 12/23/2021, assume US format
                        if num1 <= 12 and num2 > 12:
                            month, day = num1, num2
                        else:
                            # Default to US format for ambiguous cases
                            month, day = num1, num2
                            
                elif num1 > 31:  # num1 is full year
                    year = num1
                    day, month = num3, num2
                elif num2 > 31:  # num2 is full year
                    year = num2
                    day, month = num1, num3
                else:  # All numbers <= 31, assume num3 is 2-digit year
                    year = 2000 + num3 if num3 < 50 else 1900 + num3
                    # Apply same logic as above for day/month
                    if num1 > 12:
                        day, month = num1, num2
                    elif num2 > 12:
                        day, month = num2, num1
                    else:
                        # For ambiguous 2-digit year cases, default to day/month (AU format)
                        day, month = num1, num2
                
                parsed_date = datetime(year, month, day)
            except (ValueError, IndexError):
                pass
    
    # Convert to DD.M.YY format if successful
    if parsed_date and not pd.isna(parsed_date):
        try:
            # Format as DD.M.YY (remove leading zero from month)
            formatted_date = parsed_date.strftime("%d.%-m.%y")  # Unix style
            return formatted_date
        except ValueError:
            # Fallback for Windows (doesn't support %-m)
            formatted_date = parsed_date.strftime("%d.%m.%y")
            # Manually remove leading zero from month
            parts = formatted_date.split('.')
            if len(parts) == 3 and parts[1].startswith('0') and len(parts[1]) == 2:
                parts[1] = parts[1][1:]
            return '.'.join(parts)
    
    # If all else fails, return None and log the issue
    print(f"⚠️ Could not convert date: {date_str}")
    return None

def safe_date_sort_key(date_str):
    """
    Create a sort key for dates that handles multiple formats safely.
    """
    try:
        # Try to parse the standardized format first
        if date_str and '.' in str(date_str):
            return datetime.strptime(str(date_str), "%d.%m.%y")
        elif date_str:
            # Use robust parser for other formats
            standardized = robust_date_parser(date_str)
            if standardized and '.' in standardized:
                return datetime.strptime(standardized, "%d.%m.%y")
    except:
        pass
    
    # Return a very old date as fallback so sorting still works
    return datetime(1900, 1, 1)

def standardize_html_parsed_data(df):
    """
    Standardize HTML-parsed CSV data to unified format.
    """
    print(f"🔄 Standardizing HTML-parsed data...")
    
    # Check if this looks like HTML-parsed data
    expected_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
    if not all(col in df.columns for col in expected_columns):
        print(f"⚠️ Missing expected HTML columns. Available: {list(df.columns)}")
        return None
    
    # Create standardized DataFrame
    standardized = pd.DataFrame()
    
    # Map columns to unified format
    standardized['Symbol'] = df['Symbol']
    standardized['Date'] = df['Trade Date'].apply(robust_date_parser)
    standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
    standardized['Quantity'] = df['Quantity'].abs()  # Ensure positive
    standardized['Price'] = df['Price (USD)'].abs()
    standardized['Commission'] = df['Commission (USD)'].abs()
    standardized['Source'] = 'HTML_Parsed'
    
    # Remove rows where date parsing failed
    before_count = len(standardized)
    standardized = standardized.dropna(subset=['Date'])
    after_count = len(standardized)
    
    if before_count != after_count:
        print(f"⚠️ Removed {before_count - after_count} rows with unparseable dates")
    
    print(f"✅ Standardized {len(standardized)} HTML-parsed transactions")
    
    return standardized

def standardize_manual_data(df):
    """
    Standardize manual CSV data to unified format.
    """
    print(f"🔄 Standardizing manual data...")
    
    # Create standardized DataFrame
    standardized = pd.DataFrame()
    
    # Map columns (adjust these based on your manual CSV format)
    if 'Symbol' in df.columns:
        standardized['Symbol'] = df['Symbol']
    elif 'Stock' in df.columns:
        standardized['Symbol'] = df['Stock']
    else:
        print("⚠️ No symbol column found in manual data")
        return None
    
    # Handle date column
    date_column = None
    for col in ['Date', 'Trade Date', 'Transaction Date', 'date']:
        if col in df.columns:
            date_column = col
            break
    
    if date_column:
        standardized['Date'] = df[date_column].apply(robust_date_parser)
    else:
        print("⚠️ No date column found in manual data")
        return None
    
    # Handle activity/type column
    activity_column = None
    for col in ['Activity', 'Type', 'Transaction Type', 'Action']:
        if col in df.columns:
            activity_column = col
            break
    
    if activity_column:
        # Standardize activity names
        activity_mapping = {
            'BUY': 'PURCHASED',
            'PURCHASE': 'PURCHASED',
            'PURCHASED': 'PURCHASED',
            'SELL': 'SOLD',
            'SALE': 'SOLD',
            'SOLD': 'SOLD'
        }
        standardized['Activity'] = df[activity_column].str.upper().map(activity_mapping)
    else:
        print("⚠️ No activity column found in manual data")
        return None
    
    # Handle quantity
    quantity_column = None
    for col in ['Quantity', 'Shares', 'Units', 'Amount']:
        if col in df.columns:
            quantity_column = col
            break
    
    if quantity_column:
        standardized['Quantity'] = pd.to_numeric(df[quantity_column], errors='coerce').abs()
    else:
        print("⚠️ No quantity column found in manual data")
        return None
    
    # Handle price
    price_column = None
    for col in ['Price', 'Price (USD)', 'Unit Price', 'Share Price']:
        if col in df.columns:
            price_column = col
            break
    
    if price_column:
        standardized['Price'] = pd.to_numeric(df[price_column], errors='coerce').abs()
    else:
        print("⚠️ No price column found in manual data")
        return None
    
    # Handle commission with $30 default for manual transactions
    commission_column = None
    for col in ['Commission', 'Commission (USD)', 'Fee', 'Fees']:
        if col in df.columns:
            commission_column = col
            break
    
    if commission_column:
        standardized['Commission'] = pd.to_numeric(df[commission_column], errors='coerce').abs().fillna(30.0)
    else:
        standardized['Commission'] = 30.0  # Default to $30 for manual transactions
    
    standardized['Source'] = 'Manual'
    
    # Remove rows with missing essential data
    essential_columns = ['Symbol', 'Date', 'Activity', 'Quantity', 'Price']
    before_count = len(standardized)
    standardized = standardized.dropna(subset=essential_columns)
    after_count = len(standardized)
    
    if before_count != after_count:
        print(f"⚠️ Removed {before_count - after_count} rows with missing essential data")
    
    print(f"✅ Standardized {len(standardized)} manual transactions")
    
    return standardized

def load_and_combine_data(html_csv_files, manual_csv_files):
    """
    Load and combine data from multiple sources.
    """
    print("=" * 50)
    print("🔄 LOADING AND COMBINING DATA")
    print("=" * 50)
    
    all_data = []
    
    # Load HTML-parsed CSV files
    if html_csv_files:
        print(f"\n📄 Loading {len(html_csv_files)} HTML-parsed CSV files...")
        for csv_file in html_csv_files:
            try:
                df = pd.read_csv(csv_file)
                standardized = standardize_html_parsed_data(df)
                if standardized is not None and len(standardized) > 0:
                    all_data.append(standardized)
                    print(f"📄 Loaded {len(standardized)} transactions from {os.path.basename(csv_file)}")
                else:
                    print(f"⚠️ No valid data from {os.path.basename(csv_file)}")
            except Exception as e:
                print(f"❌ Error loading {csv_file}: {e}")
    
    # Load manual CSV files
    if manual_csv_files:
        print(f"\n📄 Loading {len(manual_csv_files)} manual CSV files...")
        for csv_file in manual_csv_files:
            try:
                df = pd.read_csv(csv_file)
                standardized = standardize_manual_data(df)
                if standardized is not None and len(standardized) > 0:
                    all_data.append(standardized)
                    print(f"📄 Loaded {len(standardized)} manual transactions from {os.path.basename(csv_file)}")
                else:
                    print(f"⚠️ No valid data from {os.path.basename(csv_file)}")
            except Exception as e:
                print(f"❌ Error loading {csv_file}: {e}")
    
    if not all_data:
        print("❌ No valid data loaded from any files")
        return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates
    print(f"\n🔍 Removing duplicates...")
    before_count = len(combined_df)
    combined_df = combined_df.drop_duplicates(
        subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], 
        keep='first'
    )
    after_count = len(combined_df)
    removed_count = before_count - after_count
    
    if removed_count > 0:
        print(f"✂️ Removed {removed_count} duplicate transactions")
    
    # Sort by symbol and date
    combined_df = combined_df.sort_values(['Symbol', 'Date'], key=lambda x: x.map(safe_date_sort_key) if x.name == 'Date' else x)
    combined_df = combined_df.reset_index(drop=True)
    
    print(f"\n📊 COMBINED DATA SUMMARY:")
    print(f"Total transactions: {len(combined_df)}")
    
    # Show date range
    if len(combined_df) > 0:
        dates = [safe_date_sort_key(d) for d in combined_df['Date']]
        valid_dates = [d for d in dates if d.year > 1900]
        if valid_dates:
            min_date = min(valid_dates)
            max_date = max(valid_dates)
            print(f"Date range: {min_date.strftime('%d/%m/%y')} to {max_date.strftime('%d/%m/%y')}")
    
    print(f"Activity types: {dict(combined_df['Activity'].value_counts())}")
    print(f"Unique symbols: {sorted(combined_df['Symbol'].unique())}")
    
    return combined_df

def apply_fifo_cost_basis_calculation(combined_df):
    """
    Apply FIFO (First In, First Out) processing to calculate accurate cost basis.
    This accounts for all historical sales by reducing oldest purchases first.
    """
    print("\n" + "=" * 50)
    print("🔄 APPLYING FIFO COST BASIS CALCULATION")
    print("=" * 50)
    
    if combined_df is None or len(combined_df) == 0:
        print("❌ No data to process")
        return None, None
    
    cost_basis_dict = {}
    fifo_log = {}
    
    # Process each symbol separately
    for symbol in combined_df['Symbol'].unique():
        symbol_transactions = combined_df[combined_df['Symbol'] == symbol].copy()
        symbol_transactions = symbol_transactions.sort_values('Date', key=lambda x: x.map(safe_date_sort_key))
        
        print(f"\n📊 Processing {symbol} ({len(symbol_transactions)} transactions):")
        
        # Initialize FIFO queue for purchases
        purchase_queue = []
        fifo_operations = []
        
        for _, transaction in symbol_transactions.iterrows():
            date_str = transaction['Date']
            activity = transaction['Activity']
            quantity = float(transaction['Quantity'])
            price = float(transaction['Price'])
            commission = float(transaction['Commission'])
            
            if activity == 'PURCHASED':
                # Add to purchase queue
                purchase = {
                    'units': quantity,
                    'price': price,
                    'commission': commission,
                    'date': date_str,
                    'source': transaction['Source']
                }
                purchase_queue.append(purchase)
                
                print(f"   📈 BUY: {quantity} units @ ${price:.2f} + ${commission:.2f} commission on {date_str}")
                fifo_operations.append(f"BUY: {quantity} units @ ${price:.2f} + ${commission:.2f} commission on {date_str}")
                
            elif activity == 'SOLD':
                units_to_sell = quantity
                
                print(f"   📉 SELL: {units_to_sell} units on {date_str}")
                fifo_operations.append(f"SELL: {units_to_sell} units on {date_str}")
                
                # Apply FIFO: remove from oldest purchases first
                remaining_to_sell = units_to_sell
                updated_queue = []
                
                for purchase in purchase_queue:
                    if remaining_to_sell <= 0:
                        # Keep this purchase as-is
                        updated_queue.append(purchase)
                    elif purchase['units'] <= remaining_to_sell:
                        # Sell all units from this purchase
                        print(f"      ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f}")
                        fifo_operations.append(f"   ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f}")
                        remaining_to_sell -= purchase['units']
                    else:
                        # Partially sell from this purchase
                        units_used = remaining_to_sell
                        units_remaining = purchase['units'] - units_used
                        
                        print(f"      ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} (kept {units_remaining})")
                        fifo_operations.append(f"   ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} (kept {units_remaining})")
                        
                        # Update purchase to reflect remaining units
                        updated_purchase = purchase.copy()
                        updated_purchase['units'] = units_remaining
                        # Adjust commission proportionally
                        updated_purchase['commission'] = purchase['commission'] * (units_remaining / purchase['units'])
                        
                        updated_queue.append(updated_purchase)
                        remaining_to_sell = 0
                
                purchase_queue = updated_queue
                
                if remaining_to_sell > 0:
                    warning = f"      ⚠️ WARNING: Tried to sell {remaining_to_sell} more units than available!"
                    print(warning)
                    fifo_operations.append(warning)
        
        # Store remaining purchases as cost basis
        if purchase_queue:
            cost_basis_dict[symbol] = purchase_queue
            
            total_units = sum(p['units'] for p in purchase_queue)
            total_cost = sum(p['units'] * p['price'] for p in purchase_queue)
            total_commission = sum(p['commission'] for p in purchase_queue)
            
            print(f"   ✅ Final position: {total_units:.2f} units")
            print(f"      Total cost: ${total_cost:.2f}")
            print(f"      Total commission: ${total_commission:.2f}")
            print(f"      Average price: ${total_cost/total_units:.2f}")
        else:
            print(f"   📭 No remaining units after all sales")
        
        # Store FIFO log
        fifo_log[symbol] = fifo_operations
    
    print(f"\n✅ FIFO processing complete for {len(cost_basis_dict)} symbols with remaining positions")
    
    return cost_basis_dict, fifo_log

def display_cost_basis_summary(cost_basis_dict):
    """Display summary of the cost basis dictionary."""
    if not cost_basis_dict:
        return
    
    print("\n" + "=" * 60)
    print("UNIFIED COST BASIS SUMMARY (WITH FIFO PROCESSING)")
    print("=" * 60)
    
    total_symbols = len(cost_basis_dict)
    total_units = 0
    total_cost = 0
    total_commission = 0
    
    for symbol, records in cost_basis_dict.items():
        symbol_units = sum(record['units'] for record in records)
        symbol_cost = sum(record['units'] * record['price'] for record in records)
        symbol_commission = sum(record['commission'] for record in records)
        
        total_units += symbol_units
        total_cost += symbol_cost
        total_commission += symbol_commission
        
        avg_price = symbol_cost / symbol_units if symbol_units > 0 else 0
        
        print(f"\n{symbol}:")
        print(f"  Remaining Units: {symbol_units:,.2f}")
        print(f"  Total Cost: ${symbol_cost:,.2f} USD")
        print(f"  Total Commission: ${symbol_commission:,.2f} USD")
        print(f"  Average Price: ${avg_price:.2f} USD per unit")
        print(f"  Purchase Records: {len(records)}")
        
        # Show first few records
        for i, record in enumerate(records[:3], 1):
            source_info = f" ({record.get('source', 'unknown')})" if 'source' in record else ""
            print(f"    {i}. {record['units']:,.2f} units @ ${record['price']:.2f} + ${record['commission']:.2f} commission on {record['date']}{source_info}")
        
        if len(records) > 3:
            print(f"    ... and {len(records) - 3} more purchases")
    
    print(f"\n📊 TOTALS:")
    print(f"  Symbols: {total_symbols}")
    print(f"  Units: {total_units:,.2f}")
    print(f"  Cost: ${total_cost:,.2f} USD")
    print(f"  Commission: ${total_commission:,.2f} USD")
    print(f"  Total Investment: ${total_cost + total_commission:,.2f} USD")

def save_unified_cost_basis(cost_basis_dict, fifo_log, target_financial_year=None):
    """Save the unified cost basis dictionary and FIFO log to files."""
    
    # Generate filenames
    if target_financial_year:
        cost_basis_file = f"unified_cost_basis_FY{target_financial_year}_with_FIFO.json"
        fifo_log_file = f"fifo_processing_log_FY{target_financial_year}.json"
    else:
        cost_basis_file = "unified_cost_basis_with_FIFO.json"
        fifo_log_file = "fifo_processing_log.json"
    
    try:
        # Clean the cost basis dict for JSON (remove source info)
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
        
        # Save cost basis dictionary
        with open(cost_basis_file, 'w') as f:
            json.dump(clean_dict, f, indent=2)
        print(f"\n✅ Unified cost basis dictionary saved to: {cost_basis_file}")
        
        # Save FIFO log
        with open(fifo_log_file, 'w') as f:
            json.dump(fifo_log, f, indent=2)
        print(f"✅ FIFO processing log saved to: {fifo_log_file}")
        
        return cost_basis_file, fifo_log_file
        
    except Exception as e:
        print(f"❌ Error saving files: {e}")
        return None, None

def find_files():
   def find_files():
    """Find relevant CSV files in current directory and html_folder subdirectory."""
    html_parsed_files = []
    manual_files = []
    
    # Look for HTML-parsed CSV files in html_folder subdirectory
    html_folder = "html_folder"
    if os.path.exists(html_folder):
        html_patterns = [
            os.path.join(html_folder, "*parsed*.csv"),
            os.path.join(html_folder, "*_transactions.csv"),
            os.path.join(html_folder, "*50074435*.csv"),
            os.path.join(html_folder, "*.csv")  # All CSV files in html_folder
        ]
        
        for pattern in html_patterns:
            html_parsed_files.extend(glob.glob(pattern))
        html_parsed_files = sorted(list(set(html_parsed_files)))
    
    # Look for manual CSV files in current directory
    all_csv_files = glob.glob("*.csv")
    for csv_file in all_csv_files:
        if any(keyword in csv_file.lower() for keyword in ['manual', 'personal', 'trade', 'my']):
            manual_files.append(csv_file)
    
    return html_parsed_files, manual_files

def main():
    """Main function to create unified cost basis dictionary with FIFO processing."""
    print("🚀 ENHANCED UNIFIED COST BASIS CREATOR")
    print("=" * 60)
    print("This script combines transaction data from multiple sources and applies")
    print("proper FIFO (First In, First Out) accounting for accurate cost basis:")
    print("• HTML-parsed CSV files (from Interactive Brokers)")
    print("• Manual CSV files (from other sources)")
    print("• Applies FIFO for all sales to reduce oldest purchases first")
    print("• Creates accurate cost basis accounting for all historical sales")
    print()
    
    # Find files automatically
    html_files, manual_files = find_files()
    
    print("🔍 Found files:")
    if html_files:
        print("  HTML-parsed CSV files:")
        for file in html_files:
            print(f"    • {file}")
    else:
        print("  • No HTML-parsed CSV files found")
    
    if manual_files:
        print("  Manual CSV files:")
        for file in manual_files:
            print(f"    • {file}")
    else:
        print("  • No manual CSV files found")
    
    if not html_files and not manual_files:
        print("❌ No CSV files found in current directory")
        print("Please ensure you have CSV files to process")
        return None
    
    # Get user confirmation
    try:
        print("\nProceed with these files? (y/n): ", end="")
        response = input().lower().strip()
        if response not in ['y', 'yes']:
            print("❌ Operation cancelled")
            return None
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return None
    
    # Optional: Get financial year
    try:
        print("\nFinancial year for reference (e.g., 2024-25, or press Enter for none): ", end="")
        financial_year = input().strip()
        if not financial_year:
            financial_year = None
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return None
    
    # Load and combine data
    combined_df = load_and_combine_data(html_files, manual_files)
    
    if combined_df is None:
        print("❌ Failed to load and combine data")
        return None
    
    # Apply FIFO cost basis calculation
    cost_basis_dict, fifo_log = apply_fifo_cost_basis_calculation(combined_df)
    
    if cost_basis_dict is None:
        print("❌ Failed to create cost basis dictionary")
        return None
    
    # Display summary
    display_cost_basis_summary(cost_basis_dict)
    
    # Save to files
    cost_basis_file, fifo_log_file = save_unified_cost_basis(cost_basis_dict, fifo_log, financial_year)
    
    if cost_basis_file:
        print(f"\n🎉 SUCCESS!")
        print(f"📄 Enhanced cost basis dictionary created: {cost_basis_file}")
        print(f"📄 FIFO processing log created: {fifo_log_file}")
        print(f"📊 Contains accurate cost basis for {len(cost_basis_dict)} symbols")
        print(f"💡 All historical sales have been accounted for using FIFO method")
        
        # Validation summary
        total_transactions = sum(len(records) for records in cost_basis_dict.values())
        total_units = sum(sum(record['units'] for record in records) for records in cost_basis_dict.values())
        print(f"\n📋 Final Stats:")
        print(f"  • {total_transactions} remaining purchase records")
        print(f"  • {total_units:,.2f} total units available")
        print(f"  • All dates standardized to DD.M.YY format")
        print(f"  • FIFO method applied for accurate cost basis")
        print(f"  • Manual transactions default to $30 commission")
        print(f"  • Ready for CGT calculations")
    
    return cost_basis_dict

if __name__ == "__main__":
    try:
        result = main()
        if result:
            print(f"\n✅ Script completed successfully!")
            print(f"💡 Use the enhanced cost basis file for accurate CGT calculations")
        else:
            print(f"\n❌ Script completed with errors")
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your CSV files and try again")