"""
Gold Price Data Analyzer
Provides analytics and insights from historical gold price data
"""

import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import statistics


class GoldPriceAnalyzer:
    """Analyze historical gold price data"""
    
    def __init__(self, csv_file: str = 'historical_data/historical_gold_prices.csv'):
        self.csv_file = csv_file
        self.data = self.load_data()
    
    def load_data(self) -> List[Dict]:
        """Load data from CSV file"""
        if not os.path.exists(self.csv_file):
            return []
        
        rows = []
        with open(self.csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert price strings to floats
                if row.get('buy_price'):
                    row['buy_price'] = float(row['buy_price'])
                if row.get('sell_price'):
                    row['sell_price'] = float(row['sell_price'])
                rows.append(row)
        
        return rows
    
    def reload_data(self):
        """Reload data from CSV file to get latest updates"""
        self.data = self.load_data()
    
    def filter_by_company(self, company: str) -> List[Dict]:
        """Filter data by company"""
        return [row for row in self.data if row['company'].upper() == company.upper()]
    
    def filter_by_date_range(self, days_back: int) -> List[Dict]:
        """Filter data by date range (last N days)"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        filtered = []
        for row in self.data:
            try:
                # Parse timestamp (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD)
                timestamp_str = row['timestamp']
                if ' ' in timestamp_str:
                    row_date = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                else:
                    row_date = datetime.strptime(timestamp_str, '%Y-%m-%d')
                
                if row_date >= cutoff_date:
                    filtered.append(row)
            except (ValueError, KeyError):
                continue
        
        return filtered
    
    def get_price_trends(self, company: str, days_back: int = 7,
                        location: str = None, gold_type: str = None) -> Dict:
        """
        Get price trends for a specific company and time period

        Args:
            company: Company name (SJC, DOJI, PNJ)
            days_back: Number of days to look back
            location: Location filter (None = use first available location)
            gold_type: Gold type filter (e.g., 'SJC 1L', 'DOJI Gold Bar', 'PNJ 24K Ring')

        Returns:
            Dictionary with dates, buy prices, and sell prices
        """
        # Reload data to get latest updates from CSV
        self.reload_data()
        
        # Filter data
        company_data = self.filter_by_company(company)

        # If gold_type is specified, filter by it
        if gold_type:
            company_data = [row for row in company_data if row.get('gold_type') == gold_type]

        # If no location specified, use the first available location for this company
        if location is None and company_data:
            location = company_data[0].get('location', 'National')

        date_filtered = [row for row in company_data
                        if row.get('location') == location]
        
        # Sort by timestamp
        date_filtered.sort(key=lambda x: x['timestamp'])
        
        # Get last N days
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            date_filtered = [row for row in date_filtered 
                           if self._parse_date(row['timestamp']) >= cutoff_date]
        
        # Deduplicate by date - keep only the latest entry for each date
        date_map = {}
        for row in date_filtered:
            # Extract just the date part (YYYY-MM-DD)
            timestamp_str = row['timestamp']
            date_part = timestamp_str.split(' ')[0] if ' ' in timestamp_str else timestamp_str
            
            # Keep the latest entry for each date (since data is sorted by timestamp)
            if date_part not in date_map:
                date_map[date_part] = row
            else:
                # Compare timestamps and keep the later one
                existing_ts = date_map[date_part]['timestamp']
                if timestamp_str > existing_ts:
                    date_map[date_part] = row
        
        # Extract trends from deduplicated data
        dates = []
        buy_prices = []
        sell_prices = []
        
        # Sort by date to maintain chronological order
        for date_part in sorted(date_map.keys()):
            row = date_map[date_part]
            dates.append(row['timestamp'])
            buy_prices.append(row.get('buy_price', 0))
            sell_prices.append(row.get('sell_price', 0))
        
        return {
            'dates': dates,
            'buy_prices': buy_prices,
            'sell_prices': sell_prices
        }
    
    def calculate_price_change(self, company: str, days_back: int = 7) -> Dict:
        """
        Calculate price change over a period
        
        Returns:
            Dictionary with absolute and percentage changes
        """
        trends = self.get_price_trends(company, days_back)
        
        if not trends['buy_prices'] or len(trends['buy_prices']) < 2:
            return {
                'buy_change': 0,
                'sell_change': 0,
                'buy_change_percent': 0,
                'sell_change_percent': 0
            }
        
        # Calculate changes
        buy_start = trends['buy_prices'][0]
        buy_end = trends['buy_prices'][-1]
        sell_start = trends['sell_prices'][0]
        sell_end = trends['sell_prices'][-1]
        
        buy_change = buy_end - buy_start
        sell_change = sell_end - sell_start
        
        buy_change_percent = (buy_change / buy_start * 100) if buy_start else 0
        sell_change_percent = (sell_change / sell_start * 100) if sell_start else 0
        
        return {
            'buy_change': buy_change,
            'sell_change': sell_change,
            'buy_change_percent': buy_change_percent,
            'sell_change_percent': sell_change_percent,
            'period_days': days_back
        }
    
    def calculate_volatility(self, company: str, days_back: int = 30) -> Dict:
        """
        Calculate price volatility (standard deviation)
        
        Returns:
            Dictionary with volatility metrics
        """
        trends = self.get_price_trends(company, days_back)
        
        if not trends['buy_prices'] or len(trends['buy_prices']) < 2:
            return {
                'buy_volatility': 0,
                'sell_volatility': 0,
                'buy_std_dev': 0,
                'sell_std_dev': 0
            }
        
        buy_prices = trends['buy_prices']
        sell_prices = trends['sell_prices']
        
        # Calculate standard deviation
        buy_std = statistics.stdev(buy_prices) if len(buy_prices) > 1 else 0
        sell_std = statistics.stdev(sell_prices) if len(sell_prices) > 1 else 0
        
        # Calculate coefficient of variation (volatility %)
        buy_mean = statistics.mean(buy_prices)
        sell_mean = statistics.mean(sell_prices)
        
        buy_volatility = (buy_std / buy_mean * 100) if buy_mean else 0
        sell_volatility = (sell_std / sell_mean * 100) if sell_mean else 0
        
        return {
            'buy_volatility': buy_volatility,
            'sell_volatility': sell_volatility,
            'buy_std_dev': buy_std,
            'sell_std_dev': sell_std,
            'period_days': days_back
        }
    
    def get_price_extremes(self, company: str, days_back: int = 30) -> Dict:
        """
        Get highest and lowest prices in a period
        
        Returns:
            Dictionary with min/max prices and dates
        """
        trends = self.get_price_trends(company, days_back)
        
        if not trends['buy_prices']:
            return {
                'buy_min': 0,
                'buy_max': 0,
                'sell_min': 0,
                'sell_max': 0
            }
        
        buy_prices = trends['buy_prices']
        sell_prices = trends['sell_prices']
        dates = trends['dates']
        
        # Find extremes
        buy_min_idx = buy_prices.index(min(buy_prices))
        buy_max_idx = buy_prices.index(max(buy_prices))
        sell_min_idx = sell_prices.index(min(sell_prices))
        sell_max_idx = sell_prices.index(max(sell_prices))
        
        return {
            'buy_min': min(buy_prices),
            'buy_min_date': dates[buy_min_idx],
            'buy_max': max(buy_prices),
            'buy_max_date': dates[buy_max_idx],
            'sell_min': min(sell_prices),
            'sell_min_date': dates[sell_min_idx],
            'sell_max': max(sell_prices),
            'sell_max_date': dates[sell_max_idx],
            'period_days': days_back
        }
    
    def compare_companies(self, days_back: int = 7) -> Dict:
        """
        Compare prices across all companies
        
        Returns:
            Dictionary with comparison data
        """
        companies = ['SJC', 'DOJI', 'PNJ']
        comparison = {}
        
        for company in companies:
            trends = self.get_price_trends(company, days_back)
            if trends['buy_prices']:
                latest_buy = trends['buy_prices'][-1]
                latest_sell = trends['sell_prices'][-1]
                
                comparison[company] = {
                    'latest_buy': latest_buy,
                    'latest_sell': latest_sell,
                    'spread': latest_sell - latest_buy
                }
        
        return comparison
    
    def get_moving_average(self, company: str, days_back: int = 30, 
                          window: int = 7) -> Dict:
        """
        Calculate moving average for price trends
        
        Args:
            company: Company name
            days_back: Number of days to analyze
            window: Moving average window size
        
        Returns:
            Dictionary with moving averages
        """
        trends = self.get_price_trends(company, days_back)
        
        if not trends['buy_prices'] or len(trends['buy_prices']) < window:
            return {
                'dates': [],
                'buy_ma': [],
                'sell_ma': []
            }
        
        buy_prices = trends['buy_prices']
        sell_prices = trends['sell_prices']
        dates = trends['dates']
        
        buy_ma = []
        sell_ma = []
        ma_dates = []
        
        for i in range(len(buy_prices) - window + 1):
            buy_window = buy_prices[i:i+window]
            sell_window = sell_prices[i:i+window]
            
            buy_ma.append(statistics.mean(buy_window))
            sell_ma.append(statistics.mean(sell_window))
            ma_dates.append(dates[i+window-1])
        
        return {
            'dates': ma_dates,
            'buy_ma': buy_ma,
            'sell_ma': sell_ma,
            'window': window
        }
    
    def _parse_date(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object"""
        try:
            if ' ' in timestamp_str:
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            else:
                return datetime.strptime(timestamp_str, '%Y-%m-%d')
        except ValueError:
            return datetime.min


def main():
    """Test the analyzer"""
    analyzer = GoldPriceAnalyzer()
    
    print("=" * 60)
    print("Gold Price Data Analyzer - Test")
    print("=" * 60)
    
    # Test price trends
    print("\nSJC Price Trends (Last 7 days):")
    trends = analyzer.get_price_trends('SJC', days_back=7)
    print(f"  Data points: {len(trends['dates'])}")
    
    # Test price change
    print("\nPrice Change Analysis:")
    for company in ['SJC', 'DOJI', 'PNJ']:
        change = analyzer.calculate_price_change(company, days_back=7)
        print(f"  {company}: {change['buy_change_percent']:.2f}% (Buy)")
    
    # Test volatility
    print("\nVolatility Analysis (30 days):")
    for company in ['SJC', 'DOJI', 'PNJ']:
        vol = analyzer.calculate_volatility(company, days_back=30)
        print(f"  {company}: {vol['buy_volatility']:.2f}%")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()

