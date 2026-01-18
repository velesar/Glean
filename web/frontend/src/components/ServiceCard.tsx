import { useState } from 'react'
import type { ServiceGroup, ServiceField, ServiceProvider } from '../types'

interface ServiceCardProps {
  service: ServiceGroup
  onUpdateField: (
    serviceId: string,
    fieldKey: string,
    value: string,
    providerId?: string
  ) => Promise<void>
  onSetProvider: (serviceId: string, providerId: string) => Promise<void>
  onTest: (serviceId: string) => Promise<{ success: boolean; message: string }>
  isTestPending?: boolean
}

interface FieldRowProps {
  field: ServiceField
  onSave: (value: string) => Promise<void>
}

function FieldRow({ field, onSave }: FieldRowProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [value, setValue] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onSave(value)
      setIsEditing(false)
      setValue('')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setValue('')
  }

  if (isEditing) {
    return (
      <div className="py-2">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>
        <div className="flex gap-2">
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={field.placeholder}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          <button
            onClick={handleSave}
            disabled={isSaving || !value}
            className="px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Save
          </button>
          <button
            onClick={handleCancel}
            className="px-3 py-2 text-gray-700 bg-gray-100 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="py-2 flex items-center justify-between">
      <div>
        <span className="text-sm font-medium text-gray-700">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </span>
        <span className="ml-3 text-sm font-mono text-gray-500">
          {field.is_set ? field.value || '********' : 'Not configured'}
        </span>
      </div>
      <button
        onClick={() => setIsEditing(true)}
        className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
      >
        {field.is_set ? 'Edit' : 'Set'}
      </button>
    </div>
  )
}

const SERVICE_ICONS: Record<string, string> = {
  anthropic: 'A',
  openai: 'O',
  reddit: 'R',
  twitter: 'X',
  producthunt: 'P',
  websearch: 'S',
}

export function ServiceCard({
  service,
  onUpdateField,
  onSetProvider,
  onTest,
  isTestPending,
}: ServiceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
  } | null>(null)
  const [isTesting, setIsTesting] = useState(false)

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)
    try {
      const result = await onTest(service.id)
      setTestResult(result)
      setTimeout(() => setTestResult(null), 5000)
    } finally {
      setIsTesting(false)
    }
  }

  const handleProviderChange = async (providerId: string) => {
    await onSetProvider(service.id, providerId)
  }

  const renderFields = (
    fields: ServiceField[],
    providerId?: string
  ) => {
    return fields.map((field) => (
      <FieldRow
        key={field.key}
        field={field}
        onSave={(value) => onUpdateField(service.id, field.key, value, providerId)}
      />
    ))
  }

  const renderProviderSection = (providers: ServiceProvider[], selectedProvider?: string) => {
    return (
      <div className="space-y-4">
        <div className="flex gap-4">
          {providers.map((provider) => (
            <label key={provider.id} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name={`${service.id}-provider`}
                value={provider.id}
                checked={selectedProvider === provider.id}
                onChange={() => handleProviderChange(provider.id)}
                className="text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">{provider.name}</span>
              {provider.is_configured && (
                <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded">
                  Configured
                </span>
              )}
            </label>
          ))}
        </div>
        {selectedProvider && (
          <div className="pl-4 border-l-2 border-gray-200">
            {renderFields(
              providers.find((p) => p.id === selectedProvider)?.fields || [],
              selectedProvider
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center text-sm font-bold text-gray-600">
            {SERVICE_ICONS[service.id] || service.name[0]}
          </div>
          <div className="text-left">
            <span className="font-medium text-gray-900">{service.name}</span>
            <p className="text-sm text-gray-500">{service.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {service.is_configured ? (
            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
              Configured
            </span>
          ) : (
            <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-500 rounded-full">
              Not configured
            </span>
          )}
          <span className="text-gray-400 text-sm">
            {isExpanded ? '\u25BC' : '\u25B6'}
          </span>
        </div>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="pt-4">
            {service.has_provider_choice && service.providers ? (
              renderProviderSection(service.providers, service.selected_provider)
            ) : (
              <div className="divide-y divide-gray-100">
                {service.fields && renderFields(service.fields)}
              </div>
            )}
          </div>

          {/* Test Button */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-3">
            <button
              onClick={handleTest}
              disabled={isTesting || isTestPending || !service.is_configured}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isTesting ? 'Testing...' : 'Test Connection'}
            </button>
            {testResult && (
              <span
                className={`text-sm ${
                  testResult.success ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {testResult.message}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
