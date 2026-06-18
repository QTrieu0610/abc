import React, { useState, useEffect, useRef } from 'react';
import { Card, Form, Row, Col, Button, ButtonGroup } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import axios from 'axios';

const formatDateLabel = (dateString) => {
  const date = new Date(dateString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

// Register ChartJS components including zoom plugin
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  zoomPlugin
);

const TrendChart = ({ company, period, onCompanyChange, onPeriodChange }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const chartRef = useRef(null);

  useEffect(() => {
    fetchTrendData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company, period]);

  const fetchTrendData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/analytics/trends`, {
        params: { company, period }
      });

      const data = response.data.trends;
      const maData = response.data.moving_average;

      // Format dates for labels
      const labels = data.dates.map(dateStr => {
        return formatDateLabel(dateStr);
      });

      const datasets = [
        {
          label: 'Buy Price',
          data: data.buy_prices.map(price => price / 1000000),
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          borderWidth: 3,
          tension: 0.4,
          fill: true
        },
        {
          label: 'Sell Price',
          data: data.sell_prices.map(price => price / 1000000),
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.2)',
          borderWidth: 3,
          tension: 0.4,
          fill: true
        }
      ];

      // Add moving average if available
      if (maData && maData.buy_ma && maData.buy_ma.length > 0) {
        datasets.push({
          label: `Buy MA (${maData.window} days)`,
          data: maData.buy_ma.map(price => price / 1000000),
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          tension: 0.4
        });
      }

      setChartData({
        labels,
        datasets
      });
    } catch (error) {
      console.error('Error fetching trend data:', error);
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
        text: `${company} Price Trend (Million VND)`
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
      <Card.Header className="bg-success text-white">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">
            <i className="fas fa-chart-line me-2"></i>Price Trends
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
        <Row className="mb-3">
          <Col md={6}>
            <Form.Label>Company:</Form.Label>
            <Form.Select
              value={company}
              onChange={(e) => onCompanyChange(e.target.value)}
            >
              <option value="SJC">SJC Gold</option>
              <option value="DOJI">DOJI Gold</option>
              <option value="PNJ">PNJ Gold</option>
            </Form.Select>
          </Col>
          <Col md={6}>
            <Form.Label>Time Period:</Form.Label>
            <Form.Select
              value={period}
              onChange={(e) => onPeriodChange(e.target.value)}
            >
              <option value="weekly">Weekly (7 days)</option>
              <option value="monthly">Monthly (30 days)</option>
              <option value="quarterly">Quarterly (90 days)</option>
              <option value="yearly">Yearly (365 days)</option>
            </Form.Select>
          </Col>
        </Row>
        <div className="mb-2">
          <small className="text-muted">
            <i className="fas fa-info-circle me-1"></i>
            <strong>Zoom:</strong> Mouse wheel to zoom, Ctrl+Drag to pan, or use buttons above
          </small>
        </div>
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-success" role="status">
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

export default TrendChart;

