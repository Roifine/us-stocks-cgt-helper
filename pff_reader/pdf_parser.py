#!/usr/bin/env python3
"""
PDF Transaction Parser for CommSec/Pershing Statements

This script reads a PDF file and extracts transaction data from the 
"Transactions in Date Sequence" section.
"""

import re
import sys
from typing import List, Dict, Optional
import argparse

try:
    import pdfplumber
    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        import PyPDF2
        PDF_LIBRARY = "PyPDF2"
    except ImportError:
        print("❌ Error: Please install a PDF library:")
        print("   pip install pdfplumber")
        print("   or")
        print("   pip install PyPDF2")
        sys.exit(1)

def extract_text_pypdf2(pdf_path: str) -> str:
    """Extract text from PDF using PyPDF2."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"❌ Error reading PDF with PyPDF2: {e}")
        return ""
    return text

def extract_text_pdfplumber(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except ImportError:
        print("❌ pdfplumber not available")
        return ""
    except Exception as e:
        print(f"❌ Error reading PDF with pdfplumber: {e}")
        return ""
    return text

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF using available library."""
    print(f"📄 Reading PDF: {pdf_path}")
    
    # Force pdfplumber if available, as it's better for complex layouts
    try:
        import pdfplumber
        print(f"🔧 Using library: pdfplumber")
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except ImportError:
        print(f"🔧 Using library: PyPDF2 (pdfplumber not available)")
        return extract_text_pypdf2(pdf_path)
    except Exception as e:
        print(f"❌ Error with pdfplumber, falling back to PyPDF2: {e}")
        return extract_text_pypdf2(pdf_path)

def parse_transactions(text: str, debug: bool = False) -> List[Dict[str, str]]:
    """
    Parse transactions from the extracted text.
    
    Expected format from "Transactions in Date Sequence":
    Date | Activity Type | Description | Quantity | Price | Accrued Interest | Amount Currency
    """
    
    transactions = []
    
    # Find the "Transactions in Date Sequence" section
    pattern = r'Transactions in Date Sequence.*?(?=\n\s*Total Value of Transactions|\n\s*Messages|\n\s*Important Information|\Z)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        print("⚠️ Could not find 'Transactions in Date Sequence' section")
        return transactions
    
    transaction_text = match.group(0)
    print(f"✅ Found transaction section ({len(transaction_text)} characters)")
    
    if debug:
        print(f"📄 Transaction section content:\n{transaction_text}")
        print("=" * 80)
    
    # Split into lines and process
    lines = transaction_text.split('\n')
    
    # Look for transaction lines (dates in MM/DD/YY format)
    date_pattern = r'(\d{2}/\d{2}/\d{2})'
    
    current_transaction = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        if debug:
            print(f"Line {i}: {line}")
            
        # Check if line starts with a date
        date_match = re.match(date_pattern, line)
        if date_match:
            # Process previous transaction if exists
            if current_transaction:
                transaction = parse_transaction_line_v2(current_transaction, debug)
                if transaction:
                    transactions.append(transaction)
            
            # Start new transaction
            current_transaction = {
                'date': date_match.group(1),
                'full_line': line,
                'additional_lines': []
            }
            if debug:
                print(f"   🔍 Found date: {date_match.group(1)}")
        elif current_transaction and line and not line.startswith('Total'):
            # Add continuation lines to current transaction
            current_transaction['additional_lines'].append(line)
            if debug:
                print(f"   ➕ Added to transaction: {line}")
    
    # Process the last transaction
    if current_transaction:
        transaction = parse_transaction_line_v2(current_transaction, debug)
        if transaction:
            transactions.append(transaction)
    
    return transactions

