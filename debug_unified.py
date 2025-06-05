#!/usr/bin/env python3
"""
Debug Version of Unified Cost Basis Script

This version adds detailed debugging to identify where the NoneType error is coming from.
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

def debug_csv_file(file_path):
    """Debug a CSV file to see its structure."""
    print(f"\n🔍 DEBUGGING FILE: {file_path}")
    print("=" * 60)
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ File does not exist: {file_path}")
            return None
        
        # Get file size
        file_size = os.path.getsize(file_path)
        print(f"📁 File size: {file_size:,} bytes")
        
        # Try to read the file
        df = pd.read_csv(file_path)
        print(f"✅ Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")
        
        # Show column names
        print(f"📋 Columns: {list(df.columns)}")
        
        # Show first few rows
        print(f"\n📊 First 3 rows:")
        print(df.head(3).to_string())
        
        # Check for empty dataframe
        if len(df) == 0:
            print(f"⚠️ WARNING: DataFrame is empty")
            return None
        
        return df
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        print(f"🔍 Full error: {traceback.format_exc()}")
        return None

def debug_standardize_html_data(df, file_path):
    """Debug version of HTML data standardization."""
    print(f"\n🔄 DEBUGGING HTML STANDARDIZATION FOR: {os.path.basename(file_path)}")
    print("=" * 60)
    
    if df is None:
        print("❌ Input DataFrame is None")
        return None
    
    # Check required columns
    expected_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
    missing_columns = [col for col in expected_columns if col not in df.columns]
    
    print(f"📋 Expected columns: {expected_columns}")
    print(f"📋 Available columns: {list(df.columns)}")
    
    if missing_columns:
        print(f"❌ Missing columns: {missing_columns}")
        
        # Try to find similar columns
        print(f"\n🔍 Looking for similar columns:")
        for missing_col in missing_columns:
            similar_cols = [col for col in df.columns if missing_col.lower().replace(' ', '').replace('(', '').replace(')', '') in col.lower().replace(' ', '').replace('(', '').replace(')', '')]
            if similar_cols:
                print(f"   {missing_col} might be: {similar_cols}")
        
        return None
    
    try:
        # Create standardized DataFrame
        standardized = pd.DataFrame()
        
        print(f"\n🔄 Standardizing columns...")
        
        # Symbol
        standardized['Symbol'] = df['Symbol']
        print(f"   ✅ Symbol: {len(standardized['Symbol'].dropna())} valid entries")
        
        # Date with robust parsing
        def debug_date_parser(date_str):
            if pd.isna(date_str):
                return None
            try:
                # Simple date parsing for debugging
                if isinstance(date_str, str):
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d.%m.%y']:
                        try:
                            parsed = datetime.strptime(date_str, fmt)
                            return parsed.strftime('%d.%m.%y')
                        except:
                            continue
                return str(date_str)  # Return as-is if can't parse
            except:
                return None
        
        standardized['Date'] = df['Trade Date'].apply(debug_date_parser)
        valid_dates = len(standardized['Date'].dropna())
        print(f"   ✅ Date: {valid_dates}/{len(df)} dates parsed successfully")
        
        # Activity
        standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
        valid_activities = len(standardized['Activity'].dropna())
        print(f"   ✅ Activity: {valid_activities}/{len(df)} activities mapped")
        
        # Quantity
        standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
        valid_quantities = len(standardized['Quantity'].dropna())
        print(f"   ✅ Quantity: {valid_quantities}/{len(df)} quantities parsed")
        
        # Price
        standardized['Price'] = pd.to_numeric(df['Price (USD)'], errors='coerce').abs()
        valid_prices = len(standardized['Price'].dropna())
        print(f"   ✅ Price: {valid_prices}/{len(df)} prices parsed")
        
        # Commission
        standardized['Commission'] = pd.to_numeric(df['Commission (USD)'], errors='coerce').abs()
        valid_commissions = len(standardized['Commission'].dropna())
        print(f"   ✅ Commission: {valid_commissions}/{len(df)} commissions parsed")
        
        standardized['Source'] = 'HTML_Parsed'
        
        # Remove rows with missing essential data
        essential_columns = ['Symbol', 'Date', 'Activity', 'Quantity', 'Price']
        before_count = len(standardized)
        standardized = standardized.dropna(subset=essential_columns)
        after_count = len(standardized)
        
        print(f"\n📊 Results:")
        print(f"   Before cleaning: {before_count} rows")
        print(f"   After cleaning: {after_count} rows")
        print(f"   Removed: {before_count - after_count} rows with missing data")
        
        if after_count == 0:
            print(f"❌ No valid rows remaining after standardization")
            return None
        
        print(f"✅ Standardization successful: {after_count} valid transactions")
        return standardized
        
    except Exception as e:
        print(f"❌ Error during standardization: {e}")
        print(f"🔍 Full error: {traceback.format_exc()}")
        return None

def debug_standardize_manual_data(df, file_path):
    """Debug version of manual data standardization."""
    print(f"\n🔄 DEBUGGING MANUAL STANDARDIZATION FOR: {os.path.basename(file_path)}")
    print("=" * 60)
    
    if df is None:
        print("❌ Input DataFrame is None")
        return None
    
    print(f"📋 Available columns: {list(df.columns)}")
    print(f"📊 DataFrame shape: {df.shape}")
    
    # Show sample data
    print(f"\n📊 Sample data:")
    print(df.head(3).to_string())
    
    try:
        standardized = pd.DataFrame()
        
        # Try to map columns flexibly
        column_mapping = {}
        
        # Find symbol column
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['symbol', 'stock', 'ticker']):
                column_mapping['Symbol'] = col
                break
        
        # Find date column
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['date', 'time']):
                column_mapping['Date'] = col
                break
        
        # Find activity column
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['activity', 'type', 'action', 'transaction']):
                column_mapping['Activity'] = col
                break
        
        # Find quantity column
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['quantity', 'shares', 'units', 'amount']):
                column_mapping['Quantity'] = col
                break
        
        # Find price column
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['price', 'cost']):
                column_mapping['Price'] = col
                break
        
        # Find commission column
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['commission', 'fee']):
                column_mapping['Commission'] = col
                break
        
        print(f"\n🔍 Column mapping detected:")
        for key, value in column_mapping.items():
            print(f"   {key}: {value}")
        
        # Check if we have minimum required columns
        required_cols = ['Symbol', 'Date', 'Activity', 'Quantity', 'Price']
        missing_required = [col for col in required_cols if col not in column_mapping]
        
        if missing_required:
            print(f"❌ Missing required columns: {missing_required}")
            print(f"💡 Available columns: {list(df.columns)}")
            return None
        
        # Build standardized DataFrame
        if 'Symbol' in column_mapping:
            standardized['Symbol'] = df[column_mapping['Symbol']]
        
        if 'Date' in column_mapping:
            # Simple date handling for debugging
            standardized['Date'] = df[column_mapping['Date']].astype(str)
        
        if 'Activity' in column_mapping:
            # Map activities
            activity_mapping = {
                'BUY': 'PURCHASED', 'PURCHASE': 'PURCHASED', 'PURCHASED': 'PURCHASED',
                'SELL': 'SOLD', 'SALE': 'SOLD', 'SOLD': 'SOLD'
            }
            standardized['Activity'] = df[column_mapping['Activity']].str.upper().map(activity_mapping)
        
        if 'Quantity' in column_mapping:
            standardized['Quantity'] = pd.to_numeric(df[column_mapping['Quantity']], errors='coerce').abs()
        
        if 'Price' in column_mapping:
            standardized['Price'] = pd.to_numeric(df[column_mapping['Price']], errors='coerce').abs()
        
        # Commission handling
        if 'Commission' in column_mapping:
            standardized['Commission'] = pd.to_numeric(df[column_mapping['Commission']], errors='coerce').abs().fillna(30.0)
        else:
            standardized['Commission'] = 30.0  # Default
        
        standardized['Source'] = 'Manual'
        
        # Clean up
        before_count = len(standardized)
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
        after_count = len(standardized)
        
        print(f"\n📊 Results:")
        print(f"   Before cleaning: {before_count} rows")
        print(f"   After cleaning: {after_count} rows")
        
        if after_count == 0:
            print(f"❌ No valid rows remaining after standardization")
            return None
        
        print(f"✅ Manual standardization successful: {after_count} valid transactions")
        return standardized
        
    except Exception as e:
        print(f"❌ Error during manual standardization: {e}")
        print(f"🔍 Full error: {traceback.format_exc()}")
        return None

def debug_load_and_combine_data(html_csv_files, manual_csv_files):
    """Debug version of data loading and combining."""
    print("=" * 60)
    print("🔄 DEBUG: LOADING AND COMBINING DATA")
    print("=" * 60)
    
    all_data = []
    
    # Debug HTML files
    if html_csv_files:
        print(f"\n📄 Processing {len(html_csv_files)} HTML files:")
        for csv_file in html_csv_files:
            print(f"\n{'='*40}")
            print(f"Processing HTML file: {csv_file}")
            print(f"{'='*40}")
            
            # Debug the CSV file first
            df = debug_csv_file(csv_file)
            
            if df is not None:
                # Debug standardization
                standardized = debug_standardize_html_data(df, csv_file)
                
                if standardized is not None and len(standardized) > 0:
                    all_data.append(standardized)
                    print(f"✅ Successfully processed {csv_file}: {len(standardized)} transactions")
                else:
                    print(f"❌ Standardization failed for {csv_file}")
            else:
                print(f"❌ Could not load {csv_file}")
    
    # Debug manual files
    if manual_csv_files:
        print(f"\n📄 Processing {len(manual_csv_files)} manual files:")
        for csv_file in manual_csv_files:
            print(f"\n{'='*40}")
            print(f"Processing manual file: {csv_file}")
            print(f"{'='*40}")
            
            # Debug the CSV file first
            df = debug_csv_file(csv_file)
            
            if df is not None:
                # Debug standardization
                standardized = debug_standardize_manual_data(df, csv_file)
                
                if standardized is not None and len(standardized) > 0:
                    all_data.append(standardized)
                    print(f"✅ Successfully processed {csv_file}: {len(standardized)} transactions")
                else:
                    print(f"❌ Standardization failed for {csv_file}")
            else:
                print(f"❌ Could not load {csv_file}")
    
    # Combine results
    print(f"\n📊 COMBINATION RESULTS:")
    print(f"=" * 40)
    print(f"DataFrames to combine: {len(all_data)}")
    
    if not all_data:
        print("❌ No valid data to combine")
        return None
    
    try:
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"✅ Successfully combined data: {len(combined_df)} total transactions")
        
        # Show summary
        print(f"\n📋 Combined data summary:")
        print(f"   Symbols: {combined_df['Symbol'].nunique()}")
        print(f"   Activities: {dict(combined_df['Activity'].value_counts())}")
        print(f"   Sources: {dict(combined_df['Source'].value_counts())}")
        
        return combined_df
        
    except Exception as e:
        print(f"❌ Error combining data: {e}")
        print(f"🔍 Full error: {traceback.format_exc()}")
        return None

def find_files():
    """Find files with debug output."""
    html_parsed_files = []
    manual_files = []
    
    print("🔍 DEBUG: SEARCHING FOR FILES")
    print("=" * 50)
    
    # Look for HTML-parsed CSV files in html_folder subdirectory
    html_folder = "html_folder"
    print(f"📁 Looking for HTML folder: {html_folder}")
    
    if os.path.exists(html_folder):
        print(f"✅ Found {html_folder} directory")
        
        # List all files in html_folder
        all_files_in_folder = os.listdir(html_folder)
        csv_files_in_folder = [f for f in all_files_in_folder if f.endswith('.csv')]
        
        print(f"📄 Files in {html_folder}: {all_files_in_folder}")
        print(f"📄 CSV files in {html_folder}: {csv_files_in_folder}")
        
        # Add full paths
        for csv_file in csv_files_in_folder:
            full_path = os.path.join(html_folder, csv_file)
            html_parsed_files.append(full_path)
            print(f"   ✅ Added: {full_path}")
    else:
        print(f"❌ {html_folder} directory not found")
    
    # Look for manual files in current directory
    print(f"\n📁 Looking for manual files in current directory")
    current_csv_files = glob.glob("*.csv")
    print(f"📄 CSV files in current directory: {current_csv_files}")
    
    for csv_file in current_csv_files:
        if any(keyword in csv_file.lower() for keyword in ['manual', 'personal', 'trade', 'my']):
            manual_files.append(csv_file)
            print(f"   ✅ Added manual file: {csv_file}")
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"   HTML files: {len(html_parsed_files)}")
    print(f"   Manual files: {len(manual_files)}")
    
    return html_parsed_files, manual_files

def main():
    """Debug version of main function."""
    print("🐛 DEBUG VERSION - UNIFIED COST BASIS CREATOR")
    print("=" * 70)
    print("This debug version will show detailed information about what's happening")
    print("at each step to identify where the NoneType error is coming from.")
    print()
    
    try:
        # Find files with debug output
        html_files, manual_files = find_files()
        
        if not html_files and not manual_files:
            print("❌ No files found to process")
            return None
        
        # Load and combine data with debug output
        combined_df = debug_load_and_combine_data(html_files, manual_files)
        
        if combined_df is None:
            print("❌ Failed to load and combine data")
            return None
        
        print(f"\n🎉 SUCCESS!")
        print(f"✅ Loaded {len(combined_df)} total transactions")
        print(f"✅ Ready to proceed with FIFO processing")
        
        return combined_df
        
    except Exception as e:
        print(f"\n❌ DEBUG ERROR: {e}")
        print(f"🔍 Full traceback:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()