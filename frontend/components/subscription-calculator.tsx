'use client'

import { useState, useMemo } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

const KWH_PER_KM = 0.2

interface Plan {
  id: string
  name: string
  price_mo: number
  included_kwh: number | null
  overage_rate: number | null
  note: string
  url: string
}

const PLANS: Plan[] = [
  {
    id: 'clever-one',
    name: 'Clever One',
    price_mo: 799,
    included_kwh: null,
    overage_rate: null,
    note: 'Ubegrænset kWh · med Clever ladeboks (899 kr/md uden)',
    url: 'https://clever.dk/ladeloesninger/opladning-med-abonnement-uden-ladeboks/',
  },
  {
    id: 'norlys-ude-25',
    name: 'Norlys Oplad Ude 25',
    price_mo: 699,
    included_kwh: 400,
    overage_rate: 3.0,
    note: 'Inkl. 400 kWh/md · overage ~3,00 kr/kWh · kræver Norlys elaftale',
    url: 'https://norlys.dk/opladning/oplad-ude/',
  },
  {
    id: 'norlys-ude-15',
    name: 'Norlys Oplad Ude 15',
    price_mo: 499,
    included_kwh: 250,
    overage_rate: 3.0,
    note: 'Inkl. 250 kWh/md · overage ~3,00 kr/kWh · kræver Norlys elaftale',
    url: 'https://norlys.dk/opladning/oplad-ude/',
  },
]

function planCost(plan: Plan, kwhPublic: number): number {
  if (plan.included_kwh === null) return plan.price_mo
  const over = Math.max(0, kwhPublic - plan.included_kwh)
  return plan.price_mo + over * (plan.overage_rate ?? 0)
}

function breakEvenPublicKm(plan: Plan, goPrice: number): number {
  const rate = goPrice * KWH_PER_KM
  if (rate <= 0) return Infinity
  if (plan.included_kwh === null) {
    return plan.price_mo / rate
  }
  const kmBelow = plan.price_mo / rate
  const kwhBelow = kmBelow * KWH_PER_KM
  if (kwhBelow <= plan.included_kwh) return kmBelow
  // break-even above included_kwh threshold
  const denom = KWH_PER_KM * (goPrice - (plan.overage_rate ?? 0))
  if (denom <= 0) return Infinity
  return (plan.price_mo - plan.included_kwh * (plan.overage_rate ?? 0)) / denom
}

function fmt(value: number): string {
  return Math.round(value).toLocaleString('da-DK')
}

