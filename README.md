# Gold Price Dashboard - Vietnam SJC Gold Price Tracker

A modern, real-time gold price monitoring system for Vietnamese gold markets, featuring live price updates, historical data analysis, and beautiful data visualizations.

![Gold Price Dashboard](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![React](https://img.shields.io/badge/React-18.0+-61dafb)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688)

## 🌟 Features

### Real-Time Price Monitoring
- **Live gold prices** from SJC (Saigon Jewelry Company)
- **WebSocket updates** for instant price changes
- **Multiple gold types**: Bars (1L), Rings (1C), Jewelry (24K, 99%, 18K)

### Historical Data Management
- **Automatic data collection** with gap detection
- **Historical price lookups** by date
- **Smart data filling** - automatically fetches missing dates
- **CSV storage** with 239+ unique dates of historical data

### Advanced Analytics
- **Price change analysis** over time
- **Volatility tracking** and trends
- **Price extremes** (min/max) detection
- **Moving averages** for trend analysis

### Modern UI/UX
- **Responsive design** works on all devices
- **Date picker** with automatic latest date detection
- **Interactive charts** and visualizations
- **Real-time updates** without page refresh

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Node.js 14+** and npm
- **Git**

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/gold-price-dashboard.git
cd gold-price-dashboard
```

#### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create config file from example
cp config.py.example config.py

# Edit config.py and add your API key
# Get API key from: https://vapi.vnappmob.com/api/request_api_key?scope=gold
```

#### 3. Frontend Setup

```bash
   cd frontend-react
   npm install
```

### Running the Application

#### Start Backend (Terminal 1)
```bash
# From project root
uvicorn api_fastapi:app --reload
```

Backend will run at: http://localhost:8000

#### Start Frontend (Terminal 2)
```bash
# From project root
cd frontend-react
npm start
```

Frontend will run at: http://localhost:3000

## 📊 API Endpoints

### Current Prices
```
GET /api/current-prices
```
Get the latest live gold prices.

### Historical Data
```
GET /api/historical-prices?company=sjc&days=7
```
Get historical prices for the last N days.

### Update Data
```
POST /api/update-historical-data
```
Manually trigger data update and gap filling.

### Available Dates
```
GET /api/available-dates
```
Get list of all dates with available data.

### Price by Date
```
GET /api/prices-by-date?date=2025-11-06
```
Get prices for a specific date.

### WebSocket
```
WS /ws/prices
```
Real-time price updates via WebSocket.

Full API documentation: http://localhost:8000/api/docs

## 🏗️ Project Structure

```
gold-price-dashboard/
├── api_fastapi.py              # FastAPI backend server
├── data_collector.py           # Historical data collection
├── data_analyzer.py            # Price analysis and analytics
├── config.py                   # API key configuration (not in repo)
├── config.py.example           # Config template
├── requirements.txt            # Python dependencies
│
├── frontend-react/             # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── PriceCards.js  # Main price display
│   │   │   ├── Charts.js      # Price charts
│   │   │   └── Analytics.js   # Analytics dashboard
│   │   ├── App.js
│   │   └── App.css
│   └── package.json
│
├── historical_data/            # Data storage
│   └── historical_gold_prices.csv
│
├── fill_all_gaps.py           # Manual gap-filling utility
├── test_recovery.py           # Data recovery testing
└── README.md
```

## 🔧 Configuration

### API Key Setup

1. Get your API key: https://vapi.vnappmob.com/api/request_api_key?scope=gold
2. Copy `config.py.example` to `config.py`
3. Add your API key to `config.py`:

```python
API_KEY = "your_actual_api_key_here"
```

**⚠️ Important**: 
- API keys expire after 15 days
- Never commit `config.py` to version control
- Get a new key when expired

## 🛠️ Key Features Explained

### Automatic Gap Filling

The system automatically detects and fills missing dates in historical data:

- **On startup**: Backend checks for missing data
- **Fetches 30+ days**: Ensures no gaps are missed
- **Smart merging**: Avoids duplicates
- **Status logging**: Shows what was added

```bash
# Manual gap filling
python fill_all_gaps.py
```

### Date Picker Intelligence

The frontend automatically shows the latest available date:

- **On page load**: Fetches available dates from API
- **Sets to latest**: Shows most recent data, not today
- **Smart fallback**: Uses today if API fails
- **Max date constraint**: Can't select future dates

### WebSocket Real-Time Updates

- **60-second polling**: Checks for price changes
- **Instant broadcast**: Pushes to all connected clients
- **Auto-save**: Updates CSV automatically
- **Connection management**: Handles disconnections gracefully

## 📈 Data Management

### Historical Data

Located in: `historical_data/historical_gold_prices.csv`

**Current Stats**:
- 1,159 total records
- 239 unique dates
- Date range: Dec 2024 - Nov 2025
- 5 gold types per date

### Data Update Methods

**1. Automatic (Recommended)**
- Backend updates on startup
- Background task runs every 60 seconds

**2. API Endpoint**
```bash
curl -X POST http://localhost:8000/api/update-historical-data
```

**3. Manual Script**
```bash
python fill_all_gaps.py
```

**4. Python Code**
```python
from data_collector import HistoricalDataCollector

collector = HistoricalDataCollector()
result = collector.fetch_missing_data()
print(result)
```

## 🧪 Testing

### Test Data Recovery
```bash
python test_recovery.py
```

Removes recent data and verifies automatic recovery.

### Run Frontend Tests
```bash
cd frontend-react
npm test
```

## 🎨 UI Features

### Price Display
- **Hero card** with main gold bar (SJC 1L) prices
- **Detailed breakdown** of all gold types
- **Buy/Sell spread** calculation
- **Historical vs Live** mode indicator

### Date Selection
- **Calendar picker** for any available date
- **Quick "Current Prices"** button
- **Visual indicators** for historical mode
- **Loading states** during data fetch

### Charts & Analytics
- **Line charts** for price trends
- **Moving averages** overlay
- **Volatility indicators**
- **Price extremes** highlighting

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is available
netstat -ano | findstr :8000

# Try different port
uvicorn api_fastapi:app --port 8001
```

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check `package.json` proxy setting
- Verify CORS is enabled in `api_fastapi.py`

### No data showing
```bash
# Run gap filler
python fill_all_gaps.py

# Check CSV exists
ls historical_data/historical_gold_prices.csv

# Verify API key is valid
# Check config.py has correct API_KEY
```

### API Key Expired
1. Get new key: https://vapi.vnappmob.com/api/request_api_key?scope=gold
2. Update `config.py` with new key
3. Restart backend

## 📝 Recent Updates

### November 7, 2025
- ✅ **Fixed date picker** to show latest available date
- ✅ **Enhanced gap detection** (fetches 30+ days)
- ✅ **Added auto-update** on backend startup
- ✅ **Improved data recovery** testing

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Data Source**: [VNAppMob Gold Price API](https://vapi.vnappmob.com)
- **Gold Provider**: SJC (Saigon Jewelry Company)
- **Frontend**: React + Bootstrap
- **Backend**: FastAPI + Python

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Made with ❤️ for tracking Vietnamese gold prices**
