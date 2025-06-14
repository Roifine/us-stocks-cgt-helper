#!/usr/bin/env python3
"""
Enhanced Unified Cost Basis Creator with AUD Conversion + Sales Extraction
🚀 Clean version with automatic sales extraction for CGT calculations

This script:
1. Parses HTML files directly from html_folder/
2. Loads manual CSV files from current directory
3. Applies HYBRID FIFO processing with AUD conversion
4. Creates cost basis dictionary with both USD and AUD amounts
5. Automatically extracts sales CSV for target financial year
6. Uses RBA historical exchange rates for accurate ATO reporting

PERFECT FOR: CGT optimization + ATO-compliant AUD reporting!
"""

import pandas as pd
import numpy as np
import json
import os
import glob
from datetime import datetime, timedelta
import warnings
import re
import traceback

# RBA AUD Converter Class
class RBAAUDConverter:
    """RBA AUD/USD exchange rate converter for CGT calculations."""
    
    def __init__(self):
        self.exchange_rates = {}
        self.date_range = None
        self.loaded_files = []
        
    def load_rba_csv_files(self, csv_files):
        """Load RBA CSV files and create exchange rate lookup."""
        print("💱 LOADING RBA EXCHANGE RATE DATA")
        print("=" * 50)
        
        all_rates = []
        
        for csv_file in csv_files:
            if not os.path.exists(csv_file):
                print(f"⚠️ File not found: {csv_file}")
                continue
                
            print(f"📄 Processing: {os.path.basename(csv_file)}")
            
            try:
                # Read RBA CSV
                df = pd.read_csv(csv_file, encoding='utf-8')
                
                # Parse RBA F11.1 format
                rates_data = self._parse_rba_f11_format(df, csv_file)
                
                if rates_data:
                    all_rates.extend(rates_data)
                    self.loaded_files.append(csv_file)
                    print(f"   ✅ Loaded {len(rates_data)} exchange rates")
                else:
                    print(f"   ❌ No valid rates found")
                    
            except Exception as e:
                print(f"   ❌ Error loading {csv_file}: {e}")
                continue
        
        if all_rates:
            # Convert to DataFrame and create lookup
            rates_df = pd.DataFrame(all_rates)
            rates_df['date'] = pd.to_datetime(rates_df['date'])
            rates_df = rates_df.sort_values('date').drop_duplicates(subset=['date'])
            
            # Create lookup dictionary
            for _, row in rates_df.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d')
                self.exchange_rates[date_str] = row['aud_usd_rate']
            
            self.date_range = (rates_df['date'].min(), rates_df['date'].max())
            
            print(f"\n✅ EXCHANGE RATE LOADING COMPLETE")
            print(f"   📅 Date range: {self.date_range[0].strftime('%Y-%m-%d')} to {self.date_range[1].strftime('%Y-%m-%d')}")
            print(f"   📊 Total rates: {len(self.exchange_rates)}")
            
            # Show sample rates
            print(f"\n📋 Sample exchange rates:")
            for i, (date, rate) in enumerate(list(self.exchange_rates.items())[-3:]):
                print(f"   {date}: 1 AUD = {rate:.4f} USD")
        else:
            print(f"❌ No exchange rate data loaded!")
    
    def _parse_rba_f11_format(self, df, filename):
        """Parse RBA F11.1 exchange rate format."""
        rates_data = []
        
        try:
            for index, row in df.iterrows():
                try:
                    # Convert row to list to work with positions
                    row_values = [str(val).strip() for val in row.values if pd.notna(val)]
                    
                    if len(row_values) < 2:
                        continue
                    
                    # Try to parse first column as date
                    date_str = row_values[0]
                    rate_str = row_values[1] if len(row_values) > 1 else None
                    
                    # Skip header rows and metadata
                    if any(word in date_str.lower() for word in ['date', 'series', 'unit', 'frequency', 'f11']):
                        continue
                    
                    # Try multiple date formats
                    parsed_date = self._parse_date_flexible(date_str)
                    if not parsed_date:
                        continue
                    
                    # Try to parse rate
                    if rate_str and rate_str != '':
                        try:
                            # Remove any non-numeric characters except decimal points
                            clean_rate = re.sub(r'[^\d.]', '', rate_str)
                            if clean_rate:
                                rate = float(clean_rate)
                                
                                # Sanity check: AUD/USD rate should be between 0.4 and 1.2
                                if 0.4 <= rate <= 1.2:
                                    rates_data.append({
                                        'date': parsed_date,
                                        'aud_usd_rate': rate
                                    })
                        except (ValueError, TypeError):
                            continue
                            
                except Exception:
                    continue
            
            # If we didn't find data in standard format, try alternative parsing
            if not rates_data:
                rates_data = self._parse_alternative_format(df)
                
        except Exception as e:
            print(f"   ❌ Error parsing {filename}: {e}")
        
        return rates_data
    
    def _parse_alternative_format(self, df):
        """Try alternative parsing methods for RBA data."""
        rates_data = []
        
        # Method 1: Look for columns that might contain dates and rates
        for col_idx in range(len(df.columns)):
            try:
                col_data = df.iloc[:, col_idx].dropna()
                
                # Check if this column contains dates
                date_count = 0
                
                for val in col_data.head(10):
                    if self._parse_date_flexible(str(val)):
                        date_count += 1
                
                # If this looks like a date column, look for rates in next column
                if date_count >= 5 and col_idx + 1 < len(df.columns):
                    date_col = df.iloc[:, col_idx]
                    rate_col = df.iloc[:, col_idx + 1]
                    
                    for i in range(len(date_col)):
                        try:
                            date_val = date_col.iloc[i]
                            rate_val = rate_col.iloc[i]
                            
                            parsed_date = self._parse_date_flexible(str(date_val))
                            if parsed_date and pd.notna(rate_val):
                                rate = float(str(rate_val))
                                if 0.4 <= rate <= 1.2:
                                    rates_data.append({
                                        'date': parsed_date,
                                        'aud_usd_rate': rate
                                    })
                        except:
                            continue
                    
                    if rates_data:
                        break
                        
            except Exception:
                continue
        
        return rates_data
    
    def _parse_date_flexible(self, date_str):
        """Parse dates in multiple formats commonly used by RBA."""
        if not date_str or pd.isna(date_str):
            return None
            
        date_str = str(date_str).strip()
        
        # Skip obviously non-date strings
        if len(date_str) < 6 or any(word in date_str.lower() for word in ['nan', 'series', 'unit']):
            return None
        
        formats_to_try = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
            "%d %b %Y", "%d-%b-%Y", "%b %d, %Y"
        ]
        
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def get_rate_for_date(self, date, fallback_method='previous_business_day'):
        """Get AUD/USD exchange rate for a specific date."""
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        date_str = date.strftime('%Y-%m-%d')
        
        # Direct lookup
        if date_str in self.exchange_rates:
            return self.exchange_rates[date_str]
        
        # Fallback methods
        if fallback_method == 'previous_business_day':
            # Go back up to 7 days
            for i in range(1, 8):
                fallback_date = date - timedelta(days=i)
                fallback_str = fallback_date.strftime('%Y-%m-%d')
                if fallback_str in self.exchange_rates:
                    return self.exchange_rates[fallback_str]
        
        return None
    
    def convert_usd_to_aud(self, usd_amount, date):
        """Convert USD amount to AUD using historical exchange rate."""
        if usd_amount == 0:
            return 0.0, 0.0
            
        rate = self.get_rate_for_date(date)
        
        if rate is None:
            return None, None
        
        # AUD amount = USD amount / (AUD/USD rate)
        aud_amount = usd_amount / rate
        
        return aud_amount, rate

