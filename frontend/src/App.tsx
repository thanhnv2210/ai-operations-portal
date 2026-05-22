import { ThemeProvider } from '@/components/ThemeProvider'
import { Dashboard } from '@/pages/Dashboard'

function App() {
  return (
    <ThemeProvider>
      <Dashboard />
    </ThemeProvider>
  )
}

export default App
