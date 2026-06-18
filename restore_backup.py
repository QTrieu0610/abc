"""
Restore CSV from backup
"""

import shutil
import os

def main():
    csv_file = 'historical_data/historical_gold_prices.csv'
    backup_file = 'historical_data/historical_gold_prices_backup.csv'
    
    if not os.path.exists(backup_file):
        print("❌ No backup file found!")
        print(f"   Expected: {backup_file}")
        return
    
    print("=" * 60)
    print("Restoring CSV from Backup")
    print("=" * 60)
    
    # Restore
    shutil.copy(backup_file, csv_file)
    
    print(f"✓ Restored: {csv_file}")
    print(f"✓ From:     {backup_file}")
    print("\nOriginal data has been restored!")
    print("=" * 60)

if __name__ == '__main__':
    main()

