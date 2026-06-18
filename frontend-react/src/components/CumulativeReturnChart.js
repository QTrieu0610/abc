import React, { useEffect, useMemo, useState } from 'react';
import { Card, Form, Spinner, Button } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import axios from 'axios';

const GOLD_TYPE_OPTIONS = [
  { value: 'SJC 1L', label: 'SJC 1L' },
  { value: 'SJC Ring 1C', label: 'SJC Ring 1C' },
  { value: 'SJC Jewelry 24K', label: '24K' },
  { value: 'SJC Jewelry 99%', label: '99%' },
  { value: 'SJC Jewelry 18K', label: '18K' }
];

const CHART_TYPE_OPTIONS = [
  { value: 'percent', label: 'Percentage', icon: 'fa-percent' },
  { value: 'money', label: 'Currency', icon: 'fa-dong-sign' }
];

const QUICK_RANGE_PRESETS = [
  { label: 'Last 7 days', shortLabel: '7d', days: 7 },
  { label: '1 Month', shortLabel: '1M', days: 30 },
  { label: '3 Months', shortLabel: '3M', days: 90 },
  { label: '1 Year', shortLabel: '1Y', days: 365 }
];

const MS_PER_DAY = 1000 * 60 * 60 * 24;
const DEFAULT_DATA_PERIOD = 'yearly';

const formatSignedPercent = (value) => {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }

  const absolute = Math.abs(value).toFixed(2);

  if (value > 0) {
    return `+${absolute}%`;
  }

  if (value < 0) {
    return `-${absolute}%`;
  }

  return '0.00%';
};

const formatDateLabel = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const formatCurrency = (value) => {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }

  return `${value.toLocaleString('vi-VN')} ₫`;
};

const formatSignedCurrency = (value) => {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }

  const absolute = Math.abs(value).toLocaleString('vi-VN');

  if (value > 0) {
    return `+${absolute} ₫`;
  }

  if (value < 0) {
    return `-${absolute} ₫`;
  }

  return `0 ₫`;
};