# HTML Parsing Functions
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
    
    date_part = date_text.split(',')[0].split(' ')[0].strip()
    
    try:
        return datetime.strptime(date_part, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_part, '%m/%d/%Y').strftime('%Y-%m-%d')
        except ValueError:
            return date_text

def parse_html_file_with_hybrid_filtering(html_file_path, sell_cutoff_date=None):
    """Parse HTML file with HYBRID filtering."""
    print(f"🔄 Parsing HTML file: {os.path.basename(html_file_path)}")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"❌ Error reading HTML file: {e}")
        return None
    
    transactions = []
    
    # Find all summary rows
    summary_row_pattern = r'<tr class="row-summary">([\s\S]*?)</tr>'
    summary_matches = re.findall(summary_row_pattern, html_content)
    
    buy_count = 0
    sell_count = 0
    sell_filtered_count = 0
    
    for i, row_html in enumerate(summary_matches):
        try:
            cell_pattern = r'<td[^>]*>([\s\S]*?)</td>'
            cell_matches = re.findall(cell_pattern, row_html)
            
            if len(cell_matches) < 10:
                continue
            
            cells = [clean_text(cell) for cell in cell_matches]
            
            symbol = cells[1]
            trade_datetime = cells[2]
            trade_date = parse_trade_date(trade_datetime)
            transaction_type = cells[5]
            quantity_text = cells[6]
            price_text = cells[7]
            proceeds_text = cells[8]
            commission_text = cells[9]
            
            # Skip currency transactions
            if '.' in symbol and symbol not in ['U.S', 'S.A']:
                continue
            
            # HYBRID FILTERING LOGIC
            trade_date_obj = datetime.strptime(trade_date, '%Y-%m-%d')
            
            if transaction_type == 'SELL':
                # Apply cutoff filter to SELL transactions
                if sell_cutoff_date and trade_date_obj > sell_cutoff_date:
                    sell_filtered_count += 1
                    continue
                sell_count += 1
            elif transaction_type == 'BUY':
                # Include ALL BUY transactions (no filtering)
                buy_count += 1
            
            quantity = abs(parse_number(quantity_text))
            price = abs(parse_number(price_text))
            proceeds = parse_number(proceeds_text)
            commission = parse_number(commission_text)
            
            # Adjust signs
            if transaction_type == 'BUY':
                proceeds = -abs(proceeds)
                commission = -abs(commission)
            elif transaction_type == 'SELL':
                proceeds = abs(proceeds)
                commission = -abs(commission)
            
            transaction = {
                'Symbol': symbol,
                'Trade Date': trade_date,
                'Type': transaction_type,
                'Quantity': quantity,
                'Price (USD)': price,
                'Proceeds (USD)': proceeds,
                'Commission (USD)': commission
            }
            
            transactions.append(transaction)
            
        except Exception as e:
            continue
    
    print(f"   ✅ Processed: {buy_count} BUYs, {sell_count} SELLs")
    if sell_filtered_count > 0:
        print(f"   ⏹️ Filtered out: {sell_filtered_count} SELLs after cutoff date")
    
    if not transactions:
        return None
    
    df = pd.DataFrame(transactions)
    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
    df = df.sort_values('Trade Date').reset_index(drop=True)
    
    return df

def robust_date_parser(date_str):
    """Parse dates in multiple formats and return datetime object for sorting."""
    if not date_str or pd.isna(date_str):
        return datetime(1900, 1, 1)
    
    date_str = str(date_str).strip()
    formats_to_try = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%y", "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%y", "%m/%d/%y"
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return datetime(1900, 1, 1)