def parse_transaction_line_v2(transaction_data: Dict, debug: bool = False) -> Optional[Dict[str, str]]:
    """
    Parse a transaction using the improved format.
    
    Expected formats:
    08/04/21 08/02/21 PURCHASED RSKD - RISKIFIED LTD REGISTERED SHS -A- ISIN#IL0011786493 UNSOLICITED ORDER 350.000 26.8400 -9,423.95 USD
    08/13/21 08/11/21 PURCHASED FSLY - FASTLY INC CL A UNSOLICITED ORDER ALLOCATED ORDER YOUR BROKER ACTED AS AGENT 150.000 42.3000 -6,374.95 USD
    """
    
    date = transaction_data['date']
    full_line = transaction_data['full_line']
    additional_lines = transaction_data.get('additional_lines', [])
    
    # Combine all lines into one string for parsing
    complete_line = full_line + " " + " ".join(additional_lines)
    complete_line = re.sub(r'\s+', ' ', complete_line).strip()
    
    if debug:
        print(f"🔍 Parsing transaction: {complete_line}")
    
    # Extract activity type
    activity_type = "Unknown"
    if 'PURCHASED' in complete_line:
        activity_type = "PURCHASED"
    elif 'CASH DIVIDEND RECEIVED' in complete_line:
        activity_type = "CASH DIVIDEND RECEIVED"
    elif 'NON-RESIDENT ALIEN TAX' in complete_line:
        activity_type = "NON-RESIDENT ALIEN TAX"
    elif 'AGENT SERVICING FEE' in complete_line:
        activity_type = "AGENT SERVICING FEE"
    elif 'SOLD' in complete_line:
        activity_type = "SOLD"
    
    # Extract symbol - look for pattern after activity type
    symbol = ""
    if activity_type == "PURCHASED":
        # Pattern: PURCHASED SYMBOL - Company Name
        symbol_match = re.search(r'PURCHASED\s+([A-Z]{2,5})\s*-', complete_line)
        if symbol_match:
            symbol = symbol_match.group(1)
    elif 'DIVIDEND' in activity_type:
        # Look for pattern with SHRS
        symbol_match = re.search(r'(\d+)\s*SHRS\s+([A-Z]{2,5})', complete_line)
        if symbol_match:
            symbol = symbol_match.group(2)
    
    # Extract quantity - look for decimal number followed by common patterns
    quantity = ""
    quantity_patterns = [
        r'(\d+(?:\.\d+)?)\s+\d+\.\d+\s+[-]?\d+',  # quantity price amount pattern
        r'UNSOLICITED ORDER\s+(\d+(?:\.\d+)?)',    # After unsolicited order
        r'(\d+)\s*SHRS',                           # Before SHRS
        r'(\d+(?:\.\d+)?)\s+[A-Z]+\s+[-]?\d+\.\d+' # quantity symbol amount
    ]
    
    for pattern in quantity_patterns:
        qty_match = re.search(pattern, complete_line)
        if qty_match:
            quantity = qty_match.group(1)
            break
    
    # Extract price - look for price pattern before final amounts
    price = ""
    # Look for price pattern: quantity followed by price followed by amount
    price_match = re.search(r'(\d+(?:\.\d+)?)\s+(\d+\.\d+)\s+[-]?\d+', complete_line)
    if price_match:
        price = price_match.group(2)
    
    # Extract amounts - look for USD and AUD amounts
    usd_amount = ""
    aud_amount = ""
    
    # Find all amount patterns
    amount_patterns = re.findall(r'([-]?\d+(?:,\d{3})*(?:\.\d+)?)\s+(USD|AUD)', complete_line)
    
    for amount, currency in amount_patterns:
        # Remove commas from amount
        clean_amount = amount.replace(',', '')
        if currency == "USD":
            usd_amount = clean_amount
        elif currency == "AUD":
            aud_amount = clean_amount
    
    # If we don't have a symbol, try to extract it differently
    if not symbol and activity_type == "PURCHASED":
        # Look for 4-letter uppercase words
        symbol_match = re.search(r'\b([A-Z]{2,5})\b', complete_line)
        if symbol_match:
            # Skip common words
            potential_symbol = symbol_match.group(1)
            if potential_symbol not in ['PURCHASED', 'ORDER', 'SHRS', 'ISIN', 'YOUR', 'BROKER', 'ACTED', 'AGENT']:
                symbol = potential_symbol
    
    if debug:
        print(f"   Activity: {activity_type}")
        print(f"   Symbol: {symbol}")
        print(f"   Quantity: {quantity}")
        print(f"   Price: {price}")
        print(f"   USD Amount: {usd_amount}")
        print(f"   AUD Amount: {aud_amount}")
    
    if not symbol:
        print(f"⚠️ Could not extract symbol from: {complete_line[:100]}...")
        return None
    
    return {
        'date': date,
        'activity_type': activity_type,
        'symbol': symbol,
        'quantity': quantity,
        'price': price,
        'usd_amount': usd_amount,
        'aud_amount': aud_amount,
        'description': complete_line  # Keep full description for reference
    }

