import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import { AnalysesPage } from "./pages/AnalysesPage";
import { DealReportPage } from "./pages/DealReportPage";
import { DocumentDetailPage } from "./pages/DocumentDetailPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { LoginPage } from "./pages/LoginPage";
import { NewAnalysisPage } from "./pages/NewAnalysisPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SensitivityPage } from "./pages/SensitivityPage";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/documents"
          element={
            <ProtectedRoute>
              <DocumentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/documents/:documentId"
          element={
            <ProtectedRoute>
              <DocumentDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analysis/new"
          element={
            <ProtectedRoute>
              <NewAnalysisPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analyses"
          element={
            <ProtectedRoute>
              <AnalysesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analyses/:analysisId"
          element={
            <ProtectedRoute>
              <DealReportPage />
            </ProtectedRoute>
          }
        />
        <Route path="/analysis/result" element={<Navigate to="/analyses" replace />} />
        <Route
          path="/sensitivity"
          element={
            <ProtectedRoute>
              <SensitivityPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/documents" replace />} />
        <Route path="*" element={<Navigate to="/documents" replace />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
