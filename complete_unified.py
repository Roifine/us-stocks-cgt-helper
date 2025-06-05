#!/usr/bin/env python3
"""
Complete Unified Cost Basis Creator
Handles BOTH HTML files and CSV files directly - no separate parsing needed!

This script:
1. Parses HTML files directly from html_folder/
2. Loads manual CSV files from current directory
3. Applies proper FIFO processing
4. Creates accurate cost basis dictionary
"""

import pandas as pd
import numpy as np
import json
import os
import glob
from datetime import datetime
import warnings
import re
import traceback

# HTML Parsing Functions (from your original html_to_csv.py)
def clean_text(text):
    """Clean and normalize text content."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(',', '')
    return text

def parse_number(text):
    """Parse numeric values from text, handling negative signs and commas."""
    if not text:
        return 0
    
    clean_text_val = clean_text(text)
    is_negative = clean_text_val.startswith('-') or '(' in clean_text_val
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
    
    date_part = date_text.split(',')[0].strip()
    
    try:
        return datetime.strptime(date_part, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_part, '%m/%d/%Y').strftime('%Y-%m-%d')
        except ValueError:
            return date_text

def parse_html_file_directly(html_file_path):
    """Parse HTML file directly to DataFrame."""
    print(f"🔄 Parsing HTML file: {os.path.basename(html_file_path)}")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"❌ Error reading HTML file: {e}")
        return None
    
    transactions = []
    
    # Find all summary rows
    summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
    summary_matches = re.findall(summary_row_pattern, html_content)
    
    print(f"   📊 Found {len(summary_matches)} summary transactions")
    
    for i, row_html in enumerate(summary_matches):
        try:
            cell_pattern = r'<td[^>]*>([\s\S]*?)</td>'
            cell_matches = re.findall(cell_pattern, row_html)
            
            if len(cell_matches) < 10:
                continue
            
            cells = [clean_text(cell) for cell in cell_matches]
            
            symbol = cells[1]
            trade_datetime = cells[2]
            trade_date = parse_trade_date(trade_datetime)
            transaction_type = cells[5]
            quantity_text = cells[6]
            price_text = cells[7]
            proceeds_text = cells[8]
            commission_text = cells[9]
            
            # Skip currency transactions
            if '.' in symbol and symbol not in ['U.S', 'S.A']:
                continue
            
            quantity = abs(parse_number(quantity_text))
            price = abs(parse_number(price_text))
            proceeds = parse_number(proceeds_text)
            commission = parse_number(commission_text)
            
            # Adjust signs
            if transaction_type == 'BUY':
                proceeds = -abs(proceeds)
                commission = -abs(commission)
            elif transaction_type == 'SELL':
                proceeds = abs(proceeds)
                commission = -abs(commission)
            
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
            
        except Exception as e:
            continue
    
    if not transactions:
        print(f"   ⚠️ No valid transactions found")
        return None
    
    df = pd.DataFrame(transactions)
    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
    df = df.sort_values('Trade Date').reset_index(drop=True)
    
    print(f"   ✅ Parsed {len(df)} transactions")
    
    # Show CFLT transactions if any
    cflt_data = df[df['Symbol'] == 'CFLT']
    if len(cflt_data) > 0:
        print(f"   🎯 CFLT transactions found: {len(cflt_data)}")
        for _, row in cflt_data.iterrows():
            print(f"      {row['Type']}: {row['Quantity']} @ ${row['Price (USD)']} on {row['Trade Date'].strftime('%Y-%m-%d')}")
    
    return df

def robust_date_parser(date_str):
    """Parse dates in multiple formats and return datetime object for sorting."""
    if not date_str or pd.isna(date_str):
        return datetime(1900, 1, 1)
    
    date_str = str(date_str).strip()
    formats_to_try = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%y", "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%y", "%m/%d/%y"
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return datetime(1900, 1, 1)

def format_date_for_output(date_str):
    """Format date as DD.M.YY for the final output."""
    date_obj = robust_date_parser(date_str)
    if date_obj.year > 1900:
        try:
            formatted = date_obj.strftime("%d.%-m.%y")
            return formatted
        except ValueError:
            formatted = date_obj.strftime("%d.%m.%y")
            parts = formatted.split('.')
            if len(parts) == 3 and parts[1].startswith('0') and len(parts[1]) == 2:
                parts[1] = parts[1][1:]
            return '.'.join(parts)
    return str(date_str)

def load_html_files():
    """Load and parse HTML files directly."""
    print(f"\n📁 LOADING HTML FILES")
    print("=" * 40)
    
    html_data = []
    html_folder = "html_folder"
    
    if not os.path.exists(html_folder):
        print(f"⚠️ {html_folder} directory not found")
        return html_data
    
    # Look for HTML files (.htm, .html)
    html_files = []
    for ext in ['*.htm', '*.html']:
        html_files.extend(glob.glob(os.path.join(html_folder, ext)))
    
    print(f"📄 Found {len(html_files)} HTML files:")
    for html_file in html_files:
        print(f"   • {os.path.basename(html_file)}")
    
    for html_file in html_files:
        # Parse HTML directly to DataFrame
        df = parse_html_file_directly(html_file)
        
        if df is not None and len(df) > 0:
            # Standardize HTML data
            standardized = pd.DataFrame()
            standardized['Symbol'] = df['Symbol']
            standardized['Date'] = df['Trade Date'].astype(str)
            standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
            standardized['Quantity'] = df['Quantity'].abs()
            standardized['Price'] = df['Price (USD)'].abs()
            standardized['Commission'] = df['Commission (USD)'].abs()
            standardized['Source'] = f'HTML_{os.path.basename(html_file)}'
            
            # Clean up
            standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
            
            if len(standardized) > 0:
                html_data.append(standardized)
                print(f"   ✅ Processed {os.path.basename(html_file)}: {len(standardized)} transactions")
    
    total_html_transactions = sum(len(df) for df in html_data)
    print(f"📊 Total HTML transactions loaded: {total_html_transactions}")
    
    return html_data

def load_manual_csv_files():
    """Load manual CSV files with FIXED column mapping."""
    print(f"\n📁 LOADING MANUAL CSV FILES")
    print("=" * 50)
    
    manual_data = []
    manual_files = [f for f in glob.glob("*.csv") if 'manual' in f.lower()]
    
    print(f"📄 Found {len(manual_files)} manual CSV files:")
    for manual_file in manual_files:
        print(f"   • {manual_file}")
    
    for csv_file in manual_files:
        try:
            df = pd.read_csv(csv_file)
            print(f"\n🔄 Processing {csv_file}:")
            print(f"   📋 Columns: {list(df.columns)}")
            
            # FIXED explicit column mapping for your manual CSV format
            expected_columns = ['Date', 'Activity_Type', 'Symbol', 'Quantity', 'Price_USD', 'USD_Amount', 'AUD_Amount']
            missing = [col for col in expected_columns if col not in df.columns]
            
            if missing:
                print(f"   ❌ Missing expected columns: {missing}")
                continue
            
            # Create standardized DataFrame with EXPLICIT mapping
            standardized = pd.DataFrame()
            standardized['Symbol'] = df['Symbol']
            standardized['Date'] = df['Date'].astype(str)
            standardized['Activity'] = df['Activity_Type'].map({'PURCHASED': 'PURCHASED', 'SOLD': 'SOLD'})
            
            # CRITICAL: Use correct columns (not AUD_Amount!)
            standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
            standardized['Price'] = pd.to_numeric(df['Price_USD'], errors='coerce').abs()
            standardized['Commission'] = 30.0  # Default for manual transactions
            standardized['Source'] = f'Manual_{os.path.basename(csv_file)}'
            
            # Clean up
            standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
            
            if len(standardized) > 0:
                manual_data.append(standardized)
                print(f"   ✅ Processed: {len(standardized)} transactions")
                
                # Show CFLT if it exists
                cflt_data = standardized[standardized['Symbol'] == 'CFLT']
                if len(cflt_data) > 0:
                    print(f"   🎯 CFLT transactions: {len(cflt_data)}")
                    for _, row in cflt_data.iterrows():
                        print(f"      {row['Activity']}: {row['Quantity']} @ ${row['Price']} on {row['Date']}")
            
        except Exception as e:
            print(f"   ❌ Error loading {csv_file}: {e}")
    
    total_manual_transactions = sum(len(df) for df in manual_data)
    print(f"📊 Total manual transactions loaded: {total_manual_transactions}")
    
    return manual_data

def apply_fifo_processing(combined_df):
    """Apply FIFO processing to calculate cost basis."""
    print(f"\n🔄 APPLYING FIFO PROCESSING")
    print("=" * 60)
    
    cost_basis_dict = {}
    fifo_log = {}
    
    print(f"📊 Processing {len(combined_df)} total transactions")
    print(f"   Symbols: {combined_df['Symbol'].nunique()}")
    print(f"   BUY: {len(combined_df[combined_df['Activity'] == 'PURCHASED'])}")
    print(f"   SELL: {len(combined_df[combined_df['Activity'] == 'SOLD'])}")
    
    for symbol in combined_df['Symbol'].unique():
        symbol_transactions = combined_df[combined_df['Symbol'] == symbol].copy()
        
        # Sort by date
        symbol_transactions['date_obj'] = symbol_transactions['Date'].apply(robust_date_parser)
        symbol_transactions = symbol_transactions.sort_values('date_obj')
        
        print(f"\n📊 Processing {symbol} ({len(symbol_transactions)} transactions):")
        
        purchase_queue = []
        fifo_operations = []
        
        for _, transaction in symbol_transactions.iterrows():
            date_str = format_date_for_output(transaction['Date'])
            activity = transaction['Activity']
            quantity = float(transaction['Quantity'])
            price = float(transaction['Price'])
            commission = float(transaction['Commission'])
            source = transaction['Source']
            
            if activity == 'PURCHASED':
                purchase = {
                    'units': quantity,
                    'price': price,
                    'commission': commission,
                    'date': date_str
                }
                purchase_queue.append(purchase)
                
                print(f"   📈 BUY: {quantity} units @ ${price:.2f} + ${commission:.2f} on {date_str} ({source})")
                fifo_operations.append(f"BUY: {quantity} units @ ${price:.2f} + ${commission:.2f} on {date_str} ({source})")
                
            elif activity == 'SOLD':
                units_to_sell = quantity
                
                print(f"   📉 SELL: {units_to_sell} units on {date_str} ({source})")
                fifo_operations.append(f"SELL: {units_to_sell} units on {date_str} ({source})")
                
                # Apply FIFO
                remaining_to_sell = units_to_sell
                updated_queue = []
                
                for purchase in purchase_queue:
                    if remaining_to_sell <= 0:
                        updated_queue.append(purchase)
                    elif purchase['units'] <= remaining_to_sell:
                        print(f"      ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f}")
                        fifo_operations.append(f"   ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f}")
                        remaining_to_sell -= purchase['units']
                    else:
                        units_used = remaining_to_sell
                        units_remaining = purchase['units'] - units_used
                        
                        print(f"      ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} (kept {units_remaining})")
                        fifo_operations.append(f"   ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} (kept {units_remaining})")
                        
                        updated_purchase = purchase.copy()
                        updated_purchase['units'] = units_remaining
                        updated_purchase['commission'] = purchase['commission'] * (units_remaining / purchase['units'])
                        
                        updated_queue.append(updated_purchase)
                        remaining_to_sell = 0
                
                purchase_queue = updated_queue
                
                if remaining_to_sell > 0:
                    warning = f"      ⚠️ WARNING: Tried to sell {remaining_to_sell} more units than available!"
                    print(warning)
                    fifo_operations.append(warning)
        
        # Store remaining purchases
        if purchase_queue:
            cost_basis_dict[symbol] = purchase_queue
            
            total_units = sum(p['units'] for p in purchase_queue)
            total_cost = sum(p['units'] * p['price'] for p in purchase_queue)
            total_commission = sum(p['commission'] for p in purchase_queue)
            
            print(f"   ✅ Final: {total_units:.2f} units, ${total_cost:.2f} cost, ${total_commission:.2f} commission")
        else:
            print(f"   📭 No remaining units after all sales")
        
        fifo_log[symbol] = fifo_operations
    
    return cost_basis_dict, fifo_log

def display_summary(cost_basis_dict):
    """Display cost basis summary."""
    print(f"\n📊 UNIFIED COST BASIS SUMMARY")
    print("=" * 60)
    
    total_symbols = len(cost_basis_dict)
    total_units = sum(sum(r['units'] for r in records) for records in cost_basis_dict.values())
    total_cost = sum(sum(r['units'] * r['price'] for r in records) for records in cost_basis_dict.values())
    
    print(f"Symbols with remaining units: {total_symbols}")
    print(f"Total remaining units: {total_units:,.0f}")
    print(f"Total cost basis: ${total_cost:,.2f}")
    
    print(f"\n📋 By symbol:")
    for symbol, records in sorted(cost_basis_dict.items()):
        symbol_units = sum(r['units'] for r in records)
        symbol_cost = sum(r['units'] * r['price'] for r in records)
        avg_price = symbol_cost / symbol_units if symbol_units > 0 else 0
        
        print(f"   {symbol}: {symbol_units:,.0f} units @ avg ${avg_price:.2f}")

def save_results(cost_basis_dict, fifo_log):
    """Save cost basis and log files."""
    
    cost_basis_file = "COMPLETE_unified_cost_basis_with_FIFO.json"
    log_file = "COMPLETE_fifo_processing_log.json"
    
    try:
        with open(cost_basis_file, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        print(f"✅ Cost basis saved: {cost_basis_file}")
        
        with open(log_file, 'w') as f:
            json.dump(fifo_log, f, indent=2)
        print(f"✅ FIFO log saved: {log_file}")
        
        return cost_basis_file
        
    except Exception as e:
        print(f"❌ Error saving files: {e}")
        return None

def main():
    """Main function to create complete unified cost basis."""
    print("🚀 COMPLETE UNIFIED COST BASIS CREATOR")
    print("=" * 70)
    print("Handles BOTH HTML files and CSV files directly!")
    print("• Parses HTML files from html_folder/")
    print("• Loads manual CSV files from current directory")
    print("• Applies proper FIFO processing")
    print("• Creates accurate cost basis with all data")
    print()
    
    try:
        all_data = []
        
        # Load HTML files directly (no CSV conversion needed!)
        html_data = load_html_files()
        all_data.extend(html_data)
        
        # Load manual CSV files with fixed column mapping
        manual_data = load_manual_csv_files()
        all_data.extend(manual_data)
        
        if not all_data:
            print("❌ No data loaded from any source")
            return None
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Remove duplicates
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(
            subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], 
            keep='first'
        )
        after_count = len(combined_df)
        
        if before_count != after_count:
            print(f"✂️ Removed {before_count - after_count} duplicates")
        
        print(f"\n📊 COMBINED DATA SUMMARY:")
        print(f"   Total transactions: {len(combined_df)}")
        print(f"   Unique symbols: {combined_df['Symbol'].nunique()}")
        print(f"   Sources: {dict(combined_df['Source'].value_counts())}")
        
        # Apply FIFO processing
        cost_basis_dict, fifo_log = apply_fifo_processing(combined_df)
        
        if not cost_basis_dict:
            print("❌ No cost basis calculated")
            return None
        
        # Display summary
        display_summary(cost_basis_dict)
        
        # Save results
        print(f"\n💾 SAVING RESULTS")
        print("=" * 30)
        output_file = save_results(cost_basis_dict, fifo_log)
        
        if output_file:
            print(f"\n🎉 COMPLETE SUCCESS!")
            print(f"✅ Unified cost basis created: {output_file}")
            print(f"✅ Includes data from BOTH HTML and CSV sources")
            print(f"✅ FIFO processing applied correctly")
            print(f"📊 Contains cost basis for {len(cost_basis_dict)} symbols")
            print(f"💡 Ready for accurate CGT calculations!")
        
        return cost_basis_dict
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔍 Full traceback:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()