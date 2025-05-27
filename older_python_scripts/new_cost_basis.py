import pandas as pd
from datetime import datetime, timedelta
import json
import os
import shutil
from copy import deepcopy

def create_transaction_fingerprint(row, source_file):
    """
    Create unique fingerprint for transaction to detect duplicates.
    
    Args:
        row (pandas.Series): Transaction row
        source_file (str): Source CSV filename
    
    Returns:
        str: Unique transaction fingerprint
    """
    symbol = row['Symbol']
    date = pd.to_datetime(row['Trade Date']).strftime('%Y-%m-%d')
    tx_type = row['Type']
    quantity = abs(row['Quantity'])
    price = abs(row['Price (USD)']) if 'Price (USD)' in row else 0
    commission = abs(row['Commission (USD)']) if 'Commission (USD)' in row else 0
    
    return f"{symbol}_{date}_{tx_type}_{quantity}_{price}_{commission}_{os.path.basename(source_file)}"

def load_processed_transactions(file_path='processed_transactions.json'):
    """
    Load list of already processed transaction fingerprints.
    
    Args:
        file_path (str): Path to processed transactions file
    
    Returns:
        dict: Dictionary with processed fingerprints and metadata
    """
    if not os.path.exists(file_path):
        return {
            'processed_fingerprints': [],
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': 0
        }
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load processed transactions file: {e}")
        return {
            'processed_fingerprints': [],
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_processed': 0
        }

def save_processed_transactions(processed_data, file_path='processed_transactions.json'):
    """
    Save processed transaction fingerprints.
    
    Args:
        processed_data (dict): Processed transaction data
        file_path (str): Output file path
    """
    processed_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    processed_data['total_processed'] = len(processed_data['processed_fingerprints'])
    
    try:
        with open(file_path, 'w') as f:
            json.dump(processed_data, f, indent=2)
    except Exception as e:
        print(f"Error saving processed transactions: {e}")

def backup_json_files():
    """
    Create backup copies of existing JSON files.
    
    Returns:
        dict: Backup status for each file
    """
    files_to_backup = [
        'all_transactions.json',
        'remaining_holdings.json', 
        'processed_transactions.json',
        'cost_basis_dictionary.json'  # Legacy file
    ]
    
    backup_status = {}
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for file_name in files_to_backup:
        if os.path.exists(file_name):
            try:
                backup_name = f"{file_name.split('.')[0]}_backup_{timestamp}.json"
                shutil.copy2(file_name, backup_name)
                backup_status[file_name] = f"Backed up to {backup_name}"
            except Exception as e:
                backup_status[file_name] = f"Backup failed: {e}"
        else:
            backup_status[file_name] = "File not found, no backup needed"
    
    return backup_status

def load_existing_json(file_path, default_value=None):
    """
    Load existing JSON file or return default value.
    
    Args:
        file_path (str): Path to JSON file
        default_value: Default value if file doesn't exist
    
    Returns:
        dict: Loaded data or default value
    """
    if default_value is None:
        default_value = {}
    
    if not os.path.exists(file_path):
        return default_value
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {file_path}: {e}")
        return default_value

def days_between_dates(buy_date_str, sell_date):
    """
    Calculate days between buy date (string) and sell date (datetime).
    
    Args:
        buy_date_str (str): Buy date in DD.M.YY format
        sell_date (datetime): Sell date as datetime object
    
    Returns:
        int: Number of days between dates
    """
    try:
        if isinstance(buy_date_str, str):
            buy_date = datetime.strptime(buy_date_str, "%d.%m.%y")
        else:
            buy_date = pd.to_datetime(buy_date_str)
        return (sell_date - buy_date).days
    except Exception as e:
        print(f"Warning: Could not calculate days between {buy_date_str} and {sell_date}: {e}")
        return 0

