import React from "react";
import ReactDOM from "react-dom/client";

import HomePage from "./app/page";
import LibraryPage from "./app/library/page";
import SegmentDetailPage from "./app/segments/[segmentId]/page";
import StockResearchPage from "./app/stocks/[stockCode]/page";
import WatchlistPage from "./app/watchlist/page";
import "./styles/app-shell.css";

function resolveStockCode(pathname: string): string {
  const match = pathname.match(/^\/stocks\/([^/]+)$/);
  return match?.[1] ?? "";
}

function resolveSegmentId(pathname: string): string {
  const match = pathname.match(/^\/segments\/([^/]+)$/);
  return match?.[1] ?? "1";
}

function App() {
  if (window.location.pathname === "/") {
    return <HomePage />;
  }

  if (window.location.pathname === "/library") {
    return <LibraryPage />;
  }

  if (window.location.pathname === "/watchlist") {
    return <WatchlistPage />;
  }

  if (window.location.pathname === "/stocks") {
    return <StockResearchPage stockCode="" />;
  }

  if (window.location.pathname.startsWith("/segments/")) {
    return <SegmentDetailPage segmentId={resolveSegmentId(window.location.pathname)} />;
  }

  if (window.location.pathname.startsWith("/stocks/")) {
    return <StockResearchPage stockCode={resolveStockCode(window.location.pathname)} />;
  }

  return <HomePage />;
}

const root = document.getElementById("root");
if (root === null) {
  throw new Error("root element not found");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
