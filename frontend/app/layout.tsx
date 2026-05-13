import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import Script from 'next/script'
import { Nav } from '@/components/nav'
import { ServiceWorkerRegistration } from '@/components/service-worker-registration'
import './globals.css'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: { template: '%s | Elbilspriser.dk', default: 'Elbilspriser.dk' },
  description: 'Sammenlign aktuelle ladepriser for elbiler i Danmark.',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const domain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN

  return (
    <html lang="da" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <head>
        <link rel="manifest" href="/manifest.json" />
        {domain && (
          <Script
            src="https://plausible.io/js/script.js"
            defer
            data-domain={domain}
            strategy="afterInteractive"
          />
        )}
      </head>
      <body className="min-h-full flex flex-col">
        <Nav />
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
        <ServiceWorkerRegistration />
      </body>
    </html>
  )
}
