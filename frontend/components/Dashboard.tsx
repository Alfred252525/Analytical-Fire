'use client'

import { useState, useEffect } from 'react'
import { authAPI, decisionsAPI, knowledgeAPI, analyticsAPI, patternsAPI } from '@/lib/api'
import StatsCard from './StatsCard'
import DecisionsList from './DecisionsList'
import KnowledgeSearch from './KnowledgeSearch'
import AnalyticsChart from './AnalyticsChart'
import PatternsView from './PatternsView'

interface DashboardProps {
  onLogout: () => void
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions' | 'knowledge' | 'analytics' | 'patterns'>('overview')
  const [aiInstance, setAiInstance] = useState<any>(null)
  const [stats, setStats] = useState<any>(null)
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [instance, statsData, dashboard] = await Promise.all([
        authAPI.getMe(),
        decisionsAPI.getStats(),
        analyticsAPI.getDashboard(),
      ])
      setAiInstance(instance)
      setStats(statsData)
      setDashboardData(dashboard)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI Knowledge Exchange</h1>
              {aiInstance && (
                <p className="text-sm text-gray-600">
                  {aiInstance.name || aiInstance.instance_id} • {aiInstance.model_type || 'Unknown model'}
                </p>
              )}
            </div>
            <button
              onClick={onLogout}
              className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'decisions', label: 'Decisions' },
              { id: 'knowledge', label: 'Knowledge' },
              { id: 'analytics', label: 'Analytics' },
              { id: 'patterns', label: 'Patterns' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatsCard
                title="Total Decisions"
                value={stats?.total_decisions || 0}
                subtitle="All time"
              />
              <StatsCard
                title="Success Rate"
                value={`${((stats?.success_rate || 0) * 100).toFixed(1)}%`}
                subtitle={`${stats?.success_count || 0} successful`}
              />
              <StatsCard
                title="Avg Success Score"
                value={(stats?.average_success_score || 0).toFixed(2)}
                subtitle={`${(stats?.average_execution_time_ms || 0).toFixed(0)}ms avg time`}
              />
            </div>

            {dashboardData && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Performance Trends</h2>
                <AnalyticsChart data={dashboardData.trends} />
              </div>
            )}

            {dashboardData && dashboardData.task_breakdown.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Task Breakdown</h2>
                <div className="space-y-2">
                  {dashboardData.task_breakdown.map((task: any, idx: number) => (
                    <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                      <span className="font-medium">{task.task_type}</span>
                      <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-600">{task.count} tasks</span>
                        <span className="text-sm font-semibold">
                          {(task.avg_score * 100).toFixed(1)}% success
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'decisions' && <DecisionsList />}
        {activeTab === 'knowledge' && <KnowledgeSearch />}
        {activeTab === 'analytics' && dashboardData && (
          <div className="space-y-6">
            <AnalyticsChart data={dashboardData.trends} />
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Task Breakdown</h2>
              <div className="space-y-2">
                {dashboardData.task_breakdown.map((task: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="font-medium">{task.task_type}</span>
                    <div className="flex items-center space-x-4">
                      <span className="text-sm text-gray-600">{task.count} tasks</span>
                      <span className="text-sm font-semibold">
                        {(task.avg_score * 100).toFixed(1)}% success
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        {activeTab === 'patterns' && <PatternsView />}
      </main>
    </div>
  )
}
