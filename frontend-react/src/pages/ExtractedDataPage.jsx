import { Navigate, Route, Routes } from "react-router-dom";
import TopicDashboardLayout from "../components/extracted-data/TopicDashboardLayout";
import EmptyState from "../components/common/EmptyState";
import GoldPricePage from "./GoldPricePage";

const topicMessages = {
  "house-price": {
    title: "House Price topic is not connected yet. Backend endpoint required.",
    message: "TODO: Backend needed: GET /topics/house-price or GET /house-prices",
  },
  "stock-price": {
    title: "Stock Price topic is not connected yet. Backend endpoint required.",
    message: "TODO: Backend needed: GET /topics/stock-price or GET /stock-prices",
  },
  "crypto-price": {
    title: "Crypto Price topic is not connected yet. Backend endpoint required.",
    message: "TODO: Backend needed: GET /topics/crypto-price or GET /crypto-prices",
  },
  "forex-rate": {
    title: "Forex Rate topic is not connected yet. Backend endpoint required.",
    message: "TODO: Backend needed: GET /topics/forex-rate or GET /forex-rates",
  },
  "commodity-price": {
    title: "Commodity Price topic is not connected yet. Backend endpoint required.",
    message: "TODO: Backend needed: GET /topics/commodity-price or GET /commodity-prices",
  },
};

function MissingTopic({ topic }) {
  const copy = topicMessages[topic] || {
    title: "This topic is not connected to a backend endpoint yet.",
    message: "Backend endpoint required.",
  };
  return <EmptyState title={copy.title} message={copy.message} />;
}

export default function ExtractedDataPage() {
  return (
    <TopicDashboardLayout>
      <Routes>
        <Route index element={<Navigate to="gold-price" replace />} />
        <Route path="gold-price" element={<GoldPricePage />} />
        <Route path="house-price" element={<MissingTopic topic="house-price" />} />
        <Route path="stock-price" element={<MissingTopic topic="stock-price" />} />
        <Route path="crypto-price" element={<MissingTopic topic="crypto-price" />} />
        <Route path="forex-rate" element={<MissingTopic topic="forex-rate" />} />
        <Route path="commodity-price" element={<MissingTopic topic="commodity-price" />} />
      </Routes>
    </TopicDashboardLayout>
  );
}
