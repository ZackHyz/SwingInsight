import React from "react";
import ReactDOM from "react-dom/client";

import StockResearchPage from "./app/stocks/[stockCode]/page";

function resolveStockCode(pathname: string): string {
  const match = pathname.match(/^\/stocks\/([^/]+)$/);
  return match?.[1] ?? "600157";
}

function App() {
  return <StockResearchPage stockCode={resolveStockCode(window.location.pathname)} />;
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
