import React, { useState, useEffect, useRef } from 'react';
import { Card, Form, Button, ButtonGroup } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import zoomPlugin from 'chartjs-plugin-zoom';
import axios from 'axios';

const formatDateLabel = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const ComparisonChart = ({ period }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const chartRef = useRef(null);

  useEffect(() => {
    fetchComparisonData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPeriod]);

  const fetchComparisonData = async () => {
    setLoading(true);
    try {
      const companies = ['SJC', 'DOJI', 'PNJ'];
      const companyData = {};

      // Fetch data for all companies
      for (const company of companies) {
        const response = await axios.get(`/api/analytics/trends`, {
          params: { company, period: selectedPeriod }
        });
        companyData[company] = response.data.trends;
      }

      // Use first company's dates as labels
      const labels = companyData['SJC'].dates.map(dateStr => {
        return formatDateLabel(dateStr);
      });

      // Create datasets for each company
      const colors = {
        'SJC': { border: 'rgba(255, 99, 132, 1)', bg: 'rgba(255, 99, 132, 0.2)' },
        'DOJI': { border: 'rgba(54, 162, 235, 1)', bg: 'rgba(54, 162, 235, 0.2)' },
        'PNJ': { border: 'rgba(75, 192, 192, 1)', bg: 'rgba(75, 192, 192, 0.2)' }
      };

      const datasets = companies.map(company => ({
        label: `${company} Buy`,
        data: companyData[company].buy_prices.map(price => price / 1000000),
        borderColor: colors[company].border,
        backgroundColor: colors[company].bg,
        borderWidth: 2,
        tension: 0.4,
        fill: false
      }));

      setChartData({
        labels,
        datasets
      });
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
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: true,
        position: 'top'
      },
      title: {
        display: true,
        text: `Company Comparison - Buy Prices (${selectedPeriod})`
      },
      tooltip: {
        mode: 'index',
        intersect: false,
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
          mode: 'x',
        },
        pan: {
          enabled: true,
          mode: 'x',
          modifierKey: 'ctrl',
        },
        limits: {
          x: {min: 'original', max: 'original'},
          y: {min: 'original', max: 'original'}
        }
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'Price (Million VND)'
        },
        ticks: {
          callback: function(value) {
            return new Intl.NumberFormat('vi-VN').format(value);
          }
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date'
        }
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    }
  };

  return (
    <Card className="shadow-sm h-100">
      <Card.Header className="bg-secondary text-white">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">
            <i className="fas fa-balance-scale me-2"></i>Multi-Company Comparison
          </h5>
          <ButtonGroup size="sm">
            <Button variant="light" onClick={handleZoomIn} title="Zoom In">
              <i className="fas fa-search-plus"></i>
            </Button>
            <Button variant="light" onClick={handleZoomOut} title="Zoom Out">
              <i className="fas fa-search-minus"></i>
            </Button>
            <Button variant="light" onClick={handleResetZoom} title="Reset Zoom">
              <i className="fas fa-undo"></i>
            </Button>
          </ButtonGroup>
        </div>
      </Card.Header>
      <Card.Body>
        <div className="mb-3">
          <Form.Label>Comparison Period:</Form.Label>
          <Form.Select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
          >
            <option value="weekly">Weekly (7 days)</option>
            <option value="monthly">Monthly (30 days)</option>
            <option value="quarterly">Quarterly (90 days)</option>
          </Form.Select>
        </div>
        <div className="mb-2">
          <small className="text-muted">
            <i className="fas fa-info-circle me-1"></i>
            <strong>Zoom:</strong> Mouse wheel to zoom, Ctrl+Drag to pan
          </small>
        </div>
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-secondary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : chartData ? (
          <Line ref={chartRef} data={chartData} options={options} />
        ) : (
          <p className="text-center text-muted">No data available</p>
        )}
      </Card.Body>
    </Card>
  );
};

export default ComparisonChart;

