import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'IDS Dashboard - Intrusion Detection System',
  description: 'Real-time network intrusion detection and monitoring dashboard',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen bg-dark-bg">
          {children}
        </div>
      </body>
    </html>
  )
}
