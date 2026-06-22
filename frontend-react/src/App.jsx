import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import TopicDashboardLayout from "./components/extracted-data/TopicDashboardLayout";
import BlockingSignalsPage from "./pages/BlockingSignalsPage";
import CrawlJobsPage from "./pages/CrawlJobsPage";
import EndpointMissingPage from "./pages/EndpointMissingPage";
import ExtractedDataPage from "./pages/ExtractedDataPage";
import GoldPricePage from "./pages/GoldPricePage";
import HitlReviewPage from "./pages/HitlReviewPage";
import OverviewPage from "./pages/OverviewPage";
import SessionsPage from "./pages/SessionsPage";
import SettingsPage from "./pages/SettingsPage";

function GoldWithTopics() {
  return (
    <TopicDashboardLayout>
      <GoldPricePage />
    </TopicDashboardLayout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="gold-price" element={<GoldWithTopics />} />
        <Route path="extracted-data/*" element={<ExtractedDataPage />} />
        <Route path="house-price" element={<Navigate to="/extracted-data/house-price" replace />} />
        <Route path="stock-price" element={<Navigate to="/extracted-data/stock-price" replace />} />
        <Route path="crypto-price" element={<Navigate to="/extracted-data/crypto-price" replace />} />
        <Route path="forex-rate" element={<Navigate to="/extracted-data/forex-rate" replace />} />
        <Route path="commodity-price" element={<Navigate to="/extracted-data/commodity-price" replace />} />
        <Route path="crawl-jobs" element={<CrawlJobsPage />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="blocking-signals" element={<BlockingSignalsPage />} />
        <Route path="hitl" element={<HitlReviewPage />} />
        <Route path="notifications" element={<EndpointMissingPage page="notifications" />} />
        <Route path="audit-logs" element={<EndpointMissingPage page="audit-logs" />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
