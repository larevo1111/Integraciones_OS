import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { Layout } from "@/components/layout"
import "@/lib/theme"  // inicializa tema
import { SolicitudesPage } from "@/pages/solicitudes"
import { DashboardPage } from "@/pages/dashboard"
import { PlaceholderPage } from "@/pages/placeholder"
import { Calendar, BookOpen, Settings } from "lucide-react"

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/solicitudes" element={<SolicitudesPage />} />
          <Route path="/calendario" element={<PlaceholderPage title="Calendario" icon={Calendar} descripcion="Vista mensual de solicitudes programadas (próximamente)" />} />
          <Route path="/recetas" element={<PlaceholderPage title="Recetas" icon={BookOpen} descripcion="Gestión de recetas por producto (próximamente)" />} />
          <Route path="/config" element={<PlaceholderPage title="Configuración" icon={Settings} descripcion="Parámetros del módulo (próximamente)" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
