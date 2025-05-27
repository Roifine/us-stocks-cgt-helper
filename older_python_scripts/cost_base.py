import pandas as pd
from datetime import datetime
import json

def create_cost_basis_dictionary_from_csv(csv_files):
    """
    Create a dictionary of cost basis for each symbol from buy transactions in CSV files.
    
    Args:
        csv_files (list or str): List of CSV file paths, or single CSV file path
    
    Returns:
        dict: Dictionary with symbol as key and list of purchase records as value
    """
    
    # Handle single file input
    if isinstance(csv_files, str):
        csv_files = [csv_files]
    
    print(f"Loading buy transactions from {len(csv_files)} CSV file(s)...")
    
    # Load and combine all CSV files
    all_transactions = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df['Source_File'] = csv_file  # Track source
            all_transactions.append(df)
            print(f"✅ Loaded {len(df)} transactions from {csv_file}")
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
            continue
    
    if not all_transactions:
        print("❌ No CSV files loaded successfully")
        return None
    
    # Combine all transactions
    all_df = pd.concat(all_transactions, ignore_index=True)
    
    # Filter for BUY transactions only
    buys_df = all_df[all_df['Type'] == 'BUY'].copy()
    
    print(f"📊 Total transactions loaded: {len(all_df)}")
    print(f"📈 Buy transactions found: {len(buys_df)}")
    print(f"🏷️  Unique symbols purchased: {len(buys_df['Symbol'].unique())}")
    
    if len(buys_df) == 0:
        print("❌ No buy transactions found")
        return None
    
    # Initialize the cost basis dictionary
    cost_basis_dict = {}
    
    # Process each buy transaction
    for index, row in buys_df.iterrows():
        symbol = row['Symbol']
        quantity = abs(row['Quantity'])  # Ensure positive quantity
        
        # Get price per unit in USD (excluding commission)
        price_per_unit_usd = abs(row['Price (USD)']) if 'Price (USD)' in row else 0
        commission_usd = abs(row['Commission (USD)']) if 'Commission (USD)' in row else 0
        
        # Format date as DD.M.YY (e.g., 25.5.24)
        trade_date = pd.to_datetime(row['Trade Date'])
        formatted_date = trade_date.strftime("%d.%-m.%y")  # Use %-m to remove leading zero from month
        
        # Create the record dictionary
        record = {
            'units': quantity,
            'price': round(price_per_unit_usd, 2),  # Price per unit in USD
            'commission': round(commission_usd, 2),  # Total commission in USD for this transaction
            'date': formatted_date,
            'source_file': row.get('Source_File', 'unknown')  # Track which file this came from
        }
        
        # Add to the cost basis dictionary
        if symbol not in cost_basis_dict:
            cost_basis_dict[symbol] = []
        
        cost_basis_dict[symbol].append(record)
    
    # Sort each symbol's records by date (oldest first)
    for symbol in cost_basis_dict:
        cost_basis_dict[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%y"))
    
    print(f"✅ Created cost basis dictionary for {len(cost_basis_dict)} symbols")
    
    return cost_basis_dict

def create_cost_basis_dictionary(excel_file_path):
    """
    Create a dictionary of cost basis for each symbol from buy transactions in Excel file.
    (Legacy function - kept for backward compatibility)
    
    Args:
        excel_file_path (str): Path to the Excel file with buy transactions
    
    Returns:
        dict: Dictionary with symbol as key and list of purchase records as value
    """
    
    try:
        # Read the Buy_Transactions sheet from the Excel file
        buys_df = pd.read_excel(excel_file_path, sheet_name='Buy_Transactions')
        
        print(f"Loaded {len(buys_df)} buy transactions from Excel")
        
        # Initialize the cost basis dictionary
        cost_basis_dict = {}
        
        # Process each buy transaction
        for index, row in buys_df.iterrows():
            symbol = row['Symbol']
            quantity = abs(row['Quantity'])  # Ensure positive quantity
            
            # Calculate price per unit in USD (excluding commission)
            price_per_unit_usd = abs(row['Price (USD)']) if 'Price (USD)' in row else 0
            commission_usd = abs(row['Commission (USD)']) if 'Commission (USD)' in row else 0
            
            # Format date as DD.M.YY (e.g., 25.5.24)
            trade_date = pd.to_datetime(row['Trade Date'])
            formatted_date = trade_date.strftime("%d.%-m.%y")  # Use %-m to remove leading zero from month
            
            # Create the record dictionary
            record = {
                'units': quantity,
                'price': round(price_per_unit_usd, 2),  # Price per unit in USD
                'commission': round(commission_usd, 2),  # Total commission in USD for this transaction
                'date': formatted_date
            }
            
            # Add to the cost basis dictionary
            if symbol not in cost_basis_dict:
                cost_basis_dict[symbol] = []
            
            cost_basis_dict[symbol].append(record)
        
        # Sort each symbol's records by date (oldest first)
        for symbol in cost_basis_dict:
            cost_basis_dict[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%y"))
        
        return cost_basis_dict
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None

def save_cost_basis_dictionary(cost_basis_dict, output_file_path):
    """
    Save the cost basis dictionary to a JSON file for easy access.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
        output_file_path (str): Path where to save the JSON file
    """
    try:
        with open(output_file_path, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        print(f"Cost basis dictionary saved to: {output_file_path}")
    except Exception as e:
        print(f"Error saving JSON file: {e}")

def display_cost_basis_summary(cost_basis_dict):
    """
    Display a summary of the cost basis dictionary.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
    """
    print("\n" + "="*60)
    print("COST BASIS SUMMARY")
    print("="*60)
    
    for symbol, records in cost_basis_dict.items():
        total_units = sum(record['units'] for record in records)
        total_cost = sum(record['units'] * record['price'] for record in records)
        total_commission = sum(record['commission'] for record in records)
        avg_price = total_cost / total_units if total_units > 0 else 0
        
        print(f"\n{symbol}:")
        print(f"  Total Units: {total_units:,.2f}")
        print(f"  Total Cost: ${total_cost:,.2f} USD (excluding commission)")
        print(f"  Total Commission: ${total_commission:,.2f} USD")
        print(f"  Total Cost (incl. commission): ${total_cost + total_commission:,.2f} USD")
        print(f"  Average Price: ${avg_price:.2f} USD per unit")
        print(f"  Number of Purchases: {len(records)}")
        
        # Show individual purchase records
        print("  Purchase History:")
        for i, record in enumerate(records, 1):
            print(f"    {i}. {record['units']:,.2f} units @ ${record['price']:.2f} USD + ${record['commission']:.2f} commission on {record['date']}")

def main():
    """
    Main function to create and display the cost basis dictionary.
    """
    # File paths - update these to match your actual file locations
    excel_file = "consolidated_transactions_2023-2025_all_years.xlsx"
    json_output_file = "cost_basis_dictionary.json"
    
    print("Creating cost basis dictionary from buy transactions...")
    
    # Create the cost basis dictionary
    cost_basis_dict = create_cost_basis_dictionary(excel_file)
    
    if cost_basis_dict is None:
        print("Failed to create cost basis dictionary. Please check your file path and format.")
        return
    
    # Display summary
    display_cost_basis_summary(cost_basis_dict)
    
    # Save to JSON file
    save_cost_basis_dictionary(cost_basis_dict, json_output_file)
    
    # Example of accessing the dictionary
    print("\n" + "="*60)
    print("EXAMPLE USAGE:")
    print("="*60)
    print("# To access cost basis for a specific symbol:")
    if cost_basis_dict:
        example_symbol = list(cost_basis_dict.keys())[0]
        print(f"cost_basis_dict['{example_symbol}'] = {cost_basis_dict[example_symbol]}")
    
    print("\n# To calculate total cost including commission for a symbol:")
    print("total_cost = sum(record['units'] * record['price'] + record['commission'] for record in cost_basis_dict['AAPL'])")
    
    print("\n# To get the most recent purchase:")
    print("latest_purchase = cost_basis_dict['AAPL'][-1]  # Last item (sorted by date)")
    
    return cost_basis_dict

# Example usage and additional utility functions
def get_fifo_cost_basis(cost_basis_dict, symbol, units_to_sell):
    """
    Calculate cost basis using FIFO (First In, First Out) method.
    
    Args:
        cost_basis_dict (dict): The cost basis dictionary
        symbol (str): Symbol to calculate cost basis for
        units_to_sell (float): Number of units being sold
    
    Returns:
        tuple: (total_cost_basis, remaining_units, detailed_breakdown)
    """
    if symbol not in cost_basis_dict:
        return 0, 0, []
    
    purchases = cost_basis_dict[symbol].copy()  # Don't modify original
    total_cost_basis = 0
    units_remaining = units_to_sell
    breakdown = []
    
    for purchase in purchases:
        if units_remaining <= 0:
            break
            
        units_from_this_purchase = min(units_remaining, purchase['units'])
        cost_from_this_purchase = units_from_this_purchase * purchase['price']
        # Proportional commission based on units used
        commission_from_this_purchase = (units_from_this_purchase / purchase['units']) * purchase['commission']
        
        total_cost_basis += cost_from_this_purchase + commission_from_this_purchase
        units_remaining -= units_from_this_purchase
        
        breakdown.append({
            'date': purchase['date'],
            'units_used': units_from_this_purchase,
            'price': purchase['price'],
            'commission': commission_from_this_purchase,
            'cost': cost_from_this_purchase,
            'total_cost': cost_from_this_purchase + commission_from_this_purchase
        })
    
    return total_cost_basis, units_remaining, breakdown

if __name__ == "__main__":
    import os
    
    # Run the main function directly - no interactive prompts
    cost_dict = main()
    
    # Example of using FIFO calculation
    if cost_dict:
        print("\n" + "="*60)
        print("FIFO COST BASIS EXAMPLE:")
        print("="*60)
        
        example_symbol = list(cost_dict.keys())[0]
        units_to_sell = 50  # Example: selling 50 units
        
        cost_basis, remaining, breakdown = get_fifo_cost_basis(cost_dict, example_symbol, units_to_sell)
        
        print(f"Selling {units_to_sell} units of {example_symbol} using FIFO:")
        print(f"Total cost basis: ${cost_basis:.2f} USD (including proportional commission)")
        if remaining > 0:
            print(f"Warning: Only had {units_to_sell - remaining} units available")
        
        print("\nDetailed breakdown:")
        for item in breakdown:
            print(f"  {item['units_used']:.2f} units @ ${item['price']:.2f} + ${item['commission']:.2f} commission from {item['date']} = ${item['total_cost']:.2f}")
        
        print("\n🎉 Cost basis dictionary created successfully!")
        print("📋 Next steps:")
        print("1. Use 'cost_basis_dictionary_multi_year.json' with your CGT calculator")
        print("2. The dictionary is ready for tax optimization analysis")
    
    else:
        print("\n❌ Failed to create cost basis dictionary")
        print("Please check that 'consolidated_transactions_20232025_all_years.xlsx' exists")

# Additional utility functions for advanced usage
def merge_cost_basis_dictionaries(dict1, dict2):
    """
    Merge two cost basis dictionaries.
    
    Args:
        dict1, dict2 (dict): Cost basis dictionaries to merge
    
    Returns:
        dict: Merged dictionary
    """
    merged = dict1.copy()
    
    for symbol, records in dict2.items():
        if symbol in merged:
            merged[symbol].extend(records)
            # Re-sort by date
            merged[symbol].sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%y"))
        else:
            merged[symbol] = records
    
    return merged

def filter_cost_basis_by_date(cost_basis_dict, start_date=None, end_date=None):
    """
    Filter cost basis dictionary by date range.
    
    Args:
        cost_basis_dict (dict): Original cost basis dictionary
        start_date (str): Start date in DD.M.YY format (optional)
        end_date (str): End date in DD.M.YY format (optional)
    
    Returns:
        dict: Filtered dictionary
    """
    filtered_dict = {}
    
    for symbol, records in cost_basis_dict.items():
        filtered_records = []
        
        for record in records:
            record_date = datetime.strptime(record['date'], "%d.%m.%y")
            
            include = True
            if start_date:
                start_dt = datetime.strptime(start_date, "%d.%m.%y")
                if record_date < start_dt:
                    include = False
            
            if end_date:
                end_dt = datetime.strptime(end_date, "%d.%m.%y")
                if record_date > end_dt:
                    include = False
            
            if include:
                filtered_records.append(record)
        
        if filtered_records:
            filtered_dict[symbol] = filtered_records
    
    return filtered_dict