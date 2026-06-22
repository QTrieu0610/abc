import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import EmptyState from "../common/EmptyState";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

function numericValues(values) {
  return values.map(Number).filter((value) => Number.isFinite(value));
}

function paddedRange(values, fallbackPadding = 100000) {
  const numbers = numericValues(values);
  if (!numbers.length) return {};

  const min = Math.min(...numbers);
  const max = Math.max(...numbers);
  const range = Math.max(max - min, fallbackPadding);
  const padding = Math.max(range * 0.25, fallbackPadding);
  const step = fallbackPadding;

  return {
    suggestedMin: Math.max(0, Math.floor((min - padding) / step) * step),
    suggestedMax: Math.ceil((max + padding) / step) * step,
  };
}

function formatThousands(value) {
  return new Intl.NumberFormat("vi-VN").format(Math.round(Number(value) / 1000));
}

export default function PriceTrendChart({ trends }) {
  const dates = trends?.trends?.dates || [];
  const buyPrices = trends?.trends?.buy_prices || [];
  const sellPrices = trends?.trends?.sell_prices || [];

  if (!dates.length || (!buyPrices.length && !sellPrices.length)) {
    return (
      <EmptyState
        title="No historical data available yet."
        message="Historical chart data is shown only when /api/analytics/trends returns records."
      />
    );
  }

  const spread = dates.map((_, index) => {
    const buy = Number(buyPrices[index]);
    const sell = Number(sellPrices[index]);
    return Number.isFinite(buy) && Number.isFinite(sell) ? sell - buy : null;
  });
  const priceRange = paddedRange([...buyPrices, ...sellPrices], 100000);
  const spreadRange = paddedRange(spread, 10000);

  const data = {
    labels: dates.map((value) => value.slice(0, 10)),
    datasets: [
      {
        label: "Buy",
        data: buyPrices,
        borderColor: "#22d3ee",
        backgroundColor: "rgba(34, 211, 238, 0.08)",
        borderWidth: 3,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.35,
        yAxisID: "price",
      },
      {
        label: "Sell",
        data: sellPrices,
        borderColor: "#34d399",
        backgroundColor: "rgba(52, 211, 153, 0.08)",
        borderWidth: 3,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.35,
        yAxisID: "price",
      },
      {
        label: "Spread",
        data: spread,
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245, 158, 11, 0.06)",
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.35,
        yAxisID: "spread",
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: "#bfdbfe", boxWidth: 10 },
      },
      tooltip: {
        backgroundColor: "#06111f",
        borderColor: "#14304a",
        borderWidth: 1,
        callbacks: {
          label: (context) => `${context.dataset.label}: ${formatThousands(context.parsed.y)} nghìn VND`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: "#7fa2c4" },
        grid: { color: "rgba(20, 48, 74, 0.45)" },
      },
      price: {
        position: "left",
        ...priceRange,
        ticks: {
          color: "#9cc6e8",
          callback: (value) => formatThousands(value),
        },
        title: {
          display: true,
          text: "Giá (nghìn VND)",
          color: "#7fa2c4",
        },
        grid: { color: "rgba(20, 48, 74, 0.45)" },
      },
      spread: {
        position: "right",
        ...spreadRange,
        ticks: {
          color: "#fbbf24",
          callback: (value) => formatThousands(value),
        },
        title: {
          display: true,
          text: "Spread (nghìn VND)",
          color: "#fbbf24",
        },
        grid: { drawOnChartArea: false },
      },
    },
  };

  return (
    <div className="h-[360px] rounded-lg border border-line bg-panel p-4">
      <Line data={data} options={options} />
    </div>
  );
}
