#!/usr/bin/env python3
"""
AUD Conversion System for CGT Calculator
Loads RBA exchange rate data and converts all USD amounts to AUD for ATO compliance

This module:
1. Loads multiple RBA CSV files (2018-2022, 2023-onwards)
2. Creates a comprehensive date-to-rate lookup
3. Converts all CGT calculations to AUD
4. Provides ATO-compliant reporting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import re

class RBAAUDConverter:
    """RBA AUD/USD exchange rate converter for CGT calculations."""
    
    def __init__(self):
        self.exchange_rates = {}
        self.date_range = None
        self.loaded_files = []
        
    def load_rba_csv_files(self, csv_files):
        """
        Load RBA CSV files and create exchange rate lookup.
        
        Args:
            csv_files (list): List of RBA CSV file paths
        """
        print("💱 LOADING RBA EXCHANGE RATE DATA")
        print("=" * 50)
        
        all_rates = []
        
        for csv_file in csv_files:
            if not os.path.exists(csv_file):
                print(f"⚠️ File not found: {csv_file}")
                continue
                
            print(f"📄 Processing: {csv_file}")
            
            try:
                # Read RBA CSV - usually has headers and metadata
                df = pd.read_csv(csv_file, encoding='utf-8')
                
                print(f"   📊 Columns found: {list(df.columns)}")
                print(f"   📊 Shape: {df.shape}")
                
                # Display first few rows to understand structure
                print(f"   📋 First 5 rows:")
                for i, row in df.head().iterrows():
                    print(f"      {i}: {dict(row)}")
                
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
            print(f"   📁 Files loaded: {len(self.loaded_files)}")
            
            # Show sample rates
            print(f"\n📋 Sample exchange rates:")
            for i, (date, rate) in enumerate(list(self.exchange_rates.items())[-5:]):
                print(f"   {date}: 1 AUD = {rate:.4f} USD")
        else:
            print(f"❌ No exchange rate data loaded!")
    
    def _parse_rba_f11_format(self, df, filename):
        """
        Parse RBA F11.1 exchange rate format.
        This format typically has dates in first column and rates in subsequent columns.
        """
        rates_data = []
        
        try:
            # RBA F11.1 files often have metadata rows at the top
            # Look for rows that contain actual date and rate data
            
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
                print(f"   🔍 Trying alternative parsing for {filename}")
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
                rate_count = 0
                
                for val in col_data.head(10):
                    if self._parse_date_flexible(str(val)):
                        date_count += 1
                    try:
                        rate = float(str(val))
                        if 0.4 <= rate <= 1.2:
                            rate_count += 1
                    except:
                        pass
                
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
            "%Y-%m-%d",      # 2024-01-15
            "%d/%m/%Y",      # 15/01/2024
            "%m/%d/%Y",      # 01/15/2024
            "%d-%m-%Y",      # 15-01-2024
            "%Y/%m/%d",      # 2024/01/15
            "%d %b %Y",      # 15 Jan 2024
            "%d-%b-%Y",      # 15-Jan-2024
            "%b %d, %Y",     # Jan 15, 2024
        ]
        
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def get_rate_for_date(self, date, fallback_method='previous_business_day'):
        """
        Get AUD/USD exchange rate for a specific date.
        
        Args:
            date (datetime or str): Date to get rate for
            fallback_method (str): How to handle missing dates
            
        Returns:
            float: AUD/USD exchange rate (1 AUD = X USD)
        """
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        
        date_str = date.strftime('%Y-%m-%d')
        
        # Direct lookup
        if date_str in self.exchange_rates:
            return self.exchange_rates[date_str]
        
        # Fallback methods
        if fallback_method == 'previous_business_day':
            # Go back up to 5 business days
            for i in range(1, 8):
                fallback_date = date - timedelta(days=i)
                fallback_str = fallback_date.strftime('%Y-%m-%d')
                if fallback_str in self.exchange_rates:
                    return self.exchange_rates[fallback_str]
        
        # If still no rate found, return None
        return None
    
    def convert_usd_to_aud(self, usd_amount, date):
        """
        Convert USD amount to AUD using historical exchange rate.
        
        Args:
            usd_amount (float): Amount in USD
            date (datetime or str): Date for exchange rate lookup
            
        Returns:
            tuple: (aud_amount, exchange_rate_used)
        """
        if usd_amount == 0:
            return 0.0, 0.0
            
        rate = self.get_rate_for_date(date)
        
        if rate is None:
            print(f"⚠️ No exchange rate found for {date}")
            return None, None
        
        # AUD amount = USD amount / (AUD/USD rate)
        # If rate is 0.67 (1 AUD = 0.67 USD), then 1 USD = 1/0.67 AUD
        aud_amount = usd_amount / rate
        
        return aud_amount, rate
    
    def enhance_cgt_dataframe_with_aud(self, cgt_df):
        """
        Add AUD columns to CGT calculations DataFrame.
        
        Args:
            cgt_df (pandas.DataFrame): CGT calculations with USD amounts
            
        Returns:
            pandas.DataFrame: Enhanced DataFrame with AUD columns
        """
        print("\n💱 CONVERTING CGT CALCULATIONS TO AUD")
        print("=" * 50)
        
        enhanced_df = cgt_df.copy()
        
        # Add AUD conversion columns
        aud_columns = []
        
        for index, row in enhanced_df.iterrows():
            try:
                # Get sale date for conversion
                sale_date = row['sale_date']
                if isinstance(sale_date, str):
                    sale_date = datetime.strptime(sale_date, '%Y-%m-%d')
                
                # Get purchase date for cost basis conversion
                purchase_date = row['purchase_date'] 
                if isinstance(purchase_date, str):
                    purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d')
                
                # Convert proceeds to AUD (using sale date)
                proceeds_aud, sale_rate = self.convert_usd_to_aud(row['proceeds'], sale_date)
                
                # Convert cost basis to AUD (using purchase date) 
                cost_basis_aud, purchase_rate = self.convert_usd_to_aud(row['cost_basis'], purchase_date)
                
                if proceeds_aud is not None and cost_basis_aud is not None:
                    # Calculate AUD capital gain
                    capital_gain_aud = proceeds_aud - cost_basis_aud
                    
                    # Apply CGT discount if applicable
                    taxable_gain_aud = capital_gain_aud
                    if row.get('long_term_eligible', False) and capital_gain_aud > 0:
                        taxable_gain_aud = capital_gain_aud * 0.5
                    
                    aud_columns.append({
                        'index': index,
                        'proceeds_aud': proceeds_aud,
                        'cost_basis_aud': cost_basis_aud, 
                        'capital_gain_aud': capital_gain_aud,
                        'taxable_gain_aud': taxable_gain_aud,
                        'sale_exchange_rate': sale_rate,
                        'purchase_exchange_rate': purchase_rate
                    })
                else:
                    print(f"⚠️ Could not convert row {index}: missing exchange rates")
                    
            except Exception as e:
                print(f"⚠️ Error converting row {index}: {e}")
                continue
        
        # Add AUD columns to DataFrame
        for aud_data in aud_columns:
            idx = aud_data['index']
            enhanced_df.loc[idx, 'Proceeds_AUD'] = aud_data['proceeds_aud']
            enhanced_df.loc[idx, 'Cost_Basis_AUD'] = aud_data['cost_basis_aud']
            enhanced_df.loc[idx, 'Capital_Gain_AUD'] = aud_data['capital_gain_aud']
            enhanced_df.loc[idx, 'Taxable_Gain_AUD'] = aud_data['taxable_gain_aud']
            enhanced_df.loc[idx, 'Sale_Exchange_Rate'] = aud_data['sale_exchange_rate']
            enhanced_df.loc[idx, 'Purchase_Exchange_Rate'] = aud_data['purchase_exchange_rate']
        
        print(f"✅ Converted {len(aud_columns)} transactions to AUD")
        
        return enhanced_df
    
    def create_aud_summary(self, fifo_df_aud, optimal_df_aud):
        """
        Create AUD summary for ATO reporting.
        
        Args:
            fifo_df_aud (pandas.DataFrame): FIFO results with AUD
            optimal_df_aud (pandas.DataFrame): Tax-optimal results with AUD
            
        Returns:
            dict: AUD summary for ATO reporting
        """
        print("\n🇦🇺 CREATING AUD SUMMARY FOR ATO")
        print("=" * 40)
        
        summary = {}
        
        # FIFO AUD totals
        fifo_total_gain_aud = fifo_df_aud['Capital_Gain_AUD'].sum()
        fifo_taxable_gain_aud = fifo_df_aud['Taxable_Gain_AUD'].sum()
        fifo_gains_aud = fifo_df_aud[fifo_df_aud['Capital_Gain_AUD'] > 0]['Capital_Gain_AUD'].sum()
        fifo_losses_aud = fifo_df_aud[fifo_df_aud['Capital_Gain_AUD'] < 0]['Capital_Gain_AUD'].sum()
        
        # Tax-optimal AUD totals
        optimal_total_gain_aud = optimal_df_aud['Capital_Gain_AUD'].sum()
        optimal_taxable_gain_aud = optimal_df_aud['Taxable_Gain_AUD'].sum()
        optimal_gains_aud = optimal_df_aud[optimal_df_aud['Capital_Gain_AUD'] > 0]['Capital_Gain_AUD'].sum()
        optimal_losses_aud = optimal_df_aud[optimal_df_aud['Capital_Gain_AUD'] < 0]['Capital_Gain_AUD'].sum()
        
        summary = {
            'fifo_total_gain_aud': fifo_total_gain_aud,
            'fifo_taxable_gain_aud': fifo_taxable_gain_aud,
            'fifo_gains_aud': fifo_gains_aud,
            'fifo_losses_aud': fifo_losses_aud,
            'optimal_total_gain_aud': optimal_total_gain_aud,
            'optimal_taxable_gain_aud': optimal_taxable_gain_aud,
            'optimal_gains_aud': optimal_gains_aud,
            'optimal_losses_aud': optimal_losses_aud,
            'aud_savings': fifo_taxable_gain_aud - optimal_taxable_gain_aud
        }
        
        print(f"🔄 FIFO Strategy (AUD):")
        print(f"   Total Capital Gains: ${fifo_gains_aud:,.2f} AUD")
        print(f"   Total Capital Losses: ${fifo_losses_aud:,.2f} AUD")
        print(f"   Net Capital Gain: ${fifo_total_gain_aud:,.2f} AUD")
        print(f"   Taxable Amount: ${fifo_taxable_gain_aud:,.2f} AUD")
        
        print(f"\n🎯 Tax-Optimal Strategy (AUD):")
        print(f"   Total Capital Gains: ${optimal_gains_aud:,.2f} AUD") 
        print(f"   Total Capital Losses: ${optimal_losses_aud:,.2f} AUD")
        print(f"   Net Capital Gain: ${optimal_total_gain_aud:,.2f} AUD")
        print(f"   Taxable Amount: ${optimal_taxable_gain_aud:,.2f} AUD")
        
        print(f"\n💰 AUD OPTIMIZATION BENEFIT:")
        print(f"   Reduction in Taxable Amount: ${summary['aud_savings']:,.2f} AUD")
        print(f"   🇦🇺 Report to ATO: ${optimal_taxable_gain_aud:,.2f} AUD")
        
        return summary

def test_rba_loader():
    """Test function to verify RBA data loading."""
    print("🧪 TESTING RBA EXCHANGE RATE LOADER")
    print("=" * 50)
    
    converter = RBAAUDConverter()
    
    # Test with updated file names
    rba_files = [
        "FX_2018-2022.csv",
        "FX_2023-2025.csv"
    ]
    
    converter.load_rba_csv_files(rba_files)
    
    if converter.exchange_rates:
        print(f"\n✅ Test successful!")
        print(f"📊 Loaded {len(converter.exchange_rates)} exchange rates")
        
        # Test conversion
        test_date = datetime(2024, 1, 15)
        test_amount = 1000.0
        
        aud_amount, rate = converter.convert_usd_to_aud(test_amount, test_date)
        if aud_amount:
            print(f"\n🧪 Test conversion:")
            print(f"   ${test_amount:,.2f} USD on {test_date.strftime('%Y-%m-%d')}")
            print(f"   = ${aud_amount:,.2f} AUD (rate: {rate:.4f})")
        
        return True
    else:
        print(f"❌ Test failed - no exchange rates loaded")
        return False

if __name__ == "__main__":
    test_rba_loader()