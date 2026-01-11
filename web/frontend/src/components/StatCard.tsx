interface StatCardProps {
  label: string
  value: number
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'gray'
}

const colorClasses = {
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
  green: 'bg-green-50 text-green-700 border-green-200',
  yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  gray: 'bg-gray-50 text-gray-700 border-gray-200',
}

export function StatCard({ label, value, color = 'gray' }: StatCardProps) {
  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-sm mt-1">{label}</div>
    </div>
  )
}
