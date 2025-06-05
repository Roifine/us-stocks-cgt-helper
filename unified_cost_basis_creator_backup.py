#!/usr/bin/env python3
"""
Unified Cost Basis Creator

This script combines transactions from:
1. HTML-parsed CSV files (YYYY-MM-DD format, BUY/SELL)
2. Manual CSV files (MM/DD/YY format, PURCHASED/SOLD)

And creates a unified cost basis dictionary.
"""

import pandas as pd
import json
import os
import glob
from datetime import datetime

def standardize_html_parsed_data(df):
    """
    Standardize HTML-parsed CSV data to common format.
    
    Expected columns: Symbol,Trade Date,Type,Quantity,Price (USD),Proceeds (USD),Commission (USD)
    """
    standardized = df.copy()
    
    # Rename columns to standard format
    column_mapping = {
        'Trade Date': 'Date',
        'Type': 'Activity_Type',
        'Price (USD)': 'Price_USD',
        'Proceeds (USD)': 'USD_Amount',
        'Commission (USD)': 'Commission_USD'
    }
    
    standardized = standardized.rename(columns=column_mapping)
    
    # Convert date format from "2023-09-18 10:39:42" to "18/09/23"
    def convert_html_date(date_str):
        try:
            # Parse the datetime string
            dt = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
            # Return in DD/MM/YY format
            return dt.strftime('%d/%m/%y')
        except:
            print(f"⚠️ Could not convert date: {date_str}")
            return date_str
    
    standardized['Date'] = standardized['Date'].apply(convert_html_date)
    
    # Standardize activity types
    activity_mapping = {
        'BUY': 'PURCHASED',
        'SELL': 'SOLD'
    }
    standardized['Activity_Type'] = standardized['Activity_Type'].map(activity_mapping)
    
    # Add AUD_Amount column (placeholder - you may want to add exchange rates later)
    standardized['AUD_Amount'] = standardized['USD_Amount'] * 1.5  # Approximate conversion
    
    # Add Commission to USD_Amount (HTML format has separate commission)
    standardized['USD_Amount'] = standardized['USD_Amount'] + standardized['Commission_USD']
    
    print(f"✅ Standardized {len(standardized)} HTML-parsed transactions")
    return standardized

def standardize_manual_data(df):
    """
    Standardize manual CSV data to common format.
    
    Expected columns: Date,Activity_Type,Symbol,Quantity,Price_USD,USD_Amount,AUD_Amount
    """
    standardized = df.copy()
    
    # Convert date format from "08/04/21" to "08/04/23" (DD/MM/YY)
    def convert_manual_date(date_str):
        try:
            # Parse MM/DD/YY format
            dt = datetime.strptime(date_str, '%m/%d/%y')
            # Return in DD/MM/YY format
            return dt.strftime('%d/%m/%y')
        except:
            print(f"⚠️ Could not convert date: {date_str}")
            return date_str
    
    standardized['Date'] = standardized['Date'].apply(convert_manual_date)
    
    print(f"✅ Standardized {len(standardized)} manual transactions")
    return standardized

def load_html_parsed_csvs(csv_folder_path):
    """
    Load all HTML-parsed CSV files from a folder.
    """
    csv_files = glob.glob(os.path.join(csv_folder_path, "*_parsed.csv"))
    
    if not csv_files:
        print(f"⚠️ No *_parsed.csv files found in {csv_folder_path}")
        return pd.DataFrame()
    
    all_data = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['Source_File'] = os.path.basename(csv_file)
            standardized = standardize_html_parsed_data(df)
            all_data.append(standardized)
            print(f"📄 Loaded {len(df)} transactions from {os.path.basename(csv_file)}")
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        print(f"📊 Total HTML-parsed transactions: {len(combined)}")
        return combined
    else:
        return pd.DataFrame()

def load_manual_csv(manual_csv_path):
    """
    Load manual CSV file.
    """
    try:
        df = pd.read_csv(manual_csv_path)
        df['Source_File'] = os.path.basename(manual_csv_path)
        standardized = standardize_manual_data(df)
        print(f"📄 Loaded {len(df)} manual transactions from {os.path.basename(manual_csv_path)}")
        return standardized
    except Exception as e:
        print(f"❌ Error loading manual CSV: {e}")
        return pd.DataFrame()

