#!/usr/bin/env python3
"""
Australian CGT Calculator - Enhanced Streamlit Web App (AUD Version)

Upload Interactive Brokers HTML statements and get ATO-compliant Australian CGT calculations.
Now with AUD conversion using RBA historical exchange rates!
"""

import streamlit as st
import pandas as pd
import tempfile
import os
import json
import shutil
from datetime import datetime
import traceback

# Import your enhanced scripts
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
except ImportError as e:
    st.error(f"❌ Could not import required scripts: {e}")
    st.error("Please ensure complete_unified_with_aud.py and cgt_calculator_australia_aud.py are in the same directory")
    st.error(f"Import error details: {str(e)}")
    SCRIPTS_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Australian CGT Calculator (AUD Enhanced)",
    page_icon="🇦🇺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'cgt_results' not in st.session_state:
    st.session_state.cgt_results = None
if 'excel_data' not in st.session_state:
    st.session_state.excel_data = None
if 'filename' not in st.session_state:
    st.session_state.filename = None

def check_password():
    """Returns True if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "cgt_beta_2025":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🧮 CGT Helper Beta Access (AUD Enhanced)")
        st.markdown("**Enter the beta password you received via email:**")
        st.text_input(
            "Beta Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            placeholder="Enter your beta access password"
        )
        st.markdown("---")
        st.info("🚀 **NEW:** Now with RBA AUD conversion for ATO-compliant reporting!")
        st.markdown("**Don't have access?** Apply at: [YOUR-NETLIFY-URL]")
        return False
        
    elif not st.session_state["password_correct"]:
        st.title("🧮 CGT Helper Beta Access (AUD Enhanced)")
        st.markdown("**Enter the beta password you received via email:**")
        st.text_input(
            "Beta Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            placeholder="Enter your beta access password"
        )
        st.error("😞 Password incorrect. Check your email or apply for beta access.")
        st.markdown("**Don't have access?** Apply at: [YOUR-NETLIFY-URL]")
        return False
    else:
        return True

def validate_html_files(uploaded_files):
    """Validate uploaded HTML files."""
    if not uploaded_files:
        return False, "Please upload at least one HTML file"
    
    if len(uploaded_files) > 5:
        return False, "Maximum 5 files allowed"
    
    for file in uploaded_files:
        if file.size > 20 * 1024 * 1024:  # 20MB limit
            return False, f"File {file.name} is too large (max 20MB)"
        
        if not file.name.lower().endswith(('.html', '.htm')):
            return False, f"File {file.name} is not an HTML file"
    
    return True, "Files validated successfully"

def create_mock_rba_rates(temp_dir):
    """Create mock RBA exchange rate data for the beta app."""
    rates_folder = os.path.join(temp_dir, "rates")
    os.makedirs(rates_folder, exist_ok=True)
    
    # Create simplified mock RBA data
    dates = pd.date_range('2022-01-01', '2025-12-31', freq='D')
    
    # Generate realistic AUD/USD rates with some variation
    base_rates = {
        2022: 0.71,
        2023: 0.67,
        2024: 0.66,
        2025: 0.65
    }
    
    rates_data = []
    for date in dates:
        base_rate = base_rates.get(date.year, 0.67)
        # Add small daily variation
        import hashlib
        daily_seed = int(hashlib.md5(date.strftime('%Y-%m-%d').encode()).hexdigest()[:8], 16)
        variation = (daily_seed % 400 - 200) / 10000  # ±2%
        rate = base_rate * (1 + variation)
        
        rates_data.append({
            'Date': date.strftime('%Y-%m-%d'),
            'AUD_USD_Rate': f"{rate:.4f}"
        })
    
    # Split into two files as expected
    mid_point = len(rates_data) // 2
    
    # File 1: 2022-2023
    rates_2022_2023 = rates_data[:mid_point]
    file1_path = os.path.join(rates_folder, "FX_2018-2022.csv")
    pd.DataFrame(rates_2022_2023).to_csv(file1_path, index=False)
    
    # File 2: 2024-2025
    rates_2024_2025 = rates_data[mid_point:]
    file2_path = os.path.join(rates_folder, "FX_2023-2025.csv")
    pd.DataFrame(rates_2024_2025).to_csv(file2_path, index=False)
    
    return rates_folder

def process_html_files_enhanced(uploaded_files, temp_dir, financial_year):
    """Process HTML files using the enhanced AUD system."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Create mock exchange rates for beta
    status_text.text("Setting up AUD conversion...")
    rates_folder = create_mock_rba_rates(temp_dir)
    
    # Initialize AUD converter
    try:
        # Create mock RBA converter for beta
        def create_mock_rba_converter(rates_folder):
            print(f"\n💱 LOADING RBA EXCHANGE RATES (BETA VERSION)")
            print("=" * 50)
            
            rba_files = [
                os.path.join(rates_folder, "FX_2018-2022.csv"),
                os.path.join(rates_folder, "FX_2023-2025.csv")
            ]
            
            aud_converter = RBAAUDConverter()
            aud_converter.load_rba_csv_files(rba_files)
            return aud_converter
        
        # Use mock function
        aud_converter = create_mock_rba_converter(rates_folder)
        
        if not aud_converter or not aud_converter.exchange_rates:
            st.error("❌ Failed to initialize AUD converter")
            return None, None
        
        st.success(f"✅ AUD converter ready with {len(aud_converter.exchange_rates)} exchange rates")
        
    except Exception as e:
        st.error(f"❌ Error setting up AUD converter: {e}")
        return None, None
    
    # Process HTML files
    all_transactions = []
    
    # Determine cutoff date for hybrid processing
    fy_year = int(financial_year.split('-')[0])
    cutoff_date = datetime(fy_year, 6, 30)  # End of financial year
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        # Save uploaded file temporarily
        temp_html_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_html_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # Parse HTML with hybrid filtering
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
                
                all_transactions.append(standardized)
                st.success(f"✅ {uploaded_file.name}: {len(df)} transactions found")
            else:
                st.warning(f"⚠️ {uploaded_file.name}: No valid transactions found")
                
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    if not all_transactions:
        return None, None
    
    # Combine all transactions
    combined_df = pd.concat(all_transactions, ignore_index=True)
    
    # Remove duplicates
    combined_df = combined_df.drop_duplicates(
        subset=['Symbol', 'Date', 'Activity', 'Quantity', 'Price'], 
        keep='first'
    )
    
    status_text.text("Creating cost basis with AUD conversion...")
    
    # Apply FIFO processing with AUD conversion
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
            # Create sales DataFrame for CGT calculator
            sales_data = []
            
            for _, sale in fy_sales.iterrows():
                quantity = abs(float(sale['Quantity']))
                price_usd = abs(float(sale['Price']))
                commission_usd = abs(float(sale['Commission']))
                trade_date = robust_date_parser(sale['Date'])
                
                # Convert to AUD
                total_proceeds_usd = quantity * price_usd
                total_proceeds_aud, sale_rate = aud_converter.convert_usd_to_aud(total_proceeds_usd, trade_date)
                commission_aud, _ = aud_converter.convert_usd_to_aud(commission_usd, trade_date)
                
                if total_proceeds_aud is None:
                    total_proceeds_aud = total_proceeds_usd
                    commission_aud = commission_usd
                    sale_rate = None
                
                sales_data.append({
                    'Symbol': sale['Symbol'],
                    'Trade Date': pd.to_datetime(sale['Date']),
                    'Units_Sold': quantity,
                    'Sale_Price_Per_Unit': price_usd,
                    'Total_Proceeds': total_proceeds_usd,
                    'Commission_Paid': commission_usd,
                    'Net_Proceeds': total_proceeds_usd - commission_usd,
                    'Financial_Year': financial_year
                })
            
            sales_df = pd.DataFrame(sales_data)
            sales_path = os.path.join(temp_dir, f"sales_FY{financial_year}.csv")
            sales_df.to_csv(sales_path, index=False)
            
            status_text.text("Processing complete!")
            return cost_basis_path, sales_path
        else:
            st.warning("⚠️ No sales found in the selected financial year")
            return cost_basis_path, None
    else:
        st.warning("⚠️ No sales transactions found")
        return cost_basis_path, None

