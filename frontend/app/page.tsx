import type { Metadata } from 'next'
import { PriceTable } from '@/components/price-table'

export const revalidate = 900

export const metadata: Metadata = {
  title: 'Sammenlign ladepriser',
  description: 'Se og sammenlign aktuelle ladepriser for elbiler i Danmark – Clever, Norlys, E.ON, OK, Ionity og flere.',
  openGraph: { type: 'website', locale: 'da_DK' },
}

interface Price {
  station_id: string
  name: string
  operator: string
  price_kwh: number | null
  price_min: number | null
  session_fee: number | null
  updated_at: string
}

async function getPrices(): Promise<Price[]> {
  const url = `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/prices`
  try {
    const res = await fetch(url, { next: { revalidate: 900 } })
    if (!res.ok) throw new Error(`API ${res.status}`)
    return res.json()
  } catch (err) {
    console.error('Failed to fetch prices:', err)
    return []
  }
}

export default async function HomePage() {
  const prices = await getPrices()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">Sammenlign ladepriser i realtid</h1>
      <p className="text-muted-foreground mb-6">
        Aktuelle ladepriser fra {prices.length > 0 ? 'alle større' : 'de fleste'} operatører i Danmark. Opdateres hvert 15. minut.
      </p>
      <PriceTable prices={prices} />
    </div>
  )
}