def create_unified_cost_basis_dictionary(html_csv_folder, manual_csv_path, target_financial_year=None):
    """
    Create unified cost basis dictionary from both HTML-parsed and manual CSV files.
    
    Args:
        html_csv_folder (str): Path to folder containing *_parsed.csv files
        manual_csv_path (str): Path to manual CSV file
        target_financial_year (str): Financial year to exclude sales from (e.g., "2024-25")
    
    Returns:
        dict: Unified cost basis dictionary
    """
    
    print("🔄 CREATING UNIFIED COST BASIS DICTIONARY")
    print("=" * 60)
    
    # Load HTML-parsed data
    html_data = load_html_parsed_csvs(html_csv_folder)
    
    # Load manual data  
    manual_data = load_manual_csv(manual_csv_path)
    
    # Combine all data
    if len(html_data) > 0 and len(manual_data) > 0:
        all_data = pd.concat([html_data, manual_data], ignore_index=True)
    elif len(html_data) > 0:
        all_data = html_data
    elif len(manual_data) > 0:
        all_data = manual_data
    else:
        print("❌ No transaction data found")
        return {}
    
    print(f"\n📊 COMBINED DATA SUMMARY:")
    print(f"Total transactions: {len(all_data)}")
    print(f"Date range: {all_data['Date'].min()} to {all_data['Date'].max()}")
    print(f"Activity types: {all_data['Activity_Type'].value_counts().to_dict()}")
    print(f"Unique symbols: {sorted(all_data['Symbol'].unique())}")
    
    # Filter for BUY transactions only
    buys_df = all_data[all_data['Activity_Type'] == 'PURCHASED'].copy()
    
    if len(buys_df) == 0:
        print("❌ No PURCHASED transactions found")
        return {}
    
    print(f"\n📈 BUY TRANSACTIONS: {len(buys_df)}")
    
    # Create cost basis dictionary
    cost_basis_dict = {}
    
    for index, row in buys_df.iterrows():
        symbol = row['Symbol']
        quantity = abs(row['Quantity'])
        price_per_unit_usd = abs(row['Price_USD'])
        
        # Calculate commission per unit (if commission exists separately)
        if 'Commission_USD' in row and pd.notna(row['Commission_USD']):
            commission_usd = abs(row['Commission_USD'])
        else:
            commission_usd = 0
        
        # Format date
        trade_date = row['Date']
        
        # Create record
        record = {
            'units': quantity,
            'price': round(price_per_unit_usd, 2),
            'commission': round(commission_usd, 2),
            'date': trade_date,
            'source_file': row.get('Source_File', 'unknown')
        }
        
        # Add to dictionary
        if symbol not in cost_basis_dict:
            cost_basis_dict[symbol] = []
        
        cost_basis_dict[symbol].append(record)
    
    # Sort each symbol's records by date
    for symbol in cost_basis_dict:
        cost_basis_dict[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d/%m/%y"))
    
    print(f"\n✅ Created cost basis dictionary for {len(cost_basis_dict)} symbols")
    
    return cost_basis_dict

def save_cost_basis_dictionary(cost_basis_dict, output_file_path):
    """Save cost basis dictionary to JSON file."""
    try:
        # Clean version for JSON (remove source_file info)
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
        print(f"💾 Cost basis dictionary saved to: {output_file_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving JSON file: {e}")
        return False

def display_cost_basis_summary(cost_basis_dict):
    """Display summary of cost basis dictionary."""
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
        print(f"  Total Cost: ${total_cost:,.2f} USD")
        print(f"  Total Commission: ${total_commission:,.2f} USD")
        print(f"  Average Price: ${avg_price:.2f} USD per unit")
        print(f"  Number of Purchases: {len(records)}")

def main():
    """Main function."""
    print("🚀 UNIFIED COST BASIS CREATOR")
    print("=" * 50)
    
    # File paths - UPDATE THESE
    html_csv_folder = "/Users/roifine/My python projects/Ozi_Tax_Agent/csv_folder"
    manual_csv_path = "manual_csv_path.csv"
    output_json_path = "unified_cost_basis_dictionary.json"
    
    # Create unified cost basis dictionary
    cost_basis_dict = create_unified_cost_basis_dictionary(
        html_csv_folder, 
        manual_csv_path
    )
    
    if not cost_basis_dict:
        print("❌ Failed to create cost basis dictionary")
        return
    
    # Display summary
    display_cost_basis_summary(cost_basis_dict)
    
    # Save to JSON
    if save_cost_basis_dictionary(cost_basis_dict, output_json_path):
        print(f"\n🎉 SUCCESS!")
        print(f"📄 Unified cost basis saved to: {output_json_path}")
        print(f"📊 Ready for CGT calculations!")
    else:
        print("❌ Failed to save cost basis dictionary")

if __name__ == "__main__":
    main()