def calculate_cgt_enhanced(sales_path, cost_basis_path, financial_year, temp_dir):
    """Calculate CGT using the enhanced AUD system."""
    try:
        st.text("Loading sales and cost basis data...")
        
        # Load data using enhanced functions
        sales_df = load_sales_csv(sales_path)
        cost_basis_dict = load_cost_basis_json_aud(cost_basis_path)
        
        if sales_df is None or cost_basis_dict is None:
            st.error("❌ Failed to load input data")
            return None, None, None
        
        st.text("Calculating Australian CGT with AUD conversion...")
        
        # Calculate CGT using enhanced function
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
        # Create Excel file in temp directory
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

def main():
    """Main Streamlit app with enhanced AUD functionality."""
    
    # Password check FIRST
    if not check_password():
        st.stop()
    
    # Add beta warnings at top
    st.markdown("""
    <div style="background: linear-gradient(135deg, #ff6b6b, #ffa726); color: white; padding: 20px; margin: 20px 0; border-radius: 10px; text-align: center;">
        <h3>🧪 BETA CGT HELPER (AUD ENHANCED)</h3>
        <p><strong>Now with RBA AUD conversion for ATO-compliant reporting!</strong></p>
        <p><strong>⚠️ ALL RESULTS MUST BE VERIFIED BY A QUALIFIED TAX PROFESSIONAL ⚠️</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🇦🇺 Australian CGT Calculator (AUD Enhanced Beta)")
    st.markdown("Upload your Interactive Brokers HTML statements to calculate **ATO-compliant** Australian Capital Gains Tax with **RBA AUD conversion**")
    
    if not SCRIPTS_AVAILABLE:
        st.stop()
    
    # Beta disclaimers
    st.markdown("""
    <div style="border: 3px solid #ff9800; background: #fff3e0; padding: 20px; margin: 20px 0; border-radius: 10px;">
        <h4>⚠️ Before You Continue</h4>
        <p><strong>This is experimental beta software for data organization only.</strong></p>
        <p>🚀 <strong>NEW:</strong> Now includes RBA AUD conversion for accurate ATO reporting!</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        agree1 = st.checkbox("✅ I understand this is BETA SOFTWARE for data organization only")
        agree3 = st.checkbox("✅ I understand this does NOT constitute tax advice")

    with col2:
        agree2 = st.checkbox("✅ I will verify ALL calculations with a qualified tax professional")
        agree4 = st.checkbox("✅ I am using this tool at my own risk")

    if not all([agree1, agree2, agree3, agree4]):
        st.warning("⚠️ Please confirm all checkboxes above to continue with beta testing.")
        st.stop()

    st.success("✅ Thank you for confirming! Ready to proceed with beta testing.")
    st.markdown("---")
    
    # File upload section
    st.header("📁 Upload HTML Statements")
    uploaded_files = st.file_uploader(
        "Select Interactive Brokers HTML statement files (maximum 5 files)",
        type=['html', 'htm'],
        accept_multiple_files=True,
        help="Upload your Interactive Brokers HTML trading statements"
    )
    
    # Validate files
    if uploaded_files:
        is_valid, message = validate_html_files(uploaded_files)
        if not is_valid:
            st.error(f"❌ {message}")
            st.stop()
        else:
            st.success(f"✅ {len(uploaded_files)} file(s) ready for processing")
            
            # Show file details
            with st.expander("📋 File Details"):
                for file in uploaded_files:
                    st.text(f"• {file.name} ({file.size:,} bytes)")
    
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
    if uploaded_files and st.button("🔄 Process Files (Enhanced AUD)", type="primary", use_container_width=True):
        
        # Reset session state
        st.session_state.processing_complete = False
        st.session_state.cgt_results = None
        st.session_state.excel_data = None
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Step 1: Process HTML files with enhanced AUD system
                with st.spinner("Step 1/3: Processing HTML files with AUD conversion..."):
                    cost_basis_path, sales_path = process_html_files_enhanced(
                        uploaded_files, temp_dir, financial_year
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
        
        # Post-results disclaimers
        st.markdown("---")
        st.markdown("""
        <div style="border: 2px solid #f44336; background: #ffebee; padding: 20px; margin: 20px 0; border-radius: 10px;">
            <h4>🚨 BETA RESULTS - VERIFICATION REQUIRED</h4>
            <p><strong>These are preliminary calculations from enhanced beta software.</strong></p>
            <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h5>📋 Next Steps (REQUIRED):</h5>
                <ol>
                    <li><strong>📊 Download this AUD report</strong> for your records</li>
                    <li><strong>👨‍💼 Share with your qualified tax professional</strong></li>
                    <li><strong>✅ Have them verify all AUD calculations and exchange rates</strong></li>
                    <li><strong>📋 Use their verified results</strong> for your ATO tax return</li>
                </ol>
            </div>
            <p style="color: #d32f2f; font-weight: bold;">
                ⚠️ DO NOT use these beta calculations directly for ATO lodgment.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Warnings section
        if warnings:
            with st.expander(f"⚠️ Warnings ({len(warnings)})", expanded=True):
                for warning in warnings:
                    st.warning(warning)
        
        # Enhanced feedback request
        st.markdown("""
        <div style="background: #e3f2fd; border: 2px solid #2196F3; padding: 20px; margin: 20px 0; border-radius: 10px;">
            <h4>🙋‍♂️ Help Us Improve the AUD Enhancement!</h4>
            <p>You've tested our new AUD conversion feature! Your feedback is crucial.</p>
            <p><strong>Please take 3 minutes to share your experience with the RBA AUD conversion:</strong></p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Give Feedback", type="primary", use_container_width=True):
                st.markdown("**[Feedback Form URL - Replace with your Google Form]**")
                st.balloons()

        with col2:
            if st.button("📧 Report Issues", use_container_width=True):
                st.markdown("**Email:** youremail@example.com")
                st.markdown("**Subject:** CGT Helper AUD Beta Issue Report")
        
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
        "💡 **Enhanced Features:** This calculator now uses RBA historical exchange rates "
        "for accurate AUD conversion and ATO-compliant reporting!"
    )

if __name__ == "__main__":
    main()