def format_date_for_output(date_str):
    """Format date as DD.M.YY for the final output."""
    date_obj = robust_date_parser(date_str)
    if date_obj.year > 1900:
        try:
            formatted = date_obj.strftime("%d.%-m.%y")
            return formatted
        except ValueError:
            formatted = date_obj.strftime("%d.%m.%y")
            parts = formatted.split('.')
            if len(parts) == 3 and parts[1].startswith('0') and len(parts[1]) == 2:
                parts[1] = parts[1][1:]
            return '.'.join(parts)
    return str(date_str)

def load_html_files_hybrid(sell_cutoff_date=None):
    """Load and parse HTML files with hybrid filtering."""
    print(f"\n📁 LOADING HTML FILES (HYBRID MODE)")
    if sell_cutoff_date:
        print(f"⏹️ SELL cutoff date: {sell_cutoff_date.strftime('%Y-%m-%d')}")
    print(f"📈 BUY transactions: Include ALL (no cutoff)")
    print("=" * 50)
    
    html_data = []
    html_folder = "html_folder"
    
    if not os.path.exists(html_folder):
        print(f"⚠️ {html_folder} directory not found")
        return html_data
    
    # Look for HTML files (.htm, .html)
    html_files = []
    for ext in ['*.htm', '*.html']:
        html_files.extend(glob.glob(os.path.join(html_folder, ext)))
    
    if html_files:
        print(f"📄 Found {len(html_files)} HTML files:")
        for html_file in html_files:
            print(f"   • {os.path.basename(html_file)}")
    
    for html_file in html_files:
        # Parse HTML with hybrid filtering
        df = parse_html_file_with_hybrid_filtering(html_file, sell_cutoff_date)
        
        if df is not None and len(df) > 0:
            # Standardize HTML data
            standardized = pd.DataFrame()
            standardized['Symbol'] = df['Symbol']
            standardized['Date'] = df['Trade Date'].astype(str)
            standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
            standardized['Quantity'] = df['Quantity'].abs()
            standardized['Price'] = df['Price (USD)'].abs()
            standardized['Commission'] = df['Commission (USD)'].abs()
            standardized['Source'] = f'HTML_{os.path.basename(html_file)}'
            
            # Clean up
            standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
            
            if len(standardized) > 0:
                html_data.append(standardized)
                
                # Show breakdown
                buy_count = len(standardized[standardized['Activity'] == 'PURCHASED'])
                sell_count = len(standardized[standardized['Activity'] == 'SOLD'])
                print(f"   ✅ Processed {os.path.basename(html_file)}: {buy_count} BUYs, {sell_count} SELLs")
    
    total_html_transactions = sum(len(df) for df in html_data)
    print(f"📊 Total HTML transactions loaded: {total_html_transactions}")
    
    return html_data

#!/usr/bin/env python3
"""
Fix for CSV Loading Issue in complete_unified_with_aud.py

Replace the load_manual_csv_files_hybrid() function with this enhanced version
"""

