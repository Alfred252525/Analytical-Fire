'use client'

import { useState, useEffect } from 'react'
import { knowledgeAPI } from '@/lib/api'
import { format } from 'date-fns'

export default function KnowledgeSearch() {
  const [knowledge, setKnowledge] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [category, setCategory] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newEntry, setNewEntry] = useState({
    title: '',
    description: '',
    category: '',
    tags: '',
    content: '',
    code_example: '',
  })

  useEffect(() => {
    loadKnowledge()
  }, [searchQuery, category])

  const loadKnowledge = async () => {
    setLoading(true)
    try {
      const data = await knowledgeAPI.searchKnowledge({
        search_query: searchQuery || undefined,
        category: category || undefined,
        limit: 50,
      })
      setKnowledge(data)
    } catch (error) {
      console.error('Failed to load knowledge:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateEntry = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await knowledgeAPI.createEntry({
        ...newEntry,
        tags: newEntry.tags.split(',').map((t) => t.trim()).filter(Boolean),
      })
      setShowCreateForm(false)
      setNewEntry({
        title: '',
        description: '',
        category: '',
        tags: '',
        content: '',
        code_example: '',
      })
      loadKnowledge()
    } catch (error) {
      console.error('Failed to create knowledge entry:', error)
    }
  }

  const handleVote = async (id: number, voteType: 'upvote' | 'downvote') => {
    try {
      await knowledgeAPI.vote(id, voteType)
      loadKnowledge()
    } catch (error) {
      console.error('Failed to vote:', error)
    }
  }

  return (
    <div className="space-y-4">
      {/* Search and Create */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Knowledge Base</h2>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            {showCreateForm ? 'Cancel' : '+ New Entry'}
          </button>
        </div>

        {showCreateForm && (
          <form onSubmit={handleCreateEntry} className="mb-4 p-4 bg-gray-50 rounded space-y-3">
            <input
              type="text"
              placeholder="Title"
              value={newEntry.title}
              onChange={(e) => setNewEntry({ ...newEntry, title: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <input
              type="text"
              placeholder="Category"
              value={newEntry.category}
              onChange={(e) => setNewEntry({ ...newEntry, category: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <textarea
              placeholder="Description"
              value={newEntry.description}
              onChange={(e) => setNewEntry({ ...newEntry, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={2}
            />
            <textarea
              placeholder="Content (required)"
              value={newEntry.content}
              onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={4}
            />
            <textarea
              placeholder="Code Example (optional)"
              value={newEntry.code_example}
              onChange={(e) => setNewEntry({ ...newEntry, code_example: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              rows={4}
            />
            <input
              type="text"
              placeholder="Tags (comma-separated)"
              value={newEntry.tags}
              onChange={(e) => setNewEntry({ ...newEntry, tags: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Create Entry
            </button>
          </form>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Search knowledge..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          />
          <input
            type="text"
            placeholder="Filter by category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
      </div>

      {/* Knowledge Entries */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-8">Loading knowledge...</div>
        ) : knowledge.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
            No knowledge entries found
          </div>
        ) : (
          knowledge.map((entry) => (
            <div key={entry.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="text-lg font-semibold">{entry.title}</h3>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-sm text-gray-500">{entry.category}</span>
                    {entry.verified && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        Verified
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleVote(entry.id, 'upvote')}
                    className="text-sm text-gray-600 hover:text-green-600"
                  >
                    ↑ {entry.upvotes}
                  </button>
                  <button
                    onClick={() => handleVote(entry.id, 'downvote')}
                    className="text-sm text-gray-600 hover:text-red-600"
                  >
                    ↓ {entry.downvotes}
                  </button>
                </div>
              </div>
              {entry.description && (
                <p className="text-sm text-gray-600 mb-2">{entry.description}</p>
              )}
              <p className="text-sm text-gray-700 mb-3">{entry.content}</p>
              {entry.code_example && (
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto mb-3">
                  <code>{entry.code_example}</code>
                </pre>
              )}
              <div className="flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center space-x-4">
                  <span>Used {entry.usage_count} times</span>
                  <span>{(entry.success_rate * 100).toFixed(0)}% success rate</span>
                  {entry.tags && entry.tags.length > 0 && (
                    <div className="flex space-x-1">
                      {entry.tags.map((tag: string, idx: number) => (
                        <span
                          key={idx}
                          className="bg-blue-100 text-blue-800 px-2 py-1 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <span>{format(new Date(entry.created_at), 'MMM d, yyyy')}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
