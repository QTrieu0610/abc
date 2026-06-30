"""
Fill All Gaps Script - Gold Price Historical Data
==================================================

This script fetches the last 30 days of gold price data from the API
and merges it with existing CSV data to fill any gaps.

Use this when:
- You notice missing dates in the historical data
- After a long period without updates
- To ensure data continuity

The script will:
1. Fetch data for the last 30 days
2. Merge with existing CSV (avoiding duplicates)
3. Show which dates were added

Run: python fill_all_gaps.py
"""

from data_collector import HistoricalDataCollector
from datetime import datetime, timedelta

def main():
    print("=" * 60)
    print("Filling ALL Gaps in Historical Data")
    print("=" * 60)
    
    collector = HistoricalDataCollector()
    
    # Fetch data for the last 30 days
    # This will cover all gaps between Oct 28 and today
    today = datetime.now()
    date_from = today - timedelta(days=30)
    
    date_from_str = date_from.strftime('%Y-%m-%d')
    date_to_str = today.strftime('%Y-%m-%d')
    
    print(f"\nFetching data from {date_from_str} to {date_to_str}...")
    print("This will fill any gaps in the existing data.\n")
    
    # Fetch data
    companies = ['sjc']
    missing_data = {}
    
    for company in companies:
        print(f"Fetching {company.upper()}...")
        company_data = collector.fetch_company_data(company, date_from_str, date_to_str)
        
        if company_data and 'results' in company_data:
            missing_data[company] = company_data['results']
            
            # Show unique dates
            unique_dates = set()
            for record in company_data['results']:
                if 'datetime' in record:
                    timestamp = int(record['datetime'])
                    dt = datetime.fromtimestamp(timestamp)
                    unique_dates.add(dt.strftime('%Y-%m-%d'))
            
            print(f"  [+] Got {len(company_data['results'])} records from API")
            print(f"  [+] Covering {len(unique_dates)} unique dates")
            print(f"  [+] Dates: {sorted(unique_dates)}\n")
        else:
            print(f"  [-] No data available\n")
    
    if missing_data:
        # Count existing records
        csv_file = 'historical_data/historical_gold_prices.csv'
        existing_data = collector.load_csv_data(csv_file)
        existing_count = len(existing_data)
        
        # Get existing unique dates
        existing_dates = set()
        for row in existing_data:
            timestamp = row.get('timestamp', '')
            if timestamp:
                date_part = timestamp.split(' ')[0]
                existing_dates.add(date_part)
        
        print(f"Existing data: {len(existing_data)} records covering {len(existing_dates)} dates")
        print(f"Existing dates: {sorted(existing_dates)}\n")
        
        # Merge with CSV
        print("Merging with existing data...")
        collector.append_to_csv(missing_data, csv_file)
        
        # Count after merge
        updated_data = collector.load_csv_data(csv_file)
        updated_count = len(updated_data)
        
        # Get new unique dates
        new_dates = set()
        for row in updated_data:
            timestamp = row.get('timestamp', '')
            if timestamp:
                date_part = timestamp.split(' ')[0]
                new_dates.add(date_part)
        
        dates_added = new_dates - existing_dates
        records_added = updated_count - existing_count
        
        print("\n" + "=" * 60)
        print("Update Complete!")
        print("=" * 60)
        print(f"Records added: {records_added}")
        print(f"Dates added: {len(dates_added)}")
        if dates_added:
            print(f"New dates: {sorted(dates_added)}")
        print(f"Total records now: {updated_count}")
        print(f"Total dates now: {len(new_dates)}")
        print("=" * 60)
    else:
        print("\n[-] No data fetched from API")

if __name__ == '__main__':
    main()

