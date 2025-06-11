import { Shield, Clock, PieChart, FileText, Calculator, TrendingUp } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function Features() {
  const features = [
    {
      icon: Calculator,
      title: "Accurate Calculations",
      description: "Precise tax calculations based on current US tax laws and rates",
    },
    {
      icon: Clock,
      title: "Short vs Long-term",
      description: "Automatically categorizes gains based on holding period",
    },
    {
      icon: PieChart,
      title: "Portfolio Overview",
      description: "Comprehensive view of your entire stock portfolio performance",
    },
    {
      icon: Shield,
      title: "Secure & Private",
      description: "Your financial data is processed locally and never stored",
    },
    {
      icon: FileText,
      title: "Tax Reports",
      description: "Generate detailed reports for tax filing purposes",
    },
    {
      icon: TrendingUp,
      title: "Optimization Tips",
      description: "Get suggestions to minimize your tax liability",
    },
  ]

  return (
    <section className="py-16 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Why Choose Our Tax Calculator?</h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Built specifically for US stock investors, our calculator provides accurate, comprehensive tax calculations.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <Card key={index} className="border-0 shadow-sm">
              <CardHeader>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-green-600" />
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-gray-600">{feature.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-16 p-8 bg-white rounded-xl shadow-sm border">
          <div className="text-center">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Important Disclaimer</h3>
            <p className="text-gray-600 max-w-3xl mx-auto">
              This calculator provides estimates based on simplified tax calculations. Actual tax liability may vary
              based on your complete financial situation, state taxes, and other factors. Always consult with a
              qualified tax professional or CPA for accurate tax advice and filing assistance.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
