#!/usr/bin/env python3
"""
CGT Optimizer - Compare FIFO vs Tax-Optimal CGT Strategies

This script:
1. Loads your unified cost basis JSON
2. Extracts FY 24-25 sales from HTML files
3. Applies FIFO vs Tax-Optimal matching
4. Shows potential tax savings
"""

import json
import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime, timedelta
from collections import deque
import copy

# Import HTML parsing functions from your unified script
def clean_text(text):
    """Clean and normalize text content."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(',', '')
    return text

def parse_number(text):
    """Parse numeric values from text, handling negative signs and commas."""
    if not text:
        return 0
    
    clean_text_val = clean_text(text)
    is_negative = clean_text_val.startswith('-') or '(' in clean_text_val
    numeric_part = re.sub(r'[^\d.]', '', clean_text_val)
    
    try:
        value = float(numeric_part) if numeric_part else 0
        return -value if is_negative else value
    except ValueError:
        return 0

def parse_trade_date(date_text):
    """Parse trade date from Interactive Brokers format."""
    if not date_text:
        return None
    
    # Handle full datetime strings like "2024-07-02 09:31:33"
    date_part = date_text.split(' ')[0].strip()  # Get just the date part
    
    try:
        return datetime.strptime(date_part, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_part, '%m/%d/%Y')
        except ValueError:
            print(f"⚠️ Could not parse date: {date_text}")
            return None

def parse_date_flexible(date_str):
    """Parse dates in DD.M.YY format to datetime."""
    try:
        return datetime.strptime(date_str, "%d.%m.%y")
    except:
        try:
            return datetime.strptime(date_str, "%d.%-m.%y")
        except:
            return datetime.strptime(date_str, "%Y-%m-%d")

def load_cost_basis_json(json_file):
    """Load unified cost basis JSON."""
    print(f"📊 Loading cost basis from: {json_file}")
    
    try:
        with open(json_file, 'r') as f:
            cost_basis_dict = json.load(f)
        
        print(f"✅ Loaded cost basis for {len(cost_basis_dict)} symbols")
        
        # Show summary
        total_units = 0
        total_value = 0
        for symbol, records in cost_basis_dict.items():
            symbol_units = sum(r['units'] for r in records)
            symbol_value = sum(r['units'] * r['price'] for r in records)
            total_units += symbol_units
            total_value += symbol_value
            print(f"   {symbol}: {symbol_units:,.0f} units, ${symbol_value:,.0f} value")
        
        print(f"📈 Total: {total_units:,.0f} units, ${total_value:,.0f} cost basis")
        return cost_basis_dict
        
    except Exception as e:
        print(f"❌ Error loading cost basis: {e}")
        return None

def extract_fy_sales(html_folder, financial_year="2024-25"):
    """Extract sales from specific financial year from HTML files."""
    print(f"\n📉 EXTRACTING FY {financial_year} SALES")
    print("=" * 50)
    
    # Define FY dates
    if financial_year == "2024-25":
        fy_start = datetime(2024, 7, 1)
        fy_end = datetime(2025, 6, 30)
    elif financial_year == "2023-24":
        fy_start = datetime(2023, 7, 1)
        fy_end = datetime(2024, 6, 30)
    else:
        print(f"❌ Unsupported financial year: {financial_year}")
        return None
    
    print(f"📅 FY {financial_year}: {fy_start.strftime('%Y-%m-%d')} to {fy_end.strftime('%Y-%m-%d')}")
    
    # Find HTML files
    html_files = []
    for ext in ['*.htm', '*.html']:
        html_files.extend(glob.glob(os.path.join(html_folder, ext)))
    
    print(f"📄 Found {len(html_files)} HTML files")
    
    all_sales = []
    
    for html_file in html_files:
        print(f"\n🔄 Processing {os.path.basename(html_file)}...")
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"❌ Error reading {html_file}: {e}")
            continue
        
        # Find all summary rows
        summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
        summary_matches = re.findall(summary_row_pattern, html_content)
        
        file_sales = []
        
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
                commission_text = cells[9]
                
                # Skip if not a SELL transaction
                if transaction_type != 'SELL':
                    continue
                
                # Skip currency transactions
                if '.' in symbol and symbol not in ['U.S', 'S.A']:
                    continue
                
                # Parse date and check if in FY
                trade_date = parse_trade_date(trade_datetime)
                if not trade_date or trade_date < fy_start or trade_date > fy_end:
                    continue
                
                # Parse values
                quantity = abs(parse_number(quantity_text))
                price = abs(parse_number(price_text))
                proceeds = abs(parse_number(proceeds_text))
                commission = abs(parse_number(commission_text))
                
                sale = {
                    'symbol': symbol,
                    'date': trade_date,
                    'quantity': quantity,
                    'price': price,
                    'proceeds': proceeds,
                    'commission': commission,
                    'net_proceeds': proceeds - commission,
                    'source_file': os.path.basename(html_file)
                }
                
                file_sales.append(sale)
                
            except Exception as e:
                continue
        
        if file_sales:
            print(f"   📉 Found {len(file_sales)} sales in FY {financial_year}")
            all_sales.extend(file_sales)
        else:
            print(f"   📭 No sales found in FY {financial_year}")
    
    # Sort by date
    all_sales.sort(key=lambda x: x['date'])
    
    print(f"\n✅ Total sales in FY {financial_year}: {len(all_sales)}")
    
    # Show summary by symbol
    if all_sales:
        sales_by_symbol = {}
        for sale in all_sales:
            symbol = sale['symbol']
            if symbol not in sales_by_symbol:
                sales_by_symbol[symbol] = {'count': 0, 'total_units': 0, 'total_proceeds': 0}
            sales_by_symbol[symbol]['count'] += 1
            sales_by_symbol[symbol]['total_units'] += sale['quantity']
            sales_by_symbol[symbol]['total_proceeds'] += sale['net_proceeds']
        
        print(f"\n📊 Sales by symbol:")
        for symbol, data in sorted(sales_by_symbol.items()):
            print(f"   {symbol}: {data['count']} sales, {data['total_units']:,.0f} units, ${data['total_proceeds']:,.0f}")
    
    return all_sales

def apply_fifo_strategy(sales, cost_basis_dict):
    """Apply traditional FIFO strategy to match sales with cost basis."""
    print(f"\n🔄 APPLYING FIFO STRATEGY")
    print("=" * 40)
    
    # Deep copy to avoid modifying original
    working_cost_basis = copy.deepcopy(cost_basis_dict)
    fifo_matches = []
    warnings = []
    
    for sale in sales:
        symbol = sale['symbol']
        units_to_sell = sale['quantity']
        sale_date = sale['date']
        
        print(f"\n📉 FIFO: Selling {units_to_sell} {symbol} on {sale_date.strftime('%Y-%m-%d')}")
        
        if symbol not in working_cost_basis:
            warning = f"❌ No cost basis found for {symbol}"
            warnings.append(warning)
            print(f"   {warning}")
            continue
        
        # FIFO: Use oldest purchases first
        purchases = working_cost_basis[symbol]
        purchases.sort(key=lambda x: parse_date_flexible(x['date']))
        
        remaining_to_sell = units_to_sell
        sale_matches = []
        
        for i, purchase in enumerate(purchases):
            if remaining_to_sell <= 0:
                break
            
            if purchase['units'] <= 0:
                continue
            
            units_used = min(remaining_to_sell, purchase['units'])
            purchase_date = parse_date_flexible(purchase['date'])
            days_held = (sale_date - purchase_date).days
            
            # Calculate proportional commission
            prop_commission = purchase['commission'] * (units_used / purchase['units'])
            cost_basis = (units_used * purchase['price']) + prop_commission
            
            # Calculate gain/loss
            prop_proceeds = sale['net_proceeds'] * (units_used / units_to_sell)
            capital_gain = prop_proceeds - cost_basis
            
            # Apply CGT discount if held > 12 months
            long_term_eligible = days_held >= 365
            taxable_gain = capital_gain
            if long_term_eligible and capital_gain > 0:
                taxable_gain = capital_gain * 0.5  # 50% CGT discount
            
            match = {
                'sale_symbol': symbol,
                'sale_date': sale_date,
                'sale_units': units_used,
                'sale_price': sale['price'],
                'purchase_date': purchase_date,
                'purchase_price': purchase['price'],
                'days_held': days_held,
                'long_term_eligible': long_term_eligible,
                'cost_basis': cost_basis,
                'proceeds': prop_proceeds,
                'capital_gain': capital_gain,
                'taxable_gain': taxable_gain,
                'strategy': 'FIFO'
            }
            
            sale_matches.append(match)
            
            # Update remaining units
            purchase['units'] -= units_used
            remaining_to_sell -= units_used
            
            print(f"   ✅ Used {units_used} units from {purchase_date.strftime('%Y-%m-%d')} "
                  f"({days_held} days, {'LT' if long_term_eligible else 'ST'})")
        
        if remaining_to_sell > 0:
            warning = f"⚠️ {symbol}: Missing {remaining_to_sell} units for complete matching"
            warnings.append(warning)
            print(f"   {warning}")
        
        fifo_matches.extend(sale_matches)
    
    return fifo_matches, warnings

def apply_tax_optimal_strategy(sales, cost_basis_dict):
    """Apply tax-optimal strategy: prioritize 12+ months + highest price."""
    print(f"\n🎯 APPLYING TAX-OPTIMAL STRATEGY")
    print("=" * 50)
    
    # Deep copy to avoid modifying original
    working_cost_basis = copy.deepcopy(cost_basis_dict)
    optimal_matches = []
    warnings = []
    
    for sale in sales:
        symbol = sale['symbol']
        units_to_sell = sale['quantity']
        sale_date = sale['date']
        
        print(f"\n📉 TAX-OPTIMAL: Selling {units_to_sell} {symbol} on {sale_date.strftime('%Y-%m-%d')}")
        
        if symbol not in working_cost_basis:
            warning = f"❌ No cost basis found for {symbol}"
            warnings.append(warning)
            print(f"   {warning}")
            continue
        
        # Get available purchases
        available_purchases = []
        for purchase in working_cost_basis[symbol]:
            if purchase['units'] > 0:
                purchase_date = parse_date_flexible(purchase['date'])
                days_held = (sale_date - purchase_date).days
                long_term = days_held >= 365
                
                available_purchases.append({
                    'purchase': purchase,
                    'purchase_date': purchase_date,
                    'days_held': days_held,
                    'long_term': long_term,
                    'price': purchase['price']
                })
        
        # Tax-optimal sorting:
        # 1. Prioritize long-term holdings (12+ months)
        # 2. Within each group, prioritize highest price (minimize gain)
        available_purchases.sort(key=lambda x: (
            -1 if x['long_term'] else 1,  # Long-term first
            -x['price']  # Highest price first
        ))
        
        remaining_to_sell = units_to_sell
        sale_matches = []
        
        for purchase_info in available_purchases:
            if remaining_to_sell <= 0:
                break
            
            purchase = purchase_info['purchase']
            purchase_date = purchase_info['purchase_date']
            days_held = purchase_info['days_held']
            long_term_eligible = purchase_info['long_term']
            
            units_used = min(remaining_to_sell, purchase['units'])
            
            # Calculate proportional commission
            prop_commission = purchase['commission'] * (units_used / purchase['units'])
            cost_basis = (units_used * purchase['price']) + prop_commission
            
            # Calculate gain/loss
            prop_proceeds = sale['net_proceeds'] * (units_used / units_to_sell)
            capital_gain = prop_proceeds - cost_basis
            
            # Apply CGT discount if held > 12 months
            taxable_gain = capital_gain
            if long_term_eligible and capital_gain > 0:
                taxable_gain = capital_gain * 0.5  # 50% CGT discount
            
            match = {
                'sale_symbol': symbol,
                'sale_date': sale_date,
                'sale_units': units_used,
                'sale_price': sale['price'],
                'purchase_date': purchase_date,
                'purchase_price': purchase['price'],
                'days_held': days_held,
                'long_term_eligible': long_term_eligible,
                'cost_basis': cost_basis,
                'proceeds': prop_proceeds,
                'capital_gain': capital_gain,
                'taxable_gain': taxable_gain,
                'strategy': 'TAX_OPTIMAL'
            }
            
            sale_matches.append(match)
            
            # Update remaining units
            purchase['units'] -= units_used
            remaining_to_sell -= units_used
            
            print(f"   ✅ Used {units_used} units from {purchase_date.strftime('%Y-%m-%d')} "
                  f"@ ${purchase['price']:.2f} ({days_held} days, {'LT' if long_term_eligible else 'ST'})")
        
        if remaining_to_sell > 0:
            warning = f"⚠️ {symbol}: Missing {remaining_to_sell} units for complete matching"
            warnings.append(warning)
            print(f"   {warning}")
        
        optimal_matches.extend(sale_matches)
    
    return optimal_matches, warnings

def compare_strategies(fifo_matches, optimal_matches):
    """Compare FIFO vs Tax-Optimal strategies for ATO reporting."""
    print(f"\n📊 STRATEGY COMPARISON - ATO REPORTABLE AMOUNTS")
    print("=" * 60)
    
    # Calculate totals for ATO reporting
    fifo_total_gain = sum(m['capital_gain'] for m in fifo_matches)
    fifo_taxable_gain = sum(m['taxable_gain'] for m in fifo_matches)
    
    optimal_total_gain = sum(m['capital_gain'] for m in optimal_matches)
    optimal_taxable_gain = sum(m['taxable_gain'] for m in optimal_matches)
    
    # Calculate difference in reportable amounts
    total_gain_difference = fifo_total_gain - optimal_total_gain
    taxable_gain_difference = fifo_taxable_gain - optimal_taxable_gain
    
    # Separate gains and losses for ATO reporting
    fifo_gains = sum(m['capital_gain'] for m in fifo_matches if m['capital_gain'] > 0)
    fifo_losses = sum(m['capital_gain'] for m in fifo_matches if m['capital_gain'] < 0)
    
    optimal_gains = sum(m['capital_gain'] for m in optimal_matches if m['capital_gain'] > 0)
    optimal_losses = sum(m['capital_gain'] for m in optimal_matches if m['capital_gain'] < 0)
    
    print(f"🔄 FIFO Strategy - ATO Reporting:")
    print(f"   Total Capital Gains: ${fifo_gains:,.2f}")
    print(f"   Total Capital Losses: ${fifo_losses:,.2f}")
    print(f"   Net Capital Gain/Loss: ${fifo_total_gain:,.2f}")
    print(f"   Taxable Amount (after CGT discount): ${fifo_taxable_gain:,.2f}")
    
    print(f"\n🎯 Tax-Optimal Strategy - ATO Reporting:")
    print(f"   Total Capital Gains: ${optimal_gains:,.2f}")
    print(f"   Total Capital Losses: ${optimal_losses:,.2f}")
    print(f"   Net Capital Gain/Loss: ${optimal_total_gain:,.2f}")
    print(f"   Taxable Amount (after CGT discount): ${optimal_taxable_gain:,.2f}")
    
    print(f"\n💰 OPTIMIZATION BENEFIT:")
    print(f"   Reduction in Net Capital Gain: ${total_gain_difference:,.2f}")
    print(f"   Reduction in Taxable Amount: ${taxable_gain_difference:,.2f}")
    print(f"   💡 Lower taxable amount = less income to report to ATO")
    
    # Long-term vs short-term breakdown for CGT discount analysis
    fifo_lt = sum(1 for m in fifo_matches if m['long_term_eligible'])
    optimal_lt = sum(1 for m in optimal_matches if m['long_term_eligible'])
    
    fifo_lt_gains = sum(m['capital_gain'] for m in fifo_matches if m['long_term_eligible'] and m['capital_gain'] > 0)
    optimal_lt_gains = sum(m['capital_gain'] for m in optimal_matches if m['long_term_eligible'] and m['capital_gain'] > 0)
    
    print(f"\n📈 CGT DISCOUNT UTILIZATION:")
    print(f"   FIFO: {fifo_lt}/{len(fifo_matches)} transactions used 12+ month holdings")
    print(f"   Tax-Optimal: {optimal_lt}/{len(optimal_matches)} transactions used 12+ month holdings")
    print(f"   FIFO: ${fifo_lt_gains:,.2f} in gains eligible for 50% CGT discount")
    print(f"   Tax-Optimal: ${optimal_lt_gains:,.2f} in gains eligible for 50% CGT discount")
    
    return {
        'fifo_total_gain': fifo_total_gain,
        'fifo_taxable_gain': fifo_taxable_gain,
        'fifo_gains': fifo_gains,
        'fifo_losses': fifo_losses,
        'optimal_total_gain': optimal_total_gain,
        'optimal_taxable_gain': optimal_taxable_gain,
        'optimal_gains': optimal_gains,
        'optimal_losses': optimal_losses,
        'taxable_reduction': taxable_gain_difference,
        'total_gain_reduction': total_gain_difference
    }

def generate_detailed_report(fifo_matches, optimal_matches, comparison, financial_year):
    """Generate detailed Excel report."""
    print(f"\n📄 GENERATING DETAILED REPORT")
    print("=" * 40)
    
    try:
        # Create DataFrames
        fifo_df = pd.DataFrame(fifo_matches)
        optimal_df = pd.DataFrame(optimal_matches)
        
        # Format dates
        if len(fifo_df) > 0:
            fifo_df['sale_date'] = fifo_df['sale_date'].dt.strftime('%Y-%m-%d')
            fifo_df['purchase_date'] = fifo_df['purchase_date'].dt.strftime('%Y-%m-%d')
        
        if len(optimal_df) > 0:
            optimal_df['sale_date'] = optimal_df['sale_date'].dt.strftime('%Y-%m-%d')
            optimal_df['purchase_date'] = optimal_df['purchase_date'].dt.strftime('%Y-%m-%d')
        
        # Create summary for ATO reporting
        summary_data = {
            'Metric': [
                'FIFO - Total Capital Gains',
                'FIFO - Total Capital Losses', 
                'FIFO - Net Capital Gain/Loss',
                'FIFO - Taxable Amount (after CGT discount)',
                'Tax Optimal - Total Capital Gains',
                'Tax Optimal - Total Capital Losses',
                'Tax Optimal - Net Capital Gain/Loss', 
                'Tax Optimal - Taxable Amount (after CGT discount)',
                'Reduction in Taxable Amount',
                'Financial Year'
            ],
            'Value': [
                comparison['fifo_gains'],
                comparison['fifo_losses'],
                comparison['fifo_total_gain'],
                comparison['fifo_taxable_gain'],
                comparison['optimal_gains'],
                comparison['optimal_losses'],
                comparison['optimal_total_gain'],
                comparison['optimal_taxable_gain'],
                comparison['taxable_reduction'],
                financial_year
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Save to Excel
        filename = f"CGT_Strategy_Comparison_FY{financial_year}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            if len(fifo_df) > 0:
                fifo_df.to_excel(writer, sheet_name='FIFO_Strategy', index=False)
            if len(optimal_df) > 0:
                optimal_df.to_excel(writer, sheet_name='Tax_Optimal_Strategy', index=False)
        
        print(f"✅ Report saved: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return None

def main():
    """Main function to run CGT optimization analysis with AUD conversion."""
    print("🎯 CGT OPTIMIZER with AUD CONVERSION")
    print("=" * 70)
    print("Compare FIFO vs Tax-Optimal strategies")
    print("Prioritizes: 12+ month holdings + highest cost basis")
    print("🇦🇺 NEW: AUD conversion using RBA exchange rates")
    print()
    
    # Configuration
    html_folder = "html_folder"
    cost_basis_file = "COMPLETE_unified_cost_basis_with_FIFO_hybrid_sell_cutoff_2024_06_30.json"
    financial_year = "2024-25"
    
    # RBA exchange rate files
    rba_files = [
        "FX_2018-2022.csv",
        "FX_2023-2025.csv"
    ]
    
    # Step 1: Load RBA exchange rates
    print("💱 STEP 1: LOADING RBA EXCHANGE RATES")
    print("=" * 50)
    aud_converter = RBAAUDConverter()
    aud_converter.load_rba_csv_files(rba_files)
    
    if not aud_converter.exchange_rates:
        print("❌ Failed to load exchange rate data")
        print("⚠️ Continuing with USD-only calculations...")
        aud_converter = None
    
    # Step 2: Load cost basis
    cost_basis_dict = load_cost_basis_json(cost_basis_file)
    if not cost_basis_dict:
        print("❌ Failed to load cost basis")
        return
    
    # Step 3: Extract FY sales
    sales = extract_fy_sales(html_folder, financial_year)
    if not sales:
        print("❌ No sales found for analysis")
        return
    
    # Step 4: Apply FIFO strategy
    fifo_matches, fifo_warnings = apply_fifo_strategy(sales, cost_basis_dict)
    
    # Step 5: Apply tax-optimal strategy
    optimal_matches, optimal_warnings = apply_tax_optimal_strategy(sales, cost_basis_dict)
    
    # Step 6: Convert to AUD if exchange rates available
    if aud_converter:
        print(f"\n💱 STEP 6: CONVERTING TO AUD")
        print("=" * 40)
        
        # Convert FIFO results to AUD
        fifo_df = pd.DataFrame(fifo_matches)
        if len(fifo_df) > 0:
            fifo_df_aud = aud_converter.enhance_cgt_dataframe_with_aud(fifo_df)
        else:
            fifo_df_aud = fifo_df
        
        # Convert optimal results to AUD
        optimal_df = pd.DataFrame(optimal_matches)
        if len(optimal_df) > 0:
            optimal_df_aud = aud_converter.enhance_cgt_dataframe_with_aud(optimal_df)
        else:
            optimal_df_aud = optimal_df
        
        # Create AUD comparison
        if len(fifo_df_aud) > 0 and len(optimal_df_aud) > 0:
            aud_comparison = aud_converter.create_aud_summary(fifo_df_aud, optimal_df_aud)
        else:
            aud_comparison = None
    else:
        fifo_df_aud = pd.DataFrame(fifo_matches)
        optimal_df_aud = pd.DataFrame(optimal_matches)
        aud_comparison = None
    
    # Step 7: Compare strategies (USD)
    usd_comparison = compare_strategies(fifo_matches, optimal_matches)
    
    # Step 8: Generate report with AUD data
    report_file = generate_detailed_report_with_aud(
        fifo_matches, optimal_matches, 
        fifo_df_aud, optimal_df_aud,
        usd_comparison, aud_comparison, 
        financial_year
    )
    
    # Step 9: Final summary
    print(f"\n🎉 ANALYSIS COMPLETE!")
    print("=" * 30)
    print(f"📊 Analyzed {len(sales)} sales transactions")
    
    if aud_comparison:
        print(f"🇦🇺 AUD RESULTS (for ATO):")
        print(f"   💰 Tax-optimal taxable gain: ${aud_comparison['optimal_taxable_gain_aud']:,.2f} AUD")
        print(f"   💰 AUD savings vs FIFO: ${aud_comparison['aud_savings']:,.2f} AUD")
    else:
        print(f"💰 USD reduction in taxable amount: ${usd_comparison['taxable_reduction']:,.2f}")
    
    if report_file:
        print(f"📄 Detailed report: {report_file}")
    
    if fifo_warnings or optimal_warnings:
        print(f"\n⚠️ WARNINGS:")
        for warning in set(fifo_warnings + optimal_warnings):
            print(f"   • {warning}")
    
    print(f"\n💡 Next steps:")
    if aud_comparison:
        print(f"   1. Use AUD amounts for ATO tax return")
        print(f"   2. Report taxable gain: ${aud_comparison['optimal_taxable_gain_aud']:,.2f} AUD")
        print(f"   3. Review detailed Excel report with dual currency")
    else:
        print(f"   1. Review the detailed Excel report")
        print(f"   2. Consider adding RBA exchange rate data for AUD conversion")
        print(f"   3. Use tax-optimal strategy for reporting")f"   2. Use 'Tax Optimal' strategy amounts for ATO lodgment")
    print(f"   3. Report taxable amount: ${comparison['optimal_taxable_gain']:,.2f}")

if __name__ == "__main__":
    main()