export function PlaceholderPage({ title, icon: Icon, descripcion }) {
  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">{title}</h1>
      </div>
      <div className="rounded-lg border bg-card p-12 flex flex-col items-center justify-center text-center">
        {Icon && <Icon className="h-12 w-12 text-muted-foreground mb-4" />}
        <p className="text-muted-foreground">{descripcion}</p>
      </div>
    </div>
  )
}