def print_transactions(transactions: List[Dict[str, str]]) -> None:
    """Print transactions in a formatted table."""
    
    if not transactions:
        print("❌ No transactions found")
        return
    
    print(f"\n📊 Found {len(transactions)} transactions:")
    print("=" * 130)
    print(f"{'Date':<10} {'Activity Type':<25} {'Symbol':<8} {'Qty':<12} {'Price':<10} {'USD Amount':<12} {'AUD Amount':<12}")
    print("=" * 130)
    
    for transaction in transactions:
        date = transaction['date']
        activity = transaction['activity_type'][:24]  # Truncate if too long
        symbol = transaction.get('symbol', '')[:7]
        quantity = transaction['quantity'][:11]
        price = transaction['price'][:9]
        usd_amount = transaction['usd_amount'][:11]
        aud_amount = transaction['aud_amount'][:11]
        
        print(f"{date:<10} {activity:<25} {symbol:<8} {quantity:<12} {price:<10} {usd_amount:<12} {aud_amount:<12}")
    
    print("=" * 130)
    
    # Calculate totals for AUD amounts
    total_aud = 0
    for transaction in transactions:
        if transaction['aud_amount']:
            try:
                # Remove commas and convert
                amount_str = transaction['aud_amount'].replace(',', '')
                amount = float(amount_str)
                total_aud += amount
            except ValueError:
                pass
    
    print(f"\n💰 Total AUD Amount: ${total_aud:.2f}")
    
    # Show breakdown by activity type
    activity_counts = {}
    for transaction in transactions:
        activity = transaction['activity_type']
        activity_counts[activity] = activity_counts.get(activity, 0) + 1
    
    print(f"\n📋 Transaction Types:")
    for activity, count in activity_counts.items():
        print(f"   • {activity}: {count}")
    
    # Show symbols
    symbols = set()
    for transaction in transactions:
        if transaction.get('symbol'):
            symbols.add(transaction['symbol'])
    
    if symbols:
        print(f"\n🏷️  Symbols: {', '.join(sorted(symbols))}")

def export_to_csv(transactions: List[Dict[str, str]], output_file: str) -> None:
    """Export transactions to CSV file."""
    
    if not transactions:
        print("❌ No transactions to export")
        return
    
    try:
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Date', 'Activity_Type', 'Symbol', 'Quantity', 'Price', 'USD_Amount', 'AUD_Amount', 'Description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for transaction in transactions:
                writer.writerow({
                    'Date': transaction['date'],
                    'Activity_Type': transaction['activity_type'],
                    'Symbol': transaction.get('symbol', ''),
                    'Quantity': transaction['quantity'],
                    'Price': transaction['price'],
                    'USD_Amount': transaction['usd_amount'],
                    'AUD_Amount': transaction['aud_amount'],
                    'Description': transaction['description']
                })
        
        print(f"📄 Transactions exported to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error exporting to CSV: {e}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Extract transactions from PDF statement')
    parser.add_argument('pdf_file', help='Path to the PDF file')
    parser.add_argument('--csv', help='Export to CSV file (optional)')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    
    args = parser.parse_args()
    
    print("🔍 PDF Transaction Parser")
    print("=" * 50)
    
    # Extract text from PDF
    text = extract_pdf_text(args.pdf_file)
    
    if not text:
        print("❌ Could not extract text from PDF")
        return
    
    if args.debug:
        print(f"📄 Extracted text length: {len(text)} characters")
        print(f"📄 First 500 characters:\n{text[:500]}...")
    
    # Parse transactions
    transactions = parse_transactions(text, args.debug)
    
    # Print results
    print_transactions(transactions)
    
    # Export to CSV if requested
    if args.csv:
        export_to_csv(transactions, args.csv)
    
    print(f"\n✅ Processing complete!")

if __name__ == "__main__":
    main()