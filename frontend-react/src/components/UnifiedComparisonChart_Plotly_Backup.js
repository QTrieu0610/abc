import React, { useState, useEffect, useRef } from 'react';
import { Card, Form, Badge, Button, ButtonGroup } from 'react-bootstrap';
import { Line } from 'react-chartjs-2';
import Select from 'react-select';
import axios from 'axios';

const UnifiedComparisonChart = ({ period }) => {
  const chartRef = useRef(null);
  const [chartData, setChartData] = useState({ datasets: [] });
  const [loading, setLoading] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState(period || 'weekly');
  const [selectedGoldTypes, setSelectedGoldTypes] = useState([]);

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
  }, [selectedGoldTypes, selectedPeriod]);

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
        setPlotData([]);
        setLoading(false);
        return;
      }

      // Find common dates across all datasets (intersection)
      // This ensures we only show dates where ALL selected gold types have data
      const allDatesArrays = validResults.map(r => r.data.dates);
      const commonDates = allDatesArrays.reduce((common, dates) => {
        return common.filter(date => dates.includes(date));
      });

      let traces = [];

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

        // Create Plotly traces
        traces = filteredResults.map(result => {
          const { selection, data } = result;

          // Get the appropriate price data based on type
          let priceData = [];
          if (selection.priceType === 'buy') {
            priceData = data.buy_prices;
          } else if (selection.priceType === 'sell') {
            priceData = data.sell_prices;
          }

          return {
            x: data.dates,
            y: priceData.map(price => price / 1000000), // Convert to millions
            type: 'scatter',
            mode: 'lines+markers',
            name: selection.label,
            line: { color: selection.color, width: 2 },
            marker: { size: 4 }
          };
        });
      } else {
        // Create Plotly traces for each selected gold type, using only common dates
        traces = validResults.map(result => {
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
            x: commonDates,
            y: priceData.map(price => price / 1000000), // Convert to millions
            type: 'scatter',
            mode: 'lines+markers',
            name: selection.label,
            line: { color: selection.color, width: 2 },
            marker: { size: 4 }
          };
        });
      }

      setPlotData(traces);
    } catch (error) {
      console.error('Error fetching comparison data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Plotly layout configuration
  const layout = {
    title: `Gold Price Comparison - ${selectedPeriod.charAt(0).toUpperCase() + selectedPeriod.slice(1)}`,
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
    <Card className="mb-4 fade-in">
      <Card.Header className="bg-primary text-white">
        <div className="d-flex justify-content-between align-items-center flex-wrap">
          <h5 className="mb-0">
            <i className="fas fa-chart-line me-2"></i>Unified Price Comparison Chart
          </h5>
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
            <strong>Zoom:</strong> Scroll wheel to zoom in/out, click-drag to select zoom area, double-click to reset.
            <strong className="ms-2">Pan:</strong> Click "Pan" in toolbar, then drag to move.
            <strong className="ms-2">Select:</strong> Choose unlimited combinations of buy/sell prices.
          </small>
        </div>

        {/* Chart */}
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="text-muted mt-2">Loading chart data...</p>
          </div>
        ) : plotData.length > 0 ? (
          <Plot
            data={plotData}
            layout={layout}
            config={config}
            style={{ width: '100%', height: '500px' }}
            useResizeHandler={true}
          />
        ) : (
          <div className="text-center py-5">
            <i className="fas fa-chart-line fa-3x text-muted mb-3"></i>
            <p className="text-muted">Select gold types above to view comparison chart</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default UnifiedComparisonChart;

