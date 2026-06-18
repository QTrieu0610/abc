import React, { useState, useEffect } from 'react';
import { Card, Spinner, Badge, Table, Accordion, Form, Button } from 'react-bootstrap';
import axios from 'axios';

const formatPrice = (price) => {
  if (!price) return 'N/A';
  return new Intl.NumberFormat('vi-VN').format(price);
};

// Utility function to format dates as dd/mm/yyyy
const formatDate = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const PriceCards = ({ prices }) => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [historicalPrices, setHistoricalPrices] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('current'); // 'current' or 'historical'
  const [latestAvailableDate, setLatestAvailableDate] = useState(null);

  // Convert yyyy-mm-dd to dd/mm/yyyy for display
  const formatDateForDisplay = (dateString) => {
    if (!dateString) return '';
    const [year, month, day] = dateString.split('-');
    return `${day}/${month}/${year}`;
  };

  // Convert dd/mm/yyyy to yyyy-mm-dd for date input
  const parseDateFromDisplay = (displayString) => {
    if (!displayString) return '';
    const [day, month, year] = displayString.split('/');
    return `${year}-${month}-${day}`;
  };

  // Fetch latest available date on component mount
  useEffect(() => {
    const fetchLatestDate = async () => {
      try {
        const response = await axios.get('/api/available-dates');
        if (response.data && response.data.dates && response.data.dates.length > 0) {
          // Get the most recent date (first in the array since it's sorted descending)
          const latest = response.data.dates[0];
          setLatestAvailableDate(latest);
          setSelectedDate(latest);
        }
      } catch (error) {
        console.error('Error fetching available dates:', error);
        // Fallback to today's date if API fails
        setSelectedDate(new Date().toISOString().split('T')[0]);
      }
    };
    
    fetchLatestDate();
  }, []);

  // Fetch historical data for selected date
  const fetchHistoricalData = async (date) => {
    if (!date) return;
    
    setLoading(true);
    try {
      const response = await axios.get('/api/prices-by-date', {
        params: {
          date: date
        }
      });
      setHistoricalPrices(response.data);
      setViewMode('historical');
    } catch (error) {
      console.error('Error fetching historical data:', error);
      alert('Unable to fetch data for the selected date. Please try another date.');
      setHistoricalPrices(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (e) => {
    const date = e.target.value;
    setSelectedDate(date);

    // Check if selected date is the latest available date
    const currentDate = latestAvailableDate || new Date().toISOString().split('T')[0];
    if (date === currentDate) {
      // If latest available date is selected, switch to current mode
      setHistoricalPrices(null);
      setViewMode('current');
    } else if (date) {
      // If any other date is selected, fetch historical data
      fetchHistoricalData(date);
    }
  };

  const handleViewCurrent = () => {
    const currentDate = latestAvailableDate || new Date().toISOString().split('T')[0];
    setSelectedDate(currentDate);
    setHistoricalPrices(null);
    setViewMode('current');
  };

  // Determine which data to display
  const displayData = viewMode === 'historical' && historicalPrices ? historicalPrices : prices;
  if (!displayData && !loading) {
    return (
      <Card className="price-card price-hero-card border-0 w-100">
        <div className="price-hero-banner text-white">
          <div className="banner-main">
            <div className="d-flex align-items-center gap-3 mb-3">
              <div className="skeleton" style={{ width: '58px', height: '58px', borderRadius: '18px' }}></div>
              <div>
                <div className="skeleton mb-2" style={{ width: '200px', height: '20px', borderRadius: '8px' }}></div>
                <div className="skeleton" style={{ width: '150px', height: '32px', borderRadius: '8px' }}></div>
              </div>
            </div>
            <div className="price-hero-values">
              <div className="price-hero-value">
                <div className="skeleton mb-2" style={{ width: '80px', height: '16px', borderRadius: '6px' }}></div>
                <div className="skeleton" style={{ width: '180px', height: '48px', borderRadius: '10px' }}></div>
              </div>
              <div className="price-hero-value">
                <div className="skeleton mb-2" style={{ width: '80px', height: '16px', borderRadius: '6px' }}></div>
                <div className="skeleton" style={{ width: '180px', height: '48px', borderRadius: '10px' }}></div>
              </div>
            </div>
          </div>
        </div>
        <Card.Body className="price-hero-body text-center py-5">
          <div className="d-flex align-items-center justify-content-center gap-3 mb-3">
            <Spinner animation="border" variant="warning" className="spinner-glow" style={{ width: '3rem', height: '3rem' }} />
          </div>
          <p className="text-muted mb-0 fw-semibold">
            <i className="fas fa-sync-alt fa-spin me-2"></i>
            Loading live gold prices...
          </p>
        </Card.Body>
      </Card>
    );
  }

  const sjcData = displayData?.sjc?.results?.[0];

  if (!sjcData) {
    return (
      <Card className="price-card price-hero-card border-0 w-100">
        <Card.Body className="price-hero-body text-center">
          <p className="text-muted mb-0">No SJC data available{viewMode === 'historical' ? ' for the selected date' : ''}</p>
          {viewMode === 'historical' && (
            <Button variant="outline-primary" size="sm" className="mt-3" onClick={handleViewCurrent}>
              <i className="fas fa-arrow-left me-2"></i>Back to Current Prices
            </Button>
          )}
        </Card.Body>
      </Card>
    );
  }

  const mainGold = {
    type: 'SJC 1L (1 Lượng)',
    category: 'Gold Bar',
    purity: '99.99%',
    buy: parseFloat(sjcData.buy_1l) || null,
    sell: parseFloat(sjcData.sell_1l) || null
  };

  const goldTypes = [];

  if (sjcData.buy_nhan1c || sjcData.sell_nhan1c) {
    goldTypes.push({
      type: 'SJC Ring 1C (Nhẫn 1 Chỉ)',
      category: 'Ring',
      purity: '99.99%',
      buy: parseFloat(sjcData.buy_nhan1c) || null,
      sell: parseFloat(sjcData.sell_nhan1c) || null
    });
  }

  if (sjcData.buy_nutrang_9999 || sjcData.sell_nutrang_9999) {
    goldTypes.push({
      type: 'SJC Jewelry 24K (Nữ Trang 9999)',
      category: 'Jewelry',
      purity: '99.99%',
      buy: parseFloat(sjcData.buy_nutrang_9999) || null,
      sell: parseFloat(sjcData.sell_nutrang_9999) || null
    });
  }

  if (sjcData.buy_nutrang_99 || sjcData.sell_nutrang_99) {
    goldTypes.push({
      type: 'SJC Jewelry 99% (Nữ Trang 99)',
      category: 'Jewelry',
      purity: '99%',
      buy: parseFloat(sjcData.buy_nutrang_99) || null,
      sell: parseFloat(sjcData.sell_nutrang_99) || null
    });
  }

  if (sjcData.buy_nutrang_75 || sjcData.sell_nutrang_75) {
    goldTypes.push({
      type: 'SJC Jewelry 18K (Nữ Trang 75)',
      category: 'Jewelry',
      purity: '75%',
      buy: parseFloat(sjcData.buy_nutrang_75) || null,
      sell: parseFloat(sjcData.sell_nutrang_75) || null
    });
  }

  const spread = mainGold.buy && mainGold.sell ? mainGold.sell - mainGold.buy : null;
  const spreadPercent = spread && mainGold.buy ? (spread / mainGold.buy) * 100 : null;
  const variantsCount = goldTypes.length + 1;

  const formatMillions = (price) => {
    if (!price) return 'N/A';
    return new Intl.NumberFormat('vi-VN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price / 1000000);
  };

  return (
    <Card className="price-card price-hero-card border-0 w-100 fade-in">
      {/* Date Picker Header */}
      <div className="price-date-header" style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
        padding: '1rem 1.5rem',
        borderBottom: '2px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
          <div className="d-flex align-items-center gap-2">
            <i className="fas fa-calendar-alt text-white-50"></i>
            <span className="text-white fw-semibold small">View Prices By Date</span>
          </div>
          <div className="d-flex gap-2 align-items-center">
            {viewMode === 'historical' && (
              <Button 
                variant="outline-light" 
                size="sm" 
                onClick={handleViewCurrent}
                style={{ fontSize: '0.85rem' }}
              >
                <i className="fas fa-sync-alt me-2"></i>Current Prices
              </Button>
            )}
            <div style={{ position: 'relative' }}>
              <Form.Control
                type="date"
                value={selectedDate}
                onChange={handleDateChange}
                max={latestAvailableDate || new Date().toISOString().split('T')[0]}
                size="sm"
                style={{
                  width: '150px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  color: 'transparent',
                  fontSize: '0.875rem',
                  cursor: 'pointer'
                }}
                disabled={loading}
              />
              <div 
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '12px',
                  transform: 'translateY(-50%)',
                  pointerEvents: 'none',
                  color: 'white',
                  fontSize: '0.875rem',
                  fontWeight: '500'
                }}
              >
                {formatDateForDisplay(selectedDate)}
              </div>
            </div>
            {loading && <Spinner animation="border" size="sm" variant="light" />}
          </div>
        </div>
        {viewMode === 'historical' && selectedDate && (
          <div className="mt-2">
            <Badge bg="info" className="badge-info">
              <i className="fas fa-history me-1"></i>
              Historical Data: {formatDate(selectedDate)}
            </Badge>
          </div>
        )}
      </div>

      {/* Price Display */}
      <div className="price-hero-banner text-white">
        <div className="banner-main">
          <div className="d-flex align-items-center gap-3 mb-3">
            <span className="price-hero-icon">
              <i className="fas fa-coins"></i>
            </span>
            <div>
              <p className="text-uppercase text-white-50 small mb-1">
                {viewMode === 'historical' ? 'Historical' : 'Live'} Vietnamese Gold
              </p>
              <h1 className="price-hero-title mb-0">SJC Gold Bar 1L</h1>
            </div>
          </div>
            <div className="price-hero-values">
              <div className="price-hero-value buy">
                <span className="label">Buy</span>
                <span className="value">
                  {formatPrice(mainGold.buy)}
                  <span className="currency">₫</span>
                </span>
              </div>
              <div className="price-hero-divider" aria-hidden="true"></div>
              <div className="price-hero-value sell">
                <span className="label">Sell</span>
                <span className="value">
                  {formatPrice(mainGold.sell)}
                  <span className="currency">₫</span>
                </span>
              </div>
            </div>
            </div>
          <div className="banner-meta text-lg-end">
            <Badge bg="light" text="dark" className="price-hero-badge">
              <i className={`fas ${viewMode === 'historical' ? 'fa-history' : 'fa-bolt'} me-1`}></i>
              {viewMode === 'historical' ? 'Historical Data' : 'Real-time feed'}
            </Badge>
            <p className="hero-subtext text-white-50 mb-0">Saigon Jewelry Company · 99.99% purity</p>
          </div>
        </div>

          <Card.Body className="price-hero-body">
            <div className="price-hero-stats">
              <div className="hero-stat">
                <span className="hero-stat-label">
                  <i className="fas fa-arrows-left-right me-2"></i>Buy-Sell Spread
                </span>
                <span className="hero-stat-value">{spread ? `${formatPrice(spread)} ₫` : 'N/A'}</span>
                <small className="text-muted">
                  {spreadPercent ? `${spreadPercent.toFixed(2)}% difference` : 'Awaiting live spread'}
                </small>
              </div>
              <div className="hero-stat">
                <span className="hero-stat-label">
                  <i className="fas fa-coins me-2"></i>Buy Price (Million VND)
                </span>
                <span className="hero-stat-value">{formatMillions(mainGold.buy)}</span>
                <small className="text-muted">Per tael · rounded to 2 decimals</small>
              </div>
              <div className="hero-stat">
                <span className="hero-stat-label">
                  <i className="fas fa-layer-group me-2"></i>Variants Tracked
                </span>
                <span className="hero-stat-value">{variantsCount}</span>
                <small className="text-muted">Including rings & jewelry lines</small>
              </div>
            </div>

            {goldTypes.length > 0 && (
              <div className="price-hero-more mt-4">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h6 className="text-uppercase text-muted small fw-bold mb-0">Detailed breakdown</h6>
                  <Badge bg="primary" className="price-hero-mini-badge">
                    <i className="fas fa-list-ol me-1"></i>{goldTypes.length + 1} total types
                  </Badge>
                </div>
                <Accordion className="price-hero-accordion" flush>
                  <Accordion.Item eventKey="0">
                    <Accordion.Header>
                      <small>View full SJC catalogue</small>
                    </Accordion.Header>
                    <Accordion.Body>
                      <div className="table-responsive price-hero-table">
                        <Table size="sm" className="mb-0" hover>
                          <thead>
                            <tr>
                              <th className="small">Type</th>
                              <th className="small">Purity</th>
                              <th className="small text-end">Buy</th>
                              <th className="small text-end">Sell</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="table-active">
                              <td className="small fw-bold">{mainGold.type}</td>
                              <td className="small">{mainGold.purity}</td>
                              <td className="small text-end buy-price fw-bold">{formatPrice(mainGold.buy)}</td>
                              <td className="small text-end sell-price fw-bold">{formatPrice(mainGold.sell)}</td>
                            </tr>
                            {goldTypes.map((item, idx) => (
                              <tr key={idx}>
                                <td className="small">{item.type}</td>
                                <td className="small">{item.purity}</td>
                                <td className="small text-end buy-price">{formatPrice(item.buy)}</td>
                                <td className="small text-end sell-price">{formatPrice(item.sell)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </Table>
                      </div>
                    </Accordion.Body>
                  </Accordion.Item>
                </Accordion>
              </div>
            )}
          </Card.Body>

        <Card.Footer className="price-hero-footer text-muted small">
          <i className="fas fa-info-circle me-1"></i>
          Saigon Jewelry Company · Data supplied by vnappmob API
          {viewMode === 'historical' && (
            <span className="ms-2">
              <i className="fas fa-calendar me-1"></i>
              Showing data from {formatDate(selectedDate)}
            </span>
          )}
        </Card.Footer>
    </Card>
  );
};

export default PriceCards;

