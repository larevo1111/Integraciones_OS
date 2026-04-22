import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { GoogleOAuthProvider } from "@react-oauth/google"
import { Layout } from "@/components/layout"
import "@/lib/theme"  // inicializa tema
import { auth } from "@/lib/auth"
import { LoginPage } from "@/pages/login"
import { SolicitudesPage } from "@/pages/solicitudes"
import { DashboardPage } from "@/pages/dashboard"
import { PlaceholderPage } from "@/pages/placeholder"
import { InventariosListaPage } from "@/pages/inventarios-lista"
import { InventariosExcluidosPage } from "@/pages/inventarios-excluidos"
import { InventariosObservacionesPage } from "@/pages/inventarios-observaciones"
import { InventariosOpsRevisarPage } from "@/pages/inventarios-ops-revisar"
import { InventariosCatalogoPage } from "@/pages/inventarios-catalogo"
import { InventariosSyncEffiPage } from "@/pages/inventarios-sync-effi"
import { InventariosAnalisisIAPage } from "@/pages/inventarios-analisis-ia"
import { InventariosInformesPage } from "@/pages/inventarios-informes"
import {
  Calendar, BookOpen, Settings,
  ListChecks, Boxes, EyeOff, MessageSquare, AlertTriangle,
  RefreshCw, Sparkles, FileText, Lock,
} from "lucide-react"

const GOOGLE_CLIENT_ID = "290093919454-j2l1el0p624v65cada556pdc3r2gm6k7.apps.googleusercontent.com"

function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/solicitudes" element={<SolicitudesPage />} />
        <Route path="/calendario" element={<PlaceholderPage title="Calendario" icon={Calendar} descripcion="Vista mensual de solicitudes programadas (próximamente)" />} />
        <Route path="/recetas" element={<PlaceholderPage title="Recetas" icon={BookOpen} descripcion="Gestión de recetas por producto (próximamente)" />} />
        <Route path="/config" element={<PlaceholderPage title="Configuración" icon={Settings} descripcion="Parámetros del módulo (próximamente)" />} />

        {/* ── INVENTARIOS — sub-módulo ─────────────────────────────────── */}
        <Route path="/inventarios" element={<Navigate to="/inventarios/conteo" replace />} />
        <Route path="/inventarios/conteo"        element={<PlaceholderPage title="Conteo físico"     icon={ListChecks}     descripcion="Captura de conteos físicos por bodega (en migración)" />} />
        <Route path="/inventarios/lista"         element={<InventariosListaPage />} />
        <Route path="/inventarios/catalogo"      element={<InventariosCatalogoPage />} />
        <Route path="/inventarios/excluidos"     element={<InventariosExcluidosPage />} />
        <Route path="/inventarios/observaciones" element={<InventariosObservacionesPage />} />
        <Route path="/inventarios/ops-revisar"   element={<InventariosOpsRevisarPage />} />
        <Route path="/inventarios/sync-effi"     element={<InventariosSyncEffiPage />} />
        <Route path="/inventarios/analisis-ia"   element={<InventariosAnalisisIAPage />} />
        <Route path="/inventarios/informes"      element={<InventariosInformesPage />} />
        <Route path="/inventarios/politicas"     element={<PlaceholderPage title="Políticas"         icon={Lock}           descripcion="Gestión de permisos por rol (en migración)" />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

function AuthGuard() {
  const [authed, setAuthed] = useState(auth.isAuth)
  useEffect(() => auth.subscribe(() => setAuthed(auth.isAuth)), [])
  return authed ? <AppRoutes /> : <LoginPage />
}

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <AuthGuard />
      </BrowserRouter>
    </GoogleOAuthProvider>
  )
}

export default App
