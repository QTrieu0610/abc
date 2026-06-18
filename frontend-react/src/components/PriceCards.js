import React, { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Form, Spinner, Table } from 'react-bootstrap';
import axios from 'axios';

const formatPrice = (price) => {
  if (price === null || price === undefined || price === '') return 'N/A';
  const numeric = Number(price);
  if (!Number.isFinite(numeric)) return 'N/A';
  return new Intl.NumberFormat('vi-VN').format(numeric);
};

const toPrice = (price) => {
  const numeric = Number(price);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null;
};

const getSpread = (row) => {
  if (!row || row.buy === null || row.sell === null || row.sell < row.buy) return null;
  return row.sell - row.buy;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const statusVariant = (status) => {
  if (status === 'ok') return 'success';
  if (status === 'empty') return 'secondary';
  return 'danger';
};

const buildRows = (data) => {
  const rows = [];
  const sjc = data?.sjc?.results?.[0];

  const addSjc = (fieldBuy, fieldSell, type, category, purity) => {
    if (!sjc?.[fieldBuy] && !sjc?.[fieldSell]) return;
    rows.push({
      company: 'SJC',
      location: 'National',
      type,
      category,
      purity,
      buy: toPrice(sjc[fieldBuy]),
      sell: toPrice(sjc[fieldSell])
    });
  };

  addSjc('buy_1l', 'sell_1l', 'SJC 1L', 'Gold Bar', '99.99%');
  addSjc('buy_nhan1c', 'sell_nhan1c', 'SJC Ring 1C', 'Ring', '99.99%');
  addSjc('buy_nutrang_9999', 'sell_nutrang_9999', 'SJC Jewelry 24K', 'Jewelry', '99.99%');
  addSjc('buy_nutrang_99', 'sell_nutrang_99', 'SJC Jewelry 99%', 'Jewelry', '99%');
  addSjc('buy_nutrang_75', 'sell_nutrang_75', 'SJC Jewelry 18K', 'Jewelry', '75%');

  ['doji', 'pnj'].forEach((sourceKey) => {
    data?.[sourceKey]?.results?.forEach((item) => {
      const company = item.company || sourceKey.toUpperCase();
      rows.push({
        company,
        location: item.location || 'Unknown',
        type: item.gold_type || `${company} Gold`,
        category: item.gold_type?.toLowerCase().includes('trang') ? 'Jewelry' : 'Gold Bar',
        purity: item.gold_type?.includes('99.9') || item.gold_type?.includes('9999') ? '99.9%+' : '99%',
        buy: toPrice(item.buy_price),
        sell: toPrice(item.sell_price)
      });
    });
  });

  return rows.filter((row) => row.buy !== null || row.sell !== null);
};

const PriceCards = ({ prices }) => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [historicalPrices, setHistoricalPrices] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('current');
  const [latestAvailableDate, setLatestAvailableDate] = useState(null);

  useEffect(() => {
    const fetchLatestDate = async () => {
      try {
        const response = await axios.get('/api/available-dates');
        const latest = response.data?.dates?.[0];
        if (latest) {
          setLatestAvailableDate(latest);
          setSelectedDate(latest);
        }
      } catch (error) {
        console.error('Error fetching available dates:', error);
      }
    };

    fetchLatestDate();
  }, []);

  const fetchHistoricalData = async (date) => {
    if (!date) return;
    setLoading(true);
    try {
      const response = await axios.get('/api/prices-by-date', { params: { date } });
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

  const handleDateChange = (event) => {
    const date = event.target.value;
    setSelectedDate(date);

    const currentDate = latestAvailableDate || new Date().toISOString().split('T')[0];
    if (date === currentDate) {
      setHistoricalPrices(null);
      setViewMode('current');
    } else {
      fetchHistoricalData(date);
    }
  };

  const handleViewCurrent = () => {
    const currentDate = latestAvailableDate || new Date().toISOString().split('T')[0];
    setSelectedDate(currentDate);
    setHistoricalPrices(null);
    setViewMode('current');
  };

  const displayData = viewMode === 'historical' && historicalPrices ? historicalPrices : prices;
  const rows = useMemo(() => buildRows(displayData), [displayData]);

  const sjcMain = rows.find((row) => row.company === 'SJC' && row.type === 'SJC 1L');
  const dojiMain =
    rows.find((row) => row.company === 'DOJI' && row.location === 'Hanoi' && row.type === 'SJC - Ban Le') ||
    rows.find((row) => row.company === 'DOJI' && row.location === 'Hanoi' && row.type === 'SJC - Bán Lẻ') ||
    rows.find((row) => row.company === 'DOJI' && row.type?.toLowerCase().includes('sjc')) ||
    rows.find((row) => row.company === 'DOJI');
  const pnjMain =
    rows.find((row) => row.company === 'PNJ' && row.location === 'Ho Chi Minh City' && row.type?.toLowerCase().includes('sjc')) ||
    rows.find((row) => row.company === 'PNJ' && row.type?.toLowerCase().includes('sjc')) ||
    rows.find((row) => row.company === 'PNJ');

  const bestBuy = rows.reduce((best, row) => {
    if (row.buy === null) return best;
    return !best || row.buy > best.buy ? row : best;
  }, null);
  const bestSell = rows.reduce((best, row) => {
    if (row.sell === null) return best;
    return !best || row.sell < best.sell ? row : best;
  }, null);
  const lowestSpread = rows.reduce((best, row) => {
    const spread = getSpread(row);
    const bestSpread = getSpread(best);
    if (spread === null) return best;
    if (!best || bestSpread === null || spread < bestSpread) return row;
    return best;
  }, null);

  const sjcGap = sjcMain && dojiMain && sjcMain.sell !== null && dojiMain.sell !== null
    ? dojiMain.sell - sjcMain.sell
    : null;
  const pnjGap = sjcMain && pnjMain && sjcMain.sell !== null && pnjMain.sell !== null
    ? pnjMain.sell - sjcMain.sell
    : null;

  const renderMarketCard = (title, subtitle, row, source) => (
    <div className="col-12 col-md-6 col-xxl-4 d-flex">
      <Card className="price-card price-hero-card border-0 w-100">
        <div className="price-hero-banner text-white">
          <div className="banner-main">
            <div className="d-flex align-items-center gap-3 mb-3">
              <span className="price-hero-icon">
                <i className="fas fa-coins"></i>
              </span>
              <div>
                <p className="text-uppercase text-white-50 small mb-1">{subtitle}</p>
                <h2 className="price-hero-title mb-0">{title}</h2>
              </div>
            </div>
            <div className="price-hero-values">
              <div className="price-hero-value buy">
                <span className="label">Buy</span>
                <span className="value">
                  {formatPrice(row?.buy)}
                  <span className="currency">VND</span>
                </span>
              </div>
              <div className="price-hero-divider" aria-hidden="true"></div>
              <div className="price-hero-value sell">
                <span className="label">Sell</span>
                <span className="value">
                  {formatPrice(row?.sell)}
                  <span className="currency">VND</span>
                </span>
              </div>
            </div>
          </div>
          <div className="banner-meta text-lg-end">
            <Badge bg={statusVariant(source?.status)} className="price-hero-badge">
              {source?.status || 'empty'}
            </Badge>
            <p className="hero-subtext text-white-50 mb-0">{row?.location || 'No location'} · {row?.type || 'No data'}</p>
          </div>
        </div>
      </Card>
    </div>
  );

  const renderInsight = (label, row, value, icon) => (
    <div className="hero-stat">
      <span className="hero-stat-label">
        <i className={`fas ${icon} me-2`}></i>{label}
      </span>
      <span className="hero-stat-value">{value}</span>
      <small className="text-muted">
        {row ? `${row.company} · ${row.location} · ${row.type}` : 'Awaiting data'}
      </small>
    </div>
  );

  if (!displayData && !loading) {
    return (
      <Card className="price-card price-hero-card border-0 w-100">
        <Card.Body className="price-hero-body text-center py-5">
          <Spinner animation="border" variant="warning" className="spinner-glow" />
          <p className="text-muted mb-0 fw-semibold mt-3">Loading live market prices...</p>
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="price-card price-hero-card border-0 w-100 fade-in">
      <div className="price-date-header" style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
        padding: '1rem 1.5rem',
        borderBottom: '2px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
          <div className="d-flex align-items-center gap-2">
            <i className="fas fa-calendar-alt text-white-50"></i>
            <span className="text-white fw-semibold small">View SJC + DOJI + PNJ Prices By Date</span>
          </div>
          <div className="d-flex gap-2 align-items-center">
            {viewMode === 'historical' && (
              <Button variant="outline-light" size="sm" onClick={handleViewCurrent}>
                <i className="fas fa-sync-alt me-2"></i>Current Prices
              </Button>
            )}
            <Form.Control
              type="date"
              value={selectedDate}
              onChange={handleDateChange}
              max={latestAvailableDate || new Date().toISOString().split('T')[0]}
              size="sm"
              style={{ width: '155px' }}
              disabled={loading}
            />
            {loading && <Spinner animation="border" size="sm" variant="light" />}
          </div>
        </div>
        {viewMode === 'historical' && selectedDate && (
          <Badge bg="info" className="mt-2">
            <i className="fas fa-history me-1"></i>Historical Data: {formatDate(selectedDate)}
          </Badge>
        )}
      </div>

      <Card.Body className="price-hero-body">
        <div className="row g-4 mb-4 market-source-grid">
          {renderMarketCard('SJC Reference Price', 'WebGia/SJC feed', sjcMain, displayData?.sjc)}
          {renderMarketCard('DOJI Market Price', 'Official DOJI feed', dojiMain, displayData?.doji)}
          {renderMarketCard('PNJ Retail Price', 'Official PNJ feed', pnjMain, displayData?.pnj)}
        </div>

        <div className="price-hero-stats">
          {renderInsight('Best Buy', bestBuy, bestBuy ? `${formatPrice(bestBuy.buy)} VND` : 'N/A', 'fa-arrow-up')}
          {renderInsight('Best Sell', bestSell, bestSell ? `${formatPrice(bestSell.sell)} VND` : 'N/A', 'fa-arrow-down')}
          {renderInsight(
            'Lowest Spread',
            lowestSpread,
            lowestSpread ? `${formatPrice(getSpread(lowestSpread))} VND` : 'N/A',
            'fa-arrows-left-right'
          )}
          {renderInsight(
            'SJC vs DOJI Gap',
            dojiMain,
            sjcGap === null ? 'N/A' : `${sjcGap >= 0 ? '+' : ''}${formatPrice(sjcGap)} VND`,
            'fa-scale-balanced'
          )}
          {renderInsight(
            'SJC vs PNJ Gap',
            pnjMain,
            pnjGap === null ? 'N/A' : `${pnjGap >= 0 ? '+' : ''}${formatPrice(pnjGap)} VND`,
            'fa-scale-balanced'
          )}
        </div>

        {rows.length > 0 && (
          <div className="table-responsive price-hero-table mt-4">
            <Table size="sm" hover className="mb-0">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Region</th>
                  <th>Gold Type</th>
                  <th className="text-end">Buy</th>
                  <th className="text-end">Sell</th>
                  <th className="text-end">Spread</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 10).map((row, index) => (
                  <tr key={`${row.company}-${row.location}-${row.type}-${index}`}>
                    <td><Badge bg={row.company === 'DOJI' ? 'primary' : row.company === 'PNJ' ? 'success' : 'danger'}>{row.company}</Badge></td>
                    <td className="small">{row.location}</td>
                    <td className="small">{row.type}</td>
                    <td className="text-end buy-price fw-bold">{formatPrice(row.buy)}</td>
                    <td className="text-end sell-price fw-bold">{formatPrice(row.sell)}</td>
                    <td className="text-end small text-muted">{formatPrice(getSpread(row))}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Card.Body>

      <Card.Footer className="price-hero-footer text-muted small">
        <i className="fas fa-info-circle me-1"></i>
        Showing WebGia/SJC, official DOJI, and official PNJ feeds
        {viewMode === 'historical' && <span className="ms-2">from {formatDate(selectedDate)}</span>}
      </Card.Footer>
    </Card>
  );
};

export default PriceCards;
