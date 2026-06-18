import React, { useMemo, useState } from 'react';
import { Badge, Card, Form, Table } from 'react-bootstrap';

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

const buildRows = (prices) => {
  const rows = [];
  const sjc = prices?.sjc?.results?.[0];

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
    prices?.[sourceKey]?.results?.forEach((item) => {
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

const CompletePriceTable = ({ prices }) => {
  const [companyFilter, setCompanyFilter] = useState('ALL');
  const [regionFilter, setRegionFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('spread_asc');

  const rows = useMemo(() => buildRows(prices), [prices]);

  const companies = useMemo(() => ['ALL', ...Array.from(new Set(rows.map((row) => row.company)))], [rows]);
  const regions = useMemo(() => ['ALL', ...Array.from(new Set(rows.map((row) => row.location)))], [rows]);
  const types = useMemo(() => ['ALL', ...Array.from(new Set(rows.map((row) => row.type)))], [rows]);

  const filteredRows = useMemo(() => {
    const nextRows = rows.filter((row) => {
      if (companyFilter !== 'ALL' && row.company !== companyFilter) return false;
      if (regionFilter !== 'ALL' && row.location !== regionFilter) return false;
      if (typeFilter !== 'ALL' && row.type !== typeFilter) return false;
      return true;
    });

    nextRows.sort((a, b) => {
      if (sortBy === 'buy_desc') return (b.buy ?? -Infinity) - (a.buy ?? -Infinity);
      if (sortBy === 'sell_asc') return (a.sell ?? Infinity) - (b.sell ?? Infinity);
      if (sortBy === 'spread_asc') return (getSpread(a) ?? Infinity) - (getSpread(b) ?? Infinity);
      if (sortBy === 'company') return `${a.company}${a.location}`.localeCompare(`${b.company}${b.location}`);
      return 0;
    });

    return nextRows;
  }, [rows, companyFilter, regionFilter, typeFilter, sortBy]);

  const getCompanyBadge = (company) => {
    if (company === 'DOJI') return 'primary';
    if (company === 'PNJ') return 'success';
    return 'danger';
  };

  return (
    <Card className="dashboard-card insight-card fade-in h-100 w-100">
      <Card.Header className="insight-header">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h5 className="mb-1">
              <i className="fas fa-table me-2"></i>Complete Market Price List
            </h5>
            <small className="text-muted">SJC, DOJI, and PNJ prices by region, type, and spread</small>
          </div>
          <Badge bg="primary" className="px-3 py-2">{filteredRows.length} items</Badge>
        </div>
      </Card.Header>
      <Card.Body>
        <div className="row mb-3 g-3">
          <div className="col-12 col-lg-3">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase">Company</Form.Label>
              <Form.Select value={companyFilter} onChange={(event) => setCompanyFilter(event.target.value)}>
                {companies.map((company) => <option key={company} value={company}>{company}</option>)}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-12 col-lg-3">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase">Region</Form.Label>
              <Form.Select value={regionFilter} onChange={(event) => setRegionFilter(event.target.value)}>
                {regions.map((region) => <option key={region} value={region}>{region}</option>)}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-12 col-lg-3">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase">Gold Type</Form.Label>
              <Form.Select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                {types.map((type) => <option key={type} value={type}>{type}</option>)}
              </Form.Select>
            </Form.Group>
          </div>
          <div className="col-12 col-lg-3">
            <Form.Group>
              <Form.Label className="small fw-bold text-uppercase">Sort</Form.Label>
              <Form.Select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="spread_asc">Lowest Spread</option>
                <option value="buy_desc">Highest Buy</option>
                <option value="sell_asc">Lowest Sell</option>
                <option value="company">Company / Region</option>
              </Form.Select>
            </Form.Group>
          </div>
        </div>

        <div className="table-responsive table-scroll">
          <Table striped bordered hover size="sm" className="mb-0">
            <thead className="table-dark">
              <tr>
                <th>Company</th>
                <th>Region</th>
                <th>Gold Type</th>
                <th>Category</th>
                <th>Purity</th>
                <th className="text-end">Buy Price</th>
                <th className="text-end">Sell Price</th>
                <th className="text-end">Spread</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((item, index) => (
                <tr key={`${item.company}-${item.location}-${item.type}-${index}`}>
                  <td><Badge bg={getCompanyBadge(item.company)}>{item.company}</Badge></td>
                  <td className="small">{item.location}</td>
                  <td className="small">{item.type}</td>
                  <td className="small">{item.category}</td>
                  <td className="small text-center">{item.purity}</td>
                  <td className="text-end buy-price fw-bold">{formatPrice(item.buy)}</td>
                  <td className="text-end sell-price fw-bold">{formatPrice(item.sell)}</td>
                  <td className="text-end small text-muted">{formatPrice(getSpread(item))}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </Card.Body>
      <Card.Footer className="text-muted small">
        <i className="fas fa-info-circle me-1"></i>
        Showing current rows from all successful crawler sources.
      </Card.Footer>
    </Card>
  );
};

export default CompletePriceTable;
