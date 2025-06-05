#!/usr/bin/env python3
"""
Quick fix for the sorting error in unified_cost_basis_creator.py

Replace the problematic sorting function with this robust version.
"""

from datetime import datetime
import pandas as pd
import re

def safe_date_sort_key(date_str):
    """
    Create a sort key for dates that handles multiple formats safely.
    Works with both the original formats and the patched DD.M.YY format.
    """
    if not date_str or pd.isna(date_str):
        return datetime(1900, 1, 1)
    
    # Convert to string and clean
    date_str = str(date_str).strip()
    
    # List of formats to try (most common patched format first)
    formats_to_try = [
        "%d.%m.%y",     # 23.12.21 (patched format)
        "%d.%-m.%y",    # 23.12.21 (Unix style)
        "%d/%m/%y",     # 23/12/21 (original format)
        "%d/%-m/%y",    # 23/12/21 (Unix style)
        "%m/%d/%Y",     # 12/23/2021 (US format)
        "%d/%m/%Y",     # 23/12/2021 (AU format)
        "%Y-%m-%d",     # 2021-12-23 (ISO format)
    ]
    
    # Try each format
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, try intelligent parsing
    try:
        # Extract numbers from the string
        numbers = re.findall(r'\d+', date_str)
        if len(numbers) >= 3:
            num1, num2, num3 = int(numbers[0]), int(numbers[1]), int(numbers[2])
            
            # Determine which is year, month, day
            if num3 > 31:  # num3 is full year
                year = num3
                day, month = num1, num2  # Assume DD/MM/YYYY format
            elif num1 > 31:  # num1 is full year
                year = num1
                day, month = num3, num2
            elif num2 > 31:  # num2 is full year
                year = num2
                day, month = num1, num3
            else:  # All <= 31, assume num3 is 2-digit year
                year = 2000 + num3 if num3 < 50 else 1900 + num3
                day, month = num1, num2
            
            return datetime(year, month, day)
    except:
        pass
    
    # Return fallback date if all parsing fails
    print(f"⚠️ Could not parse date for sorting: {date_str}")
    return datetime(1900, 1, 1)

def test_date_sorting():
    """Test the date sorting function."""
    test_dates = [
        "23.12.21",    # Patched format
        "1.5.24",      # Patched format
        "23/12/21",    # Original format
        "12/23/2021",  # US format
        "2021-12-23",  # ISO format
    ]
    
    print("🧪 Testing date sorting:")
    for date in test_dates:
        result = safe_date_sort_key(date)
        print(f"   {date:<12} → {result.strftime('%Y-%m-%d')}")
    
    # Test sorting
    sorted_dates = sorted(test_dates, key=safe_date_sort_key)
    print(f"\n📅 Sorted order:")
    for date in sorted_dates:
        parsed = safe_date_sort_key(date)
        print(f"   {date} ({parsed.strftime('%Y-%m-%d')})")

