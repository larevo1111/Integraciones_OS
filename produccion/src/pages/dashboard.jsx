import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function DashboardPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Programación de Producción</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>OPs Pendientes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">—</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>En Proceso</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">—</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Completadas Hoy</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">—</p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Stack listo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-muted-foreground">React 18 + Vite + Refine + Shadcn/ui + Tailwind CSS</p>
          <Button>Comenzar</Button>
        </CardContent>
      </Card>
    </div>
  )
}
