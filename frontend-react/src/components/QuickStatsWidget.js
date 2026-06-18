import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Badge, Spinner } from 'react-bootstrap';
import axios from 'axios';

const formatPrice = (price) => {
  if (!price) return 'N/A';
  return new Intl.NumberFormat('vi-VN').format(price);
};

const QuickStatsWidget = ({ prices }) => {
  const [weeklyChange, setWeeklyChange] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchWeeklyChange();
  }, []);

  const fetchWeeklyChange = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/analytics/price-change', {
        params: { company: 'SJC', days: 7 }
      });
      setWeeklyChange(response.data);
    } catch (error) {
      console.error('Error fetching weekly change:', error);
    } finally {
      setLoading(false);
    }
  };

  const sjcData = prices?.sjc?.results?.[0];

  if (!sjcData && !weeklyChange) {
    return null;
  }

  const spread = sjcData?.buy_1l && sjcData?.sell_1l
    ? parseFloat(sjcData.sell_1l) - parseFloat(sjcData.buy_1l)
    : null;

  const spreadPercent = spread && sjcData?.buy_1l
    ? (spread / parseFloat(sjcData.buy_1l)) * 100
    : null;

  const buyChange = weeklyChange?.buy_change || null;
  const buyChangePercent = weeklyChange?.buy_change_percent || null;
  const buyTrendColor = buyChange >= 0 ? 'success' : 'danger';
  const buyTrendIcon = buyChange >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';

  const renderQuickStat = (icon, label, value, badge, badgeVariant = 'secondary') => (
    <Col xs={6} md={3} className="mb-3">
      <Card className="quick-stat-card h-100 border-0">
        <Card.Body className="d-flex flex-column align-items-center justify-content-center text-center p-3">
          <div className="quick-stat-icon mb-2">
            <i className={`fas ${icon}`}></i>
          </div>
          <h6 className="quick-stat-label text-muted mb-2">{label}</h6>
          <h4 className="quick-stat-value mb-2">{value}</h4>
          {badge && (
            <Badge bg={badgeVariant} className="quick-stat-badge">
              {badge}
            </Badge>
          )}
        </Card.Body>
      </Card>
    </Col>
  );

  return (
    <Card className="dashboard-card quick-stats-widget mb-0">
      <Card.Header className="bg-white border-bottom">
        <div className="d-flex align-items-center justify-content-between">
          <h5 className="mb-0">
            <i className="fas fa-chart-pie me-2"></i>Quick Market Stats
          </h5>
          <Badge bg="light" text="dark" className="small">
            <i className="fas fa-sync-alt me-1"></i>Live
          </Badge>
        </div>
      </Card.Header>
      <Card.Body>
        {loading ? (
          <div className="text-center py-4">
            <Spinner animation="border" variant="primary" size="sm" />
            <p className="text-muted mt-2 mb-0 small">Loading stats...</p>
          </div>
        ) : (
          <Row className="g-3">
            {renderQuickStat(
              'fa-balance-scale',
              'Current Spread',
              spread ? `${formatPrice(spread)} ₫` : 'N/A',
              spreadPercent ? `${spreadPercent.toFixed(2)}%` : null,
              'info'
            )}
            {renderQuickStat(
              buyTrendIcon,
              '7-Day Change',
              buyChange !== null ? `${formatPrice(Math.abs(buyChange))} ₫` : 'N/A',
              buyChangePercent !== null ? `${buyChangePercent.toFixed(2)}%` : null,
              buyTrendColor
            )}
            {renderQuickStat(
              'fa-coins',
              'Buy Price (1L)',
              sjcData?.buy_1l ? `${formatPrice(sjcData.buy_1l)} ₫` : 'N/A',
              'SJC Gold Bar',
              'warning'
            )}
            {renderQuickStat(
              'fa-hand-holding-usd',
              'Sell Price (1L)',
              sjcData?.sell_1l ? `${formatPrice(sjcData.sell_1l)} ₫` : 'N/A',
              'SJC Gold Bar',
              'primary'
            )}
          </Row>
        )}
      </Card.Body>
    </Card>
  );
};

export default QuickStatsWidget;