function fmtDec(value: number): string {
  return value.toLocaleString('da-DK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const diffMin = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (diffMin < 1) return 'lige nu'
  if (diffMin < 60) return `${diffMin} min siden`
  return `${Math.floor(diffMin / 60)} t siden`
}

interface Props {
  goPrice: number | null
  goUpdatedAt: string | null
}

export function SubscriptionCalculator({ goPrice, goUpdatedAt }: Props) {
  const [kmMo, setKmMo] = useState(1200)
  const [publicPct, setPublicPct] = useState(30)

  const effectiveGoPrice = goPrice ?? 4.5
  const kwhPublic = kmMo * (publicPct / 100) * KWH_PER_KM

  const planResults = useMemo(
    () => PLANS.map(p => ({ ...p, total: planCost(p, kwhPublic) })),
    [kwhPublic],
  )

  const paygTotal = kwhPublic * effectiveGoPrice

  const bestSubscription = useMemo(
    () => [...planResults].sort((a, b) => a.total - b.total)[0],
    [planResults],
  )

  const subscriptionWins = bestSubscription.total < paygTotal
  const annualSavings = (paygTotal - bestSubscription.total) * 12

  const allResultsSorted = useMemo(
    () =>
      [
        ...planResults,
        {
          id: 'payg',
          name: 'Ingen aftale (Clever GO)',
          price_mo: 0,
          included_kwh: null,
          overage_rate: null,
          note: goPrice ? `${fmtDec(goPrice)} kr/kWh (live)` : `${fmtDec(4.5)} kr/kWh (estimeret)`,
          url: '',
          total: paygTotal,
        },
      ].sort((a, b) => a.total - b.total),
    [planResults, paygTotal, goPrice],
  )

  const goDisplay = goPrice ? `${fmtDec(goPrice)} kr/kWh` : `${fmtDec(4.5)} kr/kWh (estimeret)`

  return (
    <div className="space-y-6 max-w-xl">
      {/* Live price badge */}
      <div className="flex items-center flex-wrap gap-2 text-sm">
        <Badge variant={goPrice ? 'default' : 'secondary'}>{goPrice ? 'Live' : 'Estimeret'}</Badge>
        <span className="text-muted-foreground">
          Clever GO-pris:{' '}
          <span className="font-medium text-foreground">{goDisplay}</span>
          {goUpdatedAt && (
            <span> · opdateret {timeAgo(goUpdatedAt)}</span>
          )}
        </span>
        {!goPrice && (
          <span className="text-xs text-muted-foreground">(live data ikke tilgængelig)</span>
        )}
      </div>

      {/* Inputs */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Km per måned</label>
          <Input
            type="number"
            min={0}
            value={kmMo}
            onChange={e => setKmMo(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1.5">
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

      {/* Verdict card */}
      {subscriptionWins ? (
        <div className="rounded-xl border-2 border-green-200 bg-green-50 p-6 space-y-4 dark:bg-green-950/20 dark:border-green-900">
          <p className="text-xs font-semibold uppercase tracking-widest text-green-700 dark:text-green-400">
            Anbefalet aftale
          </p>
          <div>
            <h2 className="text-xl font-bold">{bestSubscription.name}</h2>
            <p className="text-sm text-muted-foreground">{bestSubscription.note}</p>
          </div>
          <div className="space-y-0.5">
            <p className="text-sm text-muted-foreground">sparer dig</p>
            <p className="text-4xl font-extrabold text-green-700 dark:text-green-400 tabular-nums">
              {fmt(annualSavings)} kr/år
            </p>
            <p className="text-sm text-muted-foreground">
              vs. at betale per opladning ({goDisplay})
            </p>
          </div>
          {publicPct > 0 && (
            <p className="text-sm text-muted-foreground">
              Break-even ved{' '}
              <span className="font-semibold text-foreground">
                {Math.ceil(breakEvenPublicKm(bestSubscription, effectiveGoPrice)).toLocaleString('da-DK')} km/md
              </span>{' '}
              offentlig opladning
            </p>
          )}
          <a
            href={bestSubscription.url}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="inline-flex items-center gap-1.5 rounded-lg bg-green-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-green-800 active:translate-y-px transition-colors"
          >
            Gå til {bestSubscription.name} →
          </a>
        </div>
      ) : (
        <div className="rounded-xl border bg-muted/40 p-6 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Ingen aftale nødvendig
          </p>
          <h2 className="text-lg font-bold">Du oplader for lidt til et abonnement</h2>
          <p className="text-sm text-muted-foreground">
            Med din nuværende kørsel er det billigst at betale per opladning ({goDisplay}).
            {publicPct > 0 && (
              <>
                {' '}Clever One betaler sig ved mere end{' '}
                <span className="font-medium text-foreground">
                  {Math.ceil(breakEvenPublicKm(PLANS[0], effectiveGoPrice)).toLocaleString('da-DK')} km/md
                </span>{' '}
                offentlig opladning.
              </>
            )}
          </p>
        </div>
      )}

      {/* Plan comparison */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Sammenligning
        </h3>
        {allResultsSorted.map((p, i) => (
          <div
            key={p.id}
            className={[
              'flex items-center justify-between gap-4 rounded-lg border px-4 py-3',
              i === 0
                ? 'border-green-200 bg-green-50/60 dark:bg-green-950/10 dark:border-green-900'
                : 'bg-card',
            ].join(' ')}
          >
            <div className="min-w-0 flex-1">
              {p.url ? (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer sponsored"
                  className="font-medium text-sm hover:underline truncate block"
                >
                  {p.name}
                </a>
              ) : (
                <p className="font-medium text-sm truncate">{p.name}</p>
              )}
              <p className="text-xs text-muted-foreground truncate">{p.note}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-sm font-semibold tabular-nums">
                {fmt(p.total)} kr/md
              </span>
              {i === 0 && (
                <Badge className="bg-green-600 text-white shrink-0">Billigst</Badge>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Info note */}
      <p className="text-xs text-muted-foreground leading-relaxed">
        Beregningen antager {KWH_PER_KM * 100} kWh/100 km og gælder udelukkende offentlig opladning.
        Norlys overage-takst estimeret til 3,00 kr/kWh (offentlig AC-pris).
        Abonnementspriser ekskl. eventuelle energitillæg (gælder begge operatører ved spotpris over 0,89 kr/kWh).
      </p>

      {/* Affiliate disclosure */}
      <p className="text-xs text-muted-foreground border-t pt-4">
        Vi modtager provision ved tegning af aftale via vores links. Priser er vejledende og kan
        afvige fra operatørernes aktuelle betingelser.{' '}
      </p>
    </div>
  )
}
