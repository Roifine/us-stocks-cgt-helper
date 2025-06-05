#!/usr/bin/env python3
"""
Complete FIFO Processing Script

This takes the working debug logic and adds the FIFO cost basis calculation
to create your final cost basis dictionary.
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

def robust_date_parser(date_str):
    """Parse dates in multiple formats and return datetime object for sorting."""
    if not date_str or pd.isna(date_str):
        return datetime(1900, 1, 1)  # Very old date for sorting
    
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
    
    # Fallback - return old date
    return datetime(1900, 1, 1)

def format_date_for_output(date_str):
    """Format date as DD.M.YY for the final output."""
    date_obj = robust_date_parser(date_str)
    if date_obj.year > 1900:
        try:
            # Format as DD.M.YY (remove leading zero from month)
            formatted = date_obj.strftime("%d.%-m.%y")  # Unix style
            return formatted
        except ValueError:
            # Fallback for Windows
            formatted = date_obj.strftime("%d.%m.%y")
            parts = formatted.split('.')
            if len(parts) == 3 and parts[1].startswith('0') and len(parts[1]) == 2:
                parts[1] = parts[1][1:]
            return '.'.join(parts)
    return str(date_str)

def load_csv_file(file_path):
    """Load and check a CSV file."""
    try:
        if not os.path.exists(file_path):
            return None
        df = pd.read_csv(file_path)
        if len(df) == 0:
            return None
        return df
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None

def standardize_html_data(df):
    """Standardize HTML-parsed data (using working debug logic)."""
    expected_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
    if not all(col in df.columns for col in expected_columns):
        return None
    
    try:
        standardized = pd.DataFrame()
        standardized['Symbol'] = df['Symbol']
        standardized['Date'] = df['Trade Date'].astype(str)
        standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
        standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
        standardized['Price'] = pd.to_numeric(df['Price (USD)'], errors='coerce').abs()
        standardized['Commission'] = pd.to_numeric(df['Commission (USD)'], errors='coerce').abs()
        standardized['Source'] = 'HTML_Parsed'
        
        # Remove rows with missing essential data
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
        
        if len(standardized) == 0:
            return None
        
        return standardized
    except Exception as e:
        print(f"❌ Error standardizing HTML data: {e}")
        return None

def standardize_manual_data(df):
    """Standardize manual data (using working debug logic)."""
    try:
        standardized = pd.DataFrame()
        
        # Find columns flexibly
        column_mapping = {}
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['symbol', 'stock', 'ticker']):
                column_mapping['Symbol'] = col
            elif any(keyword in col_lower for keyword in ['date', 'time']):
                column_mapping['Date'] = col
            elif any(keyword in col_lower for keyword in ['activity', 'type', 'action', 'transaction']):
                column_mapping['Activity'] = col
            elif any(keyword in col_lower for keyword in ['quantity', 'shares', 'units', 'amount']):
                column_mapping['Quantity'] = col
            elif any(keyword in col_lower for keyword in ['price', 'cost']):
                column_mapping['Price'] = col
            elif any(keyword in col_lower for keyword in ['commission', 'fee']):
                column_mapping['Commission'] = col
        
        # Check minimum required columns
        required_cols = ['Symbol', 'Date', 'Activity', 'Quantity', 'Price']
        if not all(col in column_mapping for col in required_cols):
            return None
        
        # Build standardized DataFrame
        standardized['Symbol'] = df[column_mapping['Symbol']]
        standardized['Date'] = df[column_mapping['Date']].astype(str)
        
        # Map activities
        activity_mapping = {
            'BUY': 'PURCHASED', 'PURCHASE': 'PURCHASED', 'PURCHASED': 'PURCHASED',
            'SELL': 'SOLD', 'SALE': 'SOLD', 'SOLD': 'SOLD'
        }
        standardized['Activity'] = df[column_mapping['Activity']].str.upper().map(activity_mapping)
        
        standardized['Quantity'] = pd.to_numeric(df[column_mapping['Quantity']], errors='coerce').abs()
        standardized['Price'] = pd.to_numeric(df[column_mapping['Price']], errors='coerce').abs()
        
        # Commission handling
        if 'Commission' in column_mapping:
            standardized['Commission'] = pd.to_numeric(df[column_mapping['Commission']], errors='coerce').abs().fillna(30.0)
        else:
            standardized['Commission'] = 30.0
        
        standardized['Source'] = 'Manual'
        
        # Clean up
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
        
        if len(standardized) == 0:
            return None
        
        return standardized
    except Exception as e:
        print(f"❌ Error standardizing manual data: {e}")
        return None

def load_and_combine_data():
    """Load and combine all data using working logic."""
    print("🔄 LOADING AND COMBINING DATA")
    print("=" * 50)
    
    all_data = []
    
    # Load HTML files
    html_folder = "html_folder"
    if os.path.exists(html_folder):
        csv_files_in_folder = [f for f in os.listdir(html_folder) if f.endswith('.csv')]
        print(f"📁 Found {len(csv_files_in_folder)} CSV files in {html_folder}/")
        
        for csv_file in csv_files_in_folder:
            full_path = os.path.join(html_folder, csv_file)
            df = load_csv_file(full_path)
            
            if df is not None:
                standardized = standardize_html_data(df)
                if standardized is not None:
                    all_data.append(standardized)
                    print(f"   ✅ {csv_file}: {len(standardized)} transactions")
    
    # Load manual files
    manual_files = [f for f in glob.glob("*.csv") if any(keyword in f.lower() for keyword in ['manual', 'personal', 'trade', 'my'])]
    print(f"📁 Found {len(manual_files)} manual CSV files")
    
    for csv_file in manual_files:
        df = load_csv_file(csv_file)
        
        if df is not None:
            standardized = standardize_manual_data(df)
            if standardized is not None:
                all_data.append(standardized)
                print(f"   ✅ {csv_file}: {len(standardized)} transactions")
    
    if not all_data:
        print("❌ No valid data loaded")
        return None
    
    # Combine
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates
    before_count = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], keep='first')
    after_count = len(combined_df)
    
    if before_count != after_count:
        print(f"   ✂️ Removed {before_count - after_count} duplicates")
    
    print(f"✅ Combined: {len(combined_df)} total transactions")
    return combined_df

def apply_fifo_processing(combined_df):
    """Apply FIFO processing to calculate cost basis."""
    print(f"\n🔄 APPLYING FIFO PROCESSING")
    print("=" * 50)
    
    cost_basis_dict = {}
    fifo_log = {}
    
    # Process each symbol
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
            
            if activity == 'PURCHASED':
                purchase = {
                    'units': quantity,
                    'price': price,
                    'commission': commission,
                    'date': date_str
                }
                purchase_queue.append(purchase)
                
                print(f"   📈 BUY: {quantity} units @ ${price:.2f} + ${commission:.2f} on {date_str}")
                fifo_operations.append(f"BUY: {quantity} units @ ${price:.2f} + ${commission:.2f} on {date_str}")
                
            elif activity == 'SOLD':
                units_to_sell = quantity
                
                print(f"   📉 SELL: {units_to_sell} units on {date_str}")
                fifo_operations.append(f"SELL: {units_to_sell} units on {date_str}")
                
                # Apply FIFO
                remaining_to_sell = units_to_sell
                updated_queue = []
                
                for purchase in purchase_queue:
                    if remaining_to_sell <= 0:
                        updated_queue.append(purchase)
                    elif purchase['units'] <= remaining_to_sell:
                        # Use all units from this purchase
                        print(f"      ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f}")
                        fifo_operations.append(f"   ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f}")
                        remaining_to_sell -= purchase['units']
                    else:
                        # Partial use
                        units_used = remaining_to_sell
                        units_remaining = purchase['units'] - units_used
                        
                        print(f"      ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} (kept {units_remaining})")
                        fifo_operations.append(f"   ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} (kept {units_remaining})")
                        
                        # Update purchase
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
            print(f"   📭 No remaining units")
        
        fifo_log[symbol] = fifo_operations
    
    return cost_basis_dict, fifo_log

def display_summary(cost_basis_dict):
    """Display cost basis summary."""
    print(f"\n📊 COST BASIS SUMMARY")
    print("=" * 60)
    
    for symbol, records in cost_basis_dict.items():
        total_units = sum(r['units'] for r in records)
        total_cost = sum(r['units'] * r['price'] for r in records)
        total_commission = sum(r['commission'] for r in records)
        avg_price = total_cost / total_units if total_units > 0 else 0
        
        print(f"\n{symbol}:")
        print(f"  Units: {total_units:,.2f}")
        print(f"  Cost: ${total_cost:,.2f}")
        print(f"  Commission: ${total_commission:,.2f}")
        print(f"  Avg Price: ${avg_price:.2f}")
        print(f"  Records: {len(records)}")

def save_cost_basis(cost_basis_dict, fifo_log):
    """Save cost basis and log files."""
    
    # Save cost basis
    cost_basis_file = "unified_cost_basis_with_FIFO.json"
    try:
        with open(cost_basis_file, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        print(f"✅ Cost basis saved: {cost_basis_file}")
    except Exception as e:
        print(f"❌ Error saving cost basis: {e}")
        return None
    
    # Save FIFO log
    log_file = "fifo_processing_log.json"
    try:
        with open(log_file, 'w') as f:
            json.dump(fifo_log, f, indent=2)
        print(f"✅ FIFO log saved: {log_file}")
    except Exception as e:
        print(f"❌ Error saving log: {e}")
    
    return cost_basis_file

def main():
    """Main function to create cost basis with FIFO."""
    print("🚀 COMPLETE FIFO COST BASIS CREATOR")
    print("=" * 60)
    print("Creating accurate cost basis with FIFO processing...")
    print()
    
    try:
        # Load data
        combined_df = load_and_combine_data()
        
        if combined_df is None:
            print("❌ Failed to load data")
            return None
        
        print(f"\n📊 Loaded {len(combined_df)} transactions:")
        print(f"   BUY: {len(combined_df[combined_df['Activity'] == 'PURCHASED'])}")
        print(f"   SELL: {len(combined_df[combined_df['Activity'] == 'SOLD'])}")
        print(f"   Symbols: {combined_df['Symbol'].nunique()}")
        
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
        output_file = save_cost_basis(cost_basis_dict, fifo_log)
        
        if output_file:
            print(f"\n🎉 SUCCESS!")
            print(f"✅ FIFO-corrected cost basis created: {output_file}")
            print(f"✅ Processing log saved for verification")
            print(f"📊 Contains cost basis for {len(cost_basis_dict)} symbols")
            print(f"💡 Ready for CGT calculations!")
        
        return cost_basis_dict
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔍 Full traceback:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()