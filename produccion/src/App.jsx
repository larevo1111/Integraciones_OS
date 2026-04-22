import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { GoogleOAuthProvider } from "@react-oauth/google"
import { Layout } from "@/components/layout"
import "@/lib/theme"
import { auth } from "@/lib/auth"
import { LoginPage } from "@/pages/login"
import { SolicitudesPage } from "@/pages/solicitudes"
import { DashboardPage } from "@/pages/dashboard"
import { PlaceholderPage } from "@/pages/placeholder"
import { InventariosLayoutPage } from "@/pages/inventarios-layout"
import { CatalogoPage } from "@/pages/catalogo"
import { Calendar, BookOpen, Settings } from "lucide-react"

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

        {/* Inventarios: flyout de fechas + vista completa por fecha */}
        <Route path="/inventarios" element={<InventariosLayoutPage />} />
        <Route path="/inventarios/:fecha" element={<InventariosLayoutPage />} />

        {/* Catálogo de productos (nuevo) */}
        <Route path="/catalogo" element={<CatalogoPage />} />

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
