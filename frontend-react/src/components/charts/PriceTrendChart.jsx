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

  const data = {
    labels: dates.map((value) => value.slice(0, 10)),
    datasets: [
      {
        label: "Buy",
        data: buyPrices,
        borderColor: "#22d3ee",
        backgroundColor: "rgba(34, 211, 238, 0.08)",
        tension: 0.35,
      },
      {
        label: "Sell",
        data: sellPrices,
        borderColor: "#34d399",
        backgroundColor: "rgba(52, 211, 153, 0.08)",
        tension: 0.35,
      },
      {
        label: "Spread",
        data: spread,
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245, 158, 11, 0.06)",
        tension: 0.35,
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
      },
    },
    scales: {
      x: {
        ticks: { color: "#7fa2c4" },
        grid: { color: "rgba(20, 48, 74, 0.45)" },
      },
      y: {
        ticks: { color: "#7fa2c4" },
        grid: { color: "rgba(20, 48, 74, 0.45)" },
      },
    },
  };

  return (
    <div className="h-[320px] rounded-lg border border-line bg-panel p-4">
      <Line data={data} options={options} />
    </div>
  );
}
