import { useEffect, useState } from "react"

const KEY = 'os_theme'

export function getTheme() {
  // TEMPORALMENTE dark para test visual con screenshot MCP que tiene bug
  // con backgrounds claros. Cambiar a 'light' al finalizar pulido visual.
  return localStorage.getItem(KEY) || 'dark'
}

export function setTheme(theme) {
  localStorage.setItem(KEY, theme)
  applyTheme(theme)
}

export function applyTheme(theme) {
  const html = document.documentElement
  if (theme === 'light') html.classList.add('light')
  else html.classList.remove('light')
}

export function useTheme() {
  const [theme, setThemeState] = useState(getTheme)

  useEffect(() => { applyTheme(theme) }, [theme])

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setThemeState(next)
    setTheme(next)
  }

  return { theme, toggle }
}

// Inicializar inmediatamente al cargar
if (typeof window !== 'undefined') {
  applyTheme(getTheme())
}
