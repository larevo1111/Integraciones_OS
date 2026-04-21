import { Refine } from "@refinedev/core"
import routerProvider from "@refinedev/react-router"
import dataProvider from "@refinedev/simple-rest"
import { BrowserRouter, Routes, Route, Outlet } from "react-router"
import { Layout } from "@/components/layout"
import { DashboardPage } from "@/pages/dashboard"

const API_URL = window.location.origin

function App() {
  return (
    <BrowserRouter>
      <Refine
        routerProvider={routerProvider}
        dataProvider={dataProvider(API_URL + "/api")}
        resources={[
          {
            name: "produccion",
            list: "/produccion",
            meta: { label: "Producción" },
          },
        ]}
        options={{
          syncWithLocation: true,
          disableTelemetry: true,
        }}
      >
        <Routes>
          <Route element={<Layout><Outlet /></Layout>}>
            <Route index element={<DashboardPage />} />
            <Route path="/produccion" element={<DashboardPage />} />
          </Route>
        </Routes>
      </Refine>
    </BrowserRouter>
  )
}

export default App
