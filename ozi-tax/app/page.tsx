import { Hero } from "@/components/hero"
import { TaxCalculator } from "@/components/tax-calculator"
import { Features } from "@/components/features"

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <Hero />
      <TaxCalculator />
      <Features />
    </div>
  )
}
