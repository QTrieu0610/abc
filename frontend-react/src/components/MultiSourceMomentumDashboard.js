import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import axios from 'axios';

const formatPrice = (price) => {
  if (price === null || price === undefined || price === '') return 'N/A';
  const numeric = Number(price);
  if (!Number.isFinite(numeric)) return 'N/A';
  return new Intl.NumberFormat('vi-VN').format(Math.abs(numeric));
};

const formatSignedPrice = (price) => {
  if (price === null || price === undefined || price === '') return 'N/A';
  const numeric = Number(price);
  if (!Number.isFinite(numeric)) return 'N/A';
  const sign = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  return `${sign}${formatPrice(numeric)} VND`;
};

const formatPercent = (percent) => {
  if (percent === null || percent === undefined || percent === '') return 'N/A';
  const numeric = Number(percent);
  if (!Number.isFinite(numeric)) return 'N/A';
  const sign = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  return `${sign}${Math.abs(numeric).toFixed(2)}%`;
};

const formatDateTime = (value) => {
  if (!value) return 'N/A';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const companyVariant = (company) => {
  if (company === 'DOJI') return 'primary';
  if (company === 'PNJ') return 'success';
  return 'danger';
};

const directionMeta = {
  up: { icon: 'fa-arrow-up', tone: '#16a34a', label: 'Up' },
  down: { icon: 'fa-arrow-down', tone: '#dc2626', label: 'Down' },
  flat: { icon: 'fa-minus', tone: '#64748b', label: 'Flat' },
  no_data: { icon: 'fa-circle-minus', tone: '#94a3b8', label: 'No prior' }
};

const primaryDirection = (item) => {
  if (item.status !== 'ok') return 'no_data';
  return item.sell_direction !== 'no_data' ? item.sell_direction : item.buy_direction;
};

const MetricRow = ({ label, current, previous, change, percent, direction }) => {
  const meta = directionMeta[direction] || directionMeta.no_data;
  const hasPrevious = previous !== null && previous !== undefined && previous !== '';

  return (
    <div className="d-flex align-items-center justify-content-between gap-3 py-2 border-bottom">
      <div>
        <div className="small text-muted text-uppercase fw-bold">{label}</div>
        <div className="fw-bold" style={{ fontSize: '1.05rem' }}>
          {formatPrice(current)}
          <span className="text-muted fw-normal ms-1">VND</span>
        </div>
        <small className="text-muted">
          Previous: {hasPrevious ? `${formatPrice(previous)} VND` : 'No saved row in CSV'}
        </small>
      </div>
      <div className="text-end" style={{ color: meta.tone, minWidth: '120px' }}>
        <div className="fw-bold">
          <i className={`fas ${meta.icon} me-2`}></i>
          {formatSignedPrice(change)}
        </div>
        <small>{formatPercent(percent)}</small>
      </div>
    </div>
  );
};

const SpreadRow = ({ item }) => {
  const direction = item.spread_change === null || item.spread_change === undefined
    ? 'no_data'
    : item.spread_change > 0
      ? 'up'
      : item.spread_change < 0
        ? 'down'
        : 'flat';
  const meta = directionMeta[direction] || directionMeta.no_data;

  return (
    <div className="d-flex align-items-center justify-content-between gap-3 pt-2">
      <div>
        <div className="small text-muted text-uppercase fw-bold">Spread</div>
        <div className="fw-bold">{formatPrice(item.spread)} VND</div>
      </div>
      <div className="text-end" style={{ color: meta.tone, minWidth: '120px' }}>
        <div className="fw-bold">
          <i className={`fas ${meta.icon} me-2`}></i>
          {formatSignedPrice(item.spread_change)}
        </div>
        <small>vs previous</small>
      </div>
    </div>
  );
};

const MomentumCard = ({ item }) => {
  const direction = primaryDirection(item);
  const meta = directionMeta[direction] || directionMeta.no_data;
  const hasComparison = item.status === 'ok';

  return (
    <Col xs={12} xl={4} className="d-flex">
      <Card className="dashboard-card h-100 w-100" style={{ borderRadius: '16px' }}>
        <Card.Header className="d-flex align-items-start justify-content-between gap-3">
          <div>
            <Badge bg={companyVariant(item.company)} className="mb-2">{item.company}</Badge>
            <h5 className="mb-1 fw-bold">{item.gold_type}</h5>
            <small className="text-muted">{item.location}</small>
          </div>
          <div className="text-end" style={{ color: meta.tone }}>
            <i className={`fas ${meta.icon}`} style={{ fontSize: '1.5rem' }}></i>
            <div className="small fw-bold">{meta.label}</div>
          </div>
        </Card.Header>
        <Card.Body>
          {!hasComparison && (
            <div className="d-flex align-items-center gap-2 mb-3 px-3 py-2 rounded-3" style={{
              background: 'rgba(148, 163, 184, 0.12)',
              border: '1px solid rgba(148, 163, 184, 0.25)',
              color: '#475569'
            }}>
              <i className="fas fa-database"></i>
              <small className="fw-semibold">
                Latest price is available, but this source has no previous saved row in CSV yet.
              </small>
            </div>
          )}
          <MetricRow
            label="Buy"
            current={item.latest_buy}
            previous={item.previous_buy}
            change={item.buy_change}
            percent={item.buy_change_percent}
            direction={item.buy_direction}
          />
          <MetricRow
            label="Sell"
            current={item.latest_sell}
            previous={item.previous_sell}
            change={item.sell_change}
            percent={item.sell_change_percent}
            direction={item.sell_direction}
          />
          <SpreadRow item={item} />
        </Card.Body>
        <Card.Footer className="small text-muted">
          Latest: {formatDateTime(item.latest_timestamp)}
          <span className="mx-2">|</span>
          Previous: {item.previous_timestamp ? formatDateTime(item.previous_timestamp) : 'No saved row'}
        </Card.Footer>
      </Card>
    </Col>
  );
};

const SummaryTile = ({ icon, label, value, color }) => (
  <Col xs={6} lg={3}>
    <div className="d-flex align-items-center gap-3 p-3 rounded-3 h-100" style={{
      background: 'rgba(255, 255, 255, 0.75)',
      border: '1px solid rgba(15, 23, 42, 0.08)'
    }}>
      <div className="d-flex align-items-center justify-content-center rounded-circle" style={{
        width: '40px',
        height: '40px',
        background: color,
        color: '#fff'
      }}>
        <i className={`fas ${icon}`}></i>
      </div>
      <div>
        <div className="small text-muted fw-bold text-uppercase">{label}</div>
        <div className="h4 mb-0 fw-bold">{value}</div>
      </div>
    </div>
  </Col>
);

const MultiSourceMomentumDashboard = ({ dataRefreshTrigger }) => {
  const [scope, setScope] = useState('main');
  const [momentum, setMomentum] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMomentum();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, dataRefreshTrigger]);

  const fetchMomentum = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/analytics/source-momentum', {
        params: { scope, compare: 'previous' }
      });
      setMomentum(response.data);
    } catch (err) {
      console.error('Error fetching source momentum:', err);
      setError('Unable to load source momentum right now.');
    } finally {
      setLoading(false);
    }
  };

  const items = momentum?.items || [];
  const summary = useMemo(() => {
    if (momentum?.summary) return momentum.summary;
    return {
      sources_up: 0,
      sources_down: 0,
      unchanged: 0,
      missing_comparison: 0
    };
  }, [momentum]);

  return (
    <Card className="dashboard-card insight-card fade-in w-100">
      <Card.Header className="insight-header">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
          <div>
            <h5 className="mb-1">
              <i className="fas fa-arrow-trend-up me-2"></i>Multi-Source Momentum
            </h5>
            <small className="text-muted">Latest crawl compared with the previous saved crawl</small>
          </div>
          <Form.Select
            size="sm"
            value={scope}
            onChange={(event) => setScope(event.target.value)}
            style={{ width: '170px' }}
          >
            <option value="main">Main Sources</option>
            <option value="all">All Sources</option>
          </Form.Select>
        </div>
      </Card.Header>
      <Card.Body>
        {loading ? (
          <div className="text-center py-5">
            <Spinner animation="border" variant="warning" />
            <p className="text-muted mb-0 mt-3">Loading source momentum...</p>
          </div>
        ) : error ? (
          <Alert variant="danger" className="mb-0">{error}</Alert>
        ) : (
          <>
            <Row className="g-3 mb-4">
              <SummaryTile icon="fa-arrow-up" label="Sources Up" value={summary.sources_up} color="#16a34a" />
              <SummaryTile icon="fa-arrow-down" label="Sources Down" value={summary.sources_down} color="#dc2626" />
              <SummaryTile icon="fa-minus" label="Unchanged" value={summary.unchanged} color="#64748b" />
              <SummaryTile icon="fa-circle-question" label="No Previous Row" value={summary.missing_comparison} color="#94a3b8" />
            </Row>

            {items.length === 0 ? (
              <Alert variant="secondary" className="mb-0">No saved source rows available for comparison.</Alert>
            ) : (
              <Row className="g-4">
                {items.map((item) => (
                  <MomentumCard
                    key={`${item.company}-${item.location}-${item.gold_type}`}
                    item={item}
                  />
                ))}
              </Row>
            )}
          </>
        )}
      </Card.Body>
    </Card>
  );
};

export default MultiSourceMomentumDashboard;