def load_manual_csv_files_hybrid_FIXED(sell_cutoff_date=None):
    """Load ALL CSV files with transaction data, not just 'manual' files."""
    print(f"\n📁 LOADING ALL CSV TRANSACTION FILES (FIXED VERSION)")
    if sell_cutoff_date:
        print(f"⏹️ SELL cutoff date: {sell_cutoff_date.strftime('%Y-%m-%d')}")
    print(f"📈 BUY transactions: Include ALL (no cutoff)")
    print("=" * 60)
    
    manual_data = []
    
    # FIXED: Look for ALL CSV files in multiple locations, not just "manual" ones
    all_csv_files = []
    
    # 1. Current directory CSV files
    current_dir_csvs = [f for f in glob.glob("*.csv")]
    all_csv_files.extend(current_dir_csvs)
    
    # 2. csv_folder directory CSV files
    csv_folder_files = [f for f in glob.glob("csv_folder/*.csv")]
    all_csv_files.extend(csv_folder_files)
    
    # 3. Filter for transaction files (exclude sales-only files)
    transaction_files = []
    for csv_file in all_csv_files:
        # Skip files that are clearly sales-only
        if 'sales_only' in csv_file.lower():
            print(f"   ⏩ Skipping sales-only file: {os.path.basename(csv_file)}")
            continue
        # Skip files that might be reports or outputs
        if any(keyword in csv_file.lower() for keyword in ['report', 'output', 'cgt_', 'result']):
            print(f"   ⏩ Skipping output file: {os.path.basename(csv_file)}")
            continue
        transaction_files.append(csv_file)
    
    if transaction_files:
        print(f"📄 Found {len(transaction_files)} potential transaction files:")
        for file in transaction_files:
            print(f"   • {file}")
    else:
        print("📄 No CSV transaction files found")
        return manual_data
    
    # Process each transaction file
    for csv_file in transaction_files:
        try:
            df = pd.read_csv(csv_file)
            print(f"\n🔄 Processing {csv_file}:")
            print(f"   📊 Shape: {df.shape}")
            print(f"   📋 Columns: {list(df.columns)}")
            
            # Detect file format and standardize
            standardized = None
            
            # Format 1: Manual CSV format (Date, Activity_Type, Symbol, Quantity, Price_USD, etc.)
            if all(col in df.columns for col in ['Date', 'Activity_Type', 'Symbol', 'Quantity', 'Price_USD']):
                print(f"   📝 Detected: Manual CSV format")
                
                # Apply hybrid filtering for manual CSV
                if sell_cutoff_date:
                    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%y', errors='coerce')
                    
                    # Split into SELL and BUY transactions
                    sell_transactions = df[df['Activity_Type'] == 'SOLD']
                    buy_transactions = df[df['Activity_Type'] == 'PURCHASED']
                    
                    # Filter SELL transactions by cutoff date
                    sell_before_cutoff = sell_transactions[sell_transactions['Date'] <= sell_cutoff_date]
                    sell_filtered_count = len(sell_transactions) - len(sell_before_cutoff)
                    
                    # Keep ALL BUY transactions
                    df_filtered = pd.concat([buy_transactions, sell_before_cutoff], ignore_index=True)
                    
                    if sell_filtered_count > 0:
                        print(f"   ⏹️ Filtered {sell_filtered_count} SELL transactions after cutoff")
                    
                    df = df_filtered
                
                # Create standardized DataFrame
                standardized = pd.DataFrame()
                standardized['Symbol'] = df['Symbol']
                standardized['Date'] = df['Date'].astype(str)
                standardized['Activity'] = df['Activity_Type'].map({'PURCHASED': 'PURCHASED', 'SOLD': 'SOLD'})
                standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
                standardized['Price'] = pd.to_numeric(df['Price_USD'], errors='coerce').abs()
                standardized['Commission'] = 30.0  # Default for manual transactions
                standardized['Source'] = f'Manual_{os.path.basename(csv_file)}'
            
            # Format 2: Parsed format (Symbol, Trade Date, Type, Quantity, Price (USD), etc.)
            elif all(col in df.columns for col in ['Symbol', 'Trade Date', 'Type', 'Quantity', 'Price (USD)']):
                print(f"   📝 Detected: Parsed HTML format")
                
                # Apply hybrid filtering for parsed CSV
                if sell_cutoff_date:
                    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
                    
                    # Split into SELL and BUY transactions
                    sell_transactions = df[df['Type'] == 'SELL']
                    buy_transactions = df[df['Type'] == 'BUY']
                    
                    # Filter SELL transactions by cutoff date
                    sell_before_cutoff = sell_transactions[sell_transactions['Trade Date'] <= sell_cutoff_date]
                    sell_filtered_count = len(sell_transactions) - len(sell_before_cutoff)
                    
                    # Keep ALL BUY transactions
                    df_filtered = pd.concat([buy_transactions, sell_before_cutoff], ignore_index=True)
                    
                    if sell_filtered_count > 0:
                        print(f"   ⏹️ Filtered {sell_filtered_count} SELL transactions after cutoff")
                    
                    df = df_filtered
                
                # Create standardized DataFrame
                standardized = pd.DataFrame()
                standardized['Symbol'] = df['Symbol']
                standardized['Date'] = df['Trade Date'].astype(str)
                standardized['Activity'] = df['Type'].map({'BUY': 'PURCHASED', 'SELL': 'SOLD'})
                standardized['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').abs()
                standardized['Price'] = pd.to_numeric(df['Price (USD)'], errors='coerce').abs()
                standardized['Commission'] = pd.to_numeric(df.get('Commission (USD)', 0), errors='coerce').abs()
                standardized['Source'] = f'Parsed_{os.path.basename(csv_file)}'
            
            else:
                print(f"   ❌ Unknown CSV format - skipping")
                continue
            
            # Clean up and validate
            if standardized is not None:
                standardized = standardized.dropna(subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'])
                
                if len(standardized) > 0:
                    manual_data.append(standardized)
                    
                    # Show breakdown
                    buy_count = len(standardized[standardized['Activity'] == 'PURCHASED'])
                    sell_count = len(standardized[standardized['Activity'] == 'SOLD'])
                    symbols = sorted(standardized['Symbol'].unique())
                    
                    print(f"   ✅ Processed: {buy_count} BUYs, {sell_count} SELLs")
                    print(f"   🏷️  Symbols: {symbols}")
                else:
                    print(f"   ⚠️ No valid transactions after processing")
            
        except Exception as e:
            print(f"   ❌ Error loading {csv_file}: {e}")
            import traceback
            print(f"   🔧 Debug: {traceback.format_exc()}")
    
    total_manual_transactions = sum(len(df) for df in manual_data)
    print(f"📊 Total transactions loaded: {total_manual_transactions}")
    
    return manual_data


# USAGE: Replace the function in complete_unified_with_aud.py
# Find this line in the file:
# def load_manual_csv_files_hybrid(sell_cutoff_date=None):
# And replace the entire function with the version above

def apply_hybrid_fifo_processing_with_aud(combined_df, aud_converter, sell_cutoff_date=None):
    """Apply HYBRID FIFO processing with AUD conversion."""
    print(f"\n🔄 APPLYING HYBRID FIFO PROCESSING WITH AUD CONVERSION")
    if sell_cutoff_date:
        print(f"⏹️ SELL transactions processed up to: {sell_cutoff_date.strftime('%Y-%m-%d')}")
    print(f"📈 BUY transactions: ALL processed (no cutoff)")
    print(f"💱 Converting to AUD using RBA historical rates")
    print("=" * 60)
    
    cost_basis_dict = {}
    fifo_log = {}
    conversion_errors = []
    
    print(f"📊 Processing {len(combined_df)} total transactions")
    print(f"   Symbols: {combined_df['Symbol'].nunique()}")
    print(f"   BUY: {len(combined_df[combined_df['Activity'] == 'PURCHASED'])}")
    print(f"   SELL: {len(combined_df[combined_df['Activity'] == 'SOLD'])}")
    
    for symbol in combined_df['Symbol'].unique():
        symbol_transactions = combined_df[combined_df['Symbol'] == symbol].copy()
        
        # Sort by date
        symbol_transactions['date_obj'] = symbol_transactions['Date'].apply(robust_date_parser)
        symbol_transactions = symbol_transactions.sort_values('date_obj')
        
        print(f"\n📊 Processing {symbol} ({len(symbol_transactions)} transactions):")
        
        purchase_queue = []
        fifo_operations = []
        
        for _, transaction in symbol_transactions.iterrows():
            date_str = format_date_for_output(transaction['Date'])
            date_obj = robust_date_parser(transaction['Date'])
            activity = transaction['Activity']
            quantity = float(transaction['Quantity'])
            price_usd = float(transaction['Price'])
            commission_usd = float(transaction['Commission'])
            source = transaction['Source']
            
            if activity == 'PURCHASED':
                # Convert USD amounts to AUD at purchase date
                total_cost_usd = (quantity * price_usd) + commission_usd
                total_cost_aud, exchange_rate = aud_converter.convert_usd_to_aud(total_cost_usd, date_obj)
                
                if total_cost_aud is None:
                    error_msg = f"⚠️ No exchange rate for {symbol} purchase on {date_str}"
                    conversion_errors.append(error_msg)
                    print(f"   {error_msg}")
                    # Use USD values as fallback
                    price_aud = price_usd
                    commission_aud = commission_usd
                    exchange_rate = None
                else:
                    # Calculate AUD per-unit price and commission
                    price_aud = (quantity * price_usd) / quantity / exchange_rate  # Price per unit in AUD
                    commission_aud = commission_usd / exchange_rate
                
                purchase = {
                    'units': quantity,
                    'price': price_usd,              # USD price per unit
                    'commission': commission_usd,    # USD commission
                    'price_aud': price_aud,          # AUD price per unit
                    'commission_aud': commission_aud, # AUD commission
                    'exchange_rate': exchange_rate,   # AUD/USD rate used
                    'date': date_str
                }
                purchase_queue.append(purchase)
                
                if exchange_rate:
                    print(f"   📈 BUY: {quantity} units @ ${price_usd:.2f} USD (${price_aud:.2f} AUD) on {date_str} (rate: {exchange_rate:.4f})")
                else:
                    print(f"   📈 BUY: {quantity} units @ ${price_usd:.2f} USD on {date_str} (NO AUD RATE)")
                
                fifo_operations.append(f"BUY: {quantity} units @ ${price_usd:.2f} USD + ${commission_usd:.2f} on {date_str} ({source})")
                
            elif activity == 'SOLD':
                units_to_sell = quantity
                
                print(f"   📉 SELL: {units_to_sell} units on {date_str} ({source})")
                fifo_operations.append(f"SELL: {units_to_sell} units on {date_str} ({source})")
                
                # Apply FIFO
                remaining_to_sell = units_to_sell
                updated_queue = []
                
                for purchase in purchase_queue:
                    if remaining_to_sell <= 0:
                        updated_queue.append(purchase)
                    elif purchase['units'] <= remaining_to_sell:
                        print(f"      ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f} USD")
                        fifo_operations.append(f"   ✂️ Used all {purchase['units']} units from {purchase['date']} @ ${purchase['price']:.2f} USD")
                        remaining_to_sell -= purchase['units']
                    else:
                        units_used = remaining_to_sell
                        units_remaining = purchase['units'] - units_used
                        
                        print(f"      ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} USD (kept {units_remaining})")
                        fifo_operations.append(f"   ✂️ Used {units_used} units from {purchase['date']} @ ${purchase['price']:.2f} USD (kept {units_remaining})")
                        
                        # Create updated purchase with proportional amounts
                        proportion = units_remaining / purchase['units']
                        updated_purchase = purchase.copy()
                        updated_purchase['units'] = units_remaining
                        updated_purchase['commission'] = purchase['commission'] * proportion
                        updated_purchase['commission_aud'] = purchase['commission_aud'] * proportion
                        
                        updated_queue.append(updated_purchase)
                        remaining_to_sell = 0
                
                purchase_queue = updated_queue
                
                if remaining_to_sell > 0:
                    warning = f"      ⚠️ WARNING: Tried to sell {remaining_to_sell} more units than available!"
                    print(warning)
                    fifo_operations.append(warning)
        
        # Store remaining purchases with both USD and AUD amounts
        if purchase_queue:
            cost_basis_dict[symbol] = purchase_queue
            
            total_units = sum(p['units'] for p in purchase_queue)
            total_cost_usd = sum(p['units'] * p['price'] + p['commission'] for p in purchase_queue)
            total_cost_aud = sum(p['units'] * p['price_aud'] + p['commission_aud'] for p in purchase_queue if p.get('price_aud'))
            
            print(f"   ✅ Final: {total_units:.2f} units, ${total_cost_usd:.2f} USD, ${total_cost_aud:.2f} AUD")
        else:
            print(f"   📭 No remaining units after all sales")
        
        fifo_log[symbol] = fifo_operations
    
    if conversion_errors:
        print(f"\n⚠️ CONVERSION WARNINGS ({len(conversion_errors)}):")
        for error in conversion_errors[:5]:  # Show first 5
            print(f"   {error}")
        if len(conversion_errors) > 5:
            print(f"   ... and {len(conversion_errors) - 5} more warnings")
    
    return cost_basis_dict, fifo_log, conversion_errors

def extract_sales_for_fy(combined_df, aud_converter, sell_cutoff_date):
    """
    Extract SELL transactions for the financial year following the cutoff date.
    Automatically determines which FY to extract based on cutoff date.
    """
    if not sell_cutoff_date:
        return None
    
    # Determine the following financial year based on cutoff date
    cutoff_year = sell_cutoff_date.year
    if sell_cutoff_date.month == 6 and sell_cutoff_date.day == 30:
        # If cutoff is June 30, extract sales from July 1 of that year to June 30 next year
        target_fy = f"{cutoff_year}-{str(cutoff_year + 1)[-2:]}"
        fy_start = datetime(cutoff_year, 7, 1)  # July 1
        fy_end = datetime(cutoff_year + 1, 6, 30)  # June 30 next year
    else:
        print("⚠️ Automatic sales extraction only works with June 30 cutoff dates")
        return None
    
    print(f"\n📉 AUTOMATIC SALES EXTRACTION FOR FY {target_fy}")
    print(f"📅 Based on cutoff: {sell_cutoff_date.strftime('%Y-%m-%d')}")
    print(f"📅 Extracting sales: {fy_start.strftime('%Y-%m-%d')} to {fy_end.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    # Extract SELL transactions from the target financial year
    sell_transactions = combined_df[combined_df['Activity'] == 'SOLD'].copy()
    
    if len(sell_transactions) == 0:
        print("📭 No SELL transactions found in data")
        return None
    
    # Convert dates to datetime for filtering
    sell_transactions['date_obj'] = sell_transactions['Date'].apply(robust_date_parser)
    
    # Filter for target financial year
    fy_sales = sell_transactions[
        (sell_transactions['date_obj'] >= fy_start) & 
        (sell_transactions['date_obj'] <= fy_end)
    ].copy()
    
    if len(fy_sales) == 0:
        print(f"📭 No SELL transactions found in FY {target_fy}")
        return None
    
    print(f"📉 Found {len(fy_sales)} SELL transactions in FY {target_fy}")
    
    # Remove duplicates
    fy_sales = fy_sales.drop_duplicates(
        subset=['Symbol', 'Date', 'Quantity', 'Price'], 
        keep='first'
    ).reset_index(drop=True)
    
    print(f"📉 After deduplication: {len(fy_sales)} unique sales")
    
    # Create sales DataFrame with proper column names for CGT calculator
    sales_data = []
    conversion_errors = []
    
    for _, sale in fy_sales.iterrows():
        try:
            symbol = sale['Symbol']
            trade_date = robust_date_parser(sale['Date'])
            quantity = abs(float(sale['Quantity']))
            price_usd = abs(float(sale['Price']))
            commission_usd = abs(float(sale['Commission']))
            
            # Calculate total proceeds
            total_proceeds_usd = quantity * price_usd
            net_proceeds_usd = total_proceeds_usd - commission_usd
            
            # Convert to AUD using sale date exchange rate
            if aud_converter:
                total_proceeds_aud, sale_rate = aud_converter.convert_usd_to_aud(total_proceeds_usd, trade_date)
                commission_aud, _ = aud_converter.convert_usd_to_aud(commission_usd, trade_date)
                sale_price_aud, _ = aud_converter.convert_usd_to_aud(price_usd, trade_date)
                
                if total_proceeds_aud is None:
                    conversion_errors.append(f"No exchange rate for {symbol} sale on {trade_date.strftime('%Y-%m-%d')}")
                    # Use USD values as fallback
                    total_proceeds_aud = total_proceeds_usd
                    commission_aud = commission_usd
                    sale_price_aud = price_usd
                    sale_rate = None
            else:
                # No converter available
                total_proceeds_aud = total_proceeds_usd
                commission_aud = commission_usd
                sale_price_aud = price_usd
                sale_rate = None
            
            net_proceeds_aud = total_proceeds_aud - commission_aud
            
            sales_record = {
                'Symbol': symbol,
                'Trade Date': trade_date,
                'Units_Sold': quantity,
                'Sale_Price_Per_Unit': price_usd,                    # USD
                'Sale_Price_Per_Unit_AUD': sale_price_aud,          # AUD
                'Total_Proceeds': total_proceeds_usd,               # USD
                'Total_Proceeds_AUD': total_proceeds_aud,           # AUD
                'Commission_Paid': commission_usd,                  # USD
                'Commission_Paid_AUD': commission_aud,              # AUD
                'Net_Proceeds': net_proceeds_usd,                   # USD
                'Net_Proceeds_AUD': net_proceeds_aud,               # AUD
                'Sale_Exchange_Rate': sale_rate,
                'Financial_Year': target_fy,
                'Source': sale['Source']
            }
            
            sales_data.append(sales_record)
            
        except Exception as e:
            print(f"   ⚠️ Error processing sale: {e}")
            continue
    
    if not sales_data:
        print("❌ No valid sales data created")
        return None
    
    # Create DataFrame
    sales_df = pd.DataFrame(sales_data)
    sales_df = sales_df.sort_values('Trade Date').reset_index(drop=True)
    
    # Generate filename
    sales_filename = f"Sales_Transactions_FY{target_fy}_for_CGT.csv"
    
    try:
        # Save to CSV
        sales_df.to_csv(sales_filename, index=False)
        print(f"✅ Sales CSV created: {sales_filename}")
        
        # Show summary
        print(f"\n📊 Sales Summary for FY {target_fy}:")
        print(f"   📉 Total sales: {len(sales_df)}")
        print(f"   🏷️  Unique symbols: {sales_df['Symbol'].nunique()}")
        print(f"   💰 Total proceeds (AUD): ${sales_df['Total_Proceeds_AUD'].sum():,.2f}")
        print(f"   📅 Date range: {sales_df['Trade Date'].min().strftime('%Y-%m-%d')} to {sales_df['Trade Date'].max().strftime('%Y-%m-%d')}")
        
        # Show by symbol
        print(f"\n📋 Sales by symbol:")
        symbol_summary = sales_df.groupby('Symbol').agg({
            'Units_Sold': 'sum',
            'Total_Proceeds_AUD': 'sum'
        }).round(2)
        
        for symbol, row in symbol_summary.iterrows():
            print(f"   {symbol}: {row['Units_Sold']:,.0f} units, ${row['Total_Proceeds_AUD']:,.2f} AUD")
        
        if conversion_errors:
            print(f"\n⚠️ {len(conversion_errors)} AUD conversion warnings:")
            for error in conversion_errors[:3]:
                print(f"   • {error}")
            if len(conversion_errors) > 3:
                print(f"   • ... and {len(conversion_errors) - 3} more")
        
        return sales_filename
        
    except Exception as e:
        print(f"❌ Error saving sales CSV: {e}")
        return None

def display_summary_hybrid_with_aud(cost_basis_dict, sell_cutoff_date=None):
    """Display cost basis summary for hybrid processing with AUD amounts."""
    print(f"\n📊 HYBRID COST BASIS SUMMARY WITH AUD")
    if sell_cutoff_date:
        print(f"⏹️ SELL cutoff: {sell_cutoff_date.strftime('%Y-%m-%d')}")
    print(f"📈 BUY coverage: ALL transactions")
    print(f"💱 AUD conversion: RBA historical rates")
    print("=" * 60)
    
    total_symbols = len(cost_basis_dict)
    total_units = sum(sum(r['units'] for r in records) for records in cost_basis_dict.values())
    total_cost_usd = sum(sum(r['units'] * r['price'] + r['commission'] for r in records) for records in cost_basis_dict.values())
    total_cost_aud = sum(sum(r['units'] * r.get('price_aud', r['price']) + r.get('commission_aud', r['commission']) for r in records) for records in cost_basis_dict.values())
    
    print(f"Symbols with remaining units: {total_symbols}")
    print(f"Total remaining units: {total_units:,.0f}")
    print(f"Total cost basis (USD): ${total_cost_usd:,.2f}")
    print(f"Total cost basis (AUD): ${total_cost_aud:,.2f}")
    
    print(f"\n📋 By symbol (AUD amounts for ATO):")
    for symbol, records in sorted(cost_basis_dict.items()):
        symbol_units = sum(r['units'] for r in records)
        symbol_cost_aud = sum(r['units'] * r.get('price_aud', r['price']) + r.get('commission_aud', r['commission']) for r in records)
        avg_price_aud = (symbol_cost_aud - sum(r.get('commission_aud', r['commission']) for r in records)) / symbol_units if symbol_units > 0 else 0
        
        print(f"   {symbol}: {symbol_units:,.0f} units @ avg ${avg_price_aud:.2f} AUD (${symbol_cost_aud:,.2f} total)")

def save_results_hybrid_with_aud(cost_basis_dict, fifo_log, conversion_errors, sell_cutoff_date=None):
    """Save cost basis and log files with AUD data."""
    
    if sell_cutoff_date:
        date_suffix = f"_hybrid_aud_sell_cutoff_{sell_cutoff_date.strftime('%Y_%m_%d')}"
        cost_basis_file = f"COMPLETE_unified_cost_basis_with_FIFO_AUD{date_suffix}.json"
        log_file = f"COMPLETE_fifo_processing_log_AUD{date_suffix}.json"
    else:
        cost_basis_file = "COMPLETE_unified_cost_basis_with_FIFO_AUD_hybrid_no_cutoff.json"
        log_file = "COMPLETE_fifo_processing_log_AUD_hybrid_no_cutoff.json"
    
    try:
        # Save cost basis with both USD and AUD
        with open(cost_basis_file, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        print(f"✅ Cost basis (USD+AUD) saved: {cost_basis_file}")
        
        # Save FIFO log with conversion errors
        log_data = {
            'fifo_operations': fifo_log,
            'conversion_errors': conversion_errors,
            'creation_date': datetime.now().isoformat(),
            'sell_cutoff_date': sell_cutoff_date.isoformat() if sell_cutoff_date else None
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"✅ FIFO log (with AUD errors) saved: {log_file}")
        
        return cost_basis_file
        
    except Exception as e:
        print(f"❌ Error saving files: {e}")
        return None

def load_rba_exchange_rates():
    """Load RBA exchange rate data from the rates folder."""
    print(f"\n💱 LOADING RBA EXCHANGE RATES")
    print("=" * 50)
    
    # RBA file paths
    rates_folder = "/Users/roifine/My python projects/Ozi_Tax_Agent/rates"
    rba_files = [
        os.path.join(rates_folder, "FX_2018-2022.csv"),
        os.path.join(rates_folder, "FX_2023-2025.csv")
    ]
    
    # Initialize converter
    aud_converter = RBAAUDConverter()
    aud_converter.load_rba_csv_files(rba_files)
    
    if not aud_converter.exchange_rates:
        print(f"❌ Failed to load exchange rate data!")
        print(f"📁 Expected files:")
        for file in rba_files:
            print(f"   • {file}")
        print(f"💡 Please ensure the rates folder exists and contains the CSV files")
        return None
    
    return aud_converter

def get_hybrid_configuration():
    """Get hybrid processing configuration from user."""
    print(f"\n" + "="*70)
    print("HYBRID PROCESSING CONFIGURATION WITH AUD CONVERSION")
    print("="*70)
    print("🚀 Hybrid processing + AUD conversion + automatic sales extraction!")
    print()
    print("How it works:")
    print("• SELL transactions: Process only up to cutoff date (for CGT optimization)")
    print("• BUY transactions: Process ALL transactions (captures all cost basis)")
    print("• AUD conversion: Uses RBA historical rates at purchase dates")
    print("• Sales extraction: Automatically creates CSV for following financial year")
    print()
    print("Recommended cutoff dates:")
    print("1. June 30, 2024 (end of FY 2023-24) → Auto-extract FY 2024-25 sales")
    print("2. June 30, 2025 (end of FY 2024-25) → Auto-extract FY 2025-26 sales")
    print("3. Custom date (YYYY-MM-DD format)")
    print("4. No cutoff (standard processing - all transactions)")
    print()
    print("💡 Choose option 1 for FY 2024-25 CGT calculations")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == '1':
                return datetime(2024, 6, 30)
            elif choice == '2':
                return datetime(2025, 6, 30)
            elif choice == '3':
                date_str = input("Enter custom date (YYYY-MM-DD): ").strip()
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    print("❌ Invalid date format. Please use YYYY-MM-DD")
                    continue
            elif choice == '4':
                return None
            elif choice.lower() in ['q', 'quit', 'exit']:
                print("Exiting...")
                return None
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4 (or 'q' to quit).")
        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted")
            return None
        except:
            print("❌ Invalid input. Please try again.")

def main():
    """Main function for hybrid cost basis creation with AUD conversion + sales extraction."""
    print("🚀 ENHANCED UNIFIED COST BASIS CREATOR WITH AUD + SALES EXTRACTION")
    print("=" * 80)
    print("🇦🇺 PERFECT for Australian CGT optimization + ATO compliance!")
    print("• Parses HTML files from html_folder/")
    print("• Loads manual CSV files from current directory")
    print("• HYBRID processing: Optimize long-term + capture short-term")
    print("• AUD conversion: Uses RBA historical exchange rates")
    print("• Creates ATO-compliant cost basis for Australian tax reporting")
    print("• BONUS: Automatically extracts sales CSV for CGT calculator")
    print()
    
    # Load RBA exchange rates first
    aud_converter = load_rba_exchange_rates()
    if not aud_converter:
        print("❌ Cannot proceed without exchange rate data")
        return None
    
    # Get hybrid configuration
    sell_cutoff_date = get_hybrid_configuration()
    
    if sell_cutoff_date:
        print(f"\n🎯 HYBRID MODE WITH AUD CONVERSION ACTIVATED!")
        print(f"⏹️ SELL cutoff: {sell_cutoff_date.strftime('%Y-%m-%d')}")
        print(f"📈 BUY coverage: ALL transactions (no cutoff)")
        print(f"💱 AUD conversion: RBA historical rates")
        print(f"📉 Sales extraction: Automatic for following FY")
        print(f"🇦🇺 Perfect for ATO-compliant CGT optimization!")
    else:
        print(f"\n🔄 STANDARD MODE WITH AUD CONVERSION: Processing ALL transactions")
        print(f"💱 AUD conversion: RBA historical rates")
    
    try:
        all_data = []
        
        # Load HTML files with hybrid processing
        html_data = load_html_files_hybrid(sell_cutoff_date)
        all_data.extend(html_data)
        
        # Load manual CSV files with hybrid processing
        manual_data = load_manual_csv_files_hybrid(sell_cutoff_date)
        all_data.extend(manual_data)
        
        if not all_data:
            print("❌ No data loaded from any source")
            return None
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Remove duplicates
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(
            subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], 
            keep='first'
        )
        after_count = len(combined_df)
        
        if before_count != after_count:
            print(f"✂️ Removed {before_count - after_count} duplicates")
        
        print(f"\n📊 COMBINED DATA SUMMARY:")
        print(f"   Total transactions: {len(combined_df)}")
        print(f"   Unique symbols: {combined_df['Symbol'].nunique()}")
        print(f"   BUY transactions: {len(combined_df[combined_df['Activity'] == 'PURCHASED'])}")
        print(f"   SELL transactions: {len(combined_df[combined_df['Activity'] == 'SOLD'])}")
        print(f"   Sources: {dict(combined_df['Source'].value_counts())}")
        
        # Extract sales for the following financial year automatically
        sales_filename = None
        if sell_cutoff_date:
            sales_filename = extract_sales_for_fy(combined_df, aud_converter, sell_cutoff_date)
        
        # Apply hybrid FIFO processing with AUD conversion
        cost_basis_dict, fifo_log, conversion_errors = apply_hybrid_fifo_processing_with_aud(
            combined_df, aud_converter, sell_cutoff_date
        )
        
        if not cost_basis_dict:
            print("❌ No cost basis calculated")
            return None
        
        # Display summary with AUD
        display_summary_hybrid_with_aud(cost_basis_dict, sell_cutoff_date)
        
        # Save results with AUD data
        print(f"\n💾 SAVING RESULTS WITH AUD DATA")
        print("=" * 40)
        output_file = save_results_hybrid_with_aud(
            cost_basis_dict, fifo_log, conversion_errors, sell_cutoff_date
        )
        
        if output_file:
            print(f"\n🎉 AUD CONVERSION SUCCESS!")
            print(f"✅ Enhanced cost basis created: {output_file}")
            if sell_cutoff_date:
                print(f"⏹️ SELL cutoff: {sell_cutoff_date.strftime('%Y-%m-%d')} (CGT optimization)")
                print(f"📈 BUY coverage: ALL transactions (complete coverage)")
            print(f"💱 AUD conversion: RBA historical rates applied")
            print(f"🇦🇺 ATO compliant: Cost basis in AUD for tax reporting")
            print(f"✅ Includes data from BOTH HTML and CSV sources")
            print(f"✅ HYBRID FIFO processing with AUD conversion applied")
            print(f"📊 Contains cost basis for {len(cost_basis_dict)} symbols")
            
            if sales_filename:
                print(f"📉 Sales CSV created: {sales_filename}")
                print(f"💡 Use this sales CSV with cgt_calculator_australia_aud.py")
            
            print(f"💡 Ready for ATO-compliant CGT calculations!")
            
            if conversion_errors:
                print(f"\n⚠️ {len(conversion_errors)} conversion warnings - check log file for details")
            
            # Show next steps
            print(f"\n📋 NEXT STEPS:")
            print(f"1. ✅ Cost basis created: {output_file}")
            if sales_filename:
                print(f"2. ✅ Sales file created: {sales_filename}")
                print(f"3. 🚀 Run: python cgt_calculator_australia_aud.py")
                print(f"4. 📊 Select both files when prompted in CGT calculator")
            else:
                print(f"2. 📉 Create/obtain sales CSV for target financial year")
                print(f"3. 🚀 Run: python cgt_calculator_australia_aud.py")
        
        return cost_basis_dict
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"🔍 Full traceback:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()