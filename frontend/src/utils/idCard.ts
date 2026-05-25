/** 从中国大陆身份证号解析出生日期（支持 18 位与 15 位） */
export function parseBirthDateFromIdCard(idCard: string): Date | null {
  const raw = idCard.trim().toUpperCase()
  if (!raw) return null

  let y = 0
  let m = 0
  let d = 0

  if (/^\d{17}[\dX]$/.test(raw)) {
    y = Number(raw.slice(6, 10))
    m = Number(raw.slice(10, 12))
    d = Number(raw.slice(12, 14))
  } else if (/^\d{15}$/.test(raw)) {
    const yy = Number(raw.slice(6, 8))
    y = yy <= 30 ? 2000 + yy : 1900 + yy
    m = Number(raw.slice(8, 10))
    d = Number(raw.slice(10, 12))
  } else {
    return null
  }

  if (!y || m < 1 || m > 12 || d < 1 || d > 31) return null
  const dt = new Date(y, m - 1, d)
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null
  return dt
}

/** 根据身份证号计算周岁年龄；无效号码返回 null */
export function ageFromIdCard(idCard: string | null | undefined): number | null {
  const birth = parseBirthDateFromIdCard(idCard || '')
  if (!birth) return null
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const monthDiff = today.getMonth() - birth.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1
  }
  return age >= 0 ? age : null
}

export function formatAgeFromIdCard(idCard: string | null | undefined): string {
  const age = ageFromIdCard(idCard)
  return age === null ? '—' : `${age}`
}
