#!/usr/bin/env python3
"""
Australian CGT Calculator - Streamlit Web App with AUD Conversion

Upload Interactive Brokers HTML statements and get ATO-compliant Australian CGT calculations
with automatic USD to AUD conversion using RBA exchange rates.
"""

import streamlit as st

# Page configuration MUST be first
st.set_page_config(
    page_title="Australian CGT Calculator (AUD Enhanced)",
    page_icon="🇦🇺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Now import everything else
import pandas as pd
import tempfile
import os
import json
from datetime import datetime
import traceback

# Import your existing scripts
try:
    from complete_unified_with_aud import (
        parse_html_file_with_hybrid_filtering,
        apply_hybrid_fifo_processing_with_aud,
        RBAAUDConverter,
        robust_date_parser,
        format_date_for_output
    )
    from cgt_calculator_australia_aud import (
        calculate_australian_cgt_aud,
        save_cgt_excel_aud,
        load_cost_basis_json_aud,
        load_sales_csv
    )
    SCRIPTS_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    SCRIPTS_AVAILABLE = False
    IMPORT_ERROR = e

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'cgt_results' not in st.session_state:
    st.session_state.cgt_results = None
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None
if 'filename' not in st.session_state:
    st.session_state.filename = None

def validate_uploaded_files(html_files, csv_files):
    """Validate uploaded HTML and CSV files."""
    total_files = len(html_files or []) + len(csv_files or [])
    
    if total_files == 0:
        return False, "Please upload at least one HTML or CSV file"
    
    if total_files > 10:
        return False, "Maximum 10 files allowed (HTML + CSV combined)"
    
    # Validate HTML files
    if html_files:
        for file in html_files:
            if file.size > 20 * 1024 * 1024:  # 20MB limit
                return False, f"File {file.name} is too large (max 20MB)"
            
            if not file.name.lower().endswith(('.html', '.htm')):
                return False, f"File {file.name} is not an HTML file"
    
    # Validate CSV files
    if csv_files:
        for file in csv_files:
            if file.size > 10 * 1024 * 1024:  # 10MB limit for CSV
                return False, f"File {file.name} is too large (max 10MB)"
            
            if not file.name.lower().endswith('.csv'):
                return False, f"File {file.name} is not a CSV file"
    
    return True, "Files validated successfully"

def process_csv_files(csv_files, temp_dir, cutoff_date):
    """Process CSV files and convert to standardized format."""
    if not csv_files:
        return []
    
    all_csv_data = []
    
    for i, uploaded_file in enumerate(csv_files):
        st.text(f"Processing CSV: {uploaded_file.name}...")
        
        try:
            # Save uploaded file temporarily
            temp_csv_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_csv_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            # Read CSV file
            df = pd.read_csv(temp_csv_path)
            
            st.text(f"   📊 Found {len(df)} rows with columns: {list(df.columns)}")
            
            # Try to detect the CSV format and standardize it
            standardized_df = standardize_csv_format(df, uploaded_file.name, cutoff_date)
            
            if standardized_df is not None and len(standardized_df) > 0:
                all_csv_data.append(standardized_df)
                st.success(f"✅ {uploaded_file.name}: {len(standardized_df)} transactions processed")
            else:
                st.warning(f"⚠️ {uploaded_file.name}: No valid transactions found or unsupported format")
                
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
            continue
    
    return all_csv_data

def standardize_csv_format(df, filename, cutoff_date):
    """Convert various CSV formats to standardized format."""
    try:
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # Remove any completely empty rows
        df = df.dropna(how='all')
        
        st.text(f"   🔍 Detecting format for {filename}...")
        
        # Case 1: Interactive Brokers format (Symbol, Trade Date, Type, Quantity, Price (USD), etc.)
        if 'Symbol' in df.columns and 'Trade Date' in df.columns and 'Type' in df.columns:
            st.text("   📋 Detected: Interactive Brokers CSV format")
            return standardize_ib_format(df, cutoff_date)
        
        # Case 2: Manual transactions format (Date, Activity_Type, Symbol, Quantity, Price_USD, etc.)
        elif 'Activity_Type' in df.columns and 'Symbol' in df.columns and 'Date' in df.columns:
            st.text("   📋 Detected: Manual transactions format")
            return standardize_manual_format(df, cutoff_date)
        
        # Case 3: Generic trading format (try to detect common patterns)
        elif any(col.lower() in ['symbol', 'ticker'] for col in df.columns):
            st.text("   📋 Detected: Generic trading format (attempting auto-detection)")
            return standardize_generic_format(df, cutoff_date)
        
        else:
            st.warning(f"   ❌ Unsupported CSV format in {filename}")
            st.text(f"   📋 Available columns: {list(df.columns)}")
            st.text("   💡 Supported formats:")
            st.text("      • Interactive Brokers CSV exports")
            st.text("      • Manual transaction CSVs (Date, Activity_Type, Symbol, Quantity, Price_USD)")
            st.text("      • Generic trading CSVs with Symbol/Ticker column")
            return None
            
    except Exception as e:
        st.error(f"❌ Error standardizing {filename}: {e}")
        return None

def standardize_ib_format(df, cutoff_date):
    """Standardize Interactive Brokers CSV format."""
    try:
        # Convert Trade Date to datetime
        df['Trade Date'] = pd.to_datetime(df['Trade Date'])
        
        # Apply cutoff date filtering (only for SELL transactions)
        if cutoff_date:
            sell_mask = df['Type'] == 'SELL'
            future_sells = sell_mask & (df['Trade Date'] > cutoff_date)
            df = df[~future_sells]  # Remove future sells
        
        # Create standardized format
        standardized = pd.DataFrame()
        standardized['Symbol'] = df['Symbol']
        standardized['Date'] = df['Trade Date'].dt.strftime('%Y-%m-%d')
        standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
        standardized['Quantity'] = df['Quantity'].abs()
        
        # Handle different price column names
        if 'Price (USD)' in df.columns:
            standardized['Price'] = df['Price (USD)'].abs()
        elif 'Price' in df.columns:
            standardized['Price'] = df['Price'].abs()
        else:
            st.warning("⚠️ No price column found, using 0")
            standardized['Price'] = 0
        
        # Handle commission
        if 'Commission (USD)' in df.columns:
            standardized['Commission'] = df['Commission (USD)'].abs()
        elif 'Commission' in df.columns:
            standardized['Commission'] = df['Commission'].abs()
        else:
            standardized['Commission'] = 0  # Default commission
        
        standardized['Source'] = f'CSV_IB'
        
        # Remove invalid entries
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity'])
        standardized = standardized[standardized['Quantity'] > 0]
        
        return standardized
        
    except Exception as e:
        st.error(f"❌ Error processing IB format: {e}")
        return None

def standardize_manual_format(df, cutoff_date):
    """Standardize manual transaction CSV format."""
    try:
        # Convert Date to datetime (handle DD.M.YY format)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Apply cutoff date filtering (only for SELL transactions)
        if cutoff_date:
            sell_mask = df['Activity_Type'] == 'SOLD'
            future_sells = sell_mask & (df['Date'] > cutoff_date)
            df = df[~future_sells]  # Remove future sells
        
        # Create standardized format
        standardized = pd.DataFrame()
        standardized['Symbol'] = df['Symbol']
        standardized['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        standardized['Activity'] = df['Activity_Type'].map({'PURCHASED': 'PURCHASED', 'SOLD': 'SOLD'})
        standardized['Quantity'] = df['Quantity'].abs()
        standardized['Price'] = df['Price_USD'].abs()
        standardized['Commission'] = 30.0  # Default commission for manual entries
        standardized['Source'] = f'CSV_Manual'
        
        # Remove invalid entries
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity'])
        standardized = standardized[standardized['Quantity'] > 0]
        
        return standardized
        
    except Exception as e:
        st.error(f"❌ Error processing manual format: {e}")
        return None

def standardize_generic_format(df, cutoff_date):
    """Attempt to standardize generic CSV format by detecting common patterns."""
    try:
        st.text("   🔍 Attempting generic format detection...")
        
        # Find symbol column
        symbol_col = None
        for col in df.columns:
            if col.lower() in ['symbol', 'ticker', 'stock']:
                symbol_col = col
                break
        
        if not symbol_col:
            st.error("❌ No symbol/ticker column found")
            return None
        
        # Find date column
        date_col = None
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                date_col = col
                break
        
        if not date_col:
            st.error("❌ No date column found")
            return None
        
        # Find transaction type column
        type_col = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['type', 'action', 'side', 'activity']):
                type_col = col
                break
        
        if not type_col:
            st.error("❌ No transaction type column found")
            return None
        
        # Find quantity column
        qty_col = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['quantity', 'qty', 'shares', 'units']):
                qty_col = col
                break
        
        if not qty_col:
            st.error("❌ No quantity column found")
            return None
        
        # Find price column
        price_col = None
        for col in df.columns:
            if 'price' in col.lower() and 'usd' in col.lower():
                price_col = col
                break
        
        if not price_col:
            # Try just 'price'
            for col in df.columns:
                if col.lower() == 'price':
                    price_col = col
                    break
        
        if not price_col:
            st.error("❌ No price column found")
            return None
        
        st.text(f"   ✅ Detected columns: {symbol_col}, {date_col}, {type_col}, {qty_col}, {price_col}")
        
        # Convert and standardize
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Apply cutoff date filtering
        if cutoff_date:
            # Try to detect sell transactions
            sell_keywords = ['sell', 'sold', 'sale', 'short']
            sell_mask = df[type_col].astype(str).str.lower().str.contains('|'.join(sell_keywords), na=False)
            future_sells = sell_mask & (df[date_col] > cutoff_date)
            df = df[~future_sells]
        
        # Create standardized format
        standardized = pd.DataFrame()
        standardized['Symbol'] = df[symbol_col]
        standardized['Date'] = df[date_col].dt.strftime('%Y-%m-%d')
        
        # Map transaction types
        def map_activity(activity_str):
            if pd.isna(activity_str):
                return None
            activity_lower = str(activity_str).lower()
            if any(keyword in activity_lower for keyword in ['buy', 'purchase', 'long']):
                return 'PURCHASED'
            elif any(keyword in activity_lower for keyword in ['sell', 'sold', 'sale', 'short']):
                return 'SOLD'
            else:
                return None
        
        standardized['Activity'] = df[type_col].apply(map_activity)
        standardized['Quantity'] = pd.to_numeric(df[qty_col], errors='coerce').abs()
        standardized['Price'] = pd.to_numeric(df[price_col], errors='coerce').abs()
        
        # Try to find commission column
        commission_col = None
        for col in df.columns:
            if 'commission' in col.lower() or 'fee' in col.lower():
                commission_col = col
                break
        
        if commission_col:
            standardized['Commission'] = pd.to_numeric(df[commission_col], errors='coerce').abs()
        else:
            standardized['Commission'] = 10.0  # Default commission
        
        standardized['Source'] = f'CSV_Generic'
        
        # Remove invalid entries
        standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity'])
        standardized = standardized[standardized['Quantity'] > 0]
        
        return standardized
        
    except Exception as e:
        st.error(f"❌ Error processing generic format: {e}")
        return None
    """Initialize the RBA AUD converter with your rates directory."""
    try:
        st.text("🔍 Looking for RBA exchange rate files...")
        
        # Try different possible locations for rates directory
        possible_directories = [
            "./rates",
            "../rates", 
            "/Users/roifine/My python projects/Ozi_Tax_Agent/rates",
            os.path.join(os.getcwd(), "rates")
        ]
        
        rates_directory = None
        for directory in possible_directories:
            if os.path.exists(directory):
                rates_directory = directory
                st.text(f"✅ Found rates directory: {directory}")
                break
        
        if not rates_directory:
            st.error(f"❌ Rates directory not found. Checked: {possible_directories}")
            return None
        
        # Find RBA CSV files
        st.text(f"🔍 Looking for FX CSV files in {rates_directory}...")
        all_files = os.listdir(rates_directory)
        st.text(f"📁 Files in rates directory: {all_files}")
        
        rba_files = []
        for file in all_files:
            if file.endswith('.csv') and ('FX_' in file or 'fx_' in file.lower()):
                full_path = os.path.join(rates_directory, file)
                rba_files.append(full_path)
                st.text(f"✅ Found RBA file: {file}")
        
        if not rba_files:
            st.error(f"❌ No RBA CSV files found in {rates_directory}")
            return None
        
        st.text(f"📊 Initializing RBA converter with {len(rba_files)} files...")
        
        # Initialize converter
        aud_converter = RBAAUDConverter()
        
        # FIXED: Parse the RBA F11.1 format manually since the built-in parser expects different format
        st.text("🔧 Using custom RBA F11.1 format parser...")
        
        total_rates_loaded = 0
        
        for rba_file in rba_files:
            try:
                st.text(f"📄 Parsing {os.path.basename(rba_file)}...")
                
                with open(rba_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse using regex (we know this works from the test)
                import re
                from datetime import datetime
                
                pattern = r'(\d{2}-[A-Za-z]{3}-\d{4})\s*[,\t]\s*([0-9.]+)'
                matches = re.findall(pattern, content)
                
                rates_added = 0
                for date_str, rate_str in matches:
                    try:
                        # Parse date from DD-MMM-YYYY format  
                        date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                        rate = float(rate_str)
                        
                        # Store as YYYY-MM-DD string for easy lookup
                        date_key = date_obj.strftime('%Y-%m-%d')
                        aud_converter.exchange_rates[date_key] = rate
                        rates_added += 1
                        
                    except ValueError as e:
                        continue  # Skip invalid dates/rates
                
                st.text(f"   ✅ Added {rates_added} rates from {os.path.basename(rba_file)}")
                total_rates_loaded += rates_added
                
            except Exception as e:
                st.error(f"❌ Error parsing {rba_file}: {e}")
                continue
        
        # Check if rates were loaded
        if total_rates_loaded > 0:
            st.text(f"✅ Successfully loaded {total_rates_loaded} exchange rates")
            
            # Show date range
            if aud_converter.exchange_rates:
                dates = list(aud_converter.exchange_rates.keys())
                min_date = min(dates)
                max_date = max(dates)
                st.text(f"📅 Date range: {min_date} to {max_date}")
                
                # Show sample rates
                st.text("📋 Sample rates loaded:")
                for i, (date, rate) in enumerate(list(aud_converter.exchange_rates.items())[:3]):
                    st.text(f"   {date}: {rate:.4f}")
            
            return aud_converter
        else:
            st.error("❌ No exchange rates were successfully parsed")
            return None
        
    except Exception as e:
        st.error(f"❌ Error initializing AUD converter: {e}")
        st.code(traceback.format_exc())
        return None

def initialize_aud_converter():
    """Initialize the RBA AUD converter with your rates directory."""
    try:
        st.text("🔍 Looking for RBA exchange rate files...")
        
        # Try different possible locations for rates directory
        possible_directories = [
            "./rates",
            "../rates", 
            "/Users/roifine/My python projects/Ozi_Tax_Agent/rates",
            os.path.join(os.getcwd(), "rates")
        ]
        
        rates_directory = None
        for directory in possible_directories:
            if os.path.exists(directory):
                rates_directory = directory
                st.text(f"✅ Found rates directory: {directory}")
                break
        
        if not rates_directory:
            st.error(f"❌ Rates directory not found. Checked: {possible_directories}")
            return None
        
        # Find RBA CSV files
        st.text(f"🔍 Looking for FX CSV files in {rates_directory}...")
        all_files = os.listdir(rates_directory)
        st.text(f"📁 Files in rates directory: {all_files}")
        
        rba_files = []
        for file in all_files:
            if file.endswith('.csv') and ('FX_' in file or 'fx_' in file.lower()):
                full_path = os.path.join(rates_directory, file)
                rba_files.append(full_path)
                st.text(f"✅ Found RBA file: {file}")
        
        if not rba_files:
            st.error(f"❌ No RBA CSV files found in {rates_directory}")
            return None
        
        st.text(f"📊 Initializing RBA converter with {len(rba_files)} files...")
        
        # Initialize converter
        aud_converter = RBAAUDConverter()
        
        # FIXED: Parse the RBA F11.1 format manually since the built-in parser expects different format
        st.text("🔧 Using custom RBA F11.1 format parser...")
        
        total_rates_loaded = 0
        
        for rba_file in rba_files:
            try:
                st.text(f"📄 Parsing {os.path.basename(rba_file)}...")
                
                with open(rba_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse using regex (we know this works from the test)
                import re
                from datetime import datetime
                
                pattern = r'(\d{2}-[A-Za-z]{3}-\d{4})\s*[,\t]\s*([0-9.]+)'
                matches = re.findall(pattern, content)
                
                rates_added = 0
                for date_str, rate_str in matches:
                    try:
                        # Parse date from DD-MMM-YYYY format  
                        date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                        rate = float(rate_str)
                        
                        # Store as YYYY-MM-DD string for easy lookup
                        date_key = date_obj.strftime('%Y-%m-%d')
                        aud_converter.exchange_rates[date_key] = rate
                        rates_added += 1
                        
                    except ValueError as e:
                        continue  # Skip invalid dates/rates
                
                st.text(f"   ✅ Added {rates_added} rates from {os.path.basename(rba_file)}")
                total_rates_loaded += rates_added
                
            except Exception as e:
                st.error(f"❌ Error parsing {rba_file}: {e}")
                continue
        
        # Check if rates were loaded
        if total_rates_loaded > 0:
            st.text(f"✅ Successfully loaded {total_rates_loaded} exchange rates")
            
            # Show date range
            if aud_converter.exchange_rates:
                dates = list(aud_converter.exchange_rates.keys())
                min_date = min(dates)
                max_date = max(dates)
                st.text(f"📅 Date range: {min_date} to {max_date}")
                
                # Show sample rates
                st.text("📋 Sample rates loaded:")
                for i, (date, rate) in enumerate(list(aud_converter.exchange_rates.items())[:3]):
                    st.text(f"   {date}: {rate:.4f}")
            
            return aud_converter
        else:
            st.error("❌ No exchange rates were successfully parsed")
            return None
        
    except Exception as e:
        st.error(f"❌ Error initializing AUD converter: {e}")
        st.code(traceback.format_exc())
        return None

def check_exchange_rates(aud_converter):
    """Check if exchange rates are available and show status."""
    try:
        st.text("🔍 Checking exchange rate status...")
        
        if not aud_converter:
            st.warning("⚠️ No AUD converter available - will use default rates")
            return False
        
        st.text(f"📊 Converter type: {type(aud_converter)}")
        st.text(f"📊 Converter attributes: {[attr for attr in dir(aud_converter) if not attr.startswith('_')]}")
        
        if hasattr(aud_converter, 'exchange_rates'):
            rates_dict = aud_converter.exchange_rates
            st.text(f"📊 Exchange rates dict type: {type(rates_dict)}")
            st.text(f"📊 Exchange rates dict size: {len(rates_dict) if rates_dict else 0}")
            
            if rates_dict and len(rates_dict) > 0:
                dates = list(rates_dict.keys())
                min_date = min(dates)
                max_date = max(dates)
                st.success(f"✅ Exchange rates loaded: {len(rates_dict):,} rates from {min_date} to {max_date}")
                
                # Show a few sample rates
                st.text("📋 Sample rates:")
                for i, (date, rate) in enumerate(list(rates_dict.items())[:3]):
                    st.text(f"   {date}: {rate}")
                
                return True
            else:
                st.error("❌ Exchange rates dictionary is empty")
                return False
        else:
            st.error("❌ AUD converter missing 'exchange_rates' attribute")
            return False
            
    except Exception as e:
        st.error(f"❌ Error checking exchange rates: {e}")
        st.code(traceback.format_exc())
        return False

def process_files_enhanced(html_files, csv_files, temp_dir, financial_year, aud_converter):
    """Process both HTML and CSV files using your enhanced AUD system."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Determine cutoff date for hybrid processing
    fy_year = int(financial_year.split('-')[0])
    cutoff_date = datetime(fy_year, 6, 30)  # End of financial year
    
    all_data = []
    total_files = len(html_files or []) + len(csv_files or [])
    current_file = 0
    
    # Process HTML files first
    if html_files:
        status_text.text("Processing HTML files...")
        
        for uploaded_file in html_files:
            status_text.text(f"Processing HTML: {uploaded_file.name}...")
            
            # Save uploaded file temporarily
            temp_html_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_html_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Parse HTML with hybrid filtering using your existing function
                df = parse_html_file_with_hybrid_filtering(temp_html_path, cutoff_date)
                
                if df is not None and len(df) > 0:
                    # Convert to standardized format
                    standardized = pd.DataFrame()
                    standardized['Symbol'] = df['Symbol']
                    standardized['Date'] = df['Trade Date'].astype(str)
                    standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
                    standardized['Quantity'] = df['Quantity'].abs()
                    standardized['Price'] = df['Price (USD)'].abs()
                    standardized['Commission'] = df['Commission (USD)'].abs()
                    standardized['Source'] = f'HTML_{uploaded_file.name}'
                    
                    all_data.append(standardized)
                    st.success(f"✅ {uploaded_file.name}: {len(df)} transactions found")
                else:
                    st.warning(f"⚠️ {uploaded_file.name}: No valid transactions found")
                    
            except Exception as e:
                st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
            
            current_file += 1
            progress_bar.progress(current_file / total_files)
    
    # Process CSV files
    if csv_files:
        status_text.text("Processing CSV files...")
        csv_data = process_csv_files(csv_files, temp_dir, cutoff_date)
        all_data.extend(csv_data)
        
        current_file += len(csv_files)
        progress_bar.progress(current_file / total_files)
    
    if not all_data:
        return None, None
    
    # Combine all transactions
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates
    before_count = len(combined_df)
    combined_df = combined_df.drop_duplicates(
        subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], 
        keep='first'
    )
    after_count = len(combined_df)
    
    if before_count != after_count:
        st.info(f"✂️ Removed {before_count - after_count} duplicate transactions")
    
    status_text.text("Creating cost basis with AUD conversion...")
    
    # Apply FIFO processing with AUD conversion using your existing function
    cost_basis_dict, fifo_log, conversion_errors = apply_hybrid_fifo_processing_with_aud(
        combined_df, aud_converter, cutoff_date
    )
    
    if not cost_basis_dict:
        st.error("❌ Failed to create cost basis dictionary")
        return None, None
    
    # Save cost basis to temp file
    cost_basis_path = os.path.join(temp_dir, f"cost_basis_aud_FY{financial_year}.json")
    with open(cost_basis_path, 'w') as f:
        json.dump(cost_basis_dict, f, indent=2)
    
    # Extract sales for the financial year
    status_text.text("Extracting sales transactions...")
    
    next_fy_year = fy_year + 1
    fy_start = datetime(fy_year, 7, 1)
    fy_end = datetime(next_fy_year, 6, 30)
    
    # Extract sales transactions for the target financial year
    sell_transactions = combined_df[combined_df['Activity'] == 'SOLD'].copy()
    
    if len(sell_transactions) > 0:
        sell_transactions['date_obj'] = sell_transactions['Date'].apply(robust_date_parser)
        
        fy_sales = sell_transactions[
            (sell_transactions['date_obj'] >= fy_start) & 
            (sell_transactions['date_obj'] <= fy_end)
        ].copy()
        
        if len(fy_sales) > 0:
            # Create sales DataFrame compatible with your CGT calculator
            sales_data = []
            
            for _, sale in fy_sales.iterrows():
                quantity = abs(float(sale['Quantity']))
                price_usd = abs(float(sale['Price']))
                commission_usd = abs(float(sale['Commission']))
                trade_date = robust_date_parser(sale['Date'])
                
                sales_data.append({
                    'Symbol': sale['Symbol'],
                    'Trade Date': pd.to_datetime(sale['Date']),
                    'Units_Sold': quantity,
                    'Sale_Price_Per_Unit': price_usd,
                    'Total_Proceeds': quantity * price_usd,
                    'Commission_Paid': commission_usd,
                    'Net_Proceeds': (quantity * price_usd) - commission_usd,
                    'Financial_Year': financial_year,
                    'Source': sale['Source']
                })
            
            sales_df = pd.DataFrame(sales_data)
            sales_path = os.path.join(temp_dir, f"sales_FY{financial_year}.csv")
            sales_df.to_csv(sales_path, index=False)
            
            status_text.text("Processing complete!")
            
            # Show summary
            st.info(f"📊 Combined data summary:")
            st.info(f"   • Total transactions: {len(combined_df)}")
            st.info(f"   • Sales in FY {financial_year}: {len(fy_sales)}")
            st.info(f"   • Data sources: {dict(combined_df['Source'].value_counts())}")
            
            return cost_basis_path, sales_path
        else:
            st.warning("⚠️ No sales found in the selected financial year")
            return cost_basis_path, None
    else:
        st.warning("⚠️ No sales transactions found")
        return cost_basis_path, None

def calculate_cgt_enhanced(sales_path, cost_basis_path, financial_year, temp_dir):
    """Calculate CGT using your enhanced AUD system."""
    try:
        st.text("Loading sales and cost basis data...")
        
        # Load data using your enhanced functions
        sales_df = load_sales_csv(sales_path)
        cost_basis_dict = load_cost_basis_json_aud(cost_basis_path)
        
        if sales_df is None or cost_basis_dict is None:
            st.error("❌ Failed to load input data")
            return None, None, None
        
        st.text("Calculating Australian CGT with AUD conversion...")
        
        # Calculate CGT using your enhanced function
        cgt_df, remaining_cost_basis, warnings_list = calculate_australian_cgt_aud(
            sales_df, cost_basis_dict
        )
        
        if cgt_df is None or len(cgt_df) == 0:
            st.error("❌ No CGT calculations generated")
            return None, None, None
        
        st.success(f"✅ CGT calculations complete: {len(cgt_df)} transactions processed")
        
        return cgt_df, remaining_cost_basis, warnings_list
        
    except Exception as e:
        st.error(f"❌ Error calculating CGT: {str(e)}")
        if st.checkbox("Show debug information"):
            st.code(traceback.format_exc())
        return None, None, None

def create_excel_download_enhanced(cgt_df, financial_year, temp_dir):
    """Create enhanced Excel file with AUD amounts for download."""
    try:
        # Create Excel file in temp directory using your function
        excel_path = os.path.join(temp_dir, f"Australian_CGT_Report_AUD_FY{financial_year}.xlsx")
        
        excel_file = save_cgt_excel_aud(cgt_df, financial_year, excel_path)
        
        if not excel_file or not os.path.exists(excel_path):
            st.error("❌ Failed to create Excel file")
            return None, None
        
        # Read file for download
        with open(excel_path, 'rb') as f:
            excel_data = f.read()
        
        return excel_data, f"Australian_CGT_Report_AUD_FY{financial_year}.xlsx"
        
    except Exception as e:
        st.error(f"❌ Error creating Excel file: {str(e)}")
        return None, None

def display_exchange_rate_info(aud_converter):
    """Display exchange rate information in sidebar."""
    with st.sidebar:
        st.header("💱 Exchange Rate Info")
        
        if aud_converter and hasattr(aud_converter, 'exchange_rates') and aud_converter.exchange_rates:
            num_rates = len(aud_converter.exchange_rates)
            dates = list(aud_converter.exchange_rates.keys())
            min_date = min(dates)
            max_date = max(dates)
            
            st.metric("Exchange Rates Loaded", f"{num_rates:,}")
            st.text(f"Date Range:\n{min_date} to {max_date}")
            
            # Show recent rates
            st.subheader("Recent Rates (AUD/USD)")
            recent_dates = sorted(dates)[-5:]
            for date in recent_dates:
                rate = aud_converter.exchange_rates[date]
                st.text(f"{date}: {rate:.4f}")
            
            st.info("💡 Rates from RBA historical data")
        else:
            st.warning("⚠️ No exchange rates loaded")
            st.info("Using default rates (0.67)")
            st.info("💡 Check rates directory for RBA CSV files")

def main():
    """Main Streamlit app with your enhanced AUD functionality."""
    
    # Header
    st.title("🇦🇺 Australian CGT Calculator (AUD Enhanced)")
    st.markdown("Upload your Interactive Brokers HTML statements to calculate **ATO-compliant** Australian Capital Gains Tax with **RBA AUD conversion**")
    
    # Check if scripts are available
    if not SCRIPTS_AVAILABLE:
        st.error(f"❌ Could not import required scripts: {IMPORT_ERROR}")
        st.error("Please ensure complete_unified_with_aud.py and cgt_calculator_australia_aud.py are in the same directory")
        st.info("💡 Make sure all Python files are in the same folder as app.py")
        st.stop()
    
    # Initialize AUD converter
    with st.spinner("💱 Loading exchange rates..."):
        aud_converter = initialize_aud_converter()
    
    # Check exchange rates status
    st.header("💱 Exchange Rate Status")
    rates_available = check_exchange_rates(aud_converter)
    
    # Display exchange rate info in sidebar
    display_exchange_rate_info(aud_converter)
    
    # File upload section
    st.header("📁 Upload Trading Data")
    
    # Create two columns for different file types
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 HTML Statements")
        html_files = st.file_uploader(
            "Interactive Brokers HTML statements",
            type=['html', 'htm'],
            accept_multiple_files=True,
            help="Upload your Interactive Brokers HTML trading statements",
            key="html_uploader"
        )
        
        if html_files:
            st.success(f"✅ {len(html_files)} HTML file(s) uploaded")
            with st.expander("📋 HTML File Details"):
                for file in html_files:
                    st.text(f"• {file.name} ({file.size:,} bytes)")
    
    with col2:
        st.subheader("📊 CSV Data Files")
        csv_files = st.file_uploader(
            "Trading CSV files",
            type=['csv'],
            accept_multiple_files=True,
            help="Upload CSV files with trading data (Interactive Brokers exports, manual transaction lists, etc.)",
            key="csv_uploader"
        )
        
        if csv_files:
            st.success(f"✅ {len(csv_files)} CSV file(s) uploaded")
            with st.expander("📋 CSV File Details"):
                for file in csv_files:
                    st.text(f"• {file.name} ({file.size:,} bytes)")
    
    # Show supported CSV formats
    if csv_files or st.checkbox("ℹ️ Show supported CSV formats"):
        with st.expander("📋 Supported CSV Formats", expanded=bool(csv_files)):
            st.markdown("""
            **Supported CSV formats:**
            
            1. **Interactive Brokers CSV exports**
               - Columns: Symbol, Trade Date, Type, Quantity, Price (USD), Commission (USD)
            
            2. **Manual transaction files**
               - Columns: Date, Activity_Type, Symbol, Quantity, Price_USD, USD_Amount, AUD_Amount
            
            3. **Generic trading CSVs**
               - Must include: Symbol/Ticker, Date, Type/Action, Quantity, Price
               - Auto-detects common column patterns
            
            **Tips:**
            - Upload multiple files of different formats - they'll be combined automatically
            - HTML files are typically more accurate than CSV exports
            - Manual CSV files are useful for older transactions or other brokers
            """)
    
    # Validate files
    if html_files or csv_files:
        is_valid, message = validate_uploaded_files(html_files, csv_files)
        if not is_valid:
            st.error(f"❌ {message}")
            st.stop()
        else:
            total_files = len(html_files or []) + len(csv_files or [])
            st.success(f"✅ {total_files} file(s) ready for processing")
    else:
        st.info("👆 Please upload HTML statements and/or CSV files to continue")
    
    # Configuration section
    st.header("⚙️ Configuration")
    col1, col2 = st.columns(2)
    
    with col1:
        financial_year = st.selectbox(
            "Financial Year",
            ["2024-25", "2023-24", "2025-26", "2022-23"],
            index=0,
            help="Australian financial year (July 1 - June 30)"
        )
    
    with col2:
        st.info(f"🇦🇺 Processing for FY {financial_year} with RBA AUD conversion")
    
    # Processing section
    if (html_files or csv_files) and st.button("🔄 Process Files (Enhanced AUD)", type="primary", use_container_width=True):
        
        # Reset session state
        st.session_state.processing_complete = False
        st.session_state.cgt_results = None
        st.session_state.excel_data = None
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Step 1: Process HTML and CSV files with enhanced AUD system
                with st.spinner("Step 1/3: Processing files with AUD conversion..."):
                    cost_basis_path, sales_path = process_files_enhanced(
                        html_files, csv_files, temp_dir, financial_year, aud_converter
                    )
                
                if not cost_basis_path:
                    st.error("❌ Failed to create cost basis with AUD conversion")
                    st.stop()
                
                if not sales_path:
                    st.warning("⚠️ No sales found for the selected financial year")
                    st.info("This might mean no sales occurred in the selected financial year")
                    st.stop()
                
                # Step 2: Calculate CGT with AUD
                with st.spinner("Step 2/3: Calculating ATO-compliant CGT..."):
                    cgt_df, remaining_cost_basis, warnings_list = calculate_cgt_enhanced(
                        sales_path, cost_basis_path, financial_year, temp_dir
                    )
                
                if cgt_df is None:
                    st.error("❌ CGT calculation failed")
                    st.stop()
                
                # Step 3: Create enhanced Excel file
                with st.spinner("Step 3/3: Creating ATO-compliant Excel report..."):
                    excel_data, filename = create_excel_download_enhanced(
                        cgt_df, financial_year, temp_dir
                    )
                
                if excel_data is None:
                    st.error("❌ Excel file creation failed")
                    st.stop()
                
                # Store results in session state
                st.session_state.processing_complete = True
                st.session_state.cgt_results = {
                    'cgt_df': cgt_df,
                    'warnings': warnings_list,
                    'remaining_cost_basis': remaining_cost_basis
                }
                st.session_state.excel_data = excel_data
                st.session_state.filename = filename
                
                st.success("✅ Enhanced AUD processing complete!")
                
            except Exception as e:
                st.error(f"❌ Processing failed: {str(e)}")
                if st.checkbox("Show debug information"):
                    st.code(traceback.format_exc())
    
    # Results section
    if st.session_state.processing_complete and st.session_state.cgt_results:
        st.header("📊 ATO-Compliant Results")
        
        cgt_df = st.session_state.cgt_results['cgt_df']
        warnings = st.session_state.cgt_results['warnings']
        
        # Enhanced AUD metrics
        total_gain_aud = cgt_df['Capital_Gain_Loss_AUD'].sum()
        taxable_gain_aud = cgt_df['Taxable_Gain_AUD'].sum()
        long_term_count = len(cgt_df[cgt_df['Long_Term_Eligible'] == True])
        short_term_count = len(cgt_df) - long_term_count
        
        # Display enhanced metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Capital Gains (AUD)",
                f"${total_gain_aud:,.2f}",
                help="Total capital gains/losses in AUD using RBA rates"
            )
        
        with col2:
            st.metric(
                "Taxable Amount (AUD)",
                f"${taxable_gain_aud:,.2f}",
                help="Report this amount to the ATO (after 50% CGT discount)"
            )
        
        with col3:
            st.metric(
                "Long-term Sales",
                f"{long_term_count}",
                help="Sales eligible for 50% CGT discount (held >12 months)"
            )
        
        with col4:
            st.metric(
                "Short-term Sales", 
                f"{short_term_count}",
                help="Sales not eligible for CGT discount (held <12 months)"
            )
        
        # Enhanced download section
        st.header("⬇️ Download ATO-Compliant Report")
        
        if st.session_state.excel_data and st.session_state.filename:
            st.download_button(
                label="📊 Download ATO-Compliant CGT Report (Excel)",
                data=st.session_state.excel_data,
                file_name=st.session_state.filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.success("✅ Your ATO-compliant CGT report is ready for download!")
            st.info("💡 This Excel file contains AUD amounts using RBA exchange rates - perfect for Australian tax lodgment")
        
        # Warnings section
        if warnings:
            with st.expander(f"⚠️ Warnings ({len(warnings)})", expanded=True):
                for warning in warnings:
                    st.warning(warning)
        
        # Optional: Show detailed data
        if st.checkbox("Show detailed AUD CGT calculations"):
            st.subheader("Detailed AUD CGT Calculations")
            display_columns = [
                'Symbol', 'Sale_Date', 'Units_Sold', 'Sale_Price_Per_Unit_AUD',
                'Buy_Date', 'Days_Held', 'Capital_Gain_Loss_AUD', 'Taxable_Gain_AUD',
                'Long_Term_Eligible', 'CGT_Discount_Applied', 'Purchase_Exchange_Rate', 'Sale_Exchange_Rate'
            ]
            
            available_columns = [col for col in display_columns if col in cgt_df.columns]
            
            st.dataframe(
                cgt_df[available_columns],
                use_container_width=True
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        💡 **Key Features:**
        - Supports both HTML statements and CSV files from various sources
        - Automatic USD to AUD conversion using RBA exchange rates (loaded seamlessly)
        - Tax-optimized CGT calculations prioritizing long-term holdings
        - 50% CGT discount applied for assets held >12 months
        - Detailed Excel report ready for Australian tax lodgment
        - Uses buy date rates for purchases and sale date rates for sales
        - Smart duplicate detection and format standardization
        """
    )

if __name__ == "__main__":
    main()