import { Navigate, Route, Routes } from "react-router-dom";

import EnvironmentDetail from "./pages/EnvironmentDetail";
import Findings from "./pages/Findings";
import Login from "./pages/Login";
import Projects from "./pages/Projects";
import RiskForecast from "./pages/RiskForecast";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/projects"
        element={
          <RequireAuth>
            <Projects />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:projectId/environments"
        element={
          <RequireAuth>
            <EnvironmentDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:projectId/environments/:environmentId/findings"
        element={
          <RequireAuth>
            <Findings />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:projectId/environments/:environmentId/risk"
        element={
          <RequireAuth>
            <RiskForecast />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  );
}

export default App;
