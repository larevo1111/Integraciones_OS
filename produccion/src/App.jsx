import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { Layout } from "@/components/layout"
import "@/lib/theme"  // inicializa tema
import { SolicitudesPage } from "@/pages/solicitudes"
import { DashboardPage } from "@/pages/dashboard"
import { PlaceholderPage } from "@/pages/placeholder"
import {
  Calendar, BookOpen, Settings,
  ListChecks, Boxes, EyeOff, MessageSquare, AlertTriangle,
  RefreshCw, Sparkles, FileText, Lock,
} from "lucide-react"

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

          {/* ── INVENTARIOS — sub-módulo ─────────────────────────────────── */}
          <Route path="/inventarios" element={<Navigate to="/inventarios/conteo" replace />} />
          <Route path="/inventarios/conteo"        element={<PlaceholderPage title="Conteo físico"     icon={ListChecks}     descripcion="Captura de conteos físicos por bodega (en migración)" />} />
          <Route path="/inventarios/lista"         element={<PlaceholderPage title="Inventarios"       icon={Boxes}          descripcion="Lista de inventarios por fecha (en migración)" />} />
          <Route path="/inventarios/catalogo"      element={<PlaceholderPage title="Catálogo"          icon={BookOpen}       descripcion="Artículos matriculados + sync Effi (en migración)" />} />
          <Route path="/inventarios/excluidos"     element={<PlaceholderPage title="Excluidos"         icon={EyeOff}         descripcion="Artículos excluidos del inventario (en migración)" />} />
          <Route path="/inventarios/observaciones" element={<PlaceholderPage title="Observaciones"     icon={MessageSquare}  descripcion="Notas por inventario (en migración)" />} />
          <Route path="/inventarios/ops-revisar"   element={<PlaceholderPage title="OPs a revisar"     icon={AlertTriangle}  descripcion="OPs sospechosas a verificar (en migración)" />} />
          <Route path="/inventarios/sync-effi"     element={<PlaceholderPage title="Sync Effi"         icon={RefreshCw}      descripcion="Envío de ajustes a Effi (en migración)" />} />
          <Route path="/inventarios/analisis-ia"   element={<PlaceholderPage title="Análisis IA"       icon={Sparkles}       descripcion="Reporte ejecutivo generado por IA (en migración)" />} />
          <Route path="/inventarios/informes"      element={<PlaceholderPage title="Informes"          icon={FileText}       descripcion="Descarga de PDFs históricos (en migración)" />} />
          <Route path="/inventarios/politicas"     element={<PlaceholderPage title="Políticas"         icon={Lock}           descripcion="Gestión de permisos por rol (en migración)" />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
