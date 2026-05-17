const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
const diasSemana = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']

export function formatFecha(fechaStr: string): string {
  const [year, month, day] = fechaStr.split('-')
  const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
  const dayOfWeek = diasSemana[date.getDay()]
  return `${dayOfWeek}, ${parseInt(day)} de ${meses[parseInt(month) - 1]}`
}

export function formatFechaDiaYMes(fechaStr: string): string {
  const [year, month, day] = fechaStr.split('-')
  return `${parseInt(day)} de ${meses[parseInt(month) - 1]}`
}

export function formatFechaCompleta(fechaStr: string): string {
  const [year, month, day] = fechaStr.split('-')
  return `${parseInt(day)} de ${meses[parseInt(month) - 1]} de ${year}`
}

export function formatTimestamp(dateString: string): string {
  const date = new Date(dateString)
  const day = date.getDate()
  const month = date.getMonth()
  const year = date.getFullYear()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${day} de ${meses[month]} de ${year}, ${hours}:${minutes}`
}

export function formatHora(timeString: string): string {
  if (!timeString) return ''
  const [hours, minutes] = timeString.split(':')
  return `${hours}:${minutes}`
}

export function getCurrentDate(): string {
  return new Date().toISOString().split('T')[0]
}
