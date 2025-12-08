import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import MainContent from './MainContent'
import FloatingChat from '../FloatingChat'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen max-h-screen text-foreground bg-background bg-gradient-mesh overflow-hidden">
      {/* Sidebar */}
      <div className="h-full flex-shrink-0">
        <Sidebar />
      </div>
      
      <div className="flex flex-col flex-1 min-w-0 min-h-0">
        <Header />
        <MainContent>{children}</MainContent>
      </div>
      <FloatingChat />
    </div>
  )
}