def select_units_for_sale_tax_optimized(holdings, units_to_sell, sell_date):
    """
    Select units to sell using tax-optimized strategy:
    1. If sell_units > available_units: clear all holdings (missing historical data)
    2. Otherwise: Long-term holdings (>365 days) with highest cost basis first
    3. Then: Short-term holdings with highest cost basis
    
    Args:
        holdings (list): Available holdings for the symbol
        units_to_sell (float): Number of units being sold
        sell_date (datetime): Sale date
    
    Returns:
        tuple: (units_used, remaining_units_needed, alerts, should_clear_all_holdings)
    """
    # Calculate total available units
    total_available = sum(h['units'] for h in holdings)
    alerts = []
    
    # If selling more than we have on record, assume missing historical data
    # and clear all holdings
    if units_to_sell > total_available:
        alerts.append(f"MISSING_HISTORICAL_DATA: Selling {units_to_sell:.6f} units but only {total_available:.6f} available in records")
        alerts.append(f"CLEARING_ALL_HOLDINGS: Assuming earlier purchases covered the shortfall")
        
        # Return all available units as "used" and signal to clear holdings
        units_used = []
        for holding in holdings:
            if holding['units'] > 0:
                holding['days_held'] = days_between_dates(holding['date'], sell_date)
                units_used.append({
                    'units': holding['units'],
                    'price': holding['price'],
                    'commission': holding['commission'],
                    'date': holding['date'],
                    'days_held': holding['days_held'],
                    'is_long_term': holding['days_held'] >= 365,
                    'cost_basis': (holding['units'] * holding['price']) + holding['commission']
                })
        
        return units_used, 0, alerts, True  # True = clear all holdings
    
    # Normal processing when we have sufficient holdings
    available_holdings = deepcopy(holdings)
    units_used = []
    remaining_units = units_to_sell
    
    # Add holding period info to each holding
    for holding in available_holdings:
        holding['days_held'] = days_between_dates(holding['date'], sell_date)
        holding['is_long_term'] = holding['days_held'] >= 365
        holding['cost_per_unit'] = holding['price']
    
    # Step 1: Use long-term holdings (highest cost first for tax benefit)
    long_term_holdings = [h for h in available_holdings if h['is_long_term'] and h['units'] > 0]
    long_term_holdings.sort(key=lambda x: x['cost_per_unit'], reverse=True)
    
    for holding in long_term_holdings:
        if remaining_units <= 0:
            break
        
        units_from_this_holding = min(remaining_units, holding['units'])
        proportional_commission = holding['commission'] * (units_from_this_holding / holding['units'])
        
        units_used.append({
            'units': units_from_this_holding,
            'price': holding['price'],
            'commission': proportional_commission,
            'date': holding['date'],
            'days_held': holding['days_held'],
            'is_long_term': True,
            'cost_basis': (units_from_this_holding * holding['price']) + proportional_commission
        })
        
        remaining_units -= units_from_this_holding
        holding['units'] -= units_from_this_holding
    
    # Step 2: Use short-term holdings if needed (highest cost first)
    if remaining_units > 0:
        short_term_holdings = [h for h in available_holdings if not h['is_long_term'] and h['units'] > 0]
        short_term_holdings.sort(key=lambda x: x['cost_per_unit'], reverse=True)
        
        for holding in short_term_holdings:
            if remaining_units <= 0:
                break
            
            units_from_this_holding = min(remaining_units, holding['units'])
            proportional_commission = holding['commission'] * (units_from_this_holding / holding['units'])
            
            units_used.append({
                'units': units_from_this_holding,
                'price': holding['price'],
                'commission': proportional_commission,
                'date': holding['date'],
                'days_held': holding['days_held'],
                'is_long_term': False,
                'cost_basis': (units_from_this_holding * holding['price']) + proportional_commission
            })
            
            remaining_units -= units_from_this_holding
            holding['units'] -= units_from_this_holding
    
    # Generate alerts for normal processing
    if remaining_units > 0:
        alerts.append(f"PARTIAL_OVERSELL: {remaining_units:.6f} units could not be matched to holdings")
    
    short_term_units = sum(u['units'] for u in units_used if not u['is_long_term'])
    if short_term_units > 0:
        alerts.append(f"SHORT_TERM_SALE: {short_term_units:.6f} units held <365 days (no CGT discount)")
    
    return units_used, remaining_units, alerts, False  # False = don't clear all holdings

