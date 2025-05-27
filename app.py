#!/usr/bin/env python3
"""
Australian CGT Calculator - Streamlit Web App

Upload Interactive Brokers HTML statements and get optimized Australian CGT calculations.
"""

import streamlit as st
import pandas as pd
import tempfile
import os
import json
from datetime import datetime
import traceback

# Import your existing scripts
try:
    from html_to_cost_basis import (
        parse_ib_html_to_csv, 
        create_cost_basis_dictionary_from_csv,
        create_cgt_analysis_sheets,
        get_financial_year_dates
    )
    from cgt_calculator_australia import (
        calculate_australian_cgt,
        save_cgt_excel
    )
    SCRIPTS_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ Could not import required scripts: {e}")
    st.error("Please ensure html_to_cost_basis.py and cgt_calculator_australia.py are in the same directory")
    SCRIPTS_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Australian CGT Calculator",
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

def process_html_to_csv(uploaded_files, temp_dir):
    """Process HTML files to CSV format."""
    csv_files = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        # Save uploaded file temporarily
        temp_html_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_html_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Parse HTML to CSV
        csv_output_path = os.path.join(temp_dir, f"{os.path.splitext(uploaded_file.name)[0]}_parsed.csv")
        
        try:
            df = parse_ib_html_to_csv(temp_html_path, csv_output_path)
            if df is not None and len(df) > 0:
                csv_files.append(csv_output_path)
                st.success(f"✅ {uploaded_file.name}: {len(df)} transactions found")
            else:
                st.warning(f"⚠️ {uploaded_file.name}: No valid transactions found")
        except Exception as e:
            st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text("HTML processing complete!")
    return csv_files

