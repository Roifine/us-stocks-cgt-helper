#!/usr/bin/env python3
"""
Australian CGT Calculator & Optimizer

This script takes:
1. Sales CSV from current financial year
2. Cost basis dictionary JSON

And produces:
1. Excel sheet with Australian CGT calculations (sales matched to optimal purchases)
2. Updated cost basis dictionary JSON (remaining units after sales)

Features:
- Tax-optimized matching (prioritizes long-term holdings for CGT discount)
- Australian CGT rules (50% discount for >12 months)
- Warnings for insufficient cost basis
- Remaining cost basis tracking

Usage:
    python cgt_calculator_australia.py
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
import warnings

# For Excel writing
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("⚠️ openpyxl not installed. Excel files will not be created.")
    print("Install with: pip install openpyxl")

def load_sales_csv(file_path):
    """
    Load sales transactions from CSV or Excel file.
    
    Args:
        file_path (str): Path to the sales CSV or Excel file
    
    Returns:
        pandas.DataFrame: Sales transactions
    """
    try:
        # Check file extension
        if file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
            # Load Excel file
            print(f"📊 Detected Excel file: {file_path}")
            
            # Try to read the Excel file, looking for sheets with sales data
            try:
                # First, try to get sheet names
                xl_file = pd.ExcelFile(file_path)
                sheet_names = xl_file.sheet_names
                print(f"   📋 Available sheets: {sheet_names}")
                
                # Look for sales sheet
                sales_sheet = None
                for sheet in sheet_names:
                    if 'sales' in sheet.lower() or 'fy' in sheet.lower():
                        sales_sheet = sheet
                        break
                
                if sales_sheet:
                    print(f"   📄 Using sheet: {sales_sheet}")
                    df = pd.read_excel(file_path, sheet_name=sales_sheet)
                else:
                    print(f"   📄 Using first sheet: {sheet_names[0]}")
                    df = pd.read_excel(file_path, sheet_name=0)
                    
            except Exception as e:
                print(f"   ⚠️ Error reading Excel sheets, trying default: {e}")
                df = pd.read_excel(file_path)
        else:
            # Load CSV file
            print(f"📄 Detected CSV file: {file_path}")
            df = pd.read_csv(file_path)
        
        # Standardize column names and data
        print(f"   📊 Loaded {len(df)} rows with columns: {list(df.columns)}")
        
        # Convert Trade Date to datetime if it exists
        if 'Trade Date' in df.columns:
            df['Trade Date'] = pd.to_datetime(df['Trade Date'])
        elif 'Date' in df.columns:
            df['Trade Date'] = pd.to_datetime(df['Date'])
        else:
            # Look for any date-like column
            date_columns = [col for col in df.columns if 'date' in col.lower()]
            if date_columns:
                df['Trade Date'] = pd.to_datetime(df[date_columns[0]])
                print(f"   📅 Using {date_columns[0]} as Trade Date")
        
        # Sort by date and reset index
        if 'Trade Date' in df.columns:
            df = df.sort_values('Trade Date').reset_index(drop=True)
        
        print(f"✅ Successfully loaded {len(df)} sales transactions from {file_path}")
        
        # Show sample of data
        print(f"   📋 Sample columns: {list(df.columns)[:8]}")
        if len(df) > 0:
            print(f"   📋 Sample data:")
            for col in ['Symbol', 'Units_Sold', 'Trade Date', 'Sale_Price_Per_Unit'][:4]:
                if col in df.columns:
                    print(f"      {col}: {df[col].iloc[0]}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading sales file: {e}")
        print(f"   💡 Make sure the file exists and contains sales transaction data")
        return None

def load_cost_basis_json(json_file_path):
    """
    Load cost basis dictionary from JSON file.
    
    Args:
        json_file_path (str): Path to the cost basis JSON file
    
    Returns:
        dict: Cost basis dictionary
    """
    try:
        with open(json_file_path, 'r') as f:
            cost_basis_dict = json.load(f)
        print(f"✅ Loaded cost basis for {len(cost_basis_dict)} symbols from {json_file_path}")
        return cost_basis_dict
    except Exception as e:
        print(f"❌ Error loading cost basis JSON: {e}")
        return None

def parse_date(date_str):
    """
    Parse date string in DD.M.YY format to datetime object.
    
    Args:
        date_str (str): Date string in DD.M.YY format
    
    Returns:
        datetime: Parsed datetime object
    """
    try:
        return datetime.strptime(date_str, "%d.%m.%y")
    except:
        try:
            return datetime.strptime(date_str, "%d.%-m.%y")
        except:
            # Fallback for different formats
            return pd.to_datetime(date_str)

def days_between_dates(buy_date_str, sell_date):
    """
    Calculate days between buy date (string) and sell date (datetime).
    
    Args:
        buy_date_str (str): Buy date in DD.M.YY format
        sell_date (datetime): Sell date as datetime object
    
    Returns:
        int: Number of days between dates
    """
    buy_date = parse_date(buy_date_str)
    return (sell_date - buy_date).days

def select_optimal_units_for_cgt(cost_basis_records, units_needed, sell_date):
    """
    Select the most tax-efficient units to sell for Australian CGT:
    1. Prioritize units held > 12 months (for 50% CGT discount)
    2. Within long-term holdings, select highest cost basis first (minimize gain)
    3. If not enough long-term, use short-term with highest cost basis
    
    Args:
        cost_basis_records (list): List of purchase records for the symbol
        units_needed (float): Number of units being sold
        sell_date (datetime): Date of the sale
    
    Returns:
        tuple: (selected_units, remaining_units_needed, updated_records)
    """
    # Make a copy to avoid modifying original data
    available_records = []
    for record in cost_basis_records:
        if record['units'] > 0:  # Only consider records with available units
            available_records.append({
                'units': record['units'],
                'price': record['price'],
                'commission': record['commission'],
                'date': record['date'],
                'days_held': days_between_dates(record['date'], sell_date),
                'long_term': days_between_dates(record['date'], sell_date) >= 365,
                'total_cost_per_unit': record['price'] + (record['commission'] / record['units'])
            })
    
    selected_units = []
    remaining_units = units_needed
    
    # Step 1: Prioritize long-term holdings (>= 365 days) with highest cost basis first
    long_term_records = [r for r in available_records if r['long_term']]
    long_term_records.sort(key=lambda x: x['total_cost_per_unit'], reverse=True)  # Highest cost first
    
    for record in long_term_records:
        if remaining_units <= 0:
            break
            
        units_to_use = min(remaining_units, record['units'])
        
        selected_units.append({
            'units': units_to_use,
            'price': record['price'],
            'commission': record['commission'] * (units_to_use / record['units']),  # Proportional commission
            'buy_date': record['date'],
            'days_held': record['days_held'],
            'long_term_eligible': True,
            'total_cost': (units_to_use * record['price']) + (record['commission'] * (units_to_use / record['units'])),
            'cost_per_unit': record['total_cost_per_unit']
        })
        
        remaining_units -= units_to_use
        record['units'] -= units_to_use  # Update available units
    
    # Step 2: If still need units, use short-term holdings with highest cost basis
    if remaining_units > 0:
        short_term_records = [r for r in available_records if not r['long_term'] and r['units'] > 0]
        short_term_records.sort(key=lambda x: x['total_cost_per_unit'], reverse=True)  # Highest cost first
        
        for record in short_term_records:
            if remaining_units <= 0:
                break
                
            units_to_use = min(remaining_units, record['units'])
            
            selected_units.append({
                'units': units_to_use,
                'price': record['price'],
                'commission': record['commission'] * (units_to_use / record['units']),
                'buy_date': record['date'],
                'days_held': record['days_held'],
                'long_term_eligible': False,
                'total_cost': (units_to_use * record['price']) + (record['commission'] * (units_to_use / record['units'])),
                'cost_per_unit': record['total_cost_per_unit']
            })
            
            remaining_units -= units_to_use
            record['units'] -= units_to_use
    
    return selected_units, remaining_units, available_records

def calculate_australian_cgt(sales_df, cost_basis_dict):
    """
    Calculate Australian Capital Gains Tax for all sales transactions.
    
    Args:
        sales_df (pandas.DataFrame): Sales transactions
        cost_basis_dict (dict): Cost basis dictionary
    
    Returns:
        tuple: (cgt_df, remaining_cost_basis_dict, warnings_list)
    """
    print(f"\n🔄 Calculating Australian CGT for {len(sales_df)} sales transactions...")
    
    # Create a working copy of cost basis dictionary
    working_cost_basis = {}
    for symbol, records in cost_basis_dict.items():
        working_cost_basis[symbol] = [record.copy() for record in records]
    
    cgt_records = []
    warnings_list = []
    
    # Process each sale transaction
    for index, sale in sales_df.iterrows():
        symbol = sale['Symbol']
        units_sold = abs(sale.get('Units_Sold', sale.get('Quantity', 0)))
        sale_price_per_unit = abs(sale.get('Sale_Price_Per_Unit', sale.get('Price (USD)', 0)))
        sale_date = sale['Trade Date']
        sale_commission = abs(sale.get('Commission_Paid', sale.get('Commission (USD)', 0)))
        total_proceeds = abs(sale.get('Total_Proceeds', sale.get('Proceeds (USD)', 0)))
        net_proceeds = sale.get('Net_Proceeds', total_proceeds - sale_commission)
        
        print(f"\n📉 Processing sale: {units_sold} units of {symbol} on {sale_date.strftime('%d.%m.%y')}")
        
        # Check if symbol exists in cost basis
        if symbol not in working_cost_basis:
            warning_msg = f"❌ NO COST BASIS FOUND for {symbol}"
            warnings_list.append(warning_msg)
            print(f"   {warning_msg}")
            
            cgt_records.append({
                'Sale_Date': sale_date.strftime('%d.%m.%y'),
                'Symbol': symbol,
                'Units_Sold': units_sold,
                'Sale_Price_Per_Unit': sale_price_per_unit,
                'Total_Proceeds': total_proceeds,
                'Sale_Commission': sale_commission,
                'Net_Proceeds': net_proceeds,
                'Buy_Date': 'N/A',
                'Buy_Price_Per_Unit': 0,
                'Buy_Commission': 0,
                'Units_Matched': 0,
                'Days_Held': 0,
                'Long_Term_Eligible': False,
                'Cost_Basis': 0,
                'Capital_Gain_Loss': net_proceeds,
                'CGT_Discount_Applied': False,
                'Taxable_Gain': net_proceeds,
                'Warning': 'NO COST BASIS DATA'
            })
            continue
        
        # Select optimal units for this sale
        selected_units, missing_units, updated_records = select_optimal_units_for_cgt(
            working_cost_basis[symbol], units_sold, sale_date
        )
        
        # Update the working cost basis with remaining units
        working_cost_basis[symbol] = updated_records
        
        if not selected_units:
            warning_msg = f"❌ NO UNITS AVAILABLE for {symbol}"
            warnings_list.append(warning_msg)
            print(f"   {warning_msg}")
            
            cgt_records.append({
                'Sale_Date': sale_date.strftime('%d.%m.%y'),
                'Symbol': symbol,
                'Units_Sold': units_sold,
                'Sale_Price_Per_Unit': sale_price_per_unit,
                'Total_Proceeds': total_proceeds,
                'Sale_Commission': sale_commission,
                'Net_Proceeds': net_proceeds,
                'Buy_Date': 'N/A',
                'Buy_Price_Per_Unit': 0,
                'Buy_Commission': 0,
                'Units_Matched': 0,
                'Days_Held': 0,
                'Long_Term_Eligible': False,
                'Cost_Basis': 0,
                'Capital_Gain_Loss': net_proceeds,
                'CGT_Discount_Applied': False,
                'Taxable_Gain': net_proceeds,
                'Warning': 'NO UNITS AVAILABLE'
            })
            continue
        
        # Create detailed records for each matched purchase
        for unit_selection in selected_units:
            # Calculate proportional proceeds for this portion
            proportion = unit_selection['units'] / units_sold
            proportional_proceeds = total_proceeds * proportion
            proportional_sale_commission = sale_commission * proportion
            proportional_net_proceeds = net_proceeds * proportion
            
            # Calculate gain/loss
            cost_basis = unit_selection['total_cost']
            capital_gain_loss = proportional_net_proceeds - cost_basis
            
            # Apply Australian CGT discount if eligible (50% discount for assets held > 12 months)
            cgt_discount_applied = unit_selection['long_term_eligible'] and capital_gain_loss > 0
            taxable_gain = capital_gain_loss
            if cgt_discount_applied:
                taxable_gain = capital_gain_loss * 0.5  # 50% CGT discount
            
            # Warning for missing units
            warning_msg = ""
            if missing_units > 0:
                warning_msg = f"MISSING {missing_units:.2f} UNITS"
            
            cgt_records.append({
                'Sale_Date': sale_date.strftime('%d.%m.%y'),
                'Symbol': symbol,
                'Units_Sold': unit_selection['units'],
                'Sale_Price_Per_Unit': sale_price_per_unit,
                'Total_Proceeds': proportional_proceeds,
                'Sale_Commission': proportional_sale_commission,
                'Net_Proceeds': proportional_net_proceeds,
                'Buy_Date': unit_selection['buy_date'],
                'Buy_Price_Per_Unit': unit_selection['price'],
                'Buy_Commission': unit_selection['commission'],
                'Units_Matched': unit_selection['units'],
                'Days_Held': unit_selection['days_held'],
                'Long_Term_Eligible': unit_selection['long_term_eligible'],
                'Cost_Basis': cost_basis,
                'Capital_Gain_Loss': capital_gain_loss,
                'CGT_Discount_Applied': cgt_discount_applied,
                'Taxable_Gain': taxable_gain,
                'Warning': warning_msg
            })
            
            print(f"   ✅ Matched {unit_selection['units']:.2f} units from {unit_selection['buy_date']} "
                  f"({unit_selection['days_held']} days, {'Long-term' if unit_selection['long_term_eligible'] else 'Short-term'})")
        
        if missing_units > 0:
            warning_msg = f"⚠️  {symbol}: Missing {missing_units:.2f} units for complete matching"
            warnings_list.append(warning_msg)
            print(f"   {warning_msg}")
    
    # Create remaining cost basis dictionary (only units that weren't sold)
    remaining_cost_basis = {}
    for symbol, records in working_cost_basis.items():
        remaining_records = []
        for record in records:
            if record['units'] > 0:  # Only keep records with remaining units
                remaining_records.append({
                    'units': record['units'],
                    'price': record['price'],
                    'commission': record['commission'],
                    'date': record['date']
                })
        
        if remaining_records:
            remaining_cost_basis[symbol] = remaining_records
    
    print(f"\n✅ CGT calculation complete:")
    print(f"   📊 {len(cgt_records)} matched transactions")
    print(f"   ⚠️  {len(warnings_list)} warnings")
    print(f"   📋 {len(remaining_cost_basis)} symbols with remaining units")
    
    return pd.DataFrame(cgt_records), remaining_cost_basis, warnings_list

def save_cgt_excel(cgt_df, financial_year, output_file=None):
    """
    Save CGT calculations to Excel file formatted for Australian tax reporting.
    
    Args:
        cgt_df (pandas.DataFrame): CGT calculations
        financial_year (str): Financial year (e.g., "2024-25")
        output_file (str): Output filename (optional)
    
    Returns:
        str: Output filename
    """
    
    if not EXCEL_AVAILABLE:
        print("❌ openpyxl not available - cannot create Excel file")
        return None
    
    if output_file is None:
        output_file = f"Australian_CGT_Report_FY{financial_year}.xlsx"
    
    print(f"\n💾 Creating Australian CGT Excel report: {output_file}")
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            # Main CGT sheet
            cgt_df.to_excel(writer, sheet_name='CGT_Calculations', index=False)
            
            # Summary sheet
            summary_data = {
                'Total_Capital_Gains': [cgt_df['Capital_Gain_Loss'].sum()],
                'Total_Taxable_Gains': [cgt_df['Taxable_Gain'].sum()],
                'Long_Term_Gains': [cgt_df[cgt_df['Long_Term_Eligible'] == True]['Capital_Gain_Loss'].sum()],
                'Short_Term_Gains': [cgt_df[cgt_df['Long_Term_Eligible'] == False]['Capital_Gain_Loss'].sum()],
                'CGT_Discount_Applied': [cgt_df['CGT_Discount_Applied'].sum()],
                'Financial_Year': [financial_year]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Warnings sheet (if any)
            warnings_data = cgt_df[cgt_df['Warning'] != '']
            if len(warnings_data) > 0:
                warnings_data.to_excel(writer, sheet_name='Warnings', index=False)
        
        print(f"✅ Australian CGT report saved: {output_file}")
        
        # Display summary
        total_gain = cgt_df['Capital_Gain_Loss'].sum()
        taxable_gain = cgt_df['Taxable_Gain'].sum()
        long_term_count = len(cgt_df[cgt_df['Long_Term_Eligible'] == True])
        
        print(f"\n📊 CGT Summary for FY {financial_year}:")
        print(f"   💰 Total Capital Gain/Loss: ${total_gain:,.2f} USD")
        print(f"   📋 Total Taxable Gain: ${taxable_gain:,.2f} USD")
        print(f"   🟢 Long-term transactions: {long_term_count}")
        print(f"   🟡 Short-term transactions: {len(cgt_df) - long_term_count}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error creating Excel file: {e}")
        return None

def save_remaining_cost_basis(remaining_cost_basis, financial_year, output_file=None):
    """
    Save remaining cost basis dictionary to JSON file.
    
    Args:
        remaining_cost_basis (dict): Remaining cost basis after sales
        financial_year (str): Financial year
        output_file (str): Output filename (optional)
    
    Returns:
        str: Output filename
    """
    
    if output_file is None:
        output_file = f"cost_basis_dictionary_post_FY{financial_year}.json"
    
    try:
        with open(output_file, 'w') as f:
            json.dump(remaining_cost_basis, f, indent=2)
        
        print(f"✅ Remaining cost basis saved: {output_file}")
        
        total_symbols = len(remaining_cost_basis)
        total_units = sum(sum(record['units'] for record in records) for records in remaining_cost_basis.values())
        total_value = sum(sum(record['units'] * record['price'] for record in records) for records in remaining_cost_basis.values())
        
        print(f"📊 Remaining holdings:")
        print(f"   🏷️  Symbols: {total_symbols}")
        print(f"   📦 Units: {total_units:,.2f}")
        print(f"   💰 Value: ${total_value:,.2f} USD (cost basis)")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving remaining cost basis: {e}")
        return None

def main():
    """
    Main function to run Australian CGT calculations.
    """
    
    print("🇦🇺 AUSTRALIAN CGT CALCULATOR & OPTIMIZER")
    print("="*60)
    print("This script calculates Australian CGT with optimal tax matching:")
    print("• Prioritizes long-term holdings (>12 months) for 50% CGT discount")
    print("• Matches highest cost basis first to minimize gains")
    print("• Provides detailed Excel report for tax lodgment")
    print("• Creates updated cost basis dictionary for remaining holdings")
    print()
    
    # Get input files
    print("📄 Input files needed:")
    print("1. Sales CSV file (current financial year)")
    print("2. Cost basis dictionary JSON file")
    print()
    
    # Look for likely files
    sales_files = []
    # Look for sales files (both CSV and Excel)
    for ext in ['.csv', '.xlsx', '.xls']:
        sales_files.extend([f for f in os.listdir('.') if 'sales' in f.lower() and f.endswith(ext)])
        sales_files.extend([f for f in os.listdir('.') if 'cgt' in f.lower() and f.endswith(ext)])
    
    # Remove duplicates and sort
    sales_files = sorted(list(set(sales_files)))
    
    cost_basis_files = [f for f in os.listdir('.') if 'cost_basis' in f.lower() and f.endswith('.json')]
    
    print("🔍 Found potential files:")
    if sales_files:
        print("   Sales files (CSV/Excel):")
        for i, file in enumerate(sales_files, 1):
            print(f"   {i}. {file}")
    
    if cost_basis_files:
        print("   Cost basis JSON files:")
        for i, file in enumerate(cost_basis_files, 1):
            print(f"   {i}. {file}")
    
    # Get file selections
    try:
        print("\nSelect files to use:")
        
        if sales_files:
            sales_choice = input(f"Sales file (1-{len(sales_files)} or filename): ").strip()
            try:
                sales_file = sales_files[int(sales_choice) - 1]
            except:
                sales_file = sales_choice
        else:
            sales_file = input("Sales file (CSV/Excel) filename: ").strip()
        
        if cost_basis_files:
            cost_choice = input(f"Cost basis JSON file (1-{len(cost_basis_files)} or filename): ").strip()
            try:
                cost_basis_file = cost_basis_files[int(cost_choice) - 1]
            except:
                cost_basis_file = cost_choice
        else:
            cost_basis_file = input("Cost basis JSON filename: ").strip()
        
        financial_year = input("Financial year (e.g., 2024-25): ").strip() or "2024-25"
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted")
        return
    
    # Load input files
    print(f"\n🔄 Loading input files...")
    sales_df = load_sales_csv(sales_file)
    cost_basis_dict = load_cost_basis_json(cost_basis_file)
    
    if sales_df is None or cost_basis_dict is None:
        print("❌ Failed to load input files")
        return
    
    # Calculate CGT
    cgt_df, remaining_cost_basis, warnings_list = calculate_australian_cgt(sales_df, cost_basis_dict)
    
    if cgt_df is None or len(cgt_df) == 0:
        print("❌ No CGT calculations generated")
        return
    
    # Save results
    print(f"\n💾 Saving results...")
    excel_file = save_cgt_excel(cgt_df, financial_year)
    json_file = save_remaining_cost_basis(remaining_cost_basis, financial_year)
    
    # Display warnings
    if warnings_list:
        print(f"\n⚠️  WARNINGS ({len(warnings_list)}):")
        for warning in warnings_list[:10]:  # Show first 10
            print(f"   • {warning}")
        if len(warnings_list) > 10:
            print(f"   • ... and {len(warnings_list) - 10} more warnings")
    
    # Final summary
    print(f"\n🎉 Australian CGT calculation complete!")
    print(f"📄 Files created:")
    if excel_file:
        print(f"   📊 {excel_file} - Australian CGT report for tax lodgment")
    if json_file:
        print(f"   📋 {json_file} - Remaining cost basis for future calculations")
    
    print(f"\n📋 Next steps:")
    print(f"1. Review the Excel file for your tax lodgment")
    print(f"2. Use the remaining cost basis JSON for future CGT calculations")
    print(f"3. Address any warnings listed above")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your input files and try again")