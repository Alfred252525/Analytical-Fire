'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

interface AnalyticsChartProps {
  data: Array<{
    date: string
    count: number
    avg_score: number
  }>
}

export default function AnalyticsChart({ data }: AnalyticsChartProps) {
  const chartData = data.map((item) => ({
    date: format(new Date(item.date), 'MMM d'),
    count: item.count,
    avgScore: (item.avg_score * 100).toFixed(1),
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis yAxisId="left" />
        <YAxis yAxisId="right" orientation="right" />
        <Tooltip />
        <Legend />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="count"
          stroke="#3b82f6"
          name="Decision Count"
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="avgScore"
          stroke="#10b981"
          name="Avg Success %"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
