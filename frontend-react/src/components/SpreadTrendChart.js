import React, { useEffect, useState } from 'react';
import { Card, Form, Spinner } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import axios from 'axios';

const PERIOD_OPTIONS = [
  { value: 'weekly', label: 'Weekly (7 days)' },
  { value: 'monthly', label: 'Monthly (30 days)' },
  { value: 'quarterly', label: 'Quarterly (90 days)' }
];

const GOLD_TYPE_OPTIONS = [
  { value: 'SJC 1L', label: 'SJC 1L (1 Lượng)' },
  { value: 'SJC Ring 1C', label: 'SJC Ring 1C' },
  { value: 'SJC Jewelry 24K', label: 'SJC Jewelry 24K' },
  { value: 'SJC Jewelry 99%', label: 'SJC Jewelry 99%' },
  { value: 'SJC Jewelry 18K', label: 'SJC Jewelry 18K' }
];

const formatCurrency = (value) => {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  return new Intl.NumberFormat('vi-VN').format(Math.round(value));
};

const formatDateLabel = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const SpreadTrendChart = ({ dataRefreshTrigger }) => {
  const [period, setPeriod] = useState('monthly');
  const [goldType, setGoldType] = useState('SJC 1L');
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSpreadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, goldType, dataRefreshTrigger]);

  const fetchSpreadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get('/api/analytics/trends', {
        params: {
          company: 'SJC',
          period,
          gold_type: goldType
        }
      });

      const trends = response.data?.trends;

      if (!trends || !trends.dates || trends.dates.length === 0) {
        setChartData(null);
        setStats(null);
        return;
      }

      const combined = trends.dates
        .map((date, idx) => {
          const buy = Number(trends.buy_prices[idx]);
          const sell = Number(trends.sell_prices[idx]);

          if (!Number.isFinite(buy) || !Number.isFinite(sell)) {
            return null;
          }

          return {
            date,
            spread: sell - buy
          };
        })
        .filter(Boolean);

      if (combined.length === 0) {
        setChartData(null);
        setStats(null);
        return;
      }

      const spreads = combined.map((entry) => entry.spread);
      const labels = combined.map((entry) => formatDateLabel(entry.date));

      const currentSpread = spreads[spreads.length - 1] ?? null;
      const maxSpread = Math.max(...spreads);
      const minSpread = Math.min(...spreads);
      const averageSpread = spreads.reduce((acc, value) => acc + value, 0) / spreads.length;

      setStats({
        currentSpread,
        maxSpread,
        minSpread,
        averageSpread,
        latestDate: combined[combined.length - 1].date
      });

      setChartData({
        labels,
        datasets: [
          {
            label: 'Spread (Million VND)',
            data: spreads.map((value) => value / 1000000),
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.18)',
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 5
          }
        ]
      });
    } catch (err) {
      console.error('Error fetching spread trend data:', err);
      setError('Unable to load spread trend data right now.');
      setChartData(null);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodChange = (event) => {
    setPeriod(event.target.value);
  };

  const handleGoldTypeChange = (event) => {
    setGoldType(event.target.value);
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const value = context.parsed.y;
            return `${value.toFixed(2)} triệu VND`;
          }
        }
      }
    },
    scales: {
      y: {
        title: {
          display: true,
          text: 'Spread (Million VND)'
        },
        ticks: {
          callback: (value) => `${value}M`
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date'
        }
      }
    }
  };

  const renderStatCard = (label, value, helper) => {
    const isNumeric = typeof value === 'number' && !Number.isNaN(value);
    const displayValue = isNumeric ? `${formatCurrency(value)} ₫` : 'N/A';

    return (
      <div className="mini-stat">
        <span className="mini-stat-label">{label}</span>
        <span className="mini-stat-value">{displayValue}</span>
        {helper && <small className="text-muted">{helper}</small>}
      </div>
    );
  };

  return (
    <Card className="dashboard-card insight-card w-100 h-100">
      <Card.Header className="insight-header d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h5 className="mb-1">
            <i className="fas fa-exchange-alt me-2"></i>SJC Spread Trend
          </h5>
          <small className="text-muted">
            Difference between sell and buy prices for selected gold type.
          </small>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <Form.Select
            size="sm"
            value={goldType}
            onChange={handleGoldTypeChange}
            className="insight-period-select"
          >
            {GOLD_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Form.Select>
          <Form.Select
            size="sm"
            value={period}
            onChange={handlePeriodChange}
            className="insight-period-select"
          >
            {PERIOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Form.Select>
        </div>
      </Card.Header>
      <Card.Body>
        {loading ? (
          <div className="insight-loading">
            <Spinner animation="border" variant="warning" />
            <p className="text-muted mt-2 mb-0">Loading spread insights...</p>
          </div>
        ) : error ? (
          <div className="insight-placeholder text-center text-muted py-5">
            <i className="fas fa-exclamation-triangle fa-2x mb-2"></i>
            <p className="mb-0">{error}</p>
          </div>
        ) : chartData ? (
          <>
            {stats && (
              <div className="insight-stats mb-3">
                {renderStatCard(
                  'Current Spread',
                  stats.currentSpread,
                  stats.latestDate
                    ? `Latest update ${formatDateLabel(stats.latestDate)}`
                    : null
                )}
                {renderStatCard('Average Spread', stats.averageSpread)}
                {renderStatCard('Widest Gap', stats.maxSpread)}
                {renderStatCard('Smallest Gap', stats.minSpread)}
              </div>
            )}
            <div className="insight-chart-container">
              <Line data={chartData} options={chartOptions} />
            </div>
          </>
        ) : (
          <div className="insight-placeholder text-center text-muted py-5">
            <i className="fas fa-chart-area fa-3x mb-3"></i>
            <p className="mb-0">No spread data available for the selected period.</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default SpreadTrendChart;
