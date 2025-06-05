#!/usr/bin/env python3
"""
HTML Files Diagnostic

Check what CFLT and other data exists in the HTML files to see why they're not being loaded.
"""

import pandas as pd
import os

def check_html_files():
    """Check what's in the HTML folder files."""
    print("🔍 HTML FILES DIAGNOSTIC")
    print("=" * 50)
    
    html_folder = "html_folder"
    
    if not os.path.exists(html_folder):
        print(f"❌ {html_folder} directory not found!")
        return
    
    files = os.listdir(html_folder)
    csv_files = [f for f in files if f.endswith('.csv')]
    
    print(f"📁 Files in {html_folder}: {files}")
    print(f"📄 CSV files: {csv_files}")
    
    if not csv_files:
        print("❌ No CSV files found in html_folder!")
        return
    
    for csv_file in csv_files:
        full_path = os.path.join(html_folder, csv_file)
        print(f"\n" + "="*60)
        print(f"📄 ANALYZING: {csv_file}")
        print("="*60)
        
        try:
            df = pd.read_csv(full_path)
            print(f"✅ Loaded successfully: {len(df)} rows, {len(df.columns)} columns")
            print(f"📋 Columns: {list(df.columns)}")
            
            # Check for CFLT specifically
            if 'Symbol' in df.columns:
                cflt_data = df[df['Symbol'] == 'CFLT']
                if len(cflt_data) > 0:
                    print(f"\n🎯 FOUND {len(cflt_data)} CFLT TRANSACTIONS:")
                    for i, row in cflt_data.iterrows():
                        print(f"   Row {i}: {row['Symbol']} {row['Type']} {row['Quantity']} @ ${row['Price (USD)']} on {row['Trade Date']}")
                else:
                    print(f"⚠️ No CFLT transactions found")
                
                # Show all unique symbols
                unique_symbols = df['Symbol'].unique()
                print(f"\n🏷️ All symbols in {csv_file}: {sorted(unique_symbols)}")
                print(f"📊 Total transactions by symbol:")
                symbol_counts = df['Symbol'].value_counts()
                for symbol, count in symbol_counts.head(10).items():
                    print(f"   {symbol}: {count} transactions")
            else:
                print(f"❌ No 'Symbol' column found")
            
            # Show sample data
            print(f"\n📊 Sample data (first 3 rows):")
            print(df.head(3).to_string())
            
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")

def check_expected_html_format():
    """Check if HTML files have the expected format."""
    print(f"\n🔍 EXPECTED HTML FORMAT CHECK")
    print("=" * 50)
    
    expected_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
    print(f"📋 Expected columns: {expected_columns}")
    
    html_folder = "html_folder"
    if os.path.exists(html_folder):
        csv_files = [f for f in os.listdir(html_folder) if f.endswith('.csv')]
        
        for csv_file in csv_files:
            full_path = os.path.join(html_folder, csv_file)
            try:
                df = pd.read_csv(full_path)
                
                missing_columns = [col for col in expected_columns if col not in df.columns]
                extra_columns = [col for col in df.columns if col not in expected_columns]
                
                print(f"\n📄 {csv_file}:")
                if missing_columns:
                    print(f"   ❌ Missing: {missing_columns}")
                else:
                    print(f"   ✅ All expected columns present")
                
                if extra_columns:
                    print(f"   ➕ Extra columns: {extra_columns}")
                
                # Check data types
                if 'Quantity' in df.columns:
                    print(f"   📊 Quantity sample: {df['Quantity'].head(3).tolist()}")
                if 'Price (USD)' in df.columns:
                    print(f"   💰 Price sample: {df['Price (USD)'].head(3).tolist()}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")

def test_html_loading_logic():
    """Test the HTML loading logic used in the main script."""
    print(f"\n🧪 TESTING HTML LOADING LOGIC")
    print("=" * 50)
    
    html_folder = "html_folder"
    html_data = []
    
    if os.path.exists(html_folder):
        csv_files = [f for f in os.listdir(html_folder) if f.endswith('.csv')]
        print(f"📄 Found {len(csv_files)} HTML CSV files")
        
        for csv_file in csv_files:
            full_path = os.path.join(html_folder, csv_file)
            print(f"\n🔄 Testing {csv_file}:")
            
            try:
                df = pd.read_csv(full_path)
                print(f"   ✅ Loaded: {len(df)} rows")
                
                # Test the standardization logic
                expected_columns = ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)', 'Commission (USD)']
                
                if all(col in df.columns for col in expected_columns):
                    print(f"   ✅ All expected columns present")
                    
                    # Try to standardize
                    standardized = pd.DataFrame()
                    standardized['Symbol'] = df['Symbol']
                    standardized['Date'] = df['Trade Date'].astype(str)
                    standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
                    standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
                    standardized['Price'] = pd.to_numeric(df['Price (USD)'], errors='coerce').abs()
                    standardized['Commission'] = pd.to_numeric(df['Commission (USD)'], errors='coerce').abs()
                    standardized['Source'] = 'HTML_Parsed'
                    
                    # Clean up
                    before_clean = len(standardized)
                    standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
                    after_clean = len(standardized)
                    
                    print(f"   📊 Standardized: {before_clean} → {after_clean} valid rows")
                    
                    if after_clean > 0:
                        html_data.append(standardized)
                        print(f"   ✅ Successfully processed")
                        
                        # Show CFLT if it exists
                        cflt_data = standardized[standardized['Symbol'] == 'CFLT']
                        if len(cflt_data) > 0:
                            print(f"   🎯 CFLT transactions: {len(cflt_data)}")
                            for _, row in cflt_data.iterrows():
                                print(f"      {row['Activity']}: {row['Quantity']} @ ${row['Price']} on {row['Date']}")
                    else:
                        print(f"   ❌ No valid rows after cleaning")
                else:
                    missing = [col for col in expected_columns if col not in df.columns]
                    print(f"   ❌ Missing columns: {missing}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
    else:
        print(f"❌ html_folder not found")
    
    print(f"\n📊 FINAL RESULT:")
    print(f"   HTML DataFrames created: {len(html_data)}")
    if html_data:
        total_html_transactions = sum(len(df) for df in html_data)
        print(f"   Total HTML transactions: {total_html_transactions}")
        
        # Combine and show summary
        if len(html_data) > 0:
            combined_html = pd.concat(html_data, ignore_index=True)
            print(f"   HTML symbols: {sorted(combined_html['Symbol'].unique())}")
            
            cflt_in_html = combined_html[combined_html['Symbol'] == 'CFLT']
            print(f"   CFLT transactions in HTML: {len(cflt_in_html)}")

def main():
    """Main diagnostic function."""
    print("🔍 HTML FILES DIAGNOSTIC")
    print("=" * 60)
    print("This will help us understand why HTML files aren't being processed")
    print()
    
    check_html_files()
    check_expected_html_format()
    test_html_loading_logic()
    
    print(f"\n🎯 SUMMARY:")
    print(f"Use this output to identify:")
    print(f"1. Are the HTML files in the right location?")
    print(f"2. Do they have the expected column format?")
    print(f"3. Is the HTML loading logic working?")
    print(f"4. How many CFLT transactions should be coming from HTML?")

if __name__ == "__main__":
    main()