def patch_unified_script():
    """
    Patch the unified_cost_basis_creator.py file to fix the sorting issue.
    """
    script_file = "unified_cost_basis_creator.py"
    
    try:
        # Read the original script
        with open(script_file, 'r') as f:
            content = f.read()
        
        # Find the problematic line
        old_line = 'cost_basis_dict[symbol].sort(key=lambda x: datetime.strptime(x[\'date\'], "%d/%m/%y"))'
        new_line = 'cost_basis_dict[symbol].sort(key=lambda x: safe_date_sort_key(x[\'date\']))'
        
        if old_line in content:
            print(f"✅ Found problematic sorting line")
            
            # Add the safe_date_sort_key function at the top of the file
            # Find where to insert it (after imports)
            import_end = content.find('\ndef ')
            if import_end == -1:
                import_end = content.find('\nclass ')
            if import_end == -1:
                import_end = content.find('\n\n')
            
            if import_end != -1:
                # Insert the function definition
                function_def = '''
def safe_date_sort_key(date_str):
    """
    Create a sort key for dates that handles multiple formats safely.
    Works with both the original formats and the patched DD.M.YY format.
    """
    if not date_str or pd.isna(date_str):
        return datetime(1900, 1, 1)
    
    # Convert to string and clean
    date_str = str(date_str).strip()
    
    # List of formats to try (most common patched format first)
    formats_to_try = [
        "%d.%m.%y",     # 23.12.21 (patched format)
        "%d.%-m.%y",    # 23.12.21 (Unix style)
        "%d/%m/%y",     # 23/12/21 (original format)
        "%d/%-m/%y",    # 23/12/21 (Unix style)
        "%m/%d/%Y",     # 12/23/2021 (US format)
        "%d/%m/%Y",     # 23/12/2021 (AU format)
        "%Y-%m-%d",     # 2021-12-23 (ISO format)
    ]
    
    # Try each format
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, try intelligent parsing
    try:
        # Extract numbers from the string
        numbers = re.findall(r'\\d+', date_str)
        if len(numbers) >= 3:
            num1, num2, num3 = int(numbers[0]), int(numbers[1]), int(numbers[2])
            
            # Determine which is year, month, day
            if num3 > 31:  # num3 is full year
                year = num3
                day, month = num1, num2  # Assume DD/MM/YYYY format
            elif num1 > 31:  # num1 is full year
                year = num1
                day, month = num3, num2
            elif num2 > 31:  # num2 is full year
                year = num2
                day, month = num1, num3
            else:  # All <= 31, assume num3 is 2-digit year
                year = 2000 + num3 if num3 < 50 else 1900 + num3
                day, month = num1, num2
            
            return datetime(year, month, day)
    except:
        pass
    
    # Return fallback date if all parsing fails
    return datetime(1900, 1, 1)

'''
                
                # Insert the function
                new_content = content[:import_end] + function_def + content[import_end:]
                
                # Replace the problematic line
                new_content = new_content.replace(old_line, new_line)
                
                # Create backup
                backup_file = script_file.replace('.py', '_backup.py')
                with open(backup_file, 'w') as f:
                    f.write(content)
                
                # Save patched file
                with open(script_file, 'w') as f:
                    f.write(new_content)
                
                print(f"✅ Patched {script_file} successfully!")
                print(f"💾 Backup saved as: {backup_file}")
                print(f"🎯 Fixed the date sorting issue")
                return True
            else:
                print(f"❌ Could not find appropriate place to insert function")
                return False
        else:
            print(f"❌ Could not find the problematic line in the script")
            print(f"💡 The line might have already been fixed or the script has changed")
            return False
    
    except FileNotFoundError:
        print(f"❌ Could not find {script_file}")
        print(f"💡 Make sure you're in the right directory")
        return False
    except Exception as e:
        print(f"❌ Error patching script: {e}")
        return False

def manual_instructions():
    """Provide manual instructions if automatic patching fails."""
    print(f"\n📋 MANUAL INSTRUCTIONS:")
    print(f"=" * 50)
    print(f"If automatic patching failed, you can fix this manually:")
    print(f"")
    print(f"1. Open your unified_cost_basis_creator.py file")
    print(f"2. Find this line:")
    print(f"   cost_basis_dict[symbol].sort(key=lambda x: datetime.strptime(x['date'], \"%d/%m/%y\"))")
    print(f"")
    print(f"3. Replace it with:")
    print(f"   cost_basis_dict[symbol].sort(key=lambda x: safe_date_sort_key(x['date']))")
    print(f"")
    print(f"4. Add the safe_date_sort_key function at the top of your file")
    print(f"   (Copy it from the code I provided above)")
    print(f"")
    print(f"5. Make sure you have this import at the top:")
    print(f"   import re")

def main():
    """Main function."""
    print("🔧 UNIFIED SCRIPT DATE SORTING FIX")
    print("=" * 50)
    print("This will fix the date sorting error in your unified_cost_basis_creator.py")
    print()
    
    # Test the date sorting function first
    test_date_sorting()
    
    try:
        print(f"\n🔧 Ready to patch your unified_cost_basis_creator.py script")
        response = input(f"Proceed with automatic patching? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            if patch_unified_script():
                print(f"\n🎉 SUCCESS!")
                print(f"✅ Your unified_cost_basis_creator.py has been patched")
                print(f"✅ You can now run it again without date sorting errors")
                print(f"💡 The script will now handle both old and new date formats")
            else:
                manual_instructions()
        else:
            print(f"ℹ️ Automatic patching cancelled")
            manual_instructions()
    
    except KeyboardInterrupt:
        print(f"\n❌ Operation cancelled")

if __name__ == "__main__":
    main()