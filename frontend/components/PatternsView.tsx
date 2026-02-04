'use client'

import { useState, useEffect } from 'react'
import { patternsAPI } from '@/lib/api'
import { format } from 'date-fns'

export default function PatternsView() {
  const [patterns, setPatterns] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    loadPatterns()
  }, [])

  const loadPatterns = async () => {
    setLoading(true)
    try {
      const data = await patternsAPI.getPatterns({ limit: 50 })
      setPatterns(data)
    } catch (error) {
      console.error('Failed to load patterns:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const result = await patternsAPI.analyzePatterns()
      alert(result.message)
      loadPatterns()
    } catch (error) {
      console.error('Failed to analyze patterns:', error)
    } finally {
      setAnalyzing(false)
    }
  }

  const getPatternTypeColor = (type: string) => {
    switch (type) {
      case 'success_pattern':
        return 'bg-green-100 text-green-800'
      case 'failure_pattern':
        return 'bg-red-100 text-red-800'
      case 'optimization':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">Identified Patterns</h2>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {analyzing ? 'Analyzing...' : 'Analyze Patterns'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8">Loading patterns...</div>
      ) : patterns.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No patterns found. Click "Analyze Patterns" to discover patterns from your decisions.
        </div>
      ) : (
        <div className="space-y-4">
          {patterns.map((pattern) => (
            <div key={pattern.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-semibold">{pattern.name}</h3>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${getPatternTypeColor(
                        pattern.pattern_type
                      )}`}
                    >
                      {pattern.pattern_type}
                    </span>
                  </div>
                  {pattern.description && (
                    <p className="text-sm text-gray-600">{pattern.description}</p>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold">
                    {(pattern.confidence * 100).toFixed(0)}% confidence
                  </div>
                  <div className="text-xs text-gray-500">
                    Observed {pattern.frequency} times
                  </div>
                </div>
              </div>

              {pattern.conditions && (
                <div className="mb-3">
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Conditions:</h4>
                  <pre className="bg-gray-50 p-2 rounded text-xs">
                    {JSON.stringify(pattern.conditions, null, 2)}
                  </pre>
                </div>
              )}

              {pattern.solution && (
                <div className="mb-3">
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Solution:</h4>
                  <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded">
                    {pattern.solution}
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between text-xs text-gray-500 mt-4">
                <div className="flex items-center space-x-4">
                  <span>
                    Success rate: {(pattern.success_rate * 100).toFixed(0)}%
                  </span>
                  {pattern.related_decisions && pattern.related_decisions.length > 0 && (
                    <span>
                      {pattern.related_decisions.length} related decisions
                    </span>
                  )}
                </div>
                <span>
                  Last observed: {format(new Date(pattern.last_observed), 'MMM d, yyyy')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
