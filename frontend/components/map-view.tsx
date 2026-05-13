'use client'

import { useEffect, useRef } from 'react'

interface Station {
  id: string
  name: string
  operator: string
  lat: number
  lon: number
  price_kwh: number | null
}

function priceColor(price: number | null): string {
  if (price === null) return '#9ca3af'
  if (price < 2.5) return '#16a34a'
  if (price < 4.0) return '#d97706'
  return '#dc2626'
}

export function MapView({ stations }: { stations: Station[] }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return
    let map: import('maplibre-gl').Map

    import('maplibre-gl').then(({ default: maplibregl }) => {
      map = new maplibregl.Map({
        container: containerRef.current!,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors',
            },
          },
          layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
        },
        center: [10.2, 56.1],
        zoom: 6,
      })

      map.on('load', () => {
        const geojson: GeoJSON.FeatureCollection = {
          type: 'FeatureCollection',
          features: stations.map(s => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
            properties: {
              id: s.id,
              name: s.name,
              operator: s.operator,
              price_kwh: s.price_kwh,
              color: priceColor(s.price_kwh),
            },
          })),
        }

        map.addSource('stations', { type: 'geojson', data: geojson })
        map.addLayer({
          id: 'stations-circle',
          type: 'circle',
          source: 'stations',
          paint: {
            'circle-radius': 6,
            'circle-color': ['get', 'color'],
            'circle-stroke-width': 1,
            'circle-stroke-color': '#fff',
          },
        })

        const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })

        map.on('click', 'stations-circle', e => {
          if (!e.features?.[0]) return
          const { name, operator, price_kwh } = e.features[0].properties as Station & { color: string }
          const coords = (e.features[0].geometry as GeoJSON.Point).coordinates as [number, number]
          const price = price_kwh != null
            ? `${Number(price_kwh).toLocaleString('da-DK', { minimumFractionDigits: 2 })} kr/kWh`
            : 'Ingen pris'
          popup.setLngLat(coords).setHTML(`<strong>${name}</strong><br/>${operator}<br/>${price}`).addTo(map)
        })

        map.on('mouseenter', 'stations-circle', () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', 'stations-circle', () => { map.getCanvas().style.cursor = '' })
      })
    })

    return () => map?.remove()
  }, [stations])

  return <div ref={containerRef} className="w-full h-[70vh] rounded-lg border" />
}
