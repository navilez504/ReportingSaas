/** API returns role as string "admin" | "user" */
export function isAdminUser(user) {
  return String(user?.role ?? '').toLowerCase() === 'admin'
}
