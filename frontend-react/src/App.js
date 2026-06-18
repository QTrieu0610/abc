import React, { useState, useEffect, useRef } from 'react';
import { Container, Navbar, Nav, Button } from 'react-bootstrap';
import axios from 'axios';
import './App.css';
import PriceCards from './components/PriceCards';
import UnifiedComparisonChart from './components/UnifiedComparisonChart';
import AnalyticsCards from './components/AnalyticsCards';
import SpreadTrendChart from './components/SpreadTrendChart';
import DailyChangeBarChart from './components/DailyChangeBarChart';
import CumulativeReturnChart from './components/CumulativeReturnChart';
import CrawlerStatusWidget from './components/CrawlerStatusWidget';

// Register Chart.js components
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  zoomPlugin
);

// Configure axios base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
axios.defaults.baseURL = API_BASE_URL;

function App() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [currentPrices, setCurrentPrices] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dataRefreshTrigger, setDataRefreshTrigger] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsReconnecting, setWsReconnecting] = useState(false);
  const [crawlerStatus, setCrawlerStatus] = useState('idle');
  const [crawlerMessage, setCrawlerMessage] = useState('Initializing...');
  const [alerts, setAlerts] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Auto-update historical data on app startup only
  useEffect(() => {
    updateHistoricalData(); // Initial update on startup
  }, []);

  // Fetch current prices
  useEffect(() => {
    fetchCurrentPrices();
    const interval = setInterval(fetchCurrentPrices, 60000); // Refresh every 60 seconds
    return () => clearInterval(interval);
  }, []);

  const updateHistoricalData = async () => {
    try {
      console.log('Checking for missing historical data...');
      const response = await axios.post('/api/update-historical-data');
      console.log('Historical data update:', response.data);

      if (response.data.status === 'updated') {
        console.log(`✓ Added ${response.data.days_added} days of missing data (${response.data.records_added} records)`);
        setDataRefreshTrigger(prev => prev + 1);
      } else if (response.data.status === 'up_to_date') {
        console.log('✓ Historical data is up to date');
        setDataRefreshTrigger(prev => prev + 1);
      }
    } catch (error) {
      console.error('Error updating historical data:', error);
      // Don't show error to user - this is a background operation
    }
  };

  const fetchCurrentPrices = async () => {
    try {
      const response = await axios.get('/api/current-prices');
      setCurrentPrices(response.data);
    } catch (error) {
      console.error('Error fetching current prices:', error);
    }
  };

  // WebSocket connection with auto-reconnect
  const connectWebSocket = () => {
    try {
      // Close existing connection if any
      if (wsRef.current) {
        wsRef.current.close();
      }

      // Clear any pending reconnection timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/prices';
      console.log('🔌 Connecting to WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setWsConnected(true);
        setWsReconnecting(false);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message:', data);
          
          if (data.type === 'price_update') {
            console.log('💰 Price update received - refreshing charts');
            setDataRefreshTrigger(prev => prev + 1);
            fetchCurrentPrices();
          } else if (data.type === 'crawler_status') {
            setCrawlerStatus(data.status);
            setCrawlerMessage(data.message);
          } else if (data.type === 'alert') {
            setAlerts(prev => [data.message, ...prev].slice(0, 10)); // Keep last 10 alerts
          } else if (data.type === 'connection') {
            console.log('✅ WebSocket connection confirmed');
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };
      
      ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected');
        setWsConnected(false);
        
        // Attempt to reconnect after 5 seconds
        if (!event.wasClean) {
          setWsReconnecting(true);
          console.log('🔄 Reconnecting in 5 seconds...');
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, 5000);
        }
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setWsReconnecting(true);
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 5000);
    }
  };

  // Connect WebSocket on mount
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      // Clean up on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const handleExportCSV = () => {
    window.open(`${API_BASE_URL}/api/export/csv`, '_blank');
  };

  const handleUpdateData = async () => {
    setLoading(true);
    try {
      await axios.post('/api/data/update');
      alert('Historical data updated successfully!');
      fetchCurrentPrices();
      setDataRefreshTrigger(prev => prev + 1);
    } catch (error) {
      alert('Failed to update data: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Format date and time
  const formatDateTime = () => {
    const weekday = currentTime.toLocaleDateString('en-US', { weekday: 'long' });
    const day = currentTime.getDate().toString().padStart(2, '0');
    const month = (currentTime.getMonth() + 1).toString().padStart(2, '0');
    const year = currentTime.getFullYear();
    const time = currentTime.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
    return `${weekday}, ${day}/${month}/${year} at ${time}`;
  };

  return (
    <div className="App">
      {/* Enhanced Navigation */}
      <Navbar bg="dark" variant="dark" expand="lg" className="shadow-lg border-bottom border-secondary" style={{ borderBottomWidth: '2px' }}>
        <Container fluid className="px-4">
          <Navbar.Brand className="d-flex align-items-center gap-2 fw-bold fs-5">
            <div className="d-flex align-items-center justify-content-center" style={{
              width: '40px',
              height: '40px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              borderRadius: '10px',
              boxShadow: '0 4px 12px rgba(245, 158, 11, 0.4)'
            }}>
              <i className="fas fa-coins text-white"></i>
            </div>
            <span className="d-none d-md-inline text-gradient-gold">Gold Price Dashboard</span>
            <span className="d-md-none text-gradient-gold">Gold Dashboard</span>
          </Navbar.Brand>
          <Nav className="ms-auto d-flex flex-row align-items-center gap-2">
            {/* WebSocket Connection Status */}
            <div 
              className="d-flex align-items-center gap-2 px-3 py-1 rounded"
              style={{ 
                background: wsConnected 
                  ? 'rgba(16, 185, 129, 0.2)' 
                  : wsReconnecting 
                  ? 'rgba(245, 158, 11, 0.2)' 
                  : 'rgba(239, 68, 68, 0.2)',
                border: wsConnected 
                  ? '1px solid rgba(16, 185, 129, 0.4)' 
                  : wsReconnecting 
                  ? '1px solid rgba(245, 158, 11, 0.4)' 
                  : '1px solid rgba(239, 68, 68, 0.4)'
              }}
            >
              <div 
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: wsConnected 
                    ? '#10b981' 
                    : wsReconnecting 
                    ? '#f59e0b' 
                    : '#ef4444',
                  animation: wsConnected 
                    ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' 
                    : 'none'
                }}
              />
              <span 
                className="d-none d-md-inline small fw-semibold"
                style={{ 
                  color: wsConnected 
                    ? '#10b981' 
                    : wsReconnecting 
                    ? '#f59e0b' 
                    : '#ef4444'
                }}
              >
                {wsConnected ? 'Live' : wsReconnecting ? 'Reconnecting' : 'Offline'}
              </span>
            </div>
            <Button
              variant="outline-success"
              size="sm"
              onClick={handleUpdateData}
              disabled={loading}
              className="d-flex align-items-center gap-2"
              style={{ 
                fontWeight: '600',
                borderWidth: '2px',
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
            >
              <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
              <span className="d-none d-md-inline">{loading ? 'Updating...' : 'Update Data'}</span>
            </Button>
            <Button
              variant="outline-info"
              size="sm"
              onClick={handleExportCSV}
              className="d-flex align-items-center gap-2"
              style={{ 
                fontWeight: '600',
                borderWidth: '2px',
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
            >
              <i className="fas fa-download"></i>
              <span className="d-none d-md-inline">Export CSV</span>
            </Button>
          </Nav>
        </Container>
      </Navbar>

      {/* Enhanced Date/Time Header with Glass Effect */}
      <div className="position-relative overflow-hidden" style={{
        background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%)',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.15)'
      }}>
        <div className="position-absolute w-100 h-100" style={{
          background: 'radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%)',
          pointerEvents: 'none'
        }}></div>
        <Container fluid className="py-4 position-relative">
          <div className="text-center">
            <div className="d-flex align-items-center justify-content-center gap-3 mb-2 fade-in">
              <div className="d-flex align-items-center justify-content-center bg-white bg-opacity-25 rounded-circle pulse" style={{
                width: '48px',
                height: '48px',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
              }}>
                <i className="fas fa-calendar-alt text-white fs-4"></i>
              </div>
              <h3 className="mb-0 fw-bold text-white" style={{ letterSpacing: '-0.02em' }}>
                {formatDateTime()}
              </h3>
            </div>
            <div className="d-flex align-items-center justify-content-center gap-2 scale-in">
              <div className="bg-success rounded-circle d-flex align-items-center justify-content-center" style={{
                width: '8px',
                height: '8px',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                boxShadow: '0 0 8px rgba(16, 185, 129, 0.8)'
              }}></div>
              <p className="mb-0 text-white fw-semibold" style={{ fontSize: '0.95rem', opacity: '0.95' }}>
                Live Gold Price Monitoring System
              </p>
            </div>
          </div>
        </Container>
      </div>

      {/* Main Content */}
      <main className="dashboard-wrapper">
        <Container fluid className="main-dashboard py-4">
          {/* Enhanced Dashboard Introduction */}
          <div className="dashboard-intro text-center mb-5 fade-in">
            <div className="d-inline-flex align-items-center justify-content-center mb-3" style={{
              background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%)',
              backdropFilter: 'blur(10px)',
              padding: '12px 28px',
              borderRadius: '50px',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)'
            }}>
              <i className="fas fa-chart-line text-white me-2 fs-5"></i>
              <span className="text-white fw-semibold" style={{ fontSize: '0.95rem', letterSpacing: '0.03em' }}>
                MARKET ANALYTICS
              </span>
            </div>
            <h1 className="mb-3 fw-bold text-white" style={{ 
              fontSize: 'clamp(2rem, 4vw, 3rem)',
              letterSpacing: '-0.03em',
              textShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
            }}>
              Vietnamese Gold Market Overview
            </h1>
            <p className="mb-0 text-white mx-auto" style={{ 
              fontSize: '1.1rem',
              maxWidth: '700px',
              opacity: '0.9',
              lineHeight: '1.7'
            }}>
              Track real-time market data, historical trends, and volatility insights in one unified, comprehensive view.
            </p>
          </div>

          <div className="dashboard-grid">
            {/* Top row: Prices and Crawler Status */}
            <section className="grid-item">
              <div className="row g-4 align-items-stretch">
                <div className="col-12 col-xl-8">
                  <PriceCards prices={currentPrices} />
                </div>
                <div className="col-12 col-xl-4">
                  <CrawlerStatusWidget 
                    status={crawlerStatus} 
                    statusMessage={crawlerMessage} 
                    alerts={alerts} 
                  />
                </div>
              </div>
            </section>

            {/* Unified Comparison Chart (moved before Investment Return Analysis) */}
            <section className="grid-item">
              <div className="d-flex">
                <UnifiedComparisonChart dataRefreshTrigger={dataRefreshTrigger} />
              </div>
            </section>

            {/* Moving Average Insight */}
            <section className="grid-item">
              <div className="d-flex">
                <CumulativeReturnChart dataRefreshTrigger={dataRefreshTrigger} />
              </div>
            </section>

            {/* Insight Charts */}
            <section className="grid-item">
              <div className="row g-4 align-items-stretch">
                <div className="col-12 col-xl-6 d-flex">
                  <SpreadTrendChart dataRefreshTrigger={dataRefreshTrigger} />
                </div>
                <div className="col-12 col-xl-6 d-flex">
                  <DailyChangeBarChart dataRefreshTrigger={dataRefreshTrigger} />
                </div>
              </div>
            </section>

            {/* Analytics Cards */}
            <section className="grid-item">
              <AnalyticsCards company="SJC" dataRefreshTrigger={dataRefreshTrigger} />
            </section>
          </div>

          {/* Enhanced Premium Footer */}
          <footer className="mt-5 pt-4 pb-3 position-relative" style={{
            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)',
            backdropFilter: 'blur(20px)',
            borderRadius: '24px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 -10px 40px rgba(0, 0, 0, 0.3)'
          }}>
            <div className="position-absolute w-100 h-100 top-0 start-0" style={{
              background: 'radial-gradient(circle at 50% 120%, rgba(102, 126, 234, 0.1) 0%, transparent 60%)',
              pointerEvents: 'none',
              borderRadius: '24px'
            }}></div>
            <Container className="position-relative">
              <div className="text-center mb-3">
                <div className="d-flex align-items-center justify-content-center gap-2 mb-2">
                  <div className="d-flex align-items-center justify-content-center" style={{
                    width: '36px',
                    height: '36px',
                    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)'
                  }}>
                    <i className="fas fa-coins text-white"></i>
                  </div>
                  <h5 className="mb-0 text-white fw-bold">Gold Price Dashboard</h5>
                </div>
                <p className="mb-3 text-white-50 small">
                  <i className="fas fa-database me-2"></i>
                  Data powered by Autonomous AI Crawler (Local Qwen2.5)
                </p>
              </div>

              <div className="d-flex flex-wrap align-items-center justify-content-center gap-3 mb-3">
                <div className="badge px-3 py-2" style={{
                  background: 'rgba(16, 185, 129, 0.2)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: '600'
                }}>
                  <i className="fab fa-react me-2"></i>React.js
                </div>
                <div className="badge px-3 py-2" style={{
                  background: 'rgba(59, 130, 246, 0.2)',
                  border: '1px solid rgba(59, 130, 246, 0.4)',
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: '600'
                }}>
                  <i className="fas fa-bolt me-2"></i>FastAPI
                </div>
                <div className="badge px-3 py-2" style={{
                  background: 'rgba(245, 158, 11, 0.2)',
                  border: '1px solid rgba(245, 158, 11, 0.4)',
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: '600'
                }}>
                  <i className="fas fa-chart-line me-2"></i>Chart.js
                </div>
                <div className="badge px-3 py-2" style={{
                  background: 'rgba(139, 92, 246, 0.2)',
                  border: '1px solid rgba(139, 92, 246, 0.4)',
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  fontWeight: '600'
                }}>
                  <i className="fab fa-bootstrap me-2"></i>Bootstrap
                </div>
              </div>

              <div className="text-center pt-3" style={{
                borderTop: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <p className="mb-1 text-white-50" style={{ fontSize: '0.875rem' }}>
                  <i className="fas fa-university me-2"></i>
                  <strong className="text-white">FPT University</strong> · DBM302m · FALL 2025
                </p>
                <p className="mb-0 text-white-50 small">
                  © 2025 Gold Price Dashboard. All rights reserved.
                </p>
              </div>
            </Container>
          </footer>
        </Container>
      </main>
    </div>
  );
}

export default App;

