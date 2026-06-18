import React, { useState, useEffect } from 'react';
import { Card, Table, Form, Badge, Spinner, Alert } from 'react-bootstrap';
import axios from 'axios';

const formatPrice = (price) => {
  if (!price) return 'N/A';
  return new Intl.NumberFormat('vi-VN').format(price);
};

const formatDateLabel = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const CompletePriceTable = ({ prices }) => {
  const [filterCompany, setFilterCompany] = useState('ALL');
  const [sortBy, setSortBy] = useState('company');
  const [selectedDate, setSelectedDate] = useState('current');
  const [availableDates, setAvailableDates] = useState([]);
  const [historicalPrices, setHistoricalPrices] = useState(null);
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available dates from CSV on component mount
  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await axios.get('/api/available-dates');
        setAvailableDates(response.data.dates || []);
      } catch (err) {
        console.error('Error fetching available dates:', err);
      }
    };

    fetchAvailableDates();
  }, []);

  // Fetch historical prices when date is selected
  useEffect(() => {
    if (selectedDate === 'current') {
      setHistoricalPrices(null);
      setError(null);
      return;
    }

    const fetchHistoricalPrices = async () => {
      setLoadingHistorical(true);
      setError(null);

      try {
        const response = await axios.get(`/api/prices-by-date?date=${selectedDate}`);
        setHistoricalPrices(response.data);
      } catch (err) {
        console.error('Error fetching historical prices:', err);
        setError('Failed to load historical prices for selected date');
        setHistoricalPrices(null);
      } finally {
        setLoadingHistorical(false);
      }
    };

    fetchHistoricalPrices();
  }, [selectedDate]);

  if (!prices) {
    return (
      <Card className="dashboard-card h-100 w-100">
        <Card.Header className="bg-info text-white">
          <h5 className="mb-0">
            <i className="fas fa-table me-2"></i>Complete Price List
          </h5>
        </Card.Header>
        <Card.Body>
          <p className="text-muted">Loading price data...</p>
        </Card.Body>
      </Card>
    );
  }

  // Use historical prices if date is selected, otherwise use current prices
  const displayPrices = selectedDate === 'current' ? prices : historicalPrices;

  // Collect all gold types from SJC only (DOJI and PNJ removed)
  const allPrices = [];

  // SJC Gold Types
  if (displayPrices && displayPrices.sjc && displayPrices.sjc.results && displayPrices.sjc.results.length > 0) {
    const sjc = displayPrices.sjc.results[0];

    // SJC 1L
    if (sjc.buy_1l) {
      allPrices.push({
        company: 'SJC',
        type: 'SJC 1L (1 Lượng)',
        category: 'Gold Bar',
        purity: '99.99%',
        location: 'National',
        buy: parseFloat(sjc.buy_1l),
        sell: parseFloat(sjc.sell_1l)
      });
    }

    // SJC Ring 1C
    if (sjc.buy_nhan1c) {
      allPrices.push({
        company: 'SJC',
        type: 'SJC Ring 1C (Nhẫn)',
        category: 'Ring',
        purity: '99.99%',
        location: 'National',
        buy: parseFloat(sjc.buy_nhan1c),
        sell: parseFloat(sjc.sell_nhan1c)
      });
    }

    // SJC Jewelry 24K
    if (sjc.buy_nutrang_9999) {
      allPrices.push({
        company: 'SJC',
        type: 'SJC Jewelry 24K',
        category: 'Jewelry',
        purity: '99.99%',
        location: 'National',
        buy: parseFloat(sjc.buy_nutrang_9999),
        sell: parseFloat(sjc.sell_nutrang_9999)
      });
    }

    // SJC Jewelry 99%
    if (sjc.buy_nutrang_99) {
      allPrices.push({
        company: 'SJC',
        type: 'SJC Jewelry 99%',
        category: 'Jewelry',
        purity: '99%',
        location: 'National',
        buy: parseFloat(sjc.buy_nutrang_99),
        sell: parseFloat(sjc.sell_nutrang_99)
      });
    }

    // SJC Jewelry 18K
    if (sjc.buy_nutrang_75) {
      allPrices.push({
        company: 'SJC',
        type: 'SJC Jewelry 18K',
        category: 'Jewelry',
        purity: '75%',
        location: 'National',
        buy: parseFloat(sjc.buy_nutrang_75),
        sell: parseFloat(sjc.sell_nutrang_75)
      });
    }
  }

  // DOJI and PNJ removed - only SJC data is displayed

  // Filter by company (only SJC now, but keeping filter for consistency)
  let filteredPrices = allPrices;
  if (filterCompany !== 'ALL' && filterCompany !== 'SJC') {
    filteredPrices = [];
  }

  // Sort prices
  filteredPrices.sort((a, b) => {
    if (sortBy === 'company') {
      return a.company.localeCompare(b.company);
    } else if (sortBy === 'buy_asc') {
      return a.buy - b.buy;
    } else if (sortBy === 'buy_desc') {
      return b.buy - a.buy;
    } else if (sortBy === 'purity') {
      return parseFloat(b.purity) - parseFloat(a.purity);
    }
    return 0;
  });

  const getCompanyBadge = (company) => {
    const badges = {
      'SJC': 'danger',
      'DOJI': 'primary',
      'PNJ': 'success'
    };
    return badges[company] || 'secondary';
  };

  const getCategoryIcon = (category) => {
    const icons = {
      'Gold Bar': 'fa-bars',
      'Ring': 'fa-ring',
      'Jewelry': 'fa-gem'
    };
    return icons[category] || 'fa-circle';
  };

  return (
  <Card className="dashboard-card insight-card fade-in h-100 w-100">
      <Card.Header className="insight-header">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h5 className="mb-1">
              <i className="fas fa-table me-2"></i>Complete Price List
            </h5>
            <small className="text-muted" style={{ fontSize: '0.8rem' }}>
              SJC gold types with live market data
            </small>
          </div>
          <Badge 
            bg="primary" 
            className="px-3 py-2" 
            style={{ 
              fontSize: '0.85rem',
              borderRadius: '12px',
              fontWeight: '700'
            }}
          >
            {filteredPrices.length} items
          </Badge>
        </div>
      </Card.Header>
      <Card.Body>
        {/* Error Message */}
        {error && (
          <Alert variant="danger" className="mb-3">
            <i className="fas fa-exclamation-triangle me-2"></i>
            {error}
          </Alert>
        )}

        {/* Enhanced Filters */}
        <div className="row mb-3 g-3">
          <div className="col-12 col-lg-4">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase" style={{ 
                fontSize: '0.75rem',
                letterSpacing: '0.05em',
                color: '#64748b'
              }}>
                <i className="fas fa-calendar me-1"></i>Select Date
              </Form.Label>
              <Form.Select
                className="insight-config-select"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                disabled={loadingHistorical}
                style={{
                  borderRadius: '12px',
                  borderWidth: '2px',
                  padding: '0.6rem 0.85rem',
                  fontWeight: '600'
                }}
              >
                <option value="current">Current Prices</option>
                {availableDates.length > 0 && <option disabled>──────────</option>}
                {availableDates.map((date) => (
                  <option key={date} value={date}>
                    {formatDateLabel(date)}
                  </option>
                ))}
              </Form.Select>
              {loadingHistorical && (
                <div className="mt-1">
                  <Spinner animation="border" size="sm" className="me-1" />
                  <small className="text-muted">Loading...</small>
                </div>
              )}
            </Form.Group>
          </div>
          <div className="col-12 col-lg-4">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase" style={{ 
                fontSize: '0.75rem',
                letterSpacing: '0.05em',
                color: '#64748b'
              }}>
                <i className="fas fa-building me-1"></i>Filter by Company
              </Form.Label>
              <Form.Select
                className="insight-config-select"
                value={filterCompany}
                onChange={(e) => setFilterCompany(e.target.value)}
                style={{
                  borderRadius: '12px',
                  borderWidth: '2px',
                  padding: '0.6rem 0.85rem',
                  fontWeight: '600'
                }}
              >
                <option value="ALL">All Companies</option>
                <option value="SJC">SJC Only</option>
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-12 col-lg-4">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase" style={{ 
                fontSize: '0.75rem',
                letterSpacing: '0.05em',
                color: '#64748b'
              }}>
                <i className="fas fa-sort me-1"></i>Sort By
              </Form.Label>
              <Form.Select
                className="insight-config-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                style={{
                  borderRadius: '12px',
                  borderWidth: '2px',
                  padding: '0.6rem 0.85rem',
                  fontWeight: '600'
                }}
              >
                <option value="company">Company Name</option>
                <option value="buy_asc">Buy Price (Low to High)</option>
                <option value="buy_desc">Buy Price (High to Low)</option>
                <option value="purity">Purity (High to Low)</option>
              </Form.Select>
            </Form.Group>
          </div>
        </div>

        {/* Price Table */}
  <div className="table-responsive table-scroll">
          <Table striped bordered hover size="sm" className="mb-0">
            <thead className="table-dark">
              <tr>
                <th>Company</th>
                <th>Gold Type</th>
                <th>Category</th>
                <th>Purity</th>
                <th>Location</th>
                <th className="text-end">Buy Price (₫)</th>
                <th className="text-end">Sell Price (₫)</th>
                <th className="text-end">Spread (₫)</th>
              </tr>
            </thead>
            <tbody>
              {filteredPrices.map((item, idx) => (
                <tr key={idx}>
                  <td>
                    <Badge bg={getCompanyBadge(item.company)}>
                      {item.company}
                    </Badge>
                  </td>
                  <td className="small">{item.type}</td>
                  <td className="small">
                    <i className={`fas ${getCategoryIcon(item.category)} me-1`}></i>
                    {item.category}
                  </td>
                  <td className="small text-center">{item.purity}</td>
                  <td className="small">{item.location}</td>
                  <td className="text-end buy-price fw-bold">{formatPrice(item.buy)}</td>
                  <td className="text-end sell-price fw-bold">{formatPrice(item.sell)}</td>
                  <td className="text-end small text-muted">
                    {formatPrice(item.sell - item.buy)}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </Card.Body>
      <Card.Footer className="text-muted small">
        <i className="fas fa-info-circle me-1"></i>
        {selectedDate === 'current'
          ? 'Showing current SJC gold prices (5 types) - 100% Real Data from API'
          : `Showing historical SJC prices from ${formatDateLabel(selectedDate)}`
        }
      </Card.Footer>
    </Card>
  );
};

export default CompletePriceTable;

