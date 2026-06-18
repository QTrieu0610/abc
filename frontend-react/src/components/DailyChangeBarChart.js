import React, { useEffect, useMemo, useState } from 'react';
import { Card, Form, Spinner } from 'react-bootstrap';
import { Bar } from 'react-chartjs-2';
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

const DailyChangeBarChart = ({ dataRefreshTrigger }) => {
  const [period, setPeriod] = useState('weekly');
  const [goldType, setGoldType] = useState('SJC 1L');
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchChangeData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, goldType, dataRefreshTrigger]);

  const fetchChangeData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get('/api/analytics/trends', {
        params: {
          company: 'SJC',
          gold_type: goldType,
          period
        }
      });

      const trends = response.data?.trends;

      if (!trends || !trends.dates || trends.dates.length < 2) {
        setChartData(null);
        setStats(null);
        return;
      }

      const entries = trends.dates
        .map((date, idx) => {
          const buy = Number(trends.buy_prices[idx]);

          if (!Number.isFinite(buy)) {
            return null;
          }

          return { date, buy };
        })
        .filter(Boolean);

      if (entries.length < 2) {
        setChartData(null);
        setStats(null);
        return;
      }

      const changes = [];
      const changeLabels = [];

      for (let idx = 1; idx < entries.length; idx += 1) {
        const current = entries[idx];
        const previous = entries[idx - 1];
        changes.push(current.buy - previous.buy);
        changeLabels.push(formatDateLabel(current.date));
      }

      const backgroundColors = changes.map((value) =>
        value >= 0 ? 'rgba(34, 197, 94, 0.75)' : 'rgba(239, 68, 68, 0.75)'
      );

      const borderColors = changes.map((value) =>
        value >= 0 ? 'rgba(22, 163, 74, 1)' : 'rgba(220, 38, 38, 1)'
      );

      const latestChange = changes[changes.length - 1] || null;
      const maxGain = Math.max(...changes);
      const maxDrop = Math.min(...changes);
      const averageChange = changes.reduce((acc, value) => acc + value, 0) / changes.length;

      setStats({ latestChange, maxGain, maxDrop, averageChange });

      setChartData({
        labels: changeLabels,
        datasets: [
          {
            label: 'Daily Change (VND)',
            data: changes.map((value) => value / 1000000),
            backgroundColor: backgroundColors,
            borderColor: borderColors,
            borderWidth: 1,
            borderRadius: 6,
            barPercentage: 0.6,
            categoryPercentage: 0.8
          }
        ]
      });
    } catch (err) {
      console.error('Error fetching daily change data:', err);
      setError('Unable to load daily change data right now.');
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

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = context.parsed.y;
              const millionValue = value.toFixed(2);
              const rawValue = value * 1000000;
              return `${millionValue} triệu VND (${formatCurrency(rawValue)} ₫)`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          title: {
            display: true,
            text: 'Change (Million VND)'
          },
          ticks: {
            callback: (value) => `${value}M`
          }
        }
      }
    }),
    []
  );

  const renderStatCard = (label, value, badgeText) => {
    const isNumeric = typeof value === 'number' && !Number.isNaN(value);
    const trendClass = !isNumeric ? '' : value >= 0 ? 'text-success' : 'text-danger';
    const formattedValue = isNumeric ? `${formatCurrency(value)} ₫` : 'N/A';

    return (
      <div className="mini-stat">
        <span className="mini-stat-label">{label}</span>
        <span className={`mini-stat-value ${trendClass}`}>{formattedValue}</span>
        {badgeText && <small className="text-muted">{badgeText}</small>}
      </div>
    );
  };

  return (
    <Card className="dashboard-card insight-card w-100 h-100">
      <Card.Header className="insight-header d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h5 className="mb-1">
            <i className="fas fa-arrow-trend-up me-2"></i>Daily Momentum
          </h5>
          <small className="text-muted">
            Day-over-day change in buy prices for selected gold type.
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
            <Spinner animation="border" variant="info" />
            <p className="text-muted mt-2 mb-0">Fetching daily momentum...</p>
          </div>
        ) : error ? (
          <div className="insight-placeholder text-center text-muted py-5">
            <i className="fas fa-exclamation-circle fa-2x mb-2"></i>
            <p className="mb-0">{error}</p>
          </div>
        ) : chartData ? (
          <>
            {stats && (
              <div className="insight-stats mb-3">
                {renderStatCard('Latest Change', stats.latestChange)}
                {renderStatCard('Largest Gain', stats.maxGain)}
                {renderStatCard('Largest Drop', stats.maxDrop)}
                {renderStatCard('Average Change', stats.averageChange, 'Mean of selected period')}
              </div>
            )}
            <div className="insight-chart-container">
              <Bar data={chartData} options={chartOptions} />
            </div>
          </>
        ) : (
          <div className="insight-placeholder text-center text-muted py-5">
            <i className="fas fa-chart-bar fa-3x mb-3"></i>
            <p className="mb-0">No daily change data available for the selected period.</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default DailyChangeBarChart;
