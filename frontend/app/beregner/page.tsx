import type { Metadata } from 'next'
import { SubscriptionCalculator } from '@/components/subscription-calculator'

export const revalidate = 900

export const metadata: Metadata = {
  title: 'Ladeprisberegner',
  description: 'Beregn hvilken ladeabonnement der er billigst for din kørsel. Sammenlign Clever One og Norlys Oplad Ude med live priser.',
}

async function getGoPrice(): Promise<{ price_kwh: number | null; updated_at: string | null }> {
  const url = `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/api/v1/operator-price?operator_id=1`
  try {
    const res = await fetch(url, { next: { revalidate: 900 } })
    if (!res.ok) throw new Error(`API ${res.status}`)
    return res.json()
  } catch {
    return { price_kwh: null, updated_at: null }
  }
}

export default async function BeregnerPage() {
  const { price_kwh, updated_at } = await getGoPrice()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">Ladeprisberegner</h1>
      <p className="text-muted-foreground mb-8">
        Indtast din kørsel og se hvilken aftale der passer bedst til dig.
      </p>
      <SubscriptionCalculator goPrice={price_kwh} goUpdatedAt={updated_at} />
    </div>
  )
}
