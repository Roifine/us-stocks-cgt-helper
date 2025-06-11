#!/usr/bin/env python3
"""
Sale Date Checker - Verify exact sale dates for missing symbols
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
    
    # Handle both formats: "2024-07-02, 09:31:33" and "2024-07-02 09:31:33"
    date_part = date_text.split(',')[0].split(' ')[0].strip()
    
    try:
        return datetime.strptime(date_part, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_part, '%m/%d/%Y')
        except ValueError:
            return None

def check_sale_dates():
    """Check exact sale dates for missing symbols."""
    print("🔍 SALE DATE VERIFICATION")
    print("=" * 50)
    
    missing_symbols = ['TAL', 'NVDA', 'TSM', 'PD', 'FRSH', 'SPXU']
    print(f"Checking sale dates for: {', '.join(missing_symbols)}")
    
    html_folder = "html_folder"
    html_files = []
    for ext in ['*.htm', '*.html']:
        html_files.extend(glob.glob(os.path.join(html_folder, ext)))
    
    all_sales = []
    
    for html_file in html_files:
        print(f"\n📄 Checking {os.path.basename(html_file)}...")
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"❌ Error reading {html_file}: {e}")
            continue
        
        # Find all summary rows
        summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
        summary_matches = re.findall(summary_row_pattern, html_content)
        
        for row_html in summary_matches:
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
                price_text = cells[7]
                proceeds_text = cells[8]
                
                # Only check for our missing symbols
                if symbol not in missing_symbols:
                    continue
                
                # Parse date
                trade_date = parse_trade_date(trade_datetime)
                if not trade_date:
                    continue
                
                # Parse values
                quantity = abs(float(clean_text(quantity_text).replace(',', '') or '0'))
                price = abs(float(clean_text(price_text).replace(',', '') or '0'))
                proceeds = abs(float(clean_text(proceeds_text).replace(',', '') or '0'))
                
                sale_info = {
                    'symbol': symbol,
                    'type': transaction_type,
                    'date': trade_date,
                    'quantity': quantity,
                    'price': price,
                    'proceeds': proceeds,
                    'file': os.path.basename(html_file)
                }
                
                all_sales.append(sale_info)
                
            except Exception as e:
                continue
    
    # Sort by date and display results
    all_sales.sort(key=lambda x: x['date'])
    
    print(f"\n📊 FOUND TRANSACTIONS FOR MISSING SYMBOLS:")
    print("=" * 70)
    
    fy_2024_25_start = datetime(2024, 7, 1)
    fy_2024_25_end = datetime(2025, 6, 30)
    
    for symbol in missing_symbols:
        symbol_transactions = [t for t in all_sales if t['symbol'] == symbol]
        
        if not symbol_transactions:
            print(f"\n❌ {symbol}: No transactions found in any HTML file")
            continue
        
        print(f"\n📈 {symbol} - All Transactions:")
        
        buys_in_fy = []
        sells_in_fy = []
        
        for tx in symbol_transactions:
            date_str = tx['date'].strftime('%Y-%m-%d')
            in_fy = fy_2024_25_start <= tx['date'] <= fy_2024_25_end
            fy_indicator = "✅ FY24-25" if in_fy else "❌ Outside FY"
            
            print(f"   {tx['type']:4s}: {tx['quantity']:>6.0f} units @ ${tx['price']:>6.2f} on {date_str} {fy_indicator} ({tx['file']})")
            
            if in_fy:
                if tx['type'] == 'BUY':
                    buys_in_fy.append(tx)
                elif tx['type'] == 'SELL':
                    sells_in_fy.append(tx)
        
        # Analysis for this symbol
        print(f"   📊 FY 24-25 Summary: {len(buys_in_fy)} BUYs, {len(sells_in_fy)} SELLs")
        
        if len(buys_in_fy) > 0 and len(sells_in_fy) > 0:
            total_bought = sum(tx['quantity'] for tx in buys_in_fy)
            total_sold = sum(tx['quantity'] for tx in sells_in_fy)
            print(f"   🔄 Net: Bought {total_bought:.0f}, Sold {total_sold:.0f}")
            
            if total_bought >= total_sold:
                print(f"   💡 SHORT-TERM TRADE: Bought & sold within FY 24-25")
            else:
                print(f"   ⚠️  Sold more than bought in FY 24-25")
        elif len(sells_in_fy) > 0:
            print(f"   📉 SELL ONLY: No purchases in FY 24-25 (missing cost basis)")
        elif len(buys_in_fy) > 0:
            print(f"   📈 BUY ONLY: No sales in FY 24-25")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print("=" * 50)
    
    # Check each symbol and provide recommendations
    for symbol in missing_symbols:
        symbol_transactions = [t for t in all_sales if t['symbol'] == symbol]
        
        if not symbol_transactions:
            print(f"❓ {symbol}: No transactions found - possibly a data entry error?")
            continue
        
        buys_in_fy = [t for t in symbol_transactions if t['type'] == 'BUY' and fy_2024_25_start <= t['date'] <= fy_2024_25_end]
        sells_in_fy = [t for t in symbol_transactions if t['type'] == 'SELL' and fy_2024_25_start <= t['date'] <= fy_2024_25_end]
        
        if len(buys_in_fy) > 0 and len(sells_in_fy) > 0:
            print(f"🔄 {symbol}: SHORT-TERM TRADE - Add FY 24-25 BUY transactions to cost basis")
        elif len(sells_in_fy) > 0 and len(buys_in_fy) == 0:
            print(f"📉 {symbol}: SELL ONLY - Need to find cost basis from before June 30, 2024")
        else:
            print(f"❓ {symbol}: No sales in FY 24-25 - why is it showing as missing?")

if __name__ == "__main__":
    check_sale_dates()