def create_cost_basis_and_sales(csv_files, financial_year, temp_dir):
    """Create cost basis dictionary and sales data."""
    try:
        # Create cost basis dictionary
        st.text("Creating cost basis dictionary...")
        cost_basis_dict = create_cost_basis_dictionary_from_csv(csv_files, financial_year)
        
        if not cost_basis_dict:
            st.error("❌ Failed to create cost basis dictionary")
            return None, None, None
        
        # Save cost basis to temp file
        cost_basis_path = os.path.join(temp_dir, f"cost_basis_dictionary_FY{financial_year}.json")
        with open(cost_basis_path, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        
        # Create sales data
        st.text("Creating sales data...")
        sales_df = create_cgt_analysis_sheets(csv_files, cost_basis_dict, financial_year)
        
        if sales_df is None or len(sales_df) == 0:
            st.warning("⚠️ No sales transactions found for the selected financial year")
            return cost_basis_dict, None, cost_basis_path
        
        # Save sales data to temp file
        sales_path = os.path.join(temp_dir, f"CGT_Sales_FY{financial_year}.csv")
        sales_df.to_csv(sales_path, index=False)
        
        return cost_basis_dict, sales_df, cost_basis_path, sales_path
        
    except Exception as e:
        st.error(f"❌ Error creating cost basis: {str(e)}")
        return None, None, None

def calculate_cgt_optimized(sales_df, cost_basis_dict, financial_year):
    """Calculate optimized Australian CGT."""
    try:
        st.text("Calculating Australian CGT with tax optimization...")
        
        # Calculate CGT using your existing function
        cgt_df, remaining_cost_basis, warnings_list = calculate_australian_cgt(
            sales_df, cost_basis_dict
        )
        
        if cgt_df is None or len(cgt_df) == 0:
            st.error("❌ No CGT calculations generated")
            return None, None, None
        
        return cgt_df, remaining_cost_basis, warnings_list
        
    except Exception as e:
        st.error(f"❌ Error calculating CGT: {str(e)}")
        st.error(f"Details: {traceback.format_exc()}")
        return None, None, None

def create_excel_download(cgt_df, financial_year, temp_dir):
    """Create Excel file for download."""
    try:
        # Create Excel file in temp directory
        excel_path = os.path.join(temp_dir, f"Australian_CGT_Report_FY{financial_year}.xlsx")
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Main CGT sheet
            cgt_df.to_excel(writer, sheet_name='CGT_Calculations', index=False)
            
            # Summary sheet
            total_gain = cgt_df['Capital_Gain_Loss'].sum()
            taxable_gain = cgt_df['Taxable_Gain'].sum()
            long_term_gains = cgt_df[cgt_df['Long_Term_Eligible'] == True]['Capital_Gain_Loss'].sum()
            short_term_gains = cgt_df[cgt_df['Long_Term_Eligible'] == False]['Capital_Gain_Loss'].sum()
            
            summary_data = {
                'Metric': ['Total Capital Gains', 'Total Taxable Gains', 'Long Term Gains', 'Short Term Gains', 'Financial Year'],
                'Value': [total_gain, taxable_gain, long_term_gains, short_term_gains, financial_year]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Warnings sheet (if any)
            warnings_data = cgt_df[cgt_df['Warning'] != '']
            if len(warnings_data) > 0:
                warnings_data.to_excel(writer, sheet_name='Warnings', index=False)
        
        # Read file for download
        with open(excel_path, 'rb') as f:
            excel_data = f.read()
        
        return excel_data, f"Australian_CGT_Report_FY{financial_year}.xlsx"
        
    except Exception as e:
        st.error(f"❌ Error creating Excel file: {str(e)}")
        return None, None

def main():
    """Main Streamlit app."""
    
    # Header
    st.title("🇦🇺 Australian CGT Calculator")
    st.markdown("Upload your Interactive Brokers HTML statements to calculate optimized Australian Capital Gains Tax")
    
    if not SCRIPTS_AVAILABLE:
        st.stop()
    
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
        st.info(f"Processing sales from FY {financial_year}")
    
    # Processing section
    if uploaded_files and st.button("🔄 Process Files", type="primary", use_container_width=True):
        
        # Reset session state
        st.session_state.processing_complete = False
        st.session_state.cgt_results = None
        st.session_state.excel_data = None
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Step 1: Process HTML files to CSV
                with st.spinner("Step 1/4: Processing HTML files..."):
                    csv_files = process_html_to_csv(uploaded_files, temp_dir)
                
                if not csv_files:
                    st.error("❌ No valid CSV files created from HTML files")
                    st.stop()
                
                # Step 2: Create cost basis and sales data
                with st.spinner("Step 2/4: Creating cost basis dictionary..."):
                    result = create_cost_basis_and_sales(csv_files, financial_year, temp_dir)
                    
                    if len(result) == 3:  # No sales found
                        cost_basis_dict, sales_df, cost_basis_path = result
                        st.warning("⚠️ No sales transactions found for the selected financial year")
                        st.info("This might mean:")
                        st.info("• No sales occurred in the selected financial year")
                        st.info("• Try selecting a different financial year")
                        st.stop()
                    else:
                        cost_basis_dict, sales_df, cost_basis_path, sales_path = result
                
                # Step 3: Calculate CGT
                with st.spinner("Step 3/4: Calculating optimized CGT..."):
                    cgt_df, remaining_cost_basis, warnings_list = calculate_cgt_optimized(
                        sales_df, cost_basis_dict, financial_year
                    )
                
                if cgt_df is None:
                    st.error("❌ CGT calculation failed")
                    st.stop()
                
                # Step 4: Create Excel file
                with st.spinner("Step 4/4: Creating Excel report..."):
                    excel_data, filename = create_excel_download(cgt_df, financial_year, temp_dir)
                
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
                
                st.success("✅ Processing complete!")
                
            except Exception as e:
                st.error(f"❌ Processing failed: {str(e)}")
                st.error("Please check your HTML files and try again")
                if st.checkbox("Show debug information"):
                    st.code(traceback.format_exc())
    
    # Results section
    if st.session_state.processing_complete and st.session_state.cgt_results:
        st.header("📊 Results")
        
        cgt_df = st.session_state.cgt_results['cgt_df']
        warnings = st.session_state.cgt_results['warnings']
        
        # Summary metrics
        total_gain = cgt_df['Capital_Gain_Loss'].sum()
        taxable_gain = cgt_df['Taxable_Gain'].sum()
        long_term_count = len(cgt_df[cgt_df['Long_Term_Eligible'] == True])
        short_term_count = len(cgt_df) - long_term_count
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Capital Gains",
                f"${total_gain:,.2f}",
                help="Total capital gains/losses before CGT discount"
            )
        
        with col2:
            st.metric(
                "Taxable Gains",
                f"${taxable_gain:,.2f}",
                help="Taxable gains after 50% CGT discount applied"
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
        
        # Download section
        st.header("⬇️ Download Report")
        
        if st.session_state.excel_data and st.session_state.filename:
            st.download_button(
                label="📊 Download Australian CGT Report (Excel)",
                data=st.session_state.excel_data,
                file_name=st.session_state.filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.success("✅ Your CGT report is ready for download!")
            st.info("💡 This Excel file contains detailed CGT calculations formatted for Australian tax reporting")
        
        # Warnings section
        if warnings:
            with st.expander(f"⚠️ Warnings ({len(warnings)})", expanded=True):
                for warning in warnings:
                    st.warning(warning)
        
        # Optional: Show detailed data
        if st.checkbox("Show detailed CGT calculations"):
            st.subheader("Detailed CGT Calculations")
            st.dataframe(
                cgt_df[[
                    'Symbol', 'Sale_Date', 'Units_Sold', 'Sale_Price_Per_Unit',
                    'Buy_Date', 'Days_Held', 'Capital_Gain_Loss', 'Taxable_Gain',
                    'Long_Term_Eligible', 'CGT_Discount_Applied'
                ]],
                use_container_width=True
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "💡 **Tips:** This calculator optimizes your CGT by prioritizing long-term holdings "
        "and highest cost basis purchases to minimize your tax liability."
    )

if __name__ == "__main__":
    main()