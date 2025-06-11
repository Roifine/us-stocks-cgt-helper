import { Calculator, TrendingUp, DollarSign } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Hero() {
  return (
    <section className="relative py-20 px-4 text-center">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-center mb-6">
          <div className="p-3 bg-green-100 rounded-full">
            <Calculator className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
          US Stock Portfolio
          <span className="text-green-600"> Tax Calculator</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Calculate your capital gains taxes, dividend taxes, and optimize your investment strategy with our
          comprehensive US stock tax calculator.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
          <Button size="lg" className="bg-green-600 hover:bg-green-700">
            Start Calculating
          </Button>
          <Button size="lg" variant="outline">
            Learn More
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl mx-auto">
          <div className="flex flex-col items-center">
            <TrendingUp className="w-8 h-8 text-green-600 mb-2" />
            <h3 className="font-semibold text-gray-900">Capital Gains</h3>
            <p className="text-sm text-gray-600">Calculate short & long-term gains</p>
          </div>
          <div className="flex flex-col items-center">
            <DollarSign className="w-8 h-8 text-green-600 mb-2" />
            <h3 className="font-semibold text-gray-900">Dividend Tax</h3>
            <p className="text-sm text-gray-600">Qualified & ordinary dividends</p>
          </div>
          <div className="flex flex-col items-center">
            <Calculator className="w-8 h-8 text-green-600 mb-2" />
            <h3 className="font-semibold text-gray-900">Tax Optimization</h3>
            <p className="text-sm text-gray-600">Minimize your tax liability</p>
          </div>
        </div>
      </div>
    </section>
  )
}
