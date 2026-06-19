"""
Historical Gold Price Data Collector
Fetches and stores historical gold price data from all companies
"""

import requests
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import threading

# Module level re-entrant lock for thread-safe CSV reads/writes
csv_lock = threading.RLock()

try:
    from config import API_KEY
except ImportError:
    API_KEY = None


class HistoricalDataCollector:
    """Collect and store historical gold price data"""
    
    BASE_URL = "https://vapi.vnappmob.com"
    DATA_DIR = "historical_data"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or API_KEY
        self.headers = {
            'Accept': 'application/json'
        }
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)
    
    def fetch_company_data(self, company: str, date_from: str, date_to: str) -> Optional[Dict]:
        """
        Fetch data for a specific company and date range

        Args:
            company: Company name (sjc only)
            date_from: Date string in format 'YYYY-MM-DD'
            date_to: Date string in format 'YYYY-MM-DD'

        Returns:
            JSON response from API
        """
        url = f"{self.BASE_URL}/api/v2/gold/{company.lower()}"

        # Convert date strings to Unix timestamps (API requires integers)
        from datetime import datetime
        date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')

        # Add one day to date_to to include the entire day
        date_to_dt = date_to_dt + timedelta(days=1)

        params = {
            'date_from': int(date_from_dt.timestamp()),
            'date_to': int(date_to_dt.timestamp())
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {company} data: {e}")
            return None
    
    def collect_current_prices(self) -> Dict[str, Dict]:
        """
        Collect current prices from all configured crawler sources.
        """
        print(f"Collecting current gold prices via Multi-Source Crawler...")
        
        try:
            from ai_crawler_engine import MultiSourceGoldCrawler
            crawler = MultiSourceGoldCrawler(use_ai_fallback=True)
            result = crawler.execute_crawling()

            if result:
                for source, payload in result.items():
                    status = payload.get('status') if isinstance(payload, dict) else 'unknown'
                    count = len(payload.get('results', [])) if isinstance(payload, dict) else 0
                    print(f"  [{status}] {source.upper()}: {count} records")
                return result

            print(f"  [-] Multi-Source Crawler returned no data")
            return {
                'sjc': {'status': 'failed', 'results': [], 'error': 'No data'},
                'doji': {'status': 'failed', 'results': [], 'error': 'No data'},
                'pnj': {'status': 'failed', 'results': [], 'error': 'No data'}
            }
                
        except Exception as e:
            print(f"  [-] Error running AI Crawler: {e}")
            return {
                'sjc': {'status': 'failed', 'results': [], 'error': str(e)},
                'doji': {'status': 'failed', 'results': [], 'error': str(e)},
                'pnj': {'status': 'failed', 'results': [], 'error': str(e)}
            }

    def collect_historical_data(self, days_back: int = 365) -> Dict[str, List[Dict]]:
        """
        Collect historical data for all companies with a single query per company

        Args:
            days_back: Number of days to go back (default: 365 for one year)

        Returns:
            Dictionary with company names as keys and list of price records as values
        """
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days_back)

        date_from_str = date_from.strftime('%Y-%m-%d')
        date_to_str = date_to.strftime('%Y-%m-%d')

        print("=" * 60)
        print(f"Collecting historical data")
        print(f"Date range: {date_from_str} to {date_to_str}")
        print(f"Total days: {days_back}")
        print("=" * 60)
        print()

        companies = ['sjc']  # DOJI and PNJ removed
        all_data = {company: [] for company in companies}

        # Query once per company for the entire date range
        for company in companies:
            print(f"Fetching {company.upper()} data...")

            # Single query for entire date range
            data = self.fetch_company_data(company, date_from_str, date_to_str)

            if data and 'results' in data and len(data['results']) > 0:
                all_data[company] = data['results']
                print(f"  [+] Collected {len(data['results'])} records")
            else:
                print(f"  [-] No data returned")

            # Small delay between companies
            time.sleep(0.5)

        # Summary
        print("\n" + "=" * 60)
        print("Data collection complete!")
        for company in companies:
            print(f"  {company.upper()}: {len(all_data[company])} total records")
        print("=" * 60)

        return all_data
    
    def save_to_csv(self, data: Dict[str, List[Dict]], filename: Optional[str] = None):
        """
        Save collected data to CSV file
        
        Args:
            data: Dictionary with company data
            filename: Optional custom filename (default: historical_gold_prices.csv)
        """
        if filename is None:
            filename = os.path.join(self.DATA_DIR, 'historical_gold_prices.csv')
        
        # Prepare rows for CSV
        rows = []
        
        for company, records in data.items():
            records = self._extract_records(records)
            for record in records:
                # Extract timestamp from API response
                # API provides Unix timestamp in 'datetime' field
                if 'datetime' in record:
                    try:
                        unix_timestamp = int(record['datetime'])
                        timestamp_dt = datetime.fromtimestamp(unix_timestamp)
                        timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')

                        # Skip old data (before 2024)
                        if timestamp_dt.year < 2024:
                            continue
                    except (ValueError, TypeError):
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if self._is_normalized_price_row(record):
                    rows.append(self._normalized_record_to_csv_row(record, timestamp))
                    continue

                # Create a row with all available price types
                if company == 'sjc':
                    # SJC has 7 gold types - save ALL of them

                    # 1. SJC 1L (1 Lượng)
                    if record.get('buy_1l') or record.get('sell_1l'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC 1L',
                            'buy_price': record.get('buy_1l'),
                            'sell_price': record.get('sell_1l'),
                            'location': 'National'
                        })

                    # SJC 5C and 1C removed per user request

                    # 2. SJC Ring 1C (Nhẫn 1 Chỉ)
                    if record.get('buy_nhan1c') or record.get('sell_nhan1c'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Ring 1C',
                            'buy_price': record.get('buy_nhan1c'),
                            'sell_price': record.get('sell_nhan1c'),
                            'location': 'National'
                        })

                    # 3. SJC Jewelry 24K (Nữ Trang 9999)
                    if record.get('buy_nutrang_9999') or record.get('sell_nutrang_9999'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Jewelry 24K',
                            'buy_price': record.get('buy_nutrang_9999'),
                            'sell_price': record.get('sell_nutrang_9999'),
                            'location': 'National'
                        })

                    # 4. SJC Jewelry 99% (Nữ Trang 99)
                    if record.get('buy_nutrang_99') or record.get('sell_nutrang_99'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Jewelry 99%',
                            'buy_price': record.get('buy_nutrang_99'),
                            'sell_price': record.get('sell_nutrang_99'),
                            'location': 'National'
                        })

                    # 5. SJC Jewelry 18K (Nữ Trang 75)
                    if record.get('buy_nutrang_75') or record.get('sell_nutrang_75'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Jewelry 18K',
                            'buy_price': record.get('buy_nutrang_75'),
                            'sell_price': record.get('sell_nutrang_75'),
                            'location': 'National'
                        })
                
                elif company == 'doji':
                    if self._is_normalized_price_row(record):
                        rows.append(self._normalized_record_to_csv_row(record, timestamp))
                        continue

                    # DOJI has 4 locations - save ALL of them

                    # 1. Ho Chi Minh City
                    if record.get('buy_hcm') or record.get('sell_hcm'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_hcm'),
                            'sell_price': record.get('sell_hcm'),
                            'location': 'Ho Chi Minh City'
                        })

                    # 2. Hanoi
                    if record.get('buy_hn') or record.get('sell_hn'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_hn'),
                            'sell_price': record.get('sell_hn'),
                            'location': 'Hanoi'
                        })

                    # 3. Can Tho
                    if record.get('buy_ct') or record.get('sell_ct'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_ct'),
                            'sell_price': record.get('sell_ct'),
                            'location': 'Can Tho'
                        })

                    # 4. Da Nang
                    if record.get('buy_dn') or record.get('sell_dn'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_dn'),
                            'sell_price': record.get('sell_dn'),
                            'location': 'Da Nang'
                        })
                
                elif company == 'pnj':
                    # PNJ has 5 jewelry types - save ALL of them

                    # 1. PNJ 24K Ring (Nhẫn 24K)
                    if record.get('buy_nhan_24k') or record.get('sell_nhan_24k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 24K Ring',
                            'buy_price': record.get('buy_nhan_24k'),
                            'sell_price': record.get('sell_nhan_24k'),
                            'location': 'National'
                        })

                    # 2. PNJ 24K Jewelry (Nữ Trang 24K)
                    if record.get('buy_nt_24k') or record.get('sell_nt_24k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 24K Jewelry',
                            'buy_price': record.get('buy_nt_24k'),
                            'sell_price': record.get('sell_nt_24k'),
                            'location': 'National'
                        })

                    # 3. PNJ 18K Jewelry (Nữ Trang 18K)
                    if record.get('buy_nt_18k') or record.get('sell_nt_18k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 18K Jewelry',
                            'buy_price': record.get('buy_nt_18k'),
                            'sell_price': record.get('sell_nt_18k'),
                            'location': 'National'
                        })

                    # 4. PNJ 14K Jewelry (Nữ Trang 14K)
                    if record.get('buy_nt_14k') or record.get('sell_nt_14k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 14K Jewelry',
                            'buy_price': record.get('buy_nt_14k'),
                            'sell_price': record.get('sell_nt_14k'),
                            'location': 'National'
                        })

                    # 5. PNJ 10K Jewelry (Nữ Trang 10K)
                    if record.get('buy_nt_10k') or record.get('sell_nt_10k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 10K Jewelry',
                            'buy_price': record.get('buy_nt_10k'),
                            'sell_price': record.get('sell_nt_10k'),
                            'location': 'National'
                        })
        
        # Write to CSV
        if rows:
            fieldnames = ['timestamp', 'company', 'gold_type', 'buy_price', 'sell_price', 'location']
            with csv_lock:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            
            print(f"\n[+] Data saved to {filename}")
            print(f"  Total records: {len(rows)}")
        else:
            print("\n[-] No data to save")
    
    def append_to_csv(self, data: Dict[str, List[Dict]], filename: Optional[str] = None):
        """
        Append new data to existing CSV file

        Args:
            data: Dictionary with company data
            filename: Optional custom filename
        """
        if filename is None:
            filename = os.path.join(self.DATA_DIR, 'historical_gold_prices.csv')

        # Prepare rows for CSV (same logic as save_to_csv - ALL gold types)
        rows = []

        for company, records in data.items():
            records = self._extract_records(records)
            for record in records:
                # Extract timestamp from API response
                if 'datetime' in record:
                    try:
                        unix_timestamp = int(record['datetime'])
                        timestamp_dt = datetime.fromtimestamp(unix_timestamp)
                        timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')

                        # Skip old data (before 2024)
                        if timestamp_dt.year < 2024:
                            continue
                    except (ValueError, TypeError):
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if self._is_normalized_price_row(record):
                    rows.append(self._normalized_record_to_csv_row(record, timestamp))
                    continue

                # Create rows based on company type
                if company == 'sjc':
                    # 1. SJC 1L (1 Lượng)
                    if record.get('buy_1l') or record.get('sell_1l'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC 1L',
                            'buy_price': record.get('buy_1l'),
                            'sell_price': record.get('sell_1l'),
                            'location': 'National'
                        })

                    # 2. SJC Ring 1C (Nhẫn 1 Chỉ)
                    if record.get('buy_nhan1c') or record.get('sell_nhan1c'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Ring 1C',
                            'buy_price': record.get('buy_nhan1c'),
                            'sell_price': record.get('sell_nhan1c'),
                            'location': 'National'
                        })

                    # 3. SJC Jewelry 24K (Nữ Trang 9999)
                    if record.get('buy_nutrang_9999') or record.get('sell_nutrang_9999'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Jewelry 24K',
                            'buy_price': record.get('buy_nutrang_9999'),
                            'sell_price': record.get('sell_nutrang_9999'),
                            'location': 'National'
                        })

                    # 4. SJC Jewelry 99% (Nữ Trang 99)
                    if record.get('buy_nutrang_99') or record.get('sell_nutrang_99'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Jewelry 99%',
                            'buy_price': record.get('buy_nutrang_99'),
                            'sell_price': record.get('sell_nutrang_99'),
                            'location': 'National'
                        })

                    # 5. SJC Jewelry 18K (Nữ Trang 75)
                    if record.get('buy_nutrang_75') or record.get('sell_nutrang_75'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'SJC',
                            'gold_type': 'SJC Jewelry 18K',
                            'buy_price': record.get('buy_nutrang_75'),
                            'sell_price': record.get('sell_nutrang_75'),
                            'location': 'National'
                        })

                elif company == 'doji':
                    if self._is_normalized_price_row(record):
                        rows.append(self._normalized_record_to_csv_row(record, timestamp))
                        continue

                    # DOJI has 4 locations - save ALL of them

                    # 1. Ho Chi Minh City
                    if record.get('buy_hcm') or record.get('sell_hcm'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_hcm'),
                            'sell_price': record.get('sell_hcm'),
                            'location': 'Ho Chi Minh City'
                        })

                    # 2. Hanoi
                    if record.get('buy_hn') or record.get('sell_hn'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_hn'),
                            'sell_price': record.get('sell_hn'),
                            'location': 'Hanoi'
                        })

                    # 3. Can Tho
                    if record.get('buy_ct') or record.get('sell_ct'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_ct'),
                            'sell_price': record.get('sell_ct'),
                            'location': 'Can Tho'
                        })

                    # 4. Da Nang
                    if record.get('buy_dn') or record.get('sell_dn'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'DOJI',
                            'gold_type': 'Gold Bar',
                            'buy_price': record.get('buy_dn'),
                            'sell_price': record.get('sell_dn'),
                            'location': 'Da Nang'
                        })

                elif company == 'pnj':
                    # PNJ has 5 jewelry types - save ALL of them

                    # 1. PNJ 24K Ring (Nhẫn 24K)
                    if record.get('buy_nhan_24k') or record.get('sell_nhan_24k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 24K Ring',
                            'buy_price': record.get('buy_nhan_24k'),
                            'sell_price': record.get('sell_nhan_24k'),
                            'location': 'National'
                        })

                    # 2. PNJ 24K Jewelry (Nữ Trang 24K)
                    if record.get('buy_nt_24k') or record.get('sell_nt_24k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 24K Jewelry',
                            'buy_price': record.get('buy_nt_24k'),
                            'sell_price': record.get('sell_nt_24k'),
                            'location': 'National'
                        })

                    # 3. PNJ 18K Jewelry (Nữ Trang 18K)
                    if record.get('buy_nt_18k') or record.get('sell_nt_18k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 18K Jewelry',
                            'buy_price': record.get('buy_nt_18k'),
                            'sell_price': record.get('sell_nt_18k'),
                            'location': 'National'
                        })

                    # 4. PNJ 14K Jewelry (Nữ Trang 14K)
                    if record.get('buy_nt_14k') or record.get('sell_nt_14k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 14K Jewelry',
                            'buy_price': record.get('buy_nt_14k'),
                            'sell_price': record.get('sell_nt_14k'),
                            'location': 'National'
                        })

                    # 5. PNJ 10K Jewelry (Nữ Trang 10K)
                    if record.get('buy_nt_10k') or record.get('sell_nt_10k'):
                        rows.append({
                            'timestamp': timestamp,
                            'company': 'PNJ',
                            'gold_type': 'PNJ 10K Jewelry',
                            'buy_price': record.get('buy_nt_10k'),
                            'sell_price': record.get('sell_nt_10k'),
                            'location': 'National'
                        })

        # Check for duplicates before appending
        if rows:
            with csv_lock:
                existing_data = self.load_csv_data(filename)

                existing_map = {}
                for row in existing_data:
                    key = self._build_row_key(row)
                    if key in existing_map:
                        current_ts = existing_map[key].get('timestamp', '')
                        row_ts = row.get('timestamp', '')
                        if row_ts > current_ts:
                            existing_map[key] = row
                    else:
                        existing_map[key] = row

                replacements = 0
                additions = 0

                for row in rows:
                    key = self._build_row_key(row)
                    if key in existing_map:
                        replacements += 1
                    else:
                        additions += 1
                    existing_map[key] = row

                if replacements or additions:
                    updated_rows = list(existing_map.values())
                    updated_rows.sort(key=lambda r: r.get('timestamp', ''))

                    fieldnames = ['timestamp', 'company', 'gold_type', 'buy_price', 'sell_price', 'location']
                    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(updated_rows)

                    print(f"\n[+] Data saved to {filename}")
                    print(f"  Records replaced: {replacements}")
                    print(f"  New records added: {additions}")
                else:
                    print("\n[-] No data changes detected")
        else:
            print("\n[-] No data to append")

    def update_csv_with_latest(self, filename: Optional[str] = None):
        """
        Update existing CSV file with latest data
        """
        if filename is None:
            filename = os.path.join(self.DATA_DIR, 'historical_gold_prices.csv')

        # Fetch current data
        data = self.collect_current_prices()

        # Append to existing file
        self.append_to_csv(data, filename)

    def get_last_csv_date(self, filename: Optional[str] = None) -> Optional[datetime]:
        """
        Get the most recent date from the CSV file

        Returns:
            datetime object of the most recent timestamp, or None if file doesn't exist
        """
        if filename is None:
            filename = os.path.join(self.DATA_DIR, 'historical_gold_prices.csv')

        if not os.path.exists(filename):
            return None

        try:
            rows = self.load_csv_data(filename)
            if not rows:
                return None

            # Find the most recent timestamp
            latest_date = None
            for row in rows:
                try:
                    timestamp_str = row.get('timestamp', '')
                    # Parse timestamp (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
                    if ' ' in timestamp_str:
                        row_date = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        row_date = datetime.strptime(timestamp_str, '%Y-%m-%d')

                    if latest_date is None or row_date > latest_date:
                        latest_date = row_date
                except (ValueError, TypeError):
                    continue

            return latest_date
        except Exception as e:
            print(f"Error getting last CSV date: {e}")
            return None

    def fetch_missing_data(self, filename: Optional[str] = None) -> Dict[str, int]:
        """
        Fetch and append missing data from the last CSV date to today
        
        IMPORTANT: The API returns ALL available historical data for the date range,
        not just the missing dates. This method will fetch a broader range and merge
        it with existing data to fill gaps.

        Returns:
            Dictionary with statistics about the update
        """
        if filename is None:
            filename = os.path.join(self.DATA_DIR, 'historical_gold_prices.csv')

        # Get the last date in CSV
        last_date = self.get_last_csv_date(filename)

        if last_date is None:
            print("No existing data found. Collecting full historical data...")
            # If no data exists, collect last 365 days
            data = self.collect_historical_data(days_back=365)
            self.save_to_csv(data, filename)
            return {
                'status': 'full_collection',
                'message': 'Collected full historical data (365 days)',
                'records_added': len(data)
            }

        # Calculate days between last date and today
        today = datetime.now()
        days_missing = (today - last_date).days

        if days_missing <= 0:
            print("CSV is up to date!")
            return {
                'status': 'up_to_date',
                'message': 'No missing data',
                'records_added': 0
            }

        print(f"Found {days_missing} days of missing data")
        print(f"Last CSV date: {last_date.strftime('%Y-%m-%d')}")
        print(f"Today: {today.strftime('%Y-%m-%d')}")

        # Check if today is Sunday (weekday() returns 6 for Sunday)
        is_sunday = today.weekday() == 6

        # Note: Gold price data is typically published around 10:00 AM Vietnam time
        # The market is closed on Sundays
        if is_sunday:
            print(f"Note: Today is Sunday - the gold market is typically closed on Sundays")
        elif days_missing == 1 and today.hour < 11:
            print(f"Note: Today's data may not be available yet (published around 10:00 AM Vietnam time)")

        # Fetch data from a broader range to catch any gaps in the middle
        # Use the last 30 days or days since last update, whichever is larger
        days_to_fetch = max(30, days_missing + 5)  # Add 5 extra days as buffer
        date_from = today - timedelta(days=days_to_fetch)
        
        date_from_str = date_from.strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        print(f"Fetching data from {date_from_str} to {date_to} (last {days_to_fetch} days)...")
        print(f"Note: This will fill any gaps in existing data, not just append to the end")

        missing_data = {}
        companies = ['sjc']  # DOJI and PNJ removed

        for company in companies:
            print(f"  Fetching {company.upper()}...")
            company_data = self.fetch_company_data(company, date_from_str, date_to)

            if company_data and 'results' in company_data:
                missing_data[company] = company_data['results']
                print(f"    [+] Got {len(company_data['results'])} records from API")
            else:
                print(f"    [-] No data available")

            time.sleep(1)  # Rate limiting

        # Append missing data to CSV (use append_to_csv which handles deduplication)
        total_records = sum(len(records) for records in missing_data.values()) if missing_data else 0

        if total_records > 0:
            # Count existing records before update
            existing_data = self.load_csv_data(filename)
            existing_count = len(existing_data)
            
            self.append_to_csv(missing_data, filename)
            
            # Count records after update
            updated_data = self.load_csv_data(filename)
            updated_count = len(updated_data)
            
            actual_added = updated_count - existing_count

            return {
                'status': 'updated',
                'message': f'Fetched {total_records} API records, added {actual_added} new records to CSV',
                'days_requested': days_missing,
                'records_fetched': total_records,
                'records_added': actual_added,
                'date_from': date_from_str,
                'date_to': date_to
            }
        else:
            # No data available - this is normal for Sundays or if today's data hasn't been published yet
            message = 'No data available from API'

            if is_sunday:
                message += ' (the gold market is typically closed on Sundays)'
            elif days_missing == 1 and today.hour < 11:
                message += ' (today\'s data may not be published yet - typically available after 10:00 AM Vietnam time)'

            return {
                'status': 'no_data',
                'message': message,
                'days_requested': days_missing,
                'records_added': 0,
                'date_from': date_from_str,
                'date_to': date_to
            }
    
    @staticmethod
    def _extract_records(records):
        if isinstance(records, dict):
            return records.get('results', [])
        return records or []

    @staticmethod
    def _is_normalized_price_row(record: Dict) -> bool:
        return all(key in record for key in ['company', 'gold_type', 'buy_price', 'sell_price', 'location'])

    @staticmethod
    def _normalized_record_to_csv_row(record: Dict, timestamp: str) -> Dict:
        return {
            'timestamp': timestamp,
            'company': record.get('company', '').upper(),
            'gold_type': record.get('gold_type', ''),
            'buy_price': record.get('buy_price'),
            'sell_price': record.get('sell_price'),
            'location': record.get('location', '')
        }

    @staticmethod
    def _build_row_key(row: Dict) -> tuple:
        timestamp = row.get('timestamp', '') or ''
        date_part = timestamp.split(' ')[0]
        return (
            date_part,
            row.get('company', '') or '',
            row.get('gold_type', '') or '',
            row.get('location', '') or ''
        )

    def load_csv_data(self, filename: Optional[str] = None) -> List[Dict]:
        """
        Load data from CSV file
        
        Returns:
            List of dictionaries containing price records
        """
        if filename is None:
            filename = os.path.join(self.DATA_DIR, 'historical_gold_prices.csv')
        
        with csv_lock:
            if not os.path.exists(filename):
                print(f"File {filename} does not exist")
                return []
            
            rows = []
            with open(filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    rows.append(row)
            
            return rows


def main():
    """Main function to collect and save historical data"""
    print("=" * 60)
    print("Historical Gold Price Data Collector")
    print("=" * 60)
    
    collector = HistoricalDataCollector()
    
    # Collect one year of historical data
    print("\nCollecting historical data for the past year...")
    data = collector.collect_historical_data(days_back=365)
    
    # Save to CSV
    print("\nSaving data to CSV...")
    collector.save_to_csv(data)
    
    print("\n" + "=" * 60)
    print("Data collection complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

