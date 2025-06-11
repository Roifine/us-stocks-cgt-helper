#!/usr/bin/env python3
"""
Sales Transaction Extractor
A script to extract and analyze sales transactions from trading CSV files.
"""

import pandas as pd
import os
from datetime import datetime

def get_csv_file():
    """Get CSV file path from user input with validation."""
    while True:
        file_path = input("\nEnter the path to your CSV file: ").strip()
        
        # Remove quotes if user wrapped path in quotes
        file_path = file_path.strip('"\'')
        
        if os.path.exists(file_path):
            if file_path.lower().endswith('.csv'):
                return file_path
            else:
                print("❌ Error: File must be a CSV file (.csv extension)")
        else:
            print("❌ Error: File not found. Please check the path and try again.")

def load_csv_data(file_path):
    """Load and validate CSV data."""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"✅ Successfully loaded CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("Could not read file with any supported encoding")
            
        return df
    
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return None

def identify_columns(df):
    """Identify relevant columns in the CSV."""
    columns = df.columns.tolist()
    print(f"\nFound columns: {columns}")
    
    # Common column name patterns
    type_patterns = ['type', 'transaction_type', 'action', 'side']
    symbol_patterns = ['symbol', 'ticker', 'stock', 'instrument']
    date_patterns = ['date', 'trade_date', 'transaction_date', 'time']
    quantity_patterns = ['quantity', 'shares', 'amount', 'qty']
    price_patterns = ['price', 'unit_price', 'price_per_share']
    proceeds_patterns = ['proceeds', 'total', 'gross_amount', 'value']
    commission_patterns = ['commission', 'fee', 'fees', 'cost']
    
    def find_column(patterns, columns):
        for pattern in patterns:
            for col in columns:
                if pattern.lower() in col.lower():
                    return col
        return None
    
    # Auto-detect columns
    detected = {
        'type': find_column(type_patterns, columns),
        'symbol': find_column(symbol_patterns, columns),
        'date': find_column(date_patterns, columns),
        'quantity': find_column(quantity_patterns, columns),
        'price': find_column(price_patterns, columns),
        'proceeds': find_column(proceeds_patterns, columns),
        'commission': find_column(commission_patterns, columns)
    }
    
    print("\n🔍 Auto-detected columns:")
    for key, value in detected.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key.title()}: {value}")
    
    return detected

def get_user_column_mapping(df, detected):
    """Allow user to confirm or modify column mappings."""
    columns = df.columns.tolist()
    mapping = {}
    
    print(f"\nAvailable columns: {', '.join(columns)}")
    print("\nPlease confirm or specify the correct column names:")
    print("(Press Enter to use auto-detected value, or type column name)")
    
    required_fields = ['type', 'symbol', 'date']
    optional_fields = ['quantity', 'price', 'proceeds', 'commission']
    
    for field in required_fields + optional_fields:
        while True:
            default = detected.get(field, '')
            prompt = f"{field.title()} column"
            if default:
                prompt += f" [{default}]"
            prompt += ": "
            
            user_input = input(prompt).strip()
            
            if not user_input and default:
                mapping[field] = default
                break
            elif user_input in columns:
                mapping[field] = user_input
                break
            elif not user_input and field in optional_fields:
                mapping[field] = None
                break
            else:
                if field in required_fields:
                    print(f"❌ '{field}' is required. Please enter a valid column name.")
                else:
                    print(f"❌ Column '{user_input}' not found. Available: {', '.join(columns)}")
    
    return mapping

