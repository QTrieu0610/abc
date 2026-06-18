import React, { useState, useEffect } from 'react';
import { Card, Row, Col } from 'react-bootstrap';
import axios from 'axios';

const formatPrice = (price) => {
  if (!price) return 'N/A';
  return new Intl.NumberFormat('vi-VN').format(price);
};

const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const AnalyticsCards = ({ company, dataRefreshTrigger }) => {
  const [priceChange, setPriceChange] = useState(null);
  const [volatility, setVolatility] = useState(null);
  const [extremes, setExtremes] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company, dataRefreshTrigger]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      // Fetch all analytics data
      const [changeRes, volRes, extremesRes] = await Promise.all([
        axios.get('/api/analytics/price-change', { params: { company, days: 7 } }),
        axios.get('/api/analytics/volatility', { params: { company, days: 30 } }),
        axios.get('/api/analytics/extremes', { params: { company, days: 30 } })
      ]);

      setPriceChange(changeRes.data);
      setVolatility(volRes.data);
      setExtremes(extremesRes.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Row className="fade-in g-4 align-items-stretch">
        {[
          { color: '#06b6d4', icon: 'fa-chart-line', title: 'Price Change' },
          { color: '#f59e0b', icon: 'fa-wave-square', title: 'Volatility' },
          { color: '#ef4444', icon: 'fa-arrows-alt-v', title: 'Price Extremes' }
        ].map((item, idx) => (
          <Col xs={12} lg={4} className="d-flex" key={idx}>
            <Card className="w-100 analytics-card">
              <Card.Header style={{
                background: `linear-gradient(135deg, ${item.color} 0%, ${item.color}dd 100%)`,
                color: 'white',
                borderBottom: 'none',
                padding: '1.25rem 1.5rem'
              }}>
                <div className="d-flex align-items-center gap-2">
                  <div className="d-flex align-items-center justify-content-center" style={{
                    width: '40px',
                    height: '40px',
                    background: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '10px'
                  }}>
                    <i className={`fas ${item.icon}`}></i>
                  </div>
                  <h5 className="mb-0 fw-bold">{item.title}</h5>
                </div>
                <div className="skeleton mt-2" style={{ width: '120px', height: '14px', borderRadius: '6px' }}></div>
              </Card.Header>
              <Card.Body className="d-flex flex-column gap-3">
                <div>
                  <div className="skeleton mb-2" style={{ width: '100%', height: '18px', borderRadius: '6px' }}></div>
                  <div className="skeleton mb-1" style={{ width: '80%', height: '32px', borderRadius: '8px' }}></div>
                  <div className="skeleton" style={{ width: '60%', height: '14px', borderRadius: '6px' }}></div>
                </div>
                <div>
                  <div className="skeleton mb-2" style={{ width: '100%', height: '18px', borderRadius: '6px' }}></div>
                  <div className="skeleton mb-1" style={{ width: '80%', height: '32px', borderRadius: '8px' }}></div>
                  <div className="skeleton" style={{ width: '60%', height: '14px', borderRadius: '6px' }}></div>
                </div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>
    );
  }

  const renderPriceChange = () => {
    if (!priceChange) return null;

    const buyChangeClass = priceChange.buy_change >= 0 ? 'text-success' : 'text-danger';
    const sellChangeClass = priceChange.sell_change >= 0 ? 'text-success' : 'text-danger';
    const buyIcon = priceChange.buy_change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
    const sellIcon = priceChange.sell_change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';

    return (
      <>
        <div className="mb-3">
          <h6 className="text-muted">Buy Price Change (7 days)</h6>
          <h4 className={buyChangeClass}>
            <i className={`fas ${buyIcon}`}></i>{' '}
            {formatPrice(Math.abs(priceChange.buy_change))} ₫
            <small> ({priceChange.buy_change_percent.toFixed(2)}%)</small>
          </h4>
        </div>
        <div>
          <h6 className="text-muted">Sell Price Change (7 days)</h6>
          <h4 className={sellChangeClass}>
            <i className={`fas ${sellIcon}`}></i>{' '}
            {formatPrice(Math.abs(priceChange.sell_change))} ₫
            <small> ({priceChange.sell_change_percent.toFixed(2)}%)</small>
          </h4>
        </div>
      </>
    );
  };

  const renderVolatility = () => {
    if (!volatility) return null;

    const buyVolClass = volatility.buy_volatility > 2 ? 'text-danger' : 
                       volatility.buy_volatility > 1 ? 'text-warning' : 'text-success';
    const sellVolClass = volatility.sell_volatility > 2 ? 'text-danger' : 
                        volatility.sell_volatility > 1 ? 'text-warning' : 'text-success';

    return (
      <>
        <div className="mb-3">
          <h6 className="text-muted">Buy Price Volatility (30 days)</h6>
          <h4 className={buyVolClass}>
            {volatility.buy_volatility.toFixed(2)}%
          </h4>
          <small className="text-muted">Std Dev: {formatPrice(volatility.buy_std_dev)} ₫</small>
        </div>
        <div>
          <h6 className="text-muted">Sell Price Volatility (30 days)</h6>
          <h4 className={sellVolClass}>
            {volatility.sell_volatility.toFixed(2)}%
          </h4>
          <small className="text-muted">Std Dev: {formatPrice(volatility.sell_std_dev)} ₫</small>
        </div>
      </>
    );
  };

  const renderExtremes = () => {
    if (!extremes) return null;

    return (
      <>
        <div className="mb-3">
          <h6 className="text-muted">Buy Price Range (30 days)</h6>
          <div className="d-flex justify-content-between">
            <div>
              <small className="text-muted">Min:</small>
              <div className="fw-bold text-success">{formatPrice(extremes.buy_min)} ₫</div>
              <small className="text-muted">{formatDate(extremes.buy_min_date)}</small>
            </div>
            <div>
              <small className="text-muted">Max:</small>
              <div className="fw-bold text-danger">{formatPrice(extremes.buy_max)} ₫</div>
              <small className="text-muted">{formatDate(extremes.buy_max_date)}</small>
            </div>
          </div>
        </div>
        <div>
          <h6 className="text-muted">Sell Price Range (30 days)</h6>
          <div className="d-flex justify-content-between">
            <div>
              <small className="text-muted">Min:</small>
              <div className="fw-bold text-success">{formatPrice(extremes.sell_min)} ₫</div>
              <small className="text-muted">{formatDate(extremes.sell_min_date)}</small>
            </div>
            <div>
              <small className="text-muted">Max:</small>
              <div className="fw-bold text-danger">{formatPrice(extremes.sell_max)} ₫</div>
              <small className="text-muted">{formatDate(extremes.sell_max_date)}</small>
            </div>
          </div>
        </div>
      </>
    );
  };

  return (
  <Row className="fade-in g-4 align-items-stretch">
      <Col xs={12} lg={4} className="d-flex">
        <Card className="w-100 analytics-card">
          <Card.Header style={{
            background: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
            color: 'white',
            borderBottom: 'none',
            padding: '1.25rem 1.5rem'
          }}>
            <div className="d-flex align-items-center gap-2">
              <div className="d-flex align-items-center justify-content-center" style={{
                width: '40px',
                height: '40px',
                background: 'rgba(255, 255, 255, 0.2)',
                borderRadius: '10px'
              }}>
                <i className="fas fa-chart-line"></i>
              </div>
              <h5 className="mb-0 fw-bold">Price Change</h5>
            </div>
            <small className="text-white-50 mt-1 d-block" style={{ fontSize: '0.8rem' }}>7-day trend analysis</small>
          </Card.Header>
          <Card.Body>
            {renderPriceChange()}
          </Card.Body>
        </Card>
      </Col>

      <Col xs={12} lg={4} className="d-flex">
        <Card className="w-100 analytics-card">
          <Card.Header style={{
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            color: 'white',
            borderBottom: 'none',
            padding: '1.25rem 1.5rem'
          }}>
            <div className="d-flex align-items-center gap-2">
              <div className="d-flex align-items-center justify-content-center" style={{
                width: '40px',
                height: '40px',
                background: 'rgba(255, 255, 255, 0.2)',
                borderRadius: '10px'
              }}>
                <i className="fas fa-wave-square"></i>
              </div>
              <h5 className="mb-0 fw-bold">Volatility</h5>
            </div>
            <small className="text-white-50 mt-1 d-block" style={{ fontSize: '0.8rem' }}>30-day price fluctuation</small>
          </Card.Header>
          <Card.Body>
            {renderVolatility()}
          </Card.Body>
        </Card>
      </Col>

      <Col xs={12} lg={4} className="d-flex">
        <Card className="w-100 analytics-card">
          <Card.Header style={{
            background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
            color: 'white',
            borderBottom: 'none',
            padding: '1.25rem 1.5rem'
          }}>
            <div className="d-flex align-items-center gap-2">
              <div className="d-flex align-items-center justify-content-center" style={{
                width: '40px',
                height: '40px',
                background: 'rgba(255, 255, 255, 0.2)',
                borderRadius: '10px'
              }}>
                <i className="fas fa-arrows-alt-v"></i>
              </div>
              <h5 className="mb-0 fw-bold">Price Extremes</h5>
            </div>
            <small className="text-white-50 mt-1 d-block" style={{ fontSize: '0.8rem' }}>High and low prices</small>
          </Card.Header>
          <Card.Body>
            {renderExtremes()}
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default AnalyticsCards;

