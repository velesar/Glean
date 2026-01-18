import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api'
import { ServiceCard } from '../components/ServiceCard'
import type { SettingValue } from '../types'

type SettingCategory = 'scouts' | 'analyzers'

interface EditingState {
  category: SettingCategory
  key: string
  value: string
}

export function Settings() {
  const queryClient = useQueryClient()
  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  })

  const { data: servicesData, isLoading: servicesLoading } = useQuery({
    queryKey: ['services'],
    queryFn: api.getServices,
  })

  const [editing, setEditing] = useState<EditingState | null>(null)

  const updateMutation = useMutation({
    mutationFn: ({
      category,
      key,
      value,
    }: {
      category: string
      key: string
      value: string
    }) => api.updateSetting(category, key, value, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setEditing(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: ({ category, key }: { category: string; key: string }) =>
      api.deleteSetting(category, key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  // Service-related mutations
  const updateServiceFieldMutation = useMutation({
    mutationFn: ({
      serviceId,
      fieldKey,
      value,
      providerId,
    }: {
      serviceId: string
      fieldKey: string
      value: string
      providerId?: string
    }) => api.updateServiceField(serviceId, fieldKey, value, providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] })
    },
  })

  const setServiceProviderMutation = useMutation({
    mutationFn: ({
      serviceId,
      providerId,
    }: {
      serviceId: string
      providerId: string
    }) => api.setServiceProvider(serviceId, providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] })
    },
  })

  const handleUpdateServiceField = async (
    serviceId: string,
    fieldKey: string,
    value: string,
    providerId?: string
  ) => {
    await updateServiceFieldMutation.mutateAsync({
      serviceId,
      fieldKey,
      value,
      providerId,
    })
  }

  const handleSetServiceProvider = async (
    serviceId: string,
    providerId: string
  ) => {
    await setServiceProviderMutation.mutateAsync({ serviceId, providerId })
  }

  const handleTestService = async (serviceId: string) => {
    return await api.testService(serviceId)
  }

  const isLoading = settingsLoading || servicesLoading

  const handleEdit = (category: SettingCategory, key: string, currentValue: string | null) => {
    setEditing({
      category,
      key,
      value: currentValue || '',
    })
  }

  const handleSave = () => {
    if (editing) {
      updateMutation.mutate({
        category: editing.category,
        key: editing.key,
        value: editing.value,
      })
    }
  }

  const handleCancel = () => {
    setEditing(null)
  }

  const handleDelete = (category: SettingCategory, key: string) => {
    if (confirm('Are you sure you want to delete this setting?')) {
      deleteMutation.mutate({ category, key })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  const categoryTitles: Record<SettingCategory, string> = {
    scouts: 'Scout Configuration',
    analyzers: 'Analyzer Configuration',
  }

  const categoryDescriptions: Record<SettingCategory, string> = {
    scouts: 'Configure data collection settings',
    analyzers: 'Configure AI analysis settings',
  }

  const renderSettingRow = (
    category: SettingCategory,
    key: string,
    setting: SettingValue
  ) => {
    const isEditing = editing?.category === category && editing?.key === key

    return (
      <div key={key} className="py-4 border-b border-gray-100 last:border-0">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-900">
              {setting.label}
            </label>
            <p className="text-sm text-gray-500 mt-0.5">{setting.description}</p>
          </div>

          {!isEditing && (
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={() =>
                  handleEdit(category, key, setting.is_secret ? '' : setting.value)
                }
                className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
              >
                {setting.is_set ? 'Edit' : 'Set'}
              </button>
              {setting.is_set && (
                <button
                  onClick={() => handleDelete(category, key)}
                  className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                >
                  Delete
                </button>
              )}
            </div>
          )}
        </div>

        {isEditing ? (
          <div className="mt-3">
            {setting.options ? (
              <select
                value={editing.value}
                onChange={(e) => setEditing({ ...editing, value: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select...</option>
                {setting.options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={setting.is_secret ? 'password' : 'text'}
                value={editing.value}
                onChange={(e) => setEditing({ ...editing, value: e.target.value })}
                placeholder={setting.placeholder}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            <div className="flex gap-2 mt-2">
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                Save
              </button>
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-gray-700 bg-gray-100 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-2">
            {setting.is_set ? (
              <span className="text-sm font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded">
                {setting.is_secret ? setting.value : setting.value || '(empty)'}
              </span>
            ) : (
              <span className="text-sm text-gray-400 italic">Not configured</span>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">
          Configure API credentials and preferences for Glean
        </p>
      </div>

      {/* API Keys Section - Service-grouped architecture */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">API Keys</h2>
        <p className="text-sm text-gray-500 mb-4">
          Configure API credentials for external services
        </p>
        <div className="space-y-3">
          {servicesData?.services.map((service) => (
            <ServiceCard
              key={service.id}
              service={service}
              onUpdateField={handleUpdateServiceField}
              onSetProvider={handleSetServiceProvider}
              onTest={handleTestService}
            />
          ))}
        </div>
      </section>

      {/* Scout and Analyzer Configuration Sections */}
      {(['scouts', 'analyzers'] as SettingCategory[]).map((category) => (
        <section key={category} className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            {categoryTitles[category]}
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            {categoryDescriptions[category]}
          </p>

          <div className="divide-y divide-gray-100">
            {settings?.[category] &&
              Object.entries(settings[category]).map(([key, setting]) =>
                renderSettingRow(category, key, setting)
              )}
          </div>
        </section>
      ))}

      <section className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h3 className="font-medium text-yellow-800">Security Note</h3>
        <p className="text-sm text-yellow-700 mt-1">
          API keys are stored encrypted and never displayed in full after saving.
          Treat your API keys like passwords and never share them.
        </p>
      </section>
    </div>
  )
}
