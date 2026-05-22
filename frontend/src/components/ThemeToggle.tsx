import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/components/ThemeProvider'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      aria-label="Toggle theme"
      className="rounded-lg border border-border bg-card p-2 text-muted-foreground hover:bg-subtle hover:text-foreground transition-colors"
    >
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}
