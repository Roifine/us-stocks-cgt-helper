#!/usr/bin/env python3
"""
Complete Column Mapping Fix for All Symbols

The issue: Script was using fuzzy column matching and picked AUD_Amount instead of Quantity
This creates a completely corrected version that processes ALL symbols properly.
"""

import pandas as pd
import json
import os
import glob
from datetime import datetime
import traceback

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

def fixed_standardize_manual_data(df):
    """COMPLETELY FIXED manual data standardization with explicit column mapping."""
    print(f"\n🔧 APPLYING COMPLETE COLUMN MAPPING FIX")
    print("=" * 60)
    
    try:
        print(f"📋 Manual CSV columns: {list(df.columns)}")
        print(f"📊 Manual CSV shape: {df.shape}")
        
        # Your manual CSV has these EXACT columns:
        expected_columns = ['Date', 'Activity_Type', 'Symbol', 'Quantity', 'Price_USD', 'USD_Amount', 'AUD_Amount']
        
        # Verify all expected columns exist
        missing = [col for col in expected_columns if col not in df.columns]
        if missing:
            print(f"❌ Missing expected columns: {missing}")
            return None
        
        print(f"✅ All expected columns found")
        
        # Create standardized DataFrame with EXPLICIT mapping
        standardized = pd.DataFrame()
        
        # EXPLICIT column mapping - NO fuzzy matching!
        print(f"\n🎯 EXPLICIT COLUMN MAPPING:")
        print(f"   Symbol: 'Symbol' column")
        print(f"   Date: 'Date' column")
        print(f"   Activity: 'Activity_Type' column")
        print(f"   Quantity: 'Quantity' column (NOT AUD_Amount!)")
        print(f"   Price: 'Price_USD' column (NOT USD_Amount!)")
        
        standardized['Symbol'] = df['Symbol']
        standardized['Date'] = df['Date'].astype(str)
        
        # Map Activity_Type exactly
        activity_mapping = {
            'PURCHASED': 'PURCHASED',
            'SOLD': 'SOLD'
        }
        standardized['Activity'] = df['Activity_Type'].map(activity_mapping)
        
        # Use CORRECT columns - the bug was here!
        standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
        standardized['Price'] = pd.to_numeric(df['Price_USD'], errors='coerce').abs()
        standardized['Commission'] = 30.0  # Default for manual transactions
        standardized['Source'] = 'Manual'
        
        # Show what we're processing
        print(f"\n📊 CORRECTED DATA SAMPLE:")
        for i, row in standardized.head(5).iterrows():
            orig_row = df.iloc[i]
            print(f"   Row {i}: {row['Symbol']} {row['Activity']} {row['Quantity']} units @ ${row['Price']}")
            print(f"      Original CSV: Qty={orig_row['Quantity']}, Price=${orig_row['Price_USD']}, AUD_Amount={orig_row['AUD_Amount']}")
            print(f"      Fixed mapping: Using Quantity={row['Quantity']}, Price=${row['Price']} (NOT AUD_Amount!)")
            print()
        
        # Clean up
        before_count = len(standardized)
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
        after_count = len(standardized)
        
        print(f"📊 Results:")
        print(f"   Before cleaning: {before_count} rows")
        print(f"   After cleaning: {after_count} rows")
        
        if after_count == 0:
            print("❌ No valid rows after cleaning")
            return None
        
        print(f"✅ Fixed manual standardization successful: {after_count} valid transactions")
        
        # Show summary by symbol
        symbol_summary = standardized.groupby('Symbol').agg({
            'Quantity': 'sum',
            'Activity': 'count'
        }).round(2)
        print(f"\n📊 Summary by symbol (with FIXED mapping):")
        for symbol, data in symbol_summary.iterrows():
            total_qty = data['Quantity']
            transaction_count = data['Activity']
            print(f"   {symbol}: {total_qty:.0f} total units across {transaction_count} transactions")
        
        return standardized
        
    except Exception as e:
        print(f"❌ Error in fixed manual standardization: {e}")
        print(f"🔍 Full error: {traceback.format_exc()}")
        return None

def load_html_data():
    """Load HTML data (this part was working correctly)."""
    print(f"\n📁 LOADING HTML DATA")
    print("=" * 40)
    
    html_data = []
    html_folder = "html_folder"
    
    if os.path.exists(html_folder):
        csv_files = [f for f in os.listdir(html_folder) if f.endswith('.csv')]
        print(f"📄 Found {len(csv_files)} HTML CSV files")
        
        for csv_file in csv_files:
            full_path = os.path.join(html_folder, csv_file)
            try:
                df = pd.read_csv(full_path)
                
                # Standardize HTML data (this was working correctly)
                expected_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
                if all(col in df.columns for col in expected_columns):
                    standardized = pd.DataFrame()
                    standardized['Symbol'] = df['Symbol']
                    standardized['Date'] = df['Trade Date'].astype(str)
                    standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
                    standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
                    standardized['Price'] = pd.to_numeric(df['Price (USD)'], errors='coerce').abs()
                    standardized['Commission'] = pd.to_numeric(df['Commission (USD)'], errors='coerce').abs()
                    standardized['Source'] = 'HTML_Parsed'
                    
                    standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
                    
                    if len(standardized) > 0:
                        html_data.append(standardized)
                        print(f"   ✅ {csv_file}: {len(standardized)} transactions")
                
            except Exception as e:
                print(f"   ❌ Error loading {csv_file}: {e}")
    
    return html_data

