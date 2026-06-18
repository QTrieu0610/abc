import React, { useEffect, useMemo, useState } from 'react';
import { Card, Form, Spinner } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import axios from 'axios';

const PERIOD_OPTIONS = [
  { value: 'weekly', label: 'Weekly (7 days)' },
  { value: 'monthly', label: 'Monthly (30 days)' },
  { value: 'quarterly', label: 'Quarterly (90 days)' },
  { value: 'yearly', label: 'Yearly (365 days)' }
];

const GOLD_TYPE_OPTIONS = [
  { value: 'SJC 1L', label: 'SJC 1L (1 Lượng)' },
  { value: 'SJC Ring 1C', label: 'SJC Ring 1C' },
  { value: 'SJC Jewelry 24K', label: 'SJC Jewelry 24K' },
  { value: 'SJC Jewelry 99%', label: 'SJC Jewelry 99%' },
  { value: 'SJC Jewelry 18K', label: 'SJC Jewelry 18K' }
];

const WINDOW_OPTIONS = [
  { value: 3, label: '3-day MA' },
  { value: 5, label: '5-day MA' },
  { value: 7, label: '7-day MA' },
  { value: 14, label: '14-day MA' }
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

const calculateMovingAverage = (values, window) => {
  if (!values || values.length === 0) {
    return [];
  }

  const averages = values.map((_, index) => {
    const start = Math.max(0, index - window + 1);
    const slice = values.slice(start, index + 1);
    const total = slice.reduce((sum, value) => sum + value, 0);
    return total / slice.length;
  });

  return averages;
};

const MovingAverageChart = () => {
  const [period, setPeriod] = useState('monthly');
  const [goldType, setGoldType] = useState('SJC 1L');
  const [windowSize, setWindowSize] = useState(7);
  const [chartData, setChartData] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, goldType, windowSize]);

  const fetchData = async () => {
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
      const entries = trends?.dates
        ?.map((date, idx) => {
          const buy = Number(trends.buy_prices[idx]);

          if (!Number.isFinite(buy)) {
            return null;
          }

          return { date, buy };
        })
        .filter(Boolean);

      if (!entries || entries.length === 0) {
        setChartData(null);
        setStats(null);
        setError('No data available for the selected gold type.');
        return;
      }

      const labels = entries.map((entry) => formatDateLabel(entry.date));
      const buyPrices = entries.map((entry) => entry.buy / 1_000_000);
      const movingAverageValues = calculateMovingAverage(entries.map((entry) => entry.buy), windowSize).map(
        (value) => value / 1_000_000
      );

      const latestEntry = entries[entries.length - 1];
      const latestMovingAverage = movingAverageValues[movingAverageValues.length - 1] * 1_000_000;
      const latestPrice = latestEntry.buy;
      const deviation = latestPrice - latestMovingAverage;
      const deviationPercent = latestMovingAverage ? (deviation / latestMovingAverage) * 100 : null;

      let windowComparison = null;
      if (entries.length > windowSize) {
        const compareEntry = entries[entries.length - 1 - windowSize];
        windowComparison = latestPrice - compareEntry.buy;
      }

      setStats({
        latestPrice,
        latestMovingAverage,
        deviation,
        deviationPercent,
        windowComparison,
        totalPoints: entries.length
      });

      setChartData({
        labels,
        datasets: [
          {
            label: `${goldType} Buy Price`,
            data: buyPrices,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.12)',
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5,
            fill: true
          },
          {
            label: `${windowSize}-day Moving Average`,
            data: movingAverageValues,
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.18)',
            borderDash: [6, 4],
            tension: 0.25,
            pointRadius: 0,
            fill: false
          }
        ]
      });
    } catch (err) {
      console.error('Error fetching moving average data:', err);
      setError('Unable to load moving average data right now.');
      setChartData(null);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top'
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
            text: 'Price (Million VND)'
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
    }),
    []
  );

  const renderStat = (label, value, helper) => (
    <div className="mini-stat">
      <span className="mini-stat-label">{label}</span>
      <span className="mini-stat-value">{value}</span>
      {helper && <small className="text-muted">{helper}</small>}
    </div>
  );

  const formattedStats = stats
    ? [
        renderStat(
          'Latest Price',
          stats.latestPrice !== null && stats.latestPrice !== undefined
            ? `${formatCurrency(stats.latestPrice)} ₫`
            : 'N/A'
        ),
        renderStat(
          `${windowSize}-day Average`,
          stats.latestMovingAverage !== null && stats.latestMovingAverage !== undefined
            ? `${formatCurrency(stats.latestMovingAverage)} ₫`
            : 'N/A'
        ),
        renderStat(
          'Above/Below MA',
          stats.deviation !== null && stats.deviation !== undefined
            ? `${formatCurrency(Math.abs(stats.deviation))} ₫`
            : 'N/A',
          stats.deviationPercent !== null && stats.deviationPercent !== undefined
            ? `${stats.deviationPercent.toFixed(2)}%`
            : undefined
        ),
        renderStat(
          `Change vs ${windowSize} days ago`,
          stats.windowComparison !== null && stats.windowComparison !== undefined
            ? `${formatCurrency(stats.windowComparison)} ₫`
            : 'N/A'
        )
      ]
    : null;

  return (
    <Card className="dashboard-card insight-card w-100 h-100">
      <Card.Header className="insight-header d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h5 className="mb-1">
            <i className="fas fa-wave-square me-2"></i>Moving Average Signal
          </h5>
          <small className="text-muted">
            Compare real prices against a configurable moving average to spot momentum shifts.
          </small>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <Form.Select
            size="sm"
            value={goldType}
            onChange={(event) => setGoldType(event.target.value)}
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
            value={windowSize}
            onChange={(event) => setWindowSize(Number(event.target.value))}
            className="insight-period-select"
          >
            {WINDOW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Form.Select>
          <Form.Select
            size="sm"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
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
            <Spinner animation="border" variant="primary" />
            <p className="text-muted mt-2 mb-0">Loading moving average data...</p>
          </div>
        ) : error ? (
          <div className="insight-placeholder text-center text-muted py-5">
            <i className="fas fa-exclamation-triangle fa-2x mb-2"></i>
            <p className="mb-0">{error}</p>
          </div>
        ) : chartData ? (
          <>
            {formattedStats && <div className="insight-stats mb-3">{formattedStats}</div>}
            <div className="insight-chart-container">
              <Line data={chartData} options={chartOptions} />
            </div>
          </>
        ) : (
          <div className="insight-placeholder text-center text-muted py-5">
            <i className="fas fa-chart-line fa-3x mb-3"></i>
            <p className="mb-0">No moving average data available for the selected period.</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default MovingAverageChart;
