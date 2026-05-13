import type { Metadata } from 'next'
import { SubscriptionCalculator } from '@/components/subscription-calculator'

export const metadata: Metadata = {
  title: 'Ladeprisberegner',
  description: 'Beregn hvilken ladeabonnement der er billigst for din kørsel. Sammenlign Clever, Norlys, E.ON og mere.',
}

export default function BeregnerPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">Ladeprisberegner</h1>
      <p className="text-muted-foreground mb-8">
        Indtast din kørsel og se hvilken aftale der passer bedst til dig.
      </p>
      <SubscriptionCalculator />
    </div>
  )
}
