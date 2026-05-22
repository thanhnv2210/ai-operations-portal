import { useState } from 'react'
import { Bot, LayoutDashboard, Search } from 'lucide-react'
import { ThemeProvider } from '@/components/ThemeProvider'
import { ThemeToggle } from '@/components/ThemeToggle'
import { AiAssistant } from '@/pages/AiAssistant'
import { Dashboard } from '@/pages/Dashboard'
import { TransactionExplorer } from '@/pages/TransactionExplorer'

type Tab = 'dashboard' | 'transactions' | 'ai'

const TABS: { id: Tab; label: string; Icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard',    label: 'Dashboard',    Icon: LayoutDashboard },
  { id: 'transactions', label: 'Transactions', Icon: Search },
  { id: 'ai',          label: 'AI Assistant', Icon: Bot },
]

function Shell() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <div className="min-h-screen bg-background">
      {/* Top nav */}
      <nav className="sticky top-0 z-30 border-b border-border bg-card/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-0">
          <div className="flex items-center gap-1">
            <span className="mr-4 text-sm font-semibold text-foreground hidden sm:block">AI Ops Portal</span>
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex items-center gap-2 px-3 py-3.5 text-sm font-medium border-b-2 transition-colors ${
                  tab === id
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
          <ThemeToggle />
        </div>
      </nav>

      {/* Page content */}
      {tab === 'dashboard'    && <Dashboard />}
      {tab === 'transactions' && <TransactionExplorer />}
      {tab === 'ai'           && <AiAssistant />}
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <Shell />
    </ThemeProvider>
  )
}

export default App