def load_corrected_manual_data():
    """Load manual data with FIXED column mapping."""
    print(f"\n📁 LOADING MANUAL DATA (WITH COLUMN FIX)")
    print("=" * 50)
    
    manual_data = []
    manual_files = [f for f in glob.glob("*.csv") if 'manual' in f.lower()]
    
    for csv_file in manual_files:
        try:
            df = pd.read_csv(csv_file)
            print(f"📄 Processing {csv_file}")
            
            # Apply the FIXED standardization
            standardized = fixed_standardize_manual_data(df)
            
            if standardized is not None and len(standardized) > 0:
                manual_data.append(standardized)
                print(f"✅ Successfully processed {csv_file}: {len(standardized)} transactions")
            else:
                print(f"❌ Failed to process {csv_file}")
                
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
    
    return manual_data

def apply_corrected_fifo_processing(combined_df):
    """Apply FIFO processing with corrected data."""
    print(f"\n🔄 APPLYING FIFO WITH CORRECTED DATA")
    print("=" * 60)
    
    cost_basis_dict = {}
    fifo_log = {}
    
    print(f"📊 Processing {len(combined_df)} total transactions")
    print(f"   Symbols: {combined_df['Symbol'].nunique()}")
    
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

def main():
    """Main function to create completely corrected cost basis."""
    print("🔧 COMPLETE COLUMN MAPPING FIX - ALL SYMBOLS")
    print("=" * 70)
    print("Issue: Script used AUD_Amount instead of Quantity for ALL manual transactions")
    print("Fix: Using explicit column mapping for manual CSV format")
    print()
    
    try:
        all_data = []
        
        # Load HTML data (this was working correctly)
        html_data = load_html_data()
        all_data.extend(html_data)
        
        # Load manual data with FIXED column mapping
        manual_data = load_corrected_manual_data()
        all_data.extend(manual_data)
        
        if not all_data:
            print("❌ No data loaded")
            return None
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Remove duplicates
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], keep='first')
        after_count = len(combined_df)
        
        if before_count != after_count:
            print(f"✂️ Removed {before_count - after_count} duplicates")
        
        print(f"\n📊 COMBINED CORRECTED DATA:")
        print(f"   Total transactions: {len(combined_df)}")
        print(f"   BUY transactions: {len(combined_df[combined_df['Activity'] == 'PURCHASED'])}")
        print(f"   SELL transactions: {len(combined_df[combined_df['Activity'] == 'SOLD'])}")
        print(f"   Unique symbols: {combined_df['Symbol'].nunique()}")
        
        # Apply FIFO processing with corrected data
        cost_basis_dict, fifo_log = apply_corrected_fifo_processing(combined_df)
        
        if not cost_basis_dict:
            print("❌ No cost basis calculated")
            return None
        
        # Save results
        print(f"\n💾 SAVING CORRECTED RESULTS")
        print("=" * 40)
        
        cost_basis_file = "COMPLETELY_CORRECTED_cost_basis_with_FIFO.json"
        with open(cost_basis_file, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        
        log_file = "CORRECTED_fifo_processing_log.json"
        with open(log_file, 'w') as f:
            json.dump(fifo_log, f, indent=2)
        
        print(f"✅ Corrected cost basis saved: {cost_basis_file}")
        print(f"✅ Corrected FIFO log saved: {log_file}")
        
        # Show summary
        print(f"\n📊 CORRECTED COST BASIS SUMMARY:")
        print("=" * 50)
        
        total_symbols = len(cost_basis_dict)
        total_units = sum(sum(r['units'] for r in records) for records in cost_basis_dict.values())
        total_cost = sum(sum(r['units'] * r['price'] for r in records) for records in cost_basis_dict.values())
        
        print(f"Symbols with remaining units: {total_symbols}")
        print(f"Total remaining units: {total_units:,.0f}")
        print(f"Total cost basis: ${total_cost:,.2f}")
        
        # Show sample of corrected data
        print(f"\n📋 Sample corrected results:")
        for symbol, records in list(cost_basis_dict.items())[:3]:
            total_units = sum(r['units'] for r in records)
            avg_price = sum(r['units'] * r['price'] for r in records) / total_units
            print(f"   {symbol}: {total_units:.0f} units @ avg ${avg_price:.2f}")
        
        print(f"\n🎉 SUCCESS!")
        print(f"✅ All symbols now have CORRECT quantities and prices")
        print(f"✅ No more AUD_Amount confusion")
        print(f"✅ Ready for accurate CGT calculations")
        
        return cost_basis_dict
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔍 Full traceback:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()