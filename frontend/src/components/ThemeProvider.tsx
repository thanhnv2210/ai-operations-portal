import { createContext, useContext, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

type ThemeContextValue = {
  theme: Theme
  setTheme: (t: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  setTheme: () => {},
})

export function useTheme() {
  return useContext(ThemeContext)
}

const STORAGE_KEY = 'ai-ops-portal:theme'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('dark')

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null
    const resolved: Theme = stored === 'light' ? 'light' : 'dark'
    setThemeState(resolved)
    document.documentElement.classList.toggle('dark', resolved === 'dark')
  }, [])

  function setTheme(t: Theme) {
    setThemeState(t)
    localStorage.setItem(STORAGE_KEY, t)
    document.documentElement.classList.toggle('dark', t === 'dark')
  }

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>
}
