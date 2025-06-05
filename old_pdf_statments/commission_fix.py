#!/usr/bin/env python3
"""
Commission Fix for Manual Transactions

This script will:
1. Read your existing cost basis JSON file
2. Set commission to $30 for any manual transactions that have 0 commission
3. Save the updated JSON file
"""

import json
import os
from datetime import datetime

def fix_commission_in_json(json_file_path, default_commission=30.0):
    """
    Fix commission values in the cost basis JSON file.
    
    Args:
        json_file_path (str): Path to the cost basis JSON file
        default_commission (float): Default commission to apply (default: $30)
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    try:
        # Load the existing JSON file
        print(f"📄 Loading cost basis from: {json_file_path}")
        with open(json_file_path, 'r') as f:
            cost_basis_dict = json.load(f)
        
        print(f"✅ Loaded cost basis for {len(cost_basis_dict)} symbols")
        
        # Track changes
        total_records = 0
        records_changed = 0
        symbols_affected = []
        
        # Process each symbol
        for symbol, records in cost_basis_dict.items():
            symbol_changes = 0
            
            for record in records:
                total_records += 1
                
                # Check if commission is 0 or missing
                current_commission = record.get('commission', 0)
                
                if current_commission == 0 or current_commission is None:
                    # Set to default commission
                    record['commission'] = default_commission
                    records_changed += 1
                    symbol_changes += 1
                    
                    print(f"   📝 {symbol}: Set commission to ${default_commission} for {record['units']} units on {record['date']}")
            
            if symbol_changes > 0:
                symbols_affected.append(f"{symbol} ({symbol_changes} records)")
        
        # Create backup of original file
        backup_file = json_file_path.replace('.json', '_backup.json')
        with open(backup_file, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        print(f"💾 Backup saved as: {backup_file}")
        
        # Save the updated JSON file
        with open(json_file_path, 'w') as f:
            json.dump(cost_basis_dict, f, indent=2)
        
        # Summary
        print(f"\n📊 COMMISSION FIX SUMMARY:")
        print(f"=" * 50)
        print(f"Total records processed: {total_records}")
        print(f"Records updated: {records_changed}")
        print(f"Default commission applied: ${default_commission}")
        
        if symbols_affected:
            print(f"\n🏷️ Symbols affected:")
            for symbol_info in symbols_affected:
                print(f"   • {symbol_info}")
        else:
            print(f"\n✅ No records needed updating (all already had commission values)")
        
        print(f"\n✅ Updated cost basis saved to: {json_file_path}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON format in: {json_file_path}")
        return False
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return False

def fix_commission_in_unified_script():
    """
    Alternative: Patch the unified script to apply default commission during processing.
    """
    script_file = "unified_cost_basis_creator.py"
    
    try:
        with open(script_file, 'r') as f:
            content = f.read()
        
        # Look for the commission handling line in the manual data processing
        old_pattern = 'standardized[\'Commission\'] = 0  # Default to 0 if no commission column'
        new_pattern = 'standardized[\'Commission\'] = 30.0  # Default to $30 if no commission column'
        
        if old_pattern in content:
            new_content = content.replace(old_pattern, new_pattern)
            
            # Also look for the other commission assignment
            old_pattern2 = 'commission = float(row[\'Commission\']) if not pd.isna(row[\'Commission\']) else 0'
            new_pattern2 = 'commission = float(row[\'Commission\']) if not pd.isna(row[\'Commission\']) else 30.0'
            
            if old_pattern2 in new_content:
                new_content = new_content.replace(old_pattern2, new_pattern2)
            
            # Save backup
            backup_file = script_file.replace('.py', '_backup_commission.py')
            with open(backup_file, 'w') as f:
                f.write(content)
            
            # Save updated script
            with open(script_file, 'w') as f:
                f.write(new_content)
            
            print(f"✅ Patched {script_file} to use $30 default commission")
            print(f"💾 Backup saved as: {backup_file}")
            return True
        else:
            print(f"⚠️ Could not find commission patterns to patch in {script_file}")
            return False
            
    except FileNotFoundError:
        print(f"❌ Could not find {script_file}")
        return False
    except Exception as e:
        print(f"❌ Error patching script: {e}")
        return False

def find_json_files():
    """Find cost basis JSON files in the current directory."""
    json_files = []
    
    for file in os.listdir('.'):
        if file.endswith('.json') and any(keyword in file.lower() for keyword in ['cost_basis', 'unified', 'basis']):
            json_files.append(file)
    
    return sorted(json_files)

def preview_commission_changes(json_file_path, default_commission=30.0):
    """
    Preview what changes would be made without actually making them.
    """
    try:
        with open(json_file_path, 'r') as f:
            cost_basis_dict = json.load(f)
        
        print(f"🔍 PREVIEW: What would change in {json_file_path}")
        print(f"=" * 60)
        
        total_zero_commission = 0
        affected_symbols = []
        
        for symbol, records in cost_basis_dict.items():
            symbol_zero_count = 0
            
            for record in records:
                current_commission = record.get('commission', 0)
                if current_commission == 0:
                    symbol_zero_count += 1
                    total_zero_commission += 1
            
            if symbol_zero_count > 0:
                affected_symbols.append(f"{symbol}: {symbol_zero_count} records")
        
        if total_zero_commission > 0:
            print(f"📊 Found {total_zero_commission} records with $0 commission")
            print(f"💰 Would set commission to ${default_commission} for:")
            for symbol_info in affected_symbols:
                print(f"   • {symbol_info}")
        else:
            print(f"✅ No records found with $0 commission - no changes needed")
        
        return total_zero_commission > 0
        
    except Exception as e:
        print(f"❌ Error previewing file: {e}")
        return False

def main():
    """Main function to fix commission values."""
    print("💰 COMMISSION FIX FOR MANUAL TRANSACTIONS")
    print("=" * 60)
    print("This will set commission to $30 for manual transactions with $0 commission")
    print()
    
    # Find JSON files
    json_files = find_json_files()
    
    if not json_files:
        print("❌ No cost basis JSON files found in current directory")
        print("💡 Looking for files containing 'cost_basis', 'unified', or 'basis'")
        return
    
    print("📄 Found cost basis JSON files:")
    for i, file in enumerate(json_files, 1):
        print(f"   {i}. {file}")
    
    try:
        # Get user selection
        if len(json_files) == 1:
            selected_file = json_files[0]
            print(f"\n✅ Using: {selected_file}")
        else:
            choice = input(f"\nSelect file to fix (1-{len(json_files)}): ").strip()
            try:
                file_index = int(choice) - 1
                if 0 <= file_index < len(json_files):
                    selected_file = json_files[file_index]
                else:
                    print("❌ Invalid selection")
                    return
            except ValueError:
                print("❌ Please enter a number")
                return
        
        # Preview changes
        print(f"\n🔍 Previewing changes...")
        has_changes = preview_commission_changes(selected_file)
        
        if not has_changes:
            print(f"✅ No changes needed!")
            return
        
        # Get commission amount
        commission_input = input(f"\nCommission amount to apply (default: $30): ").strip()
        if commission_input:
            try:
                commission_amount = float(commission_input)
            except ValueError:
                print("❌ Invalid amount, using default $30")
                commission_amount = 30.0
        else:
            commission_amount = 30.0
        
        # Confirm changes
        confirm = input(f"\nApply ${commission_amount} commission to records with $0? (y/n): ").lower().strip()
        
        if confirm in ['y', 'yes']:
            success = fix_commission_in_json(selected_file, commission_amount)
            
            if success:
                print(f"\n🎉 SUCCESS!")
                print(f"✅ Commission values updated in: {selected_file}")
                print(f"💾 Backup created for safety")
                print(f"💡 Your cost basis dictionary is now ready with proper commission values")
            else:
                print(f"\n❌ Failed to update commission values")
        else:
            print(f"❌ Operation cancelled")
    
    except KeyboardInterrupt:
        print(f"\n❌ Operation cancelled")

if __name__ == "__main__":
    main()