#!/usr/bin/env python3
"""
HTML Sales Debugger - Check what transactions are in your HTML files
"""

import re
import os
import glob
from datetime import datetime

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(',', '')
    return text

def parse_trade_date(date_text):
    if not date_text:
        return None
    
    date_part = date_text.split(',')[0].strip()
    
    try:
        return datetime.strptime(date_part, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_part, '%m/%d/%Y')
        except ValueError:
            return None

def debug_html_file(html_file):
    """Debug what's inside an HTML file."""
    print(f"\n🔍 DEBUGGING: {os.path.basename(html_file)}")
    print("=" * 60)
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # Find all summary rows
    summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
    summary_matches = re.findall(summary_row_pattern, html_content)
    
    print(f"📊 Found {len(summary_matches)} summary transactions")
    
    all_transactions = []
    fy_2024_25_start = datetime(2024, 7, 1)
    fy_2024_25_end = datetime(2025, 6, 30)
    
    for i, row_html in enumerate(summary_matches):
        try:
            cell_pattern = r'<td[^>]*>([\s\S]*?)</td>'
            cell_matches = re.findall(cell_pattern, row_html)
            
            if len(cell_matches) < 10:
                continue
            
            cells = [clean_text(cell) for cell in cell_matches]
            
            symbol = cells[1]
            trade_datetime = cells[2]
            transaction_type = cells[5]
            quantity_text = cells[6]
            
            # Parse date
            trade_date = parse_trade_date(trade_datetime)
            
            transaction = {
                'symbol': symbol,
                'date': trade_date,
                'type': transaction_type,
                'quantity': quantity_text,
                'raw_date': trade_datetime,
                'in_fy_2024_25': trade_date and fy_2024_25_start <= trade_date <= fy_2024_25_end
            }
            
            all_transactions.append(transaction)
            
        except Exception as e:
            print(f"   ❌ Error parsing row {i+1}: {e}")
            continue
    
    if not all_transactions:
        print("❌ No transactions found at all!")
        return
    
    # Show all transactions
    print(f"\n📋 ALL TRANSACTIONS ({len(all_transactions)}):")
    for i, tx in enumerate(all_transactions, 1):
        date_str = tx['date'].strftime('%Y-%m-%d') if tx['date'] else tx['raw_date']
        fy_indicator = "✅ FY24-25" if tx['in_fy_2024_25'] else "❌ Outside FY"
        print(f"   {i:2d}. {tx['symbol']:8s} {tx['type']:4s} {tx['quantity']:>8s} on {date_str} {fy_indicator}")
    
    # Focus on FY 2024-25
    fy_transactions = [tx for tx in all_transactions if tx['in_fy_2024_25']]
    print(f"\n🎯 FY 2024-25 TRANSACTIONS ({len(fy_transactions)}):")
    
    if fy_transactions:
        sell_transactions = [tx for tx in fy_transactions if tx['type'] == 'SELL']
        buy_transactions = [tx for tx in fy_transactions if tx['type'] == 'BUY']
        
        print(f"   📉 SELL transactions: {len(sell_transactions)}")
        for tx in sell_transactions:
            date_str = tx['date'].strftime('%Y-%m-%d')
            print(f"      • {tx['symbol']} SELL {tx['quantity']} on {date_str}")
        
        print(f"   📈 BUY transactions: {len(buy_transactions)}")
        for tx in buy_transactions:
            date_str = tx['date'].strftime('%Y-%m-%d')
            print(f"      • {tx['symbol']} BUY {tx['quantity']} on {date_str}")
    else:
        print("   📭 No transactions in FY 2024-25")
    
    # Show date range of file
    dates = [tx['date'] for tx in all_transactions if tx['date']]
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        print(f"\n📅 File date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    return fy_transactions

def main():
    """Debug HTML files to find sales."""
    print("🔍 HTML SALES DEBUGGER")
    print("=" * 50)
    print("Checking what transactions are in your HTML files...")
    
    html_folder = "html_folder"
    
    # Find HTML files
    html_files = []
    for ext in ['*.htm', '*.html']:
        html_files.extend(glob.glob(os.path.join(html_folder, ext)))
    
    if not html_files:
        print(f"❌ No HTML files found in {html_folder}/")
        return
    
    print(f"📄 Found {len(html_files)} HTML files:")
    for file in html_files:
        print(f"   • {os.path.basename(file)}")
    
    total_fy_sales = 0
    
    for html_file in html_files:
        fy_transactions = debug_html_file(html_file)
        if fy_transactions:
            fy_sales = len([tx for tx in fy_transactions if tx['type'] == 'SELL'])
            total_fy_sales += fy_sales
    
    print(f"\n🎯 SUMMARY:")
    print(f"📉 Total SELL transactions in FY 2024-25: {total_fy_sales}")
    
    if total_fy_sales == 0:
        print(f"\n💡 POSSIBLE REASONS:")
        print(f"   1. No sales actually occurred in FY 2024-25")
        print(f"   2. Sales are in a different HTML format")
        print(f"   3. Date parsing issue")
        print(f"   4. HTML structure is different than expected")

if __name__ == "__main__":
    main()