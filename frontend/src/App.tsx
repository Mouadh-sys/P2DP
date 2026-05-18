import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";

import RequireAuth from "./components/RequireAuth";
import DashboardLayout from "./layouts/DashboardLayout";
import LoginPage from "./pages/LoginPage";
import ProjectsPage from "./pages/ProjectsPage";
import EnvironmentPage from "./pages/EnvironmentPage";
import EnvironmentDetailPage from "./pages/EnvironmentDetailPage";
import DeploymentDashboard from "./pages/DeploymentDashboard";
import UploadTemplatePage from "./pages/UploadTemplatePage";
import FindingsPage from "./pages/FindingsPage";
import RiskForecastPage from "./pages/RiskForecastPage";
import ThreatAlertsPage from "./pages/ThreatAlertsPage";
import TracesPage from "./pages/TracesPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";

const lightTheme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#4f46e5" },
    background: { default: "#f8fafc", paper: "#ffffff" },
    error: { main: "#f43f5e" },
    warning: { main: "#f59e0b" },
    info: { main: "#0ea5e9" },
    success: { main: "#10b981" },
    text: { primary: "#0f172a", secondary: "#64748b" },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "uppercase",
          fontWeight: 700,
          borderRadius: "4px",
          fontSize: "0.625rem",
          padding: "4px 12px",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        },
      },
    },
  },
});

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: <RequireAuth />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: "dashboard", element: <DeploymentDashboard /> },
          { path: "projects", element: <ProjectsPage /> },
          { path: "projects/:projectId/environments", element: <EnvironmentDetailPage /> },
          {
            path: "projects/:projectId/environments/:environmentId/findings",
            element: <FindingsPage />,
          },
          {
            path: "projects/:projectId/environments/:environmentId/risk",
            element: <RiskForecastPage />,
          },
          { path: "environment", element: <EnvironmentPage /> },
          { path: "upload", element: <UploadTemplatePage /> },
          { path: "findings", element: <Navigate to="/projects" replace /> },
          { path: "risk", element: <Navigate to="/projects" replace /> },
          { path: "threats", element: <ThreatAlertsPage /> },
          { path: "traces", element: <TracesPage /> },
          { path: "reports", element: <ReportsPage /> },
          { path: "settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return (
    <ThemeProvider theme={lightTheme}>
      <CssBaseline />
      <RouterProvider router={router} />
    </ThemeProvider>
  );
}
