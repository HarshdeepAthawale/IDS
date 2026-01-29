import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'
import { WebSocketProviderWrapper } from '@/components/websocket-provider-wrapper'
import { PcapAnalysisProvider } from '@/contexts/pcap-analysis-context'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: 'IDS',
  description: 'Intrusion Detection System',
  generator: 'IDS',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`font-sans antialiased`}>
        <WebSocketProviderWrapper>
          <PcapAnalysisProvider>
            {children}
            <Analytics />
          </PcapAnalysisProvider>
        </WebSocketProviderWrapper>
      </body>
    </html>
  )
}
