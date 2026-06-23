import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./app/App";
import { QueryProvider } from "./app/providers/QueryProvider";
import "./styles/styles.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <QueryProvider>
      <App />
    </QueryProvider>
  </StrictMode>,
);
