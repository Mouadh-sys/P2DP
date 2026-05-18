import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import {
  Alert,
  Button,
  CssBaseline,
  TextField,
  Typography,
  Container,
  Box,
  ThemeProvider,
  createTheme,
} from "@mui/material";

import { authApi } from "../api/endpoints";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#4f46e5" },
    background: { default: "#f8fafc", paper: "#ffffff" },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "uppercase",
          fontWeight: 700,
          borderRadius: "4px",
          fontSize: "0.625rem",
          padding: "8px 16px",
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: "4px", fontSize: "0.875rem" },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { fontSize: "0.875rem" },
      },
    },
  },
});

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    try {
      const response = await authApi.login(email, password);
      localStorage.setItem("token", response.data.access_token);
      navigate("/dashboard");
    } catch {
      setError("Login failed. Verify your credentials.");
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <Container component="main" maxWidth="xs">
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              bgcolor: "background.paper",
              p: 4,
              borderRadius: 2,
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            }}
          >
            <div className="w-16 h-16 bg-indigo-50 flex items-center justify-center mb-4 rounded-full border border-indigo-100 shadow-sm">
              <ShieldAlert size={32} className="text-indigo-600" />
            </div>
            <Typography component="h1" variant="h5" className="font-bold text-slate-900 mb-2">
              P2DP
            </Typography>
            <Typography variant="body2" className="text-slate-500 text-center mb-6 text-sm">
              Predictive DevSecOps Deployment and Protection
            </Typography>
            <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1, width: "100%" }}>
              {error ? (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              ) : null}
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                size="small"
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                size="small"
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                className="bg-indigo-600 hover:bg-indigo-700 transition"
                disableElevation
              >
                Sign In
              </Button>
            </Box>
          </Box>
        </Container>
      </div>
    </ThemeProvider>
  );
}
