'use client'

import { useState, useMemo } from 'react'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

interface Price {
  station_id: string
  name: string
  operator: string
  price_kwh: number | null
  price_min: number | null
  session_fee: number | null
  updated_at: string
}

function formatDKK(value: number | null): string {
  if (value === null) return '—'
  return value.toLocaleString('da-DK', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kr'
}

function isFresh(updatedAt: string): boolean {
  return Date.now() - new Date(updatedAt).getTime() < 15 * 60 * 1000
}

export function PriceTable({ prices }: { prices: Price[] }) {
  const [query, setQuery] = useState('')

  const sorted = useMemo(() => {
    const filtered = prices.filter(p =>
      `${p.operator} ${p.name}`.toLowerCase().includes(query.toLowerCase())
    )
    return [...filtered].sort((a, b) => {
      if (a.price_kwh === null) return 1
      if (b.price_kwh === null) return -1
      return a.price_kwh - b.price_kwh
    })
  }, [prices, query])

  return (
    <div className="space-y-4">
      <Input
        placeholder="Søg operatør eller lokation…"
        value={query}
        onChange={e => setQuery(e.target.value)}
        className="max-w-sm"
      />
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Operatør</TableHead>
              <TableHead>Lokation</TableHead>
              <TableHead className="text-right">kr/kWh</TableHead>
              <TableHead className="text-right">kr/min</TableHead>
              <TableHead className="text-right">Startgebyr</TableHead>
              <TableHead>Opdateret</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  Ingen resultater
                </TableCell>
              </TableRow>
            ) : sorted.map(p => (
              <TableRow key={p.station_id}>
                <TableCell className="font-medium">{p.operator}</TableCell>
                <TableCell>{p.name}</TableCell>
                <TableCell className="text-right">{formatDKK(p.price_kwh)}</TableCell>
                <TableCell className="text-right">{formatDKK(p.price_min)}</TableCell>
                <TableCell className="text-right">{formatDKK(p.session_fee)}</TableCell>
                <TableCell>
                  <Badge variant={isFresh(p.updated_at) ? 'default' : 'secondary'}>
                    {isFresh(p.updated_at) ? 'Frisk' : 'Ældre'}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
