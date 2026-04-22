import { useState } from "react"
import { GoogleLogin } from "@react-oauth/google"
import { api } from "@/lib/api"
import { auth } from "@/lib/auth"

export function LoginPage() {
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const onGoogleSuccess = async (credentialResponse) => {
    setLoading(true); setError(null)
    try {
      const r = await api.post('/api/auth/google', { id_token: credentialResponse.credential })
      auth.login(r.token, r.usuario)
      // Redirige al home — el AuthGuard re-renderiza la app
      window.location.href = '/'
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-sm bg-card border border-border rounded-2xl p-8 shadow-lg">
        {/* Logo */}
        <div className="flex justify-center mb-5">
          <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center text-primary-foreground font-bold text-lg">
            OS
          </div>
        </div>

        <h1 className="text-center text-[18px] font-semibold mb-1">Producción + Inventario</h1>
        <p className="text-center text-[13px] text-muted-foreground mb-6">
          Iniciá sesión con tu cuenta autorizada de Origen Silvestre
        </p>

        {error && (
          <div className="mb-4 px-3 py-2 rounded bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">
            {error}
          </div>
        )}

        <div className="flex justify-center">
          {loading
            ? <span className="text-[13px] text-muted-foreground">Verificando…</span>
            : (
              <GoogleLogin
                onSuccess={onGoogleSuccess}
                onError={() => setError('Login con Google falló')}
                theme="filled_black"
                size="large"
                text="signin_with"
                width="280"
              />
            )}
        </div>

        <p className="text-center text-[11px] text-muted-foreground mt-6">
          Solo usuarios autorizados en sys_usuarios pueden acceder
        </p>
      </div>
    </div>
  )
}
