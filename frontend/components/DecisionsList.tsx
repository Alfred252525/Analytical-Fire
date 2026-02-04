'use client'

import { useState, useEffect } from 'react'
import { decisionsAPI } from '@/lib/api'
import { format } from 'date-fns'

export default function DecisionsList() {
  const [decisions, setDecisions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    task_type: '',
    outcome: '',
    limit: 50,
  })

  useEffect(() => {
    loadDecisions()
  }, [filters])

  const loadDecisions = async () => {
    setLoading(true)
    try {
      const data = await decisionsAPI.getDecisions(filters)
      setDecisions(data)
    } catch (error) {
      console.error('Failed to load decisions:', error)
    } finally {
      setLoading(false)
    }
  }

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'success':
        return 'bg-green-100 text-green-800'
      case 'partial':
        return 'bg-yellow-100 text-yellow-800'
      case 'failure':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading decisions...</div>
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Task Type
            </label>
            <input
              type="text"
              value={filters.task_type}
              onChange={(e) => setFilters({ ...filters, task_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Filter by task type"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Outcome
            </label>
            <select
              value={filters.outcome}
              onChange={(e) => setFilters({ ...filters, outcome: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="partial">Partial</option>
              <option value="failure">Failure</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Limit
            </label>
            <input
              type="number"
              value={filters.limit}
              onChange={(e) => setFilters({ ...filters, limit: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              min="1"
              max="1000"
            />
          </div>
        </div>
      </div>

      {/* Decisions List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">Recent Decisions</h2>
        </div>
        <div className="divide-y">
          {decisions.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No decisions found
            </div>
          ) : (
            decisions.map((decision) => (
              <div key={decision.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="font-medium">{decision.task_type}</span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getOutcomeColor(
                          decision.outcome
                        )}`}
                      >
                        {decision.outcome}
                      </span>
                      <span className="text-sm text-gray-500">
                        Score: {(decision.success_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {decision.task_description && (
                      <p className="text-sm text-gray-600 mb-1">
                        {decision.task_description}
                      </p>
                    )}
                    {decision.reasoning && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                        {decision.reasoning}
                      </p>
                    )}
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>
                        {format(new Date(decision.created_at), 'MMM d, yyyy HH:mm')}
                      </span>
                      {decision.execution_time_ms && (
                        <span>{decision.execution_time_ms}ms</span>
                      )}
                      {decision.tools_used && decision.tools_used.length > 0 && (
                        <span>{decision.tools_used.length} tools used</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
