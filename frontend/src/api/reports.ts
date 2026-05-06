import { http } from '@/api/http'

async function downloadCsv(path: string, filename: string) {
  const res = await http.get(path, { responseType: 'blob' })
  const blob = res.data as Blob
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const reportExports = {
  vehicles: () => downloadCsv('/reports/export/vehicles.csv', 'vehicles.csv'),
  drivers: () => downloadCsv('/reports/export/drivers.csv', 'drivers.csv'),
  trips: () => downloadCsv('/reports/export/trip-requests.csv', 'trip_requests.csv'),
  maintenance: () => downloadCsv('/reports/export/maintenance.csv', 'maintenance.csv'),
  fuelCards: () => downloadCsv('/reports/export/fuel-cards.csv', 'fuel_cards.csv'),
  fuelRecords: () => downloadCsv('/reports/export/fuel-records.csv', 'fuel_records.csv'),
  summary: () => downloadCsv('/reports/export/summary.csv', 'summary.csv'),
}
