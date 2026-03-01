/**
 * api.ts — Auth-aware fetch wrapper
 * localStorage'daki token'ı otomatik olarak Authorization header'ına ekler.
 * 401 alınca admin login sayfasına yönlendirir.
 */

export function getToken(): string | null {
  return localStorage.getItem('admin_token');
}

export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
    // FormData olduğunda Content-Type otomatik set edilmeli, elle koymayalım
  }

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('admin_token');
    window.location.href = '/admin/login';
  }

  return res;
}
