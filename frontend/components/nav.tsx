'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const links = [
  { href: '/', label: 'Priser' },
  { href: '/map', label: 'Kort' },
  { href: '/beregner', label: 'Beregner' },
]

export function Nav() {
  const pathname = usePathname()
  return (
    <nav className="border-b mb-6">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-6">
        <span className="font-bold text-green-600">Elbilspriser.dk</span>
        {links.map(l => (
          <Link
            key={l.href}
            href={l.href}
            className={cn(
              'text-sm font-medium transition-colors hover:text-foreground',
              pathname === l.href ? 'text-foreground' : 'text-muted-foreground',
            )}
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  )
}
