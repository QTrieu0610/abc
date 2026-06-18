import React, { useState, useEffect, useRef } from 'react';
import { Card, Form, Button, ButtonGroup, Badge } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import Select from 'react-select';
import zoomPlugin from 'chartjs-plugin-zoom';
import axios from 'axios';

const formatDateLabel = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const UnifiedComparisonChart = ({ period, dataRefreshTrigger }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState(period || 'weekly');
  const [selectedGoldTypes, setSelectedGoldTypes] = useState([]);
  const chartRef = useRef(null);

  // Define all available gold types with buy/sell options (DOJI and PNJ removed - only SJC)
  const goldTypeOptions = [
    // SJC Options only (DOJI and PNJ removed completely)
    {
      label: 'SJC Gold Types',
      options: [
        { value: 'SJC_1L_BUY', label: 'SJC 1L - Buy', company: 'SJC', goldType: 'SJC 1L', type: 'buy_1l', priceType: 'buy', color: '#dc3545' },
        { value: 'SJC_1L_SELL', label: 'SJC 1L - Sell', company: 'SJC', goldType: 'SJC 1L', type: 'sell_1l', priceType: 'sell', color: '#c82333' },
        { value: 'SJC_RING_BUY', label: 'SJC Ring 1C - Buy', company: 'SJC', goldType: 'SJC Ring 1C', type: 'buy_nhan1c', priceType: 'buy', color: '#6f42c1' },
        { value: 'SJC_RING_SELL', label: 'SJC Ring 1C - Sell', company: 'SJC', goldType: 'SJC Ring 1C', type: 'sell_nhan1c', priceType: 'sell', color: '#5a32a3' },
        { value: 'SJC_J24K_BUY', label: 'SJC Jewelry 24K - Buy', company: 'SJC', goldType: 'SJC Jewelry 24K', type: 'buy_nutrang_9999', priceType: 'buy', color: '#e83e8c' },
        { value: 'SJC_J24K_SELL', label: 'SJC Jewelry 24K - Sell', company: 'SJC', goldType: 'SJC Jewelry 24K', type: 'sell_nutrang_9999', priceType: 'sell', color: '#d63384' },
        { value: 'SJC_J99_BUY', label: 'SJC Jewelry 99% - Buy', company: 'SJC', goldType: 'SJC Jewelry 99%', type: 'buy_nutrang_99', priceType: 'buy', color: '#20c997' },
        { value: 'SJC_J99_SELL', label: 'SJC Jewelry 99% - Sell', company: 'SJC', goldType: 'SJC Jewelry 99%', type: 'sell_nutrang_99', priceType: 'sell', color: '#1aa179' },
        { value: 'SJC_J18K_BUY', label: 'SJC Jewelry 18K - Buy', company: 'SJC', goldType: 'SJC Jewelry 18K', type: 'buy_nutrang_75', priceType: 'buy', color: '#6610f2' },
        { value: 'SJC_J18K_SELL', label: 'SJC Jewelry 18K - Sell', company: 'SJC', goldType: 'SJC Jewelry 18K', type: 'sell_nutrang_75', priceType: 'sell', color: '#520dc2' }
      ]
    }
  ];

  // Default selection: SJC 1L Buy and Sell
  useEffect(() => {
    if (selectedGoldTypes.length === 0) {
      const defaultSelections = goldTypeOptions[0].options.slice(0, 2); // SJC 1L Buy and Sell
      setSelectedGoldTypes(defaultSelections);
    }
  }, []);

  useEffect(() => {
    if (selectedGoldTypes.length > 0) {
      fetchComparisonData();
    }
  }, [selectedGoldTypes, selectedPeriod, dataRefreshTrigger]);

  // REMOVED: Automatic zoom restoration
  // The zoom state is now preserved by Chart.js itself through the zoom plugin
  // We only save the state for manual restoration via Reset Zoom button

  const fetchComparisonData = async () => {
    setLoading(true);
    try {
      // Fetch data for each selected gold type individually
      const fetchPromises = selectedGoldTypes.map(async (selection) => {
        try {
          const params = {
            company: selection.company,
            period: selectedPeriod,
            gold_type: selection.goldType
          };

          // Add location for DOJI (since they have different locations)
          if (selection.location) {
            params.location = selection.location;
          }

          const response = await axios.get(`/api/analytics/trends`, { params });
          return {
            selection,
            data: response.data.trends
          };
        } catch (error) {
          console.error(`Error fetching ${selection.label} data:`, error);
          return null;
        }
      });

      const results = await Promise.all(fetchPromises);
      const validResults = results.filter(r => r !== null && r.data && r.data.dates && r.data.dates.length > 0);

      if (validResults.length === 0) {
        setChartData(null);
        setLoading(false);
        return;
      }

      // Find common dates across all datasets (intersection)
      // This ensures we only show dates where ALL selected gold types have data
      const allDatesArrays = validResults.map(r => r.data.dates);
      const commonDates = allDatesArrays.reduce((common, dates) => {
        return common.filter(date => dates.includes(date));
      });

      if (commonDates.length === 0) {
        // No common dates - use the most recent date range that has the most overlap
        // Find the latest start date among all datasets
        const latestStartDate = new Date(Math.max(...allDatesArrays.map(dates => new Date(dates[0]).getTime())));

        // Filter all datasets to only include dates >= latestStartDate
        const filteredResults = validResults.map(result => {
          const { selection, data } = result;
          const indices = data.dates
            .map((date, idx) => ({ date, idx }))
            .filter(({ date }) => new Date(date) >= latestStartDate)
            .map(({ idx }) => idx);

          return {
            selection,
            data: {
              dates: indices.map(idx => data.dates[idx]),
              buy_prices: indices.map(idx => data.buy_prices[idx]),
              sell_prices: indices.map(idx => data.sell_prices[idx])
            }
          };
        });

        // Use the filtered dates as labels
        const labels = filteredResults[0].data.dates.map(dateStr => {
          return formatDateLabel(dateStr);
        });

        // Create datasets with aligned data
        const datasets = filteredResults.map(result => {
          const { selection, data } = result;

          // Get the appropriate price data based on type
          let priceData = [];
          if (selection.priceType === 'buy') {
            priceData = data.buy_prices;
          } else if (selection.priceType === 'sell') {
            priceData = data.sell_prices;
          }

          return {
            label: selection.label,
            data: priceData.map(price => price / 1000000), // Convert to millions
            borderColor: selection.color,
            backgroundColor: selection.color + '30', // Add transparency
            borderWidth: 3,
            tension: 0.3,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 7,
            pointBackgroundColor: selection.color,
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
          };
        });

        setChartData({ labels, datasets });
      } else {
        // Use common dates as labels
        const labels = commonDates.map(dateStr => {
          return formatDateLabel(dateStr);
        });

        // Create datasets for each selected gold type, using only common dates
        const datasets = validResults.map(result => {
          const { selection, data } = result;

          // Find indices of common dates in this dataset
          const indices = commonDates.map(commonDate => data.dates.indexOf(commonDate));

          // Get the appropriate price data based on type
          let priceData = [];
          if (selection.priceType === 'buy') {
            priceData = indices.map(idx => data.buy_prices[idx]);
          } else if (selection.priceType === 'sell') {
            priceData = indices.map(idx => data.sell_prices[idx]);
          }

          return {
            label: selection.label,
            data: priceData.map(price => price / 1000000), // Convert to millions
            borderColor: selection.color,
            backgroundColor: selection.color + '30', // Add transparency
            borderWidth: 3,
            tension: 0.3,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 7,
            pointBackgroundColor: selection.color,
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
          };
        });

        setChartData({ labels, datasets });
      }
    } catch (error) {
      console.error('Error fetching comparison data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Zoom control functions
  const handleResetZoom = () => {
    if (chartRef.current) {
      chartRef.current.resetZoom();
    }
  };

  const handleZoomIn = () => {
    if (chartRef.current) {
      chartRef.current.zoom(1.1);
    }
  };

  const handleZoomOut = () => {
    if (chartRef.current) {
      chartRef.current.zoom(0.9);
    }
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    elements: {
      line: {
        tension: 0.2,
        borderWidth: 3
      },
      point: {
        radius: 4,
        hoverRadius: 6,
        hitRadius: 10
      }
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          boxWidth: 16,
          padding: 15,
          font: {
            size: 13,
            weight: '600'
          },
          usePointStyle: true,
          pointStyle: 'circle'
        }
      },
      title: {
        display: true,
        text: `Gold Price Comparison - ${selectedPeriod.charAt(0).toUpperCase() + selectedPeriod.slice(1)}`,
        font: {
          size: 18,
          weight: 'bold'
        },
        padding: {
          top: 10,
          bottom: 15
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        titleFont: {
          size: 14,
          weight: 'bold'
        },
        bodyFont: {
          size: 13
        },
        padding: 12,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += new Intl.NumberFormat('vi-VN', { 
                minimumFractionDigits: 2,
                maximumFractionDigits: 2 
              }).format(context.parsed.y) + ' M VND';
            }
            return label;
          }
        }
      },
      zoom: {
        zoom: {
          wheel: {
            enabled: true,
            speed: 0.1
          },
          pinch: {
            enabled: true
          },
          mode: 'x'
        },
        pan: {
          enabled: true,
          mode: 'x',
          modifierKey: 'ctrl'
        },
        limits: {
          x: { min: 'original', max: 'original' },
          y: { min: 'original', max: 'original' }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        grid: {
          color: 'rgba(0, 0, 0, 0.08)',
          lineWidth: 1
        },
        title: {
          display: true,
          text: 'Price (Million VND)',
          font: {
            size: 14,
            weight: 'bold'
          },
          padding: { top: 0, bottom: 10 }
        },
        ticks: {
          font: {
            size: 12,
            weight: '500'
          },
          callback: function(value) {
            return new Intl.NumberFormat('vi-VN').format(value);
          },
          padding: 8
        }
      },
      x: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
          lineWidth: 1
        },
        title: {
          display: true,
          text: 'Date',
          font: {
            size: 14,
            weight: 'bold'
          },
          padding: { top: 10, bottom: 0 }
        },
        ticks: {
          font: {
            size: 12,
            weight: '500'
          },
          maxRotation: 45,
          minRotation: 0,
          padding: 8
        }
      }
    }
  };

  return (
    <Card className="dashboard-card insight-card fade-in h-100 w-100">
      <Card.Header className="insight-header">
        <div className="d-flex justify-content-between align-items-center flex-wrap">
          <div>
            <h5 className="mb-1">
              <i className="fas fa-chart-line me-2"></i>Unified Price Comparison Chart
            </h5>
            <small className="text-muted">Interactive gold price trends across time periods</small>
          </div>
          <ButtonGroup size="sm">
            <Button variant="outline-secondary" onClick={handleZoomIn} title="Zoom In">
              <i className="fas fa-search-plus"></i>
            </Button>
            <Button variant="outline-secondary" onClick={handleZoomOut} title="Zoom Out">
              <i className="fas fa-search-minus"></i>
            </Button>
            <Button variant="outline-secondary" onClick={handleResetZoom} title="Reset Zoom">
              <i className="fas fa-undo"></i>
            </Button>
          </ButtonGroup>
        </div>
      </Card.Header>
      <Card.Body>
        {/* Selection Controls */}
        <div className="row mb-3 g-3">
          <div className="col-12 col-lg-8">
            <Form.Group>
              <Form.Label className="small fw-bold">
                Select Gold Types to Compare
                <Badge bg="info" className="ms-2">{selectedGoldTypes.length} selected</Badge>
              </Form.Label>
              <Select
                isMulti
                options={goldTypeOptions}
                value={selectedGoldTypes}
                onChange={setSelectedGoldTypes}
                placeholder="Select gold types to compare..."
                className="basic-multi-select"
                classNamePrefix="select"
              />
            </Form.Group>
          </div>
          <div className="col-12 col-lg-4">
            <Form.Group>
              <Form.Label className="small fw-bold">Time Period</Form.Label>
              <Form.Select
                size="sm"
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
              >
                <option value="weekly">Weekly (7 days)</option>
                <option value="monthly">Monthly (30 days)</option>
                <option value="quarterly">Quarterly (90 days)</option>
                <option value="yearly">Yearly (365 days)</option>
              </Form.Select>
            </Form.Group>
          </div>
        </div>

        {/* Help Text */}
        <div className="mb-2">
          <small className="text-muted">
            <i className="fas fa-info-circle me-1"></i>
            <strong>Zoom:</strong> Mouse wheel to zoom, Ctrl+Drag to pan, or use buttons above. 
            <strong className="ms-2">Select:</strong> Choose unlimited combinations of buy/sell prices from all companies.
          </small>
        </div>

        {/* Chart Container with Enhanced Visibility */}
        <div style={{ 
          height: '500px', 
          minHeight: '450px',
          position: 'relative',
          padding: '1rem',
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
          borderRadius: '16px',
          border: '2px solid rgba(148, 163, 184, 0.1)',
          boxShadow: 'inset 0 2px 8px rgba(0, 0, 0, 0.03)'
        }}>
          {loading ? (
            <div className="text-center py-5" style={{ 
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)'
            }}>
              <div className="spinner-border text-primary" role="status" style={{ width: '3rem', height: '3rem' }}>
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="text-muted mt-3 fw-semibold">Loading chart data...</p>
            </div>
          ) : chartData ? (
            <Line ref={chartRef} data={chartData} options={options} />
          ) : (
            <div className="text-center" style={{ 
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '100%'
            }}>
              <i className="fas fa-chart-line fa-4x text-muted mb-3" style={{ opacity: 0.5 }}></i>
              <p className="text-muted fw-semibold">Select gold types above to view comparison chart</p>
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default UnifiedComparisonChart;

