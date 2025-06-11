"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"

interface Transaction {
  symbol: string
  purchasePrice: number
  salePrice: number
  shares: number
  purchaseDate: string
  saleDate: string
}

interface TaxResult {
  shortTermGains: number
  longTermGains: number
  shortTermTax: number
  longTermTax: number
  totalTax: number
  netProceeds: number
}

export function TaxCalculator() {
  const [filingStatus, setFilingStatus] = useState("single")
  const [income, setIncome] = useState("")
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [currentTransaction, setCurrentTransaction] = useState<Transaction>({
    symbol: "",
    purchasePrice: 0,
    salePrice: 0,
    shares: 0,
    purchaseDate: "",
    saleDate: "",
  })
  const [results, setResults] = useState<TaxResult | null>(null)

  const addTransaction = () => {
    if (currentTransaction.symbol && currentTransaction.shares > 0) {
      setTransactions([...transactions, currentTransaction])
      setCurrentTransaction({
        symbol: "",
        purchasePrice: 0,
        salePrice: 0,
        shares: 0,
        purchaseDate: "",
        saleDate: "",
      })
    }
  }

  const calculateTaxes = () => {
    let shortTermGains = 0
    let longTermGains = 0

    transactions.forEach((transaction) => {
      const gain = (transaction.salePrice - transaction.purchasePrice) * transaction.shares
      const purchaseDate = new Date(transaction.purchaseDate)
      const saleDate = new Date(transaction.saleDate)
      const daysDiff = (saleDate.getTime() - purchaseDate.getTime()) / (1000 * 3600 * 24)

      if (daysDiff > 365) {
        longTermGains += gain
      } else {
        shortTermGains += gain
      }
    })

    // Simplified tax calculation (actual rates vary by income)
    const incomeNum = Number.parseFloat(income) || 0
    let shortTermRate = 0.22 // Simplified rate
    let longTermRate = 0.15 // Simplified rate

    // Adjust rates based on income brackets (simplified)
    if (incomeNum > 200000) {
      shortTermRate = 0.32
      longTermRate = 0.2
    } else if (incomeNum < 40000) {
      shortTermRate = 0.12
      longTermRate = 0.0
    }

    const shortTermTax = Math.max(0, shortTermGains * shortTermRate)
    const longTermTax = Math.max(0, longTermGains * longTermRate)
    const totalTax = shortTermTax + longTermTax
    const netProceeds = shortTermGains + longTermGains - totalTax

    setResults({
      shortTermGains,
      longTermGains,
      shortTermTax,
      longTermTax,
      totalTax,
      netProceeds,
    })
  }

  return (
    <section className="py-16 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Calculate Your Stock Taxes</h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Enter your stock transactions and tax information to get an estimate of your capital gains tax liability.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Tax Information</CardTitle>
                <CardDescription>Your filing status and income details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="filing-status">Filing Status</Label>
                  <Select value={filingStatus} onValueChange={setFilingStatus}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="single">Single</SelectItem>
                      <SelectItem value="married-joint">Married Filing Jointly</SelectItem>
                      <SelectItem value="married-separate">Married Filing Separately</SelectItem>
                      <SelectItem value="head-household">Head of Household</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="income">Annual Income ($)</Label>
                  <Input
                    id="income"
                    type="number"
                    value={income}
                    onChange={(e) => setIncome(e.target.value)}
                    placeholder="75000"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Add Stock Transaction</CardTitle>
                <CardDescription>Enter details for each stock sale</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="symbol">Stock Symbol</Label>
                    <Input
                      id="symbol"
                      value={currentTransaction.symbol}
                      onChange={(e) => setCurrentTransaction({ ...currentTransaction, symbol: e.target.value })}
                      placeholder="AAPL"
                    />
                  </div>
                  <div>
                    <Label htmlFor="shares">Shares</Label>
                    <Input
                      id="shares"
                      type="number"
                      value={currentTransaction.shares || ""}
                      onChange={(e) =>
                        setCurrentTransaction({ ...currentTransaction, shares: Number.parseFloat(e.target.value) || 0 })
                      }
                      placeholder="100"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="purchase-price">Purchase Price ($)</Label>
                    <Input
                      id="purchase-price"
                      type="number"
                      step="0.01"
                      value={currentTransaction.purchasePrice || ""}
                      onChange={(e) =>
                        setCurrentTransaction({
                          ...currentTransaction,
                          purchasePrice: Number.parseFloat(e.target.value) || 0,
                        })
                      }
                      placeholder="150.00"
                    />
                  </div>
                  <div>
                    <Label htmlFor="sale-price">Sale Price ($)</Label>
                    <Input
                      id="sale-price"
                      type="number"
                      step="0.01"
                      value={currentTransaction.salePrice || ""}
                      onChange={(e) =>
                        setCurrentTransaction({
                          ...currentTransaction,
                          salePrice: Number.parseFloat(e.target.value) || 0,
                        })
                      }
                      placeholder="175.00"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="purchase-date">Purchase Date</Label>
                    <Input
                      id="purchase-date"
                      type="date"
                      value={currentTransaction.purchaseDate}
                      onChange={(e) => setCurrentTransaction({ ...currentTransaction, purchaseDate: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="sale-date">Sale Date</Label>
                    <Input
                      id="sale-date"
                      type="date"
                      value={currentTransaction.saleDate}
                      onChange={(e) => setCurrentTransaction({ ...currentTransaction, saleDate: e.target.value })}
                    />
                  </div>
                </div>
                <Button onClick={addTransaction} className="w-full">
                  Add Transaction
                </Button>
              </CardContent>
            </Card>

            {transactions.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Your Transactions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {transactions.map((transaction, index) => {
                      const gain = (transaction.salePrice - transaction.purchasePrice) * transaction.shares
                      const isLongTerm =
                        new Date(transaction.saleDate).getTime() - new Date(transaction.purchaseDate).getTime() >
                        365 * 24 * 60 * 60 * 1000
                      return (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <span className="font-medium">{transaction.symbol}</span>
                            <span className="text-sm text-gray-600 ml-2">{transaction.shares} shares</span>
                          </div>
                          <div className="text-right">
                            <div className={`font-medium ${gain >= 0 ? "text-green-600" : "text-red-600"}`}>
                              ${gain.toFixed(2)}
                            </div>
                            <Badge variant={isLongTerm ? "default" : "secondary"} className="text-xs">
                              {isLongTerm ? "Long-term" : "Short-term"}
                            </Badge>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <Button onClick={calculateTaxes} className="w-full mt-4 bg-green-600 hover:bg-green-700">
                    Calculate Taxes
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          <div>
            {results && (
              <Card>
                <CardHeader>
                  <CardTitle>Tax Calculation Results</CardTitle>
                  <CardDescription>Your estimated tax liability</CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="summary" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="summary">Summary</TabsTrigger>
                      <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
                    </TabsList>
                    <TabsContent value="summary" className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-green-50 rounded-lg">
                          <div className="text-2xl font-bold text-green-600">${results.netProceeds.toFixed(2)}</div>
                          <div className="text-sm text-green-700">Net Proceeds</div>
                        </div>
                        <div className="p-4 bg-red-50 rounded-lg">
                          <div className="text-2xl font-bold text-red-600">${results.totalTax.toFixed(2)}</div>
                          <div className="text-sm text-red-700">Total Tax Owed</div>
                        </div>
                      </div>
                      <div className="p-4 bg-blue-50 rounded-lg">
                        <div className="text-lg font-semibold text-blue-900">
                          Total Capital Gains: ${(results.shortTermGains + results.longTermGains).toFixed(2)}
                        </div>
                        <div className="text-sm text-blue-700 mt-1">
                          Effective Tax Rate:{" "}
                          {((results.totalTax / (results.shortTermGains + results.longTermGains)) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </TabsContent>
                    <TabsContent value="breakdown" className="space-y-4">
                      <div className="space-y-3">
                        <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                          <span>Short-term Capital Gains</span>
                          <span className="font-medium">${results.shortTermGains.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                          <span>Short-term Tax</span>
                          <span className="font-medium text-red-600">${results.shortTermTax.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                          <span>Long-term Capital Gains</span>
                          <span className="font-medium">${results.longTermGains.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                          <span>Long-term Tax</span>
                          <span className="font-medium text-red-600">${results.longTermTax.toFixed(2)}</span>
                        </div>
                        <div className="border-t pt-3">
                          <div className="flex justify-between items-center font-bold">
                            <span>Total Tax Liability</span>
                            <span className="text-red-600">${results.totalTax.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            )}

            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Tax Tips</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-900">Hold for Long-term</h4>
                  <p className="text-sm text-blue-700">
                    Hold stocks for over 1 year to qualify for lower long-term capital gains rates.
                  </p>
                </div>
                <div className="p-3 bg-yellow-50 rounded-lg">
                  <h4 className="font-medium text-yellow-900">Tax-Loss Harvesting</h4>
                  <p className="text-sm text-yellow-700">
                    Offset gains with losses to reduce your overall tax liability.
                  </p>
                </div>
                <div className="p-3 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-900">Consult a Professional</h4>
                  <p className="text-sm text-green-700">
                    This is an estimate. Consult a tax professional for accurate calculations.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  )
}
