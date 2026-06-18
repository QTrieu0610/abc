import React, { useState, useEffect } from 'react';
import { Card, Form, Row, Col } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import axios from 'axios';

const TrendChart = ({ company, period, onCompanyChange, onPeriodChange }) => {
  const [plotData, setPlotData] = useState([]);
  const [loading, setLoading] = useState(true);

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

      const traces = [
        {
          x: data.dates,
          y: data.buy_prices.map(price => price / 1000000),
          type: 'scatter',
          mode: 'lines+markers',
          name: 'Buy Price',
          line: { color: 'rgba(75, 192, 192, 1)', width: 2 },
          marker: { size: 4 },
          fill: 'tozeroy',
          fillcolor: 'rgba(75, 192, 192, 0.2)'
        },
        {
          x: data.dates,
          y: data.sell_prices.map(price => price / 1000000),
          type: 'scatter',
          mode: 'lines+markers',
          name: 'Sell Price',
          line: { color: 'rgba(255, 99, 132, 1)', width: 2 },
          marker: { size: 4 },
          fill: 'tozeroy',
          fillcolor: 'rgba(255, 99, 132, 0.2)'
        }
      ];

      // Add moving average if available
      if (maData && maData.buy_ma && maData.buy_ma.length > 0) {
        traces.push({
          x: data.dates,
          y: maData.buy_ma.map(price => price / 1000000),
          type: 'scatter',
          mode: 'lines',
          name: `Buy MA (${maData.window} days)`,
          line: { color: 'rgba(54, 162, 235, 1)', width: 2, dash: 'dash' }
        });
      }

      setPlotData(traces);
    } catch (error) {
      console.error('Error fetching trend data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Plotly layout configuration
  const layout = {
    title: `${company} Price Trend (Million VND)`,
    xaxis: {
      title: 'Date',
      type: 'date',
      fixedrange: false,  // Allow zooming on x-axis
      autorange: true
    },
    yaxis: {
      title: 'Price (Million VND)',
      tickformat: ',.2f',
      fixedrange: false,  // Allow zooming on y-axis
      autorange: true
    },
    hovermode: 'x unified',
    showlegend: true,
    legend: {
      orientation: 'h',
      y: -0.2
    },
    margin: { t: 50, b: 100, l: 60, r: 30 },
    dragmode: 'zoom',  // Default to zoom mode (not pan)
    uirevision: 'true'  // Preserve UI state (zoom/pan) across updates
  };

  // Plotly config - enables better zoom/pan controls
  const config = {
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
    scrollZoom: true,  // Enable scroll to zoom
    responsive: true,
    doubleClick: 'reset'  // Double-click to reset axes
  };

  return (
    <Card className="shadow-sm h-100">
      <Card.Header className="bg-success text-white">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">
            <i className="fas fa-chart-line me-2"></i>Price Trends
          </h5>
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
            <strong>Zoom:</strong> Scroll wheel to zoom in/out, click-drag to select zoom area, double-click to reset.
            <strong className="ms-2">Pan:</strong> Click "Pan" in toolbar, then drag to move.
          </small>
        </div>
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-success" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : plotData.length > 0 ? (
          <Plot
            data={plotData}
            layout={layout}
            config={config}
            style={{ width: '100%', height: '400px' }}
            useResizeHandler={true}
          />
        ) : (
          <p className="text-center text-muted">No data available</p>
        )}
      </Card.Body>
    </Card>
  );
};

export default TrendChart;

