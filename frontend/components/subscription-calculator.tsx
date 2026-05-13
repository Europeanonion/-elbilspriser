'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

interface Plan {
  name: string
  price_mo: number
  price_kwh: number
  affiliate_url: string
}

const PLANS: Plan[] = [
  { name: 'Clever Ubegrænset', price_mo: 799, price_kwh: 0, affiliate_url: '#' },
  { name: 'Norlys EV+', price_mo: 599, price_kwh: 1.99, affiliate_url: '#' },
  { name: 'Norlys EV', price_mo: 449, price_kwh: 2.49, affiliate_url: '#' },
  { name: 'Ingen aftale (markedssnit)', price_mo: 0, price_kwh: 4.5, affiliate_url: '' },
]

const KWH_PER_KM = 0.2

function monthlyCost(plan: Plan, kmMo: number, publicPct: number): number {
  const publicKm = kmMo * (publicPct / 100)
  const kwhPublic = publicKm * KWH_PER_KM
  return plan.price_mo + kwhPublic * plan.price_kwh
}

export function SubscriptionCalculator() {
  const [kmMo, setKmMo] = useState(1000)
  const [publicPct, setPublicPct] = useState(30)

  const results = [...PLANS]
    .map(p => ({ ...p, total: monthlyCost(p, kmMo, publicPct) }))
    .sort((a, b) => a.total - b.total)

  return (
    <div className="space-y-6 max-w-xl">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-sm font-medium">Km per måned</label>
          <Input
            type="number"
            min={0}
            value={kmMo}
            onChange={e => setKmMo(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Offentlig opladning (%)</label>
          <Input
            type="number"
            min={0}
            max={100}
            value={publicPct}
            onChange={e => setPublicPct(Number(e.target.value))}
          />
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Beregningen antager 0,2 kWh/km og gælder udelukkende offentlig opladning.
      </p>

      <div className="space-y-3">
        {results.map((p, i) => (
          <Card key={p.name} className={i === 0 ? 'border-green-500' : ''}>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-base flex items-center gap-2">
                {i === 0 && <Badge className="bg-green-600">Billigst</Badge>}
                {p.affiliate_url ? (
                  <a href={p.affiliate_url} className="hover:underline" rel="sponsored noopener">
                    {p.name}
                  </a>
                ) : p.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 text-sm text-muted-foreground">
              <span className="text-foreground font-semibold text-lg">
                {p.total.toLocaleString('da-DK', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} kr/md
              </span>
              {' '}(abonnement {p.price_mo} kr + {(p.total - p.price_mo).toLocaleString('da-DK', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} kr forbrug)
              {p.affiliate_url && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Affiliatelink – vi modtager provision ved køb. <a href="/om" className="underline">Læs mere</a>
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