const CumulativeReturnChart = ({ dataRefreshTrigger }) => {
  const [goldType, setGoldType] = useState('SJC 1L');
  const [chartType, setChartType] = useState('percent');
  const [entries, setEntries] = useState([]);
  const [activePresetDays, setActivePresetDays] = useState(null);
  const [buyDate, setBuyDate] = useState('');
  const [sellDate, setSellDate] = useState('');
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goldType, dataRefreshTrigger]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    setEntries([]);
    setChartData(null);
    setStats(null);
  setActivePresetDays(null);

    try {
      const response = await axios.get('/api/analytics/trends', {
        params: {
          company: 'SJC',
          gold_type: goldType,
          period: DEFAULT_DATA_PERIOD
        }
      });

      const trends = response.data?.trends;
      const processedEntries = trends?.dates
        ?.map((date, idx) => {
          const buy = Number(trends.buy_prices[idx]);
          const sell = Number(trends.sell_prices?.[idx]);

          if (!Number.isFinite(buy) || !Number.isFinite(sell)) {
            return null;
          }

          return { date, buy, sell };
        })
        .filter(Boolean);

      if (!processedEntries || processedEntries.length === 0) {
        setError('No data available for the selected gold type.');
        return;
      }

      const sortedEntries = [...processedEntries].sort((a, b) => new Date(a.date) - new Date(b.date));
      const defaultBuyDate = sortedEntries[0].date;
      const defaultSellDate = sortedEntries[sortedEntries.length - 1].date;

      setEntries(sortedEntries);
      setBuyDate((previous) =>
        previous && sortedEntries.some((entry) => entry.date === previous) ? previous : defaultBuyDate
      );
      setSellDate((previous) =>
        previous && sortedEntries.some((entry) => entry.date === previous) ? previous : defaultSellDate
      );
    } catch (err) {
      console.error('Error fetching cumulative return data:', err);
      setError('Unable to load return data right now.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!entries.length || !buyDate || !sellDate) {
      return;
    }

    const sorted = [...entries].sort((a, b) => new Date(a.date) - new Date(b.date));
    const buyIndex = sorted.findIndex((entry) => entry.date === buyDate);
    const sellIndex = sorted.findIndex((entry) => entry.date === sellDate);

    if (buyIndex === -1 || sellIndex === -1) {
      return;
    }

    if (sellIndex < buyIndex) {
      setChartData(null);
      setStats(null);
      setError('Sell date must be the same as or after the buy date.');
      return;
    }

    const windowEntries = sorted.slice(buyIndex, sellIndex + 1);

    if (!windowEntries.length) {
      setChartData(null);
      setStats(null);
      setError('No data in the selected window.');
      return;
    }

    // Entry Cost: When you buy gold, you pay the shop's SELL price
    const entryCost = windowEntries[0].sell;

    if (!Number.isFinite(entryCost) || entryCost <= 0) {
      setChartData(null);
      setStats(null);
      setError('Sell price unavailable for the selected start date.');
      return;
    }

    const labels = windowEntries.map((entry) => formatDateLabel(entry.date));
    // Exit Proceeds: When you sell gold back, you receive the shop's BUY price
    const returns = windowEntries.map((entry) => ((entry.buy - entryCost) / entryCost) * 100);
    const absoluteReturns = windowEntries.map((entry) => entry.buy - entryCost);
    const exitProceeds = windowEntries[windowEntries.length - 1].buy;
    const absoluteChange = exitProceeds - entryCost;
    const holdingDays = Math.max(
      0,
      Math.round((new Date(sellDate).getTime() - new Date(buyDate).getTime()) / (1000 * 60 * 60 * 24))
    );

    setError(null);
    setStats({
      latestReturn: returns[returns.length - 1],
      entryCost,
      exitProceeds,
      absoluteChange,
      holdingDays
    });

    setChartData({
      labels,
      datasets: [
        {
          label: 'Cumulative Return',
          data: returns,
          absoluteData: absoluteReturns,
          tension: 0.4,
          pointRadius: 2,
          pointHoverRadius: 6,
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          borderWidth: 3,
          fill: {
            target: 'origin',
            above: 'rgba(16, 185, 129, 0.12)',
            below: 'rgba(239, 68, 68, 0.12)'
          },
          // Dynamic segment coloring - green for positive, gray for zero, red for negative
          segment: {
            borderColor: (ctx) => {
              const value = ctx.p1.parsed.y;
              if (value === 0) return '#94a3b8'; // gray for zero
              return value > 0 ? '#10b981' : '#ef4444';
            },
            backgroundColor: (ctx) => {
              const value = ctx.p1.parsed.y;
              if (value === 0) return 'rgba(148, 163, 184, 0.12)'; // gray area for zero
              return value > 0 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)';
            }
          },
          // Point colors based on value
          pointBackgroundColor: (ctx) => {
            const value = ctx.parsed?.y;
            if (value === 0) return '#94a3b8'; // gray for zero
            return value > 0 ? '#10b981' : '#ef4444';
          }
        }
      ]
    });
  }, [entries, buyDate, sellDate]);

  const chartOptions = useMemo(
    () => {
      const isMoneyView = chartType === 'money';

      return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const elementIndex = elements[0].index;
            
            // Find the corresponding date from entries
            const sorted = [...entries].sort((a, b) => new Date(a.date) - new Date(b.date));
            const buyIndex = sorted.findIndex((entry) => entry.date === buyDate);
            const windowEntries = sorted.slice(buyIndex);
            
            if (windowEntries[elementIndex]) {
              const newSellDate = windowEntries[elementIndex].date;
              setSellDate(newSellDate);
              setActivePresetDays(null);
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.95)',
            padding: 12,
            cornerRadius: 8,
            titleFont: {
              size: 13,
              weight: '600'
            },
            bodyFont: {
              size: 14,
              weight: '700'
            },
            footerFont: {
              size: 11,
              weight: '400',
              style: 'italic'
            },
            callbacks: {
              label: (context) => {
                const ds = context.dataset;
                const idx = context.dataIndex;
                if (isMoneyView && ds?.absoluteData) {
                  const value = ds.absoluteData?.[idx];
                  return ` P/L: ${value >= 0 ? '+' : ''}${formatCurrency(value)}`;
                }
                const value = context.parsed?.y;
                return ` Return: ${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
              },
              footer: () => {
                return '💡 Click to set as exit date';
              }
            }
          }
        },
        scales: {
          y: {
            title: {
              display: true,
              text: isMoneyView ? 'Profit/Loss (₫)' : 'Cumulative Return (%)',
              font: {
                size: 12,
                weight: '600'
              },
              color: '#64748b'
            },
            ticks: {
              callback: (value) => {
                if (isMoneyView) {
                  return `${value >= 0 ? '+' : ''}${(value / 1000).toFixed(0)}K`;
                }
                return `${value >= 0 ? '+' : ''}${value}%`;
              },
              font: {
                size: 11
              },
              color: '#94a3b8'
            },
            grid: {
              color: 'rgba(148, 163, 184, 0.15)',
              drawBorder: false
            }
          },
          x: {
            title: {
              display: true,
              text: 'Date',
              font: {
                size: 12,
                weight: '600'
              },
              color: '#64748b'
            },
            ticks: {
              font: {
                size: 11
              },
              color: '#94a3b8',
              maxRotation: 45,
              minRotation: 0
            },
            grid: {
              display: false
            }
          }
        }
      };
    },
    [chartType, chartData, entries, buyDate]
  );

  const displayChartData = useMemo(() => {
    if (!chartData) return null;

    const isMoneyView = chartType === 'money';
    const dataset = chartData.datasets[0];

    return {
      labels: chartData.labels,
      datasets: [
        {
          ...dataset,
          data: isMoneyView ? dataset.absoluteData : dataset.data
        }
      ]
    };
  }, [chartData, chartType]);

  const renderStat = (label, value, helper, tone) => (
    <div className={`mini-stat${tone ? ` mini-stat-${tone}` : ''}`}>
      <span className="mini-stat-label">{label}</span>
      <span className="mini-stat-value">{value}</span>
      {helper && <small className="text-muted">{helper}</small>}
    </div>
  );

  const buyOptions = useMemo(() => {
    if (!entries.length) {
      return [];
    }

    return entries.filter((entry) => !sellDate || new Date(entry.date) <= new Date(sellDate));
  }, [entries, sellDate]);

  const sellOptions = useMemo(() => {
    if (!entries.length) {
      return [];
    }

    return entries.filter((entry) => !buyDate || new Date(entry.date) >= new Date(buyDate));
  }, [entries, buyDate]);

  const statTiles = stats
    ? [
        renderStat(
          'Net Return',
          formatSignedPercent(stats.latestReturn),
          stats.holdingDays ? `${stats.holdingDays} day${stats.holdingDays !== 1 ? 's' : ''}` : undefined,
          stats.latestReturn > 0 ? 'positive' : stats.latestReturn < 0 ? 'negative' : 'neutral'
        ),
        renderStat(
          'Profit / Loss',
          formatSignedCurrency(stats.absoluteChange),
          'Net gain/loss from investment',
          stats.absoluteChange > 0 ? 'positive' : stats.absoluteChange < 0 ? 'negative' : 'neutral'
        ),
        renderStat('Entry Cost', formatCurrency(stats.entryCost), 'Amount paid to purchase gold'),
        renderStat('Exit Proceeds', formatCurrency(stats.exitProceeds), 'Amount received when selling back')
      ]
    : null;

  const handleBuyDateChange = (event) => {
    const value = event.target.value;
    setBuyDate(value);
    setActivePresetDays(null);

    if (sellDate && new Date(value) > new Date(sellDate)) {
      setSellDate(value);
    }
  };

  const handleSellDateChange = (event) => {
    const value = event.target.value;
    setSellDate(value);
    setActivePresetDays(null);

    if (buyDate && new Date(value) < new Date(buyDate)) {
      setBuyDate(value);
    }
  };

  const handleQuickRange = (days) => {
    if (!entries.length) {
      return;
    }

    const sorted = [...entries].sort((a, b) => new Date(a.date) - new Date(b.date));
    const latest = sorted[sorted.length - 1];

    if (!latest) {
      return;
    }

    const latestDate = new Date(latest.date).getTime();
    const targetTime = latestDate - days * MS_PER_DAY;

    let candidate = sorted[0].date;

    for (let index = sorted.length - 1; index >= 0; index -= 1) {
      const entry = sorted[index];
      const entryTime = new Date(entry.date).getTime();

      if (entryTime <= targetTime) {
        candidate = entry.date;
        break;
      }
    }

    setSellDate(latest.date);
    setBuyDate(candidate);
    setActivePresetDays(days);
  };

  const handleResetRange = () => {
    if (!entries.length) {
      return;
    }

    setBuyDate(entries[0].date);
    setSellDate(entries[entries.length - 1].date);
    setActivePresetDays(null);
  };

  const activeRange = useMemo(() => {
    if (!buyDate || !sellDate) {
      return null;
    }

    const difference = Math.max(
      0,
      Math.round((new Date(sellDate).getTime() - new Date(buyDate).getTime()) / MS_PER_DAY)
    );

    return difference;
  }, [buyDate, sellDate]);

  const sentiment = useMemo(() => {
    if (!stats) {
      return null;
    }

    const tone = stats.latestReturn > 0.2 ? 'positive' : stats.latestReturn < -0.2 ? 'negative' : 'neutral';
    const icon = tone === 'positive' ? 'fa-arrow-trend-up' : tone === 'negative' ? 'fa-arrow-trend-down' : 'fa-wave-square';
    const headline =
      tone === 'positive' ? 'Uptrend in motion' : tone === 'negative' ? 'Drawdown warning' : 'Range-bound returns';
    const absoluteChangeLabel = formatCurrency(Math.abs(stats.absoluteChange));
    const summary =
      stats.absoluteChange === 0
        ? 'Returns have stayed flat since your entry point.'
        : stats.absoluteChange > 0
        ? `Portfolio gained ${absoluteChangeLabel} since ${formatDateLabel(buyDate)}.`
        : `Loss of ${absoluteChangeLabel} relative to ${formatDateLabel(buyDate)}.`;

    return {
      tone,
      icon,
      headline,
      summary,
      percent: formatSignedPercent(stats.latestReturn),
      absolute: formatSignedCurrency(stats.absoluteChange)
    };
  }, [stats, buyDate]);

  return (
    <Card className="dashboard-card insight-card cumulative-return-card w-100 h-100">
      <Card.Header className="insight-header">
        <div className="d-flex align-items-center justify-content-between">
          <div>
            <h5 className="mb-1">
              <i className="fas fa-chart-line me-2"></i>Investment Return Analysis
            </h5>
            <small className="text-muted d-block">
              Track your gold investment performance over time
            </small>
          </div>
        </div>
      </Card.Header>
      <Card.Body className="d-flex flex-column flex-lg-row gap-3 p-0">
        {/* Sidebar Controls */}
        <div className="insight-sidebar">
          <div className="insight-control-section insight-control-full">
            <label className="insight-control-label">
              <i className="fas fa-coins me-1"></i>Type
            </label>
            <Form.Select
              size="sm"
              value={goldType}
              onChange={(event) => setGoldType(event.target.value)}
              className="insight-control-select"
            >
              {GOLD_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Form.Select>
          </div>

          <div className="insight-control-grid">
            <div className="insight-control-section">
              <label className="insight-control-label">
                <i className="fas fa-calendar-plus me-1"></i>Entry
              </label>
              <Form.Select
                size="sm"
                value={buyDate}
                onChange={handleBuyDateChange}
                disabled={!buyOptions.length}
                className="insight-control-select"
              >
                {buyOptions.map((option) => {
                  const label = formatDateLabel(option.date);
                  return (
                    <option key={`buy-${option.date}`} value={option.date}>
                      {label}
                    </option>
                  );
                })}
              </Form.Select>
            </div>

            <div className="insight-control-section">
              <label className="insight-control-label">
                <i className="fas fa-calendar-check me-1"></i>Exit
              </label>
              <Form.Select
                size="sm"
                value={sellDate}
                onChange={handleSellDateChange}
                disabled={!sellOptions.length}
                className="insight-control-select"
              >
                {sellOptions.map((option) => {
                  const label = formatDateLabel(option.date);
                  return (
                    <option key={`sell-${option.date}`} value={option.date}>
                      {label}
                    </option>
                  );
                })}
              </Form.Select>
            </div>
          </div>

          <div className="insight-control-footer">
            <div className="insight-control-section insight-range-section">
              <label className="insight-control-label d-block mb-1">
                <i className="fas fa-sliders me-1"></i>Range
              </label>
              <div className="insight-quick-grid">
                {QUICK_RANGE_PRESETS.map((preset) => {
                  const tolerance =
                    preset.days >= 365 ? 15 : preset.days >= 90 ? 7 : preset.days >= 30 ? 4 : 2;
                  const matchesRange =
                    activeRange !== null &&
                    activeRange >= Math.max(0, preset.days - tolerance) &&
                    activeRange <= preset.days + tolerance;
                  const isActive = activePresetDays === preset.days || (!activePresetDays && matchesRange);

                  return (
                    <Button
                      key={preset.days}
                      size="sm"
                      variant={isActive ? 'primary' : 'outline-secondary'}
                      className="insight-quick-btn"
                      disabled={!entries.length}
                      onClick={() => handleQuickRange(preset.days)}
                    >
                      {preset.shortLabel}
                    </Button>
                  );
                })}
              </div>
              <Button
                size="sm"
                variant="link"
                className="insight-reset-btn w-100 mt-2"
                disabled={!entries.length}
                onClick={handleResetRange}
              >
                <i className="fas fa-rotate-left me-2"></i>Reset to full range
              </Button>
            </div>

            <div className="insight-control-section insight-control-view">
              <label className="insight-control-label d-flex align-items-center mb-2">
                <i className="fas fa-eye me-2"></i>
                <span>Display Mode</span>
              </label>
              <div className="btn-group w-100 shadow-sm" role="group">
                {CHART_TYPE_OPTIONS.map((option) => (
                  <Button
                    key={option.value}
                    size="sm"
                    variant={chartType === option.value ? 'primary' : 'outline-secondary'}
                    className={`insight-chart-type-btn flex-fill d-flex align-items-center justify-content-center gap-2 ${
                      chartType === option.value ? 'active' : ''
                    }`}
                    onClick={() => setChartType(option.value)}
                    style={{
                      transition: 'all 0.2s ease',
                      fontWeight: chartType === option.value ? '600' : '500',
                      borderWidth: '1.5px'
                    }}
                  >
                    <i className={`fas ${option.icon}`}></i>
                    <span>{option.label}</span>
                  </Button>
                ))}
              </div>
              <small className="text-muted d-block mt-2 text-center">
                {chartType === 'percent' ? 'Showing percentage change' : 'Showing absolute value change'}
              </small>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="insight-main-content flex-fill">
          {loading ? (
            <div className="insight-loading">
              <Spinner animation="border" variant="success" />
              <p className="text-muted mt-2 mb-0">Calculating returns...</p>
            </div>
          ) : error ? (
            <div className="insight-placeholder text-center text-muted py-5">
              <i className="fas fa-exclamation-triangle fa-2x mb-2"></i>
              <p className="mb-0">{error}</p>
            </div>
          ) : displayChartData ? (
            <>
              {sentiment && (
                <div className={`insight-highlight insight-highlight-${sentiment.tone}`}>
                  <div className="d-flex align-items-center gap-3 flex-grow-1 flex-wrap">
                    <div className="insight-highlight-icon">
                      <i className={`fas ${sentiment.icon}`}></i>
                    </div>
                    <div className="insight-highlight-body flex-grow-1">
                      <span className="insight-highlight-title">{sentiment.headline}</span>
                      <p className="insight-highlight-text mb-0">{sentiment.summary}</p>
                    </div>
                  </div>
                  <div className="insight-highlight-metric">
                    <span className="insight-highlight-value">{sentiment.percent}</span>
                    <small className="d-block text-muted mt-1">{sentiment.absolute}</small>
                  </div>
                </div>
              )}
              {statTiles && <div className="insight-stats">{statTiles}</div>}
              <div className="insight-chart-container" style={{ cursor: 'pointer' }}>
                <Line data={displayChartData} options={chartOptions} />
              </div>
            </>
          ) : (
            <div className="insight-placeholder text-center text-muted py-5">
              <i className="fas fa-chart-area fa-3x mb-3"></i>
              <p className="mb-0">No return data available for the selected range.</p>
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default CumulativeReturnChart;
