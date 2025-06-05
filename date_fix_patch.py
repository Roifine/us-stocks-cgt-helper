#!/usr/bin/env python3
"""
Quick patch to fix date parsing issues in your existing unified_cost_basis_creator.py

Run this first, then run your main script again.
"""

import pandas as pd
import re
from datetime import datetime

def robust_date_parser(date_str):
    """
    Parse dates in multiple formats and return in DD.M.YY format.
    Handles US format dates like 12/23/2021 that were causing errors.
    """
    if not date_str or pd.isna(date_str):
        return None
    
    # Convert to string and clean
    date_str = str(date_str).strip()
    
    # List of formats to try (most common first)
    formats_to_try = [
        "%m/%d/%Y",     # 12/23/2021 (US format) - most problematic
        "%d/%m/%Y",     # 23/12/2021 (AU format)
        "%m/%d/%y",     # 12/23/21 (US format short)
        "%d/%m/%y",     # 23/12/21 (AU format short)
        "%d.%m.%y",     # 23.12.21
        "%d.%-m.%y",    # 23.12.21 (Unix style)
        "%Y-%m-%d",     # 2021-12-23 (ISO format)
        "%d-%m-%Y",     # 23-12-2021
        "%m-%d-%Y",     # 12-23-2021
    ]
    
    parsed_date = None
    
    # Try each format
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    
    # If standard parsing fails, try intelligent parsing
    if parsed_date is None:
        try:
            # Extract numbers from the string
            numbers = re.findall(r'\d+', date_str)
            if len(numbers) >= 3:
                num1, num2, num3 = int(numbers[0]), int(numbers[1]), int(numbers[2])
                
                # Smart detection of US vs AU format
                if num3 > 31:  # num3 is full year (e.g., 2021)
                    year = num3
                    # Check if it's clearly US format (month > 12)
                    if num1 > 12:  # num1 can't be month, so it's day (AU format)
                        day, month = num1, num2
                    elif num2 > 12:  # num2 can't be month, so it's day (US format)
                        month, day = num1, num2
                    else:
                        # Ambiguous - use heuristics
                        # For dates like 12/23/2021, assume US format
                        if num1 <= 12 and num2 > 12:
                            month, day = num1, num2  # US format
                        elif num1 > 12 and num2 <= 12:
                            day, month = num1, num2  # AU format
                        else:
                            # Both could be valid - default to US for ambiguous cases
                            # This handles cases like 12/23/2021
                            month, day = num1, num2
                    
                    parsed_date = datetime(year, month, day)
                    
        except (ValueError, IndexError):
            pass
    
    # Convert to DD.M.YY format if successful
    if parsed_date:
        try:
            # Format as DD.M.YY (remove leading zero from month)
            formatted_date = parsed_date.strftime("%d.%-m.%y")  # Unix style
            return formatted_date
        except ValueError:
            # Fallback for Windows (doesn't support %-m)
            formatted_date = parsed_date.strftime("%d.%m.%y")
            # Manually remove leading zero from month
            parts = formatted_date.split('.')
            if len(parts) == 3 and parts[1].startswith('0') and len(parts[1]) == 2:
                parts[1] = parts[1][1:]
            return '.'.join(parts)
    
    # If all else fails, return None
    print(f"⚠️ Could not parse date: {date_str}")
    return None

def test_problematic_dates():
    """Test the dates that were causing issues."""
    problematic_dates = [
        "12/23/2021",  # Main problematic format
        "8/4/2021",
        "8/13/2021", 
        "8/12/2021",
        "8/8/2023",
        "12/6/2021",
        "15/12/22",
        "2/6/2023",
        "1/3/2022"
    ]
    
    print("🧪 Testing problematic dates:")
    print("-" * 40)
    
    for date in problematic_dates:
        result = robust_date_parser(date)
        status = "✅" if result else "❌"
        print(f"{status} {date:<12} → {result}")
    
    print("-" * 40)

def safe_date_sort_key(date_str):
    """
    Create a sort key for dates that handles failures gracefully.
    """
    try:
        if date_str and '.' in str(date_str):
            return datetime.strptime(str(date_str), "%d.%m.%y")
        elif date_str:
            standardized = robust_date_parser(date_str)
            if standardized and '.' in standardized:
                return datetime.strptime(standardized, "%d.%m.%y")
    except:
        pass
    
    # Return a very old date as fallback
    return datetime(1900, 1, 1)

def patch_existing_csv_file(csv_file):
    """
    Patch an existing CSV file to fix date formatting issues.
    """
    try:
        print(f"🔧 Patching {csv_file}...")
        
        # Load the CSV
        df = pd.read_csv(csv_file)
        
        # Find date columns to fix
        date_columns = []
        for col in df.columns:
            if 'date' in col.lower() or 'Date' in col:
                date_columns.append(col)
        
        if not date_columns:
            print(f"   No date columns found in {csv_file}")
            return False
        
        # Fix each date column
        changes_made = False
        for col in date_columns:
            print(f"   Fixing column: {col}")
            original_values = df[col].copy()
            df[col] = df[col].apply(robust_date_parser)
            
            # Count changes
            changes = sum(1 for orig, new in zip(original_values, df[col]) if str(orig) != str(new) and new is not None)
            if changes > 0:
                print(f"   ✅ Fixed {changes} dates in column {col}")
                changes_made = True
        
        if changes_made:
            # Save the patched file
            backup_file = csv_file.replace('.csv', '_backup.csv')
            df.to_csv(backup_file, index=False)  # Create backup first
            df.to_csv(csv_file, index=False)     # Overwrite original
            print(f"   💾 Saved patched file (backup: {backup_file})")
            return True
        else:
            print(f"   No changes needed for {csv_file}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error patching {csv_file}: {e}")
        return False

def main():
    """Main function to test and optionally patch files."""
    print("🔧 DATE PARSING FIX PATCH")
    print("=" * 40)
    
    # Test the problematic dates first
    test_problematic_dates()
    
    print(f"\n💡 This patch can fix date formatting in your CSV files.")
    print(f"   It will create backups before making changes.")
    
    try:
        response = input(f"\nWould you like to patch your CSV files? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            import glob
            csv_files = glob.glob("*.csv")
            
            if not csv_files:
                print("❌ No CSV files found in current directory")
                return
            
            print(f"\n📄 Found {len(csv_files)} CSV files:")
            for file in csv_files:
                print(f"   • {file}")
            
            proceed = input(f"\nPatch all these files? (y/n): ").lower().strip()
            if proceed in ['y', 'yes']:
                patched_count = 0
                for csv_file in csv_files:
                    if patch_existing_csv_file(csv_file):
                        patched_count += 1
                
                print(f"\n✅ Patched {patched_count} files successfully!")
                print(f"💡 You can now run your unified_cost_basis_creator.py again")
            else:
                print("❌ Patching cancelled")
        else:
            print("ℹ️ No files patched. You can copy the robust_date_parser function to your script manually.")
    
    except KeyboardInterrupt:
        print(f"\n❌ Operation cancelled")

if __name__ == "__main__":
    main()