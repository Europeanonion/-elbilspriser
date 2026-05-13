import type { Metadata } from 'next'
import { MapView } from '@/components/map-view'

export const revalidate = 900

export const metadata: Metadata = {
  title: 'Ladestationer kort',
  description: 'Se alle offentlige elbilladestationer i Danmark på et interaktivt kort med aktuelle priser.',
}

interface Station {
  id: string
  name: string
  operator: string
  lat: number
  lon: number
  price_kwh: number | null
}

async function getStations(): Promise<Station[]> {
  const url = `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/stations?lat=56.0&lon=10.0&radius_km=500`
  try {
    const res = await fetch(url, { next: { revalidate: 900 } })
    if (!res.ok) throw new Error(`API ${res.status}`)
    return res.json()
  } catch (err) {
    console.error('Failed to fetch stations:', err)
    return []
  }
}

export default async function MapPage() {
  const stations = await getStations()
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Ladestationer i Danmark</h1>
      <MapView stations={stations} />
    </div>
  )
}
