#!/usr/bin/env python3
"""
CFLT Data Diagnostic Script

This will examine exactly what CFLT data is being loaded from your files
to identify where the wrong numbers are coming from.
"""

import pandas as pd
import json
import os
import glob

def examine_cflt_in_html_files():
    """Check CFLT data in HTML-parsed files."""
    print("🔍 EXAMINING CFLT IN HTML FILES")
    print("=" * 50)
    
    html_folder = "html_folder"
    if not os.path.exists(html_folder):
        print("❌ html_folder not found")
        return
    
    csv_files = [f for f in os.listdir(html_folder) if f.endswith('.csv')]
    
    for csv_file in csv_files:
        full_path = os.path.join(html_folder, csv_file)
        print(f"\n📄 Checking {csv_file}:")
        
        try:
            df = pd.read_csv(full_path)
            
            # Filter for CFLT
            cflt_data = df[df['Symbol'] == 'CFLT']
            
            if len(cflt_data) > 0:
                print(f"   ✅ Found {len(cflt_data)} CFLT transactions")
                print(f"   📋 Columns: {list(df.columns)}")
                print(f"\n   📊 CFLT Data:")
                for i, row in cflt_data.iterrows():
                    print(f"      Row {i}:")
                    for col in df.columns:
                        print(f"         {col}: {row[col]}")
                    print()
            else:
                print(f"   ⚠️ No CFLT data found")
                
        except Exception as e:
            print(f"   ❌ Error reading {csv_file}: {e}")

def examine_cflt_in_manual_files():
    """Check CFLT data in manual files."""
    print("\n🔍 EXAMINING CFLT IN MANUAL FILES")
    print("=" * 50)
    
    manual_files = [f for f in glob.glob("*.csv") if 'manual' in f.lower()]
    
    for csv_file in manual_files:
        print(f"\n📄 Checking {csv_file}:")
        
        try:
            df = pd.read_csv(csv_file)
            
            # Look for CFLT in any column that might contain symbols
            symbol_columns = []
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['symbol', 'stock', 'ticker']):
                    symbol_columns.append(col)
            
            print(f"   📋 All columns: {list(df.columns)}")
            print(f"   🏷️ Symbol columns: {symbol_columns}")
            
            cflt_found = False
            
            for symbol_col in symbol_columns:
                cflt_data = df[df[symbol_col] == 'CFLT']
                if len(cflt_data) > 0:
                    cflt_found = True
                    print(f"\n   ✅ Found {len(cflt_data)} CFLT transactions in column '{symbol_col}'")
                    print(f"\n   📊 CFLT Data:")
                    for i, row in cflt_data.iterrows():
                        print(f"      Row {i}:")
                        for col in df.columns:
                            print(f"         {col}: {row[col]}")
                        print()
            
            if not cflt_found:
                print(f"   ⚠️ No CFLT data found")
                # Show a few sample rows to see what symbols are there
                print(f"\n   📊 Sample data (first 3 rows):")
                for i, row in df.head(3).iterrows():
                    print(f"      Row {i}:")
                    for col in df.columns:
                        print(f"         {col}: {row[col]}")
                    print()
                
        except Exception as e:
            print(f"   ❌ Error reading {csv_file}: {e}")

def examine_existing_cost_basis():
    """Check what's in the existing cost basis files."""
    print("\n🔍 EXAMINING EXISTING COST BASIS FILES")
    print("=" * 50)
    
    json_files = [f for f in glob.glob("*.json") if 'cost_basis' in f.lower()]
    
    for json_file in json_files:
        print(f"\n📄 Checking {json_file}:")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            if 'CFLT' in data:
                print(f"   ✅ Found CFLT in {json_file}")
                cflt_records = data['CFLT']
                print(f"   📊 CFLT has {len(cflt_records)} records:")
                
                for i, record in enumerate(cflt_records):
                    print(f"      Record {i+1}:")
                    for key, value in record.items():
                        print(f"         {key}: {value}")
                    print()
                
                # Calculate totals
                total_units = sum(r.get('units', 0) for r in cflt_records)
                total_cost = sum(r.get('units', 0) * r.get('price', 0) for r in cflt_records)
                print(f"   📊 Totals: {total_units:.2f} units, ${total_cost:.2f} cost")
            else:
                print(f"   ⚠️ No CFLT found in {json_file}")
                print(f"   🏷️ Available symbols: {list(data.keys())}")
                
        except Exception as e:
            print(f"   ❌ Error reading {json_file}: {e}")

def show_processing_log():
    """Show the FIFO processing log for CFLT."""
    print("\n🔍 EXAMINING FIFO PROCESSING LOG")
    print("=" * 50)
    
    log_file = "fifo_processing_log.json"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
            
            if 'CFLT' in log_data:
                print(f"✅ Found CFLT processing log:")
                cflt_log = log_data['CFLT']
                
                for i, operation in enumerate(cflt_log):
                    print(f"   {i+1}. {operation}")
            else:
                print(f"⚠️ No CFLT in processing log")
                print(f"🏷️ Available symbols in log: {list(log_data.keys())}")
                
        except Exception as e:
            print(f"❌ Error reading log: {e}")
    else:
        print(f"⚠️ No processing log file found")

def trace_cflt_problem():
    """Trace exactly where the CFLT problem is coming from."""
    print("🔍 CFLT PROBLEM DIAGNOSIS")
    print("=" * 60)
    print("Let's trace exactly where this wrong CFLT data is coming from...")
    print()
    
    # Check all possible sources
    examine_cflt_in_html_files()
    examine_cflt_in_manual_files()
    examine_existing_cost_basis()
    show_processing_log()
    
    print("\n🎯 ANALYSIS:")
    print("=" * 30)
    print("Based on the data above, we can see:")
    print("1. What CFLT data exists in your source files")
    print("2. How it's being processed")
    print("3. Where the wrong numbers are coming from")
    print()
    print("💡 Common causes:")
    print("   • Wrong column mapping in manual CSV")
    print("   • Data corruption during processing")
    print("   • Multiple sources with conflicting data")
    print("   • Date parsing issues affecting FIFO order")

def quick_fix_suggestions():
    """Provide quick fix suggestions based on findings."""
    print("\n🔧 QUICK FIX SUGGESTIONS:")
    print("=" * 40)
    print("1. Check your manual CSV file format")
    print("2. Verify column names match expected format")
    print("3. Look for data entry errors (wrong units/prices)")
    print("4. Check for duplicate transactions")
    print("5. Verify date formats are consistent")

def main():
    """Main diagnostic function."""
    print("🚨 CFLT DATA DIAGNOSTIC")
    print("=" * 60)
    print("This will help us find where the wrong CFLT data is coming from.")
    print(f"Expected: ~1,150 units at ~$21-36 price range")
    print(f"Actual: 6,887 units at $69.90")
    print(f"This suggests a major data parsing issue!")
    print()
    
    trace_cflt_problem()
    quick_fix_suggestions()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"After reviewing the output above:")
    print(f"1. Identify which file has the wrong CFLT data")
    print(f"2. Check if it's a column mapping issue")
    print(f"3. Fix the source data or parsing logic")
    print(f"4. Re-run the FIFO processing")

if __name__ == "__main__":
    main()