def extract_sales(df, mapping):
    """Extract sales transactions from the dataframe."""
    type_col = mapping['type']
    
    if type_col not in df.columns:
        print(f"❌ Error: Column '{type_col}' not found")
        return None
    
    # Find sales - try common variations
    sales_keywords = ['SELL', 'sell', 'Sell', 'SALE', 'sale', 'Sale', 'S']
    
    # Show unique values in type column
    unique_types = df[type_col].unique()
    print(f"\nUnique transaction types found: {list(unique_types)}")
    
    # Try to find sales automatically
    sales_df = None
    for keyword in sales_keywords:
        if keyword in unique_types:
            sales_df = df[df[type_col] == keyword].copy()
            print(f"✅ Found {len(sales_df)} sales transactions using '{keyword}'")
            break
    
    if sales_df is None or len(sales_df) == 0:
        print("❌ No sales found with common keywords.")
        print("Please specify the exact value for sales transactions:")
        sale_type = input(f"Enter the value for sales from {list(unique_types)}: ").strip()
        if sale_type in unique_types:
            sales_df = df[df[type_col] == sale_type].copy()
        else:
            print("❌ Invalid sale type specified")
            return None
    
    return sales_df

def format_sales_output(sales_df, mapping):
    """Format and display sales transactions."""
    if sales_df is None or len(sales_df) == 0:
        print("❌ No sales transactions to display")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 SALES TRANSACTIONS SUMMARY")
    print(f"{'='*60}")
    print(f"Total Sales Transactions: {len(sales_df)}")
    
    # Calculate totals if proceeds/commission columns exist
    if mapping.get('proceeds') and mapping['proceeds'] in sales_df.columns:
        total_proceeds = sales_df[mapping['proceeds']].sum()
        print(f"Total Gross Proceeds: ${total_proceeds:,.2f}")
        
        if mapping.get('commission') and mapping['commission'] in sales_df.columns:
            total_commission = sales_df[mapping['commission']].sum()
            net_proceeds = total_proceeds + total_commission  # Assuming commission is negative
            print(f"Total Commissions: ${total_commission:,.2f}")
            print(f"Total Net Proceeds: ${net_proceeds:,.2f}")
    
    print(f"\n{'='*60}")
    print("📋 INDIVIDUAL TRANSACTIONS:")
    print(f"{'='*60}")
    
    # Display each transaction
    for idx, row in sales_df.iterrows():
        print(f"\nTransaction {sales_df.index.get_loc(idx) + 1}:")
        
        for field, col_name in mapping.items():
            if col_name and col_name in sales_df.columns:
                value = row[col_name]
                if field in ['price', 'proceeds', 'commission'] and pd.notna(value):
                    print(f"  {field.title()}: ${value:,.2f}")
                else:
                    print(f"  {field.title()}: {value}")

def save_sales_csv(sales_df, original_file):
    """Save sales transactions to a new CSV file."""
    save_option = input("\n💾 Save sales transactions to a new CSV? (y/n): ").strip().lower()
    
    if save_option in ['y', 'yes']:
        # Generate output filename
        base_name = os.path.splitext(original_file)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_name}_sales_only_{timestamp}.csv"
        
        try:
            sales_df.to_csv(output_file, index=False)
            print(f"✅ Sales transactions saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving file: {e}")

def main():
    """Main function to run the sales extractor."""
    print("🚀 Sales Transaction Extractor")
    print("="*40)
    
    while True:
        # Get CSV file
        csv_file = get_csv_file()
        
        # Load data
        df = load_csv_data(csv_file)
        if df is None:
            continue
        
        print(f"\n📈 Loaded {len(df)} total transactions")
        
        # Identify columns
        detected_columns = identify_columns(df)
        
        # Get user confirmation on column mapping
        column_mapping = get_user_column_mapping(df, detected_columns)
        
        # Extract sales
        sales_transactions = extract_sales(df, column_mapping)
        
        # Display results
        format_sales_output(sales_transactions, column_mapping)
        
        # Option to save
        if sales_transactions is not None and len(sales_transactions) > 0:
            save_sales_csv(sales_transactions, csv_file)
        
        # Ask if user wants to process another file
        another = input("\n🔄 Process another CSV file? (y/n): ").strip().lower()
        if another not in ['y', 'yes']:
            break
    
    print("\n👋 Thanks for using Sales Transaction Extractor!")

if __name__ == "__main__":
    main()