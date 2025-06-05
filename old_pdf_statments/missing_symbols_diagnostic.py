#!/usr/bin/env python3
"""
Missing Symbols Diagnostic

This will check what symbols exist in your source files but are missing from the final cost basis.
It will help identify if symbols like SHOP were:
1. Completely sold (FIFO removed all units)
2. Not loaded from source files
3. Had data loading issues
"""

import pandas as pd
import json
import os
import glob
import re

def parse_html_for_symbols(html_file_path):
    """Quick parse of HTML file to extract symbols."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        transactions = []
        summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
        summary_matches = re.findall(summary_row_pattern, html_content)
        
        for row_html in summary_matches:
            cell_pattern = r'<td[^>]*>([\s\S]*?)</td>'
            cell_matches = re.findall(cell_pattern, row_html)
            
            if len(cell_matches) >= 6:
                cells = [re.sub(r'<[^>]+>', '', str(cell)).strip() for cell in cell_matches]
                symbol = cells[1]
                transaction_type = cells[5]
                
                # Skip currency transactions
                if '.' not in symbol or symbol in ['U.S', 'S.A']:
                    transactions.append({
                        'symbol': symbol,
                        'type': transaction_type,
                        'source': f'HTML_{os.path.basename(html_file_path)}'
                    })
        
        return transactions
        
    except Exception as e:
        print(f"Error parsing {html_file_path}: {e}")
        return []

def check_symbols_in_html_files():
    """Check what symbols exist in HTML files."""
    print("🔍 SYMBOLS IN HTML FILES")
    print("=" * 50)
    
    html_folder = "html_folder"
    all_html_symbols = set()
    html_transactions = []
    
    if os.path.exists(html_folder):
        html_files = glob.glob(os.path.join(html_folder, "*.htm")) + glob.glob(os.path.join(html_folder, "*.html"))
        
        for html_file in html_files:
            print(f"\n📄 {os.path.basename(html_file)}:")
            transactions = parse_html_for_symbols(html_file)
            
            if transactions:
                file_symbols = set(t['symbol'] for t in transactions)
                all_html_symbols.update(file_symbols)
                html_transactions.extend(transactions)
                
                print(f"   📊 {len(transactions)} transactions")
                print(f"   🏷️ Symbols: {sorted(file_symbols)}")
                
                # Check for SHOP specifically
                shop_transactions = [t for t in transactions if t['symbol'] == 'SHOP']
                if shop_transactions:
                    print(f"   🎯 SHOP transactions: {len(shop_transactions)}")
                    for t in shop_transactions:
                        print(f"      {t['type']}")
            else:
                print(f"   ⚠️ No transactions found")
    else:
        print("❌ html_folder not found")
    
    print(f"\n📊 ALL HTML SYMBOLS: {sorted(all_html_symbols)}")
    return all_html_symbols, html_transactions

def check_symbols_in_manual_csv():
    """Check what symbols exist in manual CSV files."""
    print(f"\n🔍 SYMBOLS IN MANUAL CSV FILES")
    print("=" * 50)
    
    all_manual_symbols = set()
    manual_transactions = []
    
    manual_files = [f for f in glob.glob("*.csv") if 'manual' in f.lower()]
    
    for csv_file in manual_files:
        try:
            df = pd.read_csv(csv_file)
            print(f"\n📄 {csv_file}:")
            
            if 'Symbol' in df.columns:
                file_symbols = set(df['Symbol'].unique())
                all_manual_symbols.update(file_symbols)
                
                print(f"   📊 {len(df)} transactions")
                print(f"   🏷️ Symbols: {sorted(file_symbols)}")
                
                # Check for SHOP specifically
                shop_data = df[df['Symbol'] == 'SHOP']
                if len(shop_data) > 0:
                    print(f"   🎯 SHOP transactions: {len(shop_data)}")
                    for _, row in shop_data.iterrows():
                        print(f"      {row['Activity_Type']}: {row['Quantity']} @ ${row['Price_USD']} on {row['Date']}")
                        manual_transactions.append({
                            'symbol': 'SHOP',
                            'type': row['Activity_Type'],
                            'quantity': row['Quantity'],
                            'price': row['Price_USD'],
                            'date': row['Date'],
                            'source': f'Manual_{csv_file}'
                        })
            else:
                print(f"   ❌ No Symbol column found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 ALL MANUAL SYMBOLS: {sorted(all_manual_symbols)}")
    return all_manual_symbols, manual_transactions

def check_symbols_in_cost_basis():
    """Check what symbols exist in the final cost basis."""
    print(f"\n🔍 SYMBOLS IN FINAL COST BASIS")
    print("=" * 50)
    
    cost_basis_files = [f for f in glob.glob("*.json") if 'cost_basis' in f.lower() and 'COMPLETE' in f]
    
    if not cost_basis_files:
        cost_basis_files = [f for f in glob.glob("*.json") if 'cost_basis' in f.lower()]
    
    final_symbols = set()
    
    if cost_basis_files:
        latest_file = sorted(cost_basis_files)[-1]  # Use most recent
        print(f"📄 Using: {latest_file}")
        
        try:
            with open(latest_file, 'r') as f:
                cost_basis = json.load(f)
            
            final_symbols = set(cost_basis.keys())
            print(f"📊 {len(final_symbols)} symbols in final cost basis")
            print(f"🏷️ Symbols: {sorted(final_symbols)}")
            
        except Exception as e:
            print(f"❌ Error loading cost basis: {e}")
    else:
        print("❌ No cost basis JSON files found")
    
    return final_symbols

def check_fifo_log_for_missing_symbols(missing_symbols):
    """Check FIFO log to see what happened to missing symbols."""
    print(f"\n🔍 CHECKING FIFO LOG FOR MISSING SYMBOLS")
    print("=" * 60)
    
    log_files = [f for f in glob.glob("*.json") if 'log' in f.lower() and 'COMPLETE' in f]
    
    if not log_files:
        log_files = [f for f in glob.glob("*.json") if 'log' in f.lower()]
    
    if log_files:
        latest_log = sorted(log_files)[-1]
        print(f"📄 Using log: {latest_log}")
        
        try:
            with open(latest_log, 'r') as f:
                fifo_log = json.load(f)
            
            for symbol in missing_symbols:
                if symbol in fifo_log:
                    print(f"\n🎯 {symbol} FIFO operations:")
                    operations = fifo_log[symbol]
                    for i, op in enumerate(operations, 1):
                        print(f"   {i}. {op}")
                    
                    # Analyze if completely sold
                    buy_count = len([op for op in operations if 'BUY:' in op])
                    sell_count = len([op for op in operations if 'SELL:' in op])
                    used_count = len([op for op in operations if 'Used all' in op])
                    
                    print(f"   📊 Summary: {buy_count} buys, {sell_count} sells, {used_count} complete uses")
                    
                    if used_count >= buy_count:
                        print(f"   💡 Likely completely sold out (all purchases used)")
                else:
                    print(f"\n❌ {symbol} not found in FIFO log (not processed)")
                    
        except Exception as e:
            print(f"❌ Error loading FIFO log: {e}")
    else:
        print("❌ No FIFO log files found")

def analyze_missing_symbols():
    """Complete analysis of missing symbols."""
    print("🔍 MISSING SYMBOLS ANALYSIS")
    print("=" * 70)
    print("This will identify symbols that exist in source files but are missing from cost basis")
    print()
    
    # Get symbols from all sources
    html_symbols, html_transactions = check_symbols_in_html_files()
    manual_symbols, manual_transactions = check_symbols_in_manual_csv()
    final_symbols = check_symbols_in_cost_basis()
    
    # Find missing symbols
    all_source_symbols = html_symbols | manual_symbols
    missing_symbols = all_source_symbols - final_symbols
    
    print(f"\n📊 SYMBOL COMPARISON")
    print("=" * 40)
    print(f"HTML symbols: {len(html_symbols)}")
    print(f"Manual symbols: {len(manual_symbols)}")
    print(f"All source symbols: {len(all_source_symbols)}")
    print(f"Final cost basis symbols: {len(final_symbols)}")
    print(f"Missing symbols: {len(missing_symbols)}")
    
    if missing_symbols:
        print(f"\n❌ MISSING SYMBOLS: {sorted(missing_symbols)}")
        
        # Analyze each missing symbol
        for symbol in sorted(missing_symbols):
            print(f"\n🔍 Analyzing {symbol}:")
            
            # Check if in HTML
            html_count = len([t for t in html_transactions if t['symbol'] == symbol])
            if html_count > 0:
                html_types = [t['type'] for t in html_transactions if t['symbol'] == symbol]
                print(f"   📄 HTML: {html_count} transactions ({dict(pd.Series(html_types).value_counts())})")
            
            # Check if in manual
            manual_count = len([t for t in manual_transactions if t['symbol'] == symbol])
            if manual_count > 0:
                manual_types = [t['type'] for t in manual_transactions if t['symbol'] == symbol]
                print(f"   📝 Manual: {manual_count} transactions ({dict(pd.Series(manual_types).value_counts())})")
        
        # Check FIFO log for explanations
        check_fifo_log_for_missing_symbols(missing_symbols)
        
        print(f"\n💡 POSSIBLE REASONS FOR MISSING SYMBOLS:")
        print(f"1. Completely sold out (FIFO used all purchased units)")
        print(f"2. Data loading issues (failed to parse or standardize)")
        print(f"3. Date parsing problems (invalid dates filtered out)")
        print(f"4. Duplicate removal (transactions marked as duplicates)")
        
    else:
        print(f"\n✅ No missing symbols - all source symbols are in final cost basis")
    
    # Show symbols that ARE in final cost basis
    present_symbols = all_source_symbols & final_symbols
    if present_symbols:
        print(f"\n✅ SYMBOLS SUCCESSFULLY PROCESSED: {sorted(present_symbols)}")

def main():
    """Main diagnostic function."""
    analyze_missing_symbols()
    
    print(f"\n🎯 NEXT STEPS:")
    print("=" * 30)
    print("1. Review the missing symbols analysis above")
    print("2. Check if symbols were completely sold (FIFO explanation)")
    print("3. If data loading issues, check source file format")
    print("4. If needed, re-run the unified script with debug output")

if __name__ == "__main__":
    main()