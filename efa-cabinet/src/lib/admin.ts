export const ADMIN_EMAIL = "rustem.vakil@gmail.com";

export function isAdminEmail(email?: string | null): boolean {
  if (!email) return false;
  return email.toLowerCase() === ADMIN_EMAIL.toLowerCase();
}