def process_incremental_transactions(csv_files):
    """
    Process transactions incrementally, only adding new ones.
    
    Args:
        csv_files (list): List of CSV file paths
    
    Returns:
        dict: Processing results and alerts
    """
    print("🔄 Starting incremental transaction processing...")
    
    # Load existing data
    processed_data = load_processed_transactions()
    all_transactions = load_existing_json('all_transactions.json')
    remaining_holdings = load_existing_json('remaining_holdings.json')
    
    # Initialize processing results
    results = {
        'new_transactions': 0,
        'skipped_duplicates': 0,
        'symbols_updated': set(),
        'buy_transactions': 0,
        'sell_transactions': 0,
        'alerts': [],
        'detailed_changes': [],
        'summary_changes': {}
    }
    
    # Process each CSV file
    for csv_file in csv_files:
        if not os.path.exists(csv_file):
            results['alerts'].append(f"CSV file not found: {csv_file}")
            continue
        
        print(f"📂 Processing {csv_file}...")
        
        try:
            df = pd.read_csv(csv_file)
            df['Trade Date'] = pd.to_datetime(df['Trade Date'])
            
            for index, row in df.iterrows():
                # Create transaction fingerprint
                fingerprint = create_transaction_fingerprint(row, csv_file)
                
                # Skip if already processed
                if fingerprint in processed_data['processed_fingerprints']:
                    results['skipped_duplicates'] += 1
                    continue
                
                # Process new transaction
                symbol = row['Symbol']
                tx_type = row['Type']
                trade_date = row['Trade Date']
                quantity = abs(row['Quantity'])
                price = abs(row['Price (USD)']) if 'Price (USD)' in row else 0
                commission = abs(row['Commission (USD)']) if 'Commission (USD)' in row else 0
                
                # Format date as DD.M.YY
                formatted_date = trade_date.strftime("%d.%-m.%y")
                
                # Create transaction record
                transaction_record = {
                    'units': quantity,
                    'price': price,
                    'commission': commission,
                    'date': formatted_date,
                    'transaction_type': tx_type,
                    'source_file': os.path.basename(csv_file),
                    'processed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add to all_transactions
                if symbol not in all_transactions:
                    all_transactions[symbol] = []
                all_transactions[symbol].append(transaction_record)
                
                # Update remaining holdings based on transaction type
                if symbol not in remaining_holdings:
                    remaining_holdings[symbol] = []
                
                if tx_type == 'BUY':
                    # Add to holdings
                    remaining_holdings[symbol].append({
                        'units': quantity,
                        'price': price,
                        'commission': commission,
                        'date': formatted_date,
                        'original_purchase_units': quantity,
                        'remaining_from_purchase': quantity
                    })
                    results['buy_transactions'] += 1
                    
                elif tx_type == 'SELL':
                    # Remove from holdings using tax-optimized strategy
                    units_used, remaining_units, alerts, should_clear_all = select_units_for_sale_tax_optimized(
                        remaining_holdings[symbol], quantity, trade_date
                    )
                    
                    # Update remaining holdings
                    if should_clear_all:
                        # Clear all holdings - selling more than available (missing historical data)
                        remaining_holdings[symbol] = []
                    else:
                        # Normal update - remove units that were sold
                        remaining_holdings[symbol] = [h for h in remaining_holdings[symbol] if h['units'] > 0]
                    
                    # Record alerts
                    for alert in alerts:
                        results['alerts'].append(f"{symbol} on {formatted_date}: {alert}")
                    
                    results['sell_transactions'] += 1
                
                # Track changes
                results['symbols_updated'].add(symbol)
                results['detailed_changes'].append({
                    'symbol': symbol,
                    'type': tx_type,
                    'units': quantity,
                    'date': formatted_date,
                    'source': os.path.basename(csv_file)
                })
                
                # Add to processed list
                processed_data['processed_fingerprints'].append(fingerprint)
                results['new_transactions'] += 1
                
        except Exception as e:
            results['alerts'].append(f"Error processing {csv_file}: {e}")
    
    # Sort transactions by date within each symbol
    for symbol in all_transactions:
        all_transactions[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%y"))
    
    for symbol in remaining_holdings:
        remaining_holdings[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%y"))
    
    # Generate summary changes
    for symbol in results['symbols_updated']:
        symbol_transactions = [t for t in results['detailed_changes'] if t['symbol'] == symbol]
        buy_count = len([t for t in symbol_transactions if t['type'] == 'BUY'])
        sell_count = len([t for t in symbol_transactions if t['type'] == 'SELL'])
        buy_units = sum(t['units'] for t in symbol_transactions if t['type'] == 'BUY')
        sell_units = sum(t['units'] for t in symbol_transactions if t['type'] == 'SELL')
        
        results['summary_changes'][symbol] = {
            'buy_transactions': buy_count,
            'sell_transactions': sell_count,
            'buy_units': buy_units,
            'sell_units': sell_units,
            'net_units': buy_units - sell_units,
            'remaining_units': sum(h['units'] for h in remaining_holdings.get(symbol, []))
        }
    
    # Save updated files
    try:
        with open('all_transactions.json', 'w') as f:
            json.dump(all_transactions, f, indent=2)
            
        with open('remaining_holdings.json', 'w') as f:
            json.dump(remaining_holdings, f, indent=2)
            
        save_processed_transactions(processed_data)
        
    except Exception as e:
        results['alerts'].append(f"Error saving JSON files: {e}")
    
    return results

def generate_change_report(results, output_file='processing_report.txt'):
    """
    Generate detailed change report.
    
    Args:
        results (dict): Processing results
        output_file (str): Output report file path
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("INCREMENTAL TRANSACTION PROCESSING REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Processing Summary
    report_lines.append("PROCESSING SUMMARY:")
    report_lines.append("-" * 40)
    report_lines.append(f"New transactions processed: {results['new_transactions']}")
    report_lines.append(f"Duplicate transactions skipped: {results['skipped_duplicates']}")
    report_lines.append(f"Buy transactions: {results['buy_transactions']}")
    report_lines.append(f"Sell transactions: {results['sell_transactions']}")
    report_lines.append(f"Symbols updated: {len(results['symbols_updated'])}")
    report_lines.append("")
    
    # Summary by Symbol
    if results['summary_changes']:
        report_lines.append("SUMMARY BY SYMBOL:")
        report_lines.append("-" * 40)
        for symbol, changes in results['summary_changes'].items():
            report_lines.append(f"{symbol}:")
            report_lines.append(f"  Buy transactions: {changes['buy_transactions']} ({changes['buy_units']:.2f} units)")
            report_lines.append(f"  Sell transactions: {changes['sell_transactions']} ({changes['sell_units']:.2f} units)")
            report_lines.append(f"  Net change: {changes['net_units']:+.2f} units")
            report_lines.append(f"  Remaining holdings: {changes['remaining_units']:.2f} units")
            report_lines.append("")
    
    # Detailed Changes
    if results['detailed_changes']:
        report_lines.append("DETAILED TRANSACTION LIST:")
        report_lines.append("-" * 40)
        for change in results['detailed_changes']:
            report_lines.append(f"{change['date']} | {change['symbol']} | {change['type']} | {change['units']:.2f} units | {change['source']}")
        report_lines.append("")
    
    # Alerts
    if results['alerts']:
        report_lines.append("ALERTS AND WARNINGS:")
        report_lines.append("-" * 40)
        for alert in results['alerts']:
            report_lines.append(f"⚠️  {alert}")
        report_lines.append("")
    
    report_lines.append("=" * 80)
    
    # Write to file
    try:
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_lines))
        print(f"📄 Change report saved to: {output_file}")
    except Exception as e:
        print(f"Error saving report: {e}")
    
    # Also print to console
    print('\n'.join(report_lines))

def create_enhanced_cost_basis_from_csv(csv_files):
    """
    Enhanced version that creates both transaction history and remaining holdings.
    
    Args:
        csv_files (list or str): List of CSV file paths, or single CSV file path
    
    Returns:
        tuple: (all_transactions_dict, remaining_holdings_dict, processing_results)
    """
    # Handle single file input
    if isinstance(csv_files, str):
        csv_files = [csv_files]
    
    print("🚀 Enhanced Cost Basis Processing with Incremental Updates")
    print("=" * 70)
    
    # Create backups
    print("💾 Creating backups of existing files...")
    backup_status = backup_json_files()
    for file_name, status in backup_status.items():
        print(f"  {file_name}: {status}")
    
    # Process transactions incrementally
    results = process_incremental_transactions(csv_files)
    
    # Generate change report
    generate_change_report(results)
    
    # Load final results
    all_transactions = load_existing_json('all_transactions.json')
    remaining_holdings = load_existing_json('remaining_holdings.json')
    
    return all_transactions, remaining_holdings, results

def display_enhanced_summary(all_transactions, remaining_holdings):
    """
    Display summary of all transactions and current holdings.
    
    Args:
        all_transactions (dict): Complete transaction history
        remaining_holdings (dict): Current holdings after sales
    """
    print("\n" + "="*70)
    print("ENHANCED COST BASIS SUMMARY")
    print("="*70)
    
    # Transaction History Summary
    print("\nTRANSACTION HISTORY:")
    print("-" * 30)
    for symbol, transactions in all_transactions.items():
        buy_count = len([t for t in transactions if t['transaction_type'] == 'BUY'])
        sell_count = len([t for t in transactions if t['transaction_type'] == 'SELL'])
        total_bought = sum(t['units'] for t in transactions if t['transaction_type'] == 'BUY')
        total_sold = sum(t['units'] for t in transactions if t['transaction_type'] == 'SELL')
        
        print(f"\n{symbol}:")
        print(f"  Transactions: {buy_count} buys, {sell_count} sells")
        print(f"  Units: {total_bought:.2f} bought, {total_sold:.2f} sold")
        print(f"  Date range: {transactions[0]['date']} to {transactions[-1]['date']}")
    
    # Current Holdings Summary
    print(f"\nCURRENT HOLDINGS:")
    print("-" * 30)
    for symbol, holdings in remaining_holdings.items():
        if not holdings:  # Skip symbols with no remaining holdings
            continue
            
        total_units = sum(h['units'] for h in holdings)
        total_cost = sum(h['units'] * h['price'] + h['commission'] for h in holdings)
        avg_price = total_cost / total_units if total_units > 0 else 0
        
        print(f"\n{symbol}:")
        print(f"  Current Units: {total_units:,.2f}")
        print(f"  Total Cost Basis: ${total_cost:,.2f} USD")
        print(f"  Average Cost: ${avg_price:.4f} USD per unit")
        print(f"  Holdings from {len(holdings)} purchase(s)")
        
        # Show individual holdings
        for i, holding in enumerate(holdings, 1):
            print(f"    {i}. {holding['units']:,.2f} units @ ${holding['price']:.4f} from {holding['date']}")

def main():
    """
    Main function to run enhanced cost basis processing.
    """
    print("🎯 Enhanced Cost Basis Tracker with Incremental Processing")
    print("=" * 60)
    
    # File paths - update these to match your actual files
    csv_files = [
        "all_years_transactions.csv",  # Your parsed HTML data              # Your cleaned trades
        # Add more CSV files as needed
    ]
    
    # Filter to only existing files
    existing_files = [f for f in csv_files if os.path.exists(f)]
    missing_files = [f for f in csv_files if not os.path.exists(f)]
    
    if missing_files:
        print("⚠️  Missing files (will be skipped):")
        for file in missing_files:
            print(f"   - {file}")
    
    if not existing_files:
        print("❌ No CSV files found. Please check your file paths.")
        return None, None, None
    
    print(f"\n📁 Processing {len(existing_files)} CSV file(s):")
    for file in existing_files:
        print(f"   ✅ {file}")
    
    try:
        # Process transactions
        all_transactions, remaining_holdings, results = create_enhanced_cost_basis_from_csv(existing_files)
        
        # Display summary
        display_enhanced_summary(all_transactions, remaining_holdings)
        
        print(f"\n🎉 Processing completed successfully!")
        print(f"\nFiles created/updated:")
        print(f"📄 all_transactions.json - Complete transaction history")
        print(f"📄 remaining_holdings.json - Current holdings for CGT calculations")
        print(f"📄 processed_transactions.json - Tracking file for incremental updates")
        print(f"📄 processing_report.txt - Detailed change report")
        
        return all_transactions, remaining_holdings, results
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return None, None, None

if __name__ == "__main__":
    all_transactions, remaining_holdings, results = main()
    
    if all_transactions and remaining_holdings:
        print(f"\n📊 Quick Stats:")
        print(f"Total symbols in transaction history: {len(all_transactions)}")
        print(f"Symbols with current holdings: {len([s for s, h in remaining_holdings.items() if h])}")
        print(f"New transactions processed this run: {results['new_transactions'] if results else 0}")