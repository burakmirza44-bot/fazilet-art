/**
 * AdminLogin.tsx
 * Admin giriş sayfası — email + şifre ile kimlik doğrulama.
 */
import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Eye, EyeOff, LogIn } from 'lucide-react';

export default function AdminLogin() {
  const { login } = useAuth();
  const navigate   = useNavigate();
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate('/admin', { replace: true });
    } catch (err: any) {
      setError(err.message ?? 'Giriş başarısız');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f9f9f9]">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-10 flex justify-center">
          <img src="/logo.png" alt="Fazilet Secgin" className="h-7 w-auto object-contain opacity-80" />
        </div>

        {/* Kart */}
        <div className="bg-white border border-ink/6 rounded-sm p-8 shadow-sm">
          <h1 className="text-sm font-medium tracking-[0.18em] text-ink mb-1 uppercase">Admin Girişi</h1>
          <p className="text-xs text-ink/40 mb-8">Devam etmek için giriş yapın.</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-ink/50 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
                placeholder="admin@faziletart.com"
                className="w-full border border-ink/12 rounded-sm px-3 py-2.5 text-sm text-ink placeholder:text-ink/25 focus:outline-none focus:border-ink/40 transition-colors bg-transparent"
              />
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-widest text-ink/50 mb-2">
                Şifre
              </label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full border border-ink/12 rounded-sm px-3 py-2.5 pr-10 text-sm text-ink placeholder:text-ink/25 focus:outline-none focus:border-ink/40 transition-colors bg-transparent"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/30 hover:text-ink/60 transition-colors"
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded-sm border border-red-100">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-ink text-paper text-xs font-medium tracking-[0.18em] uppercase py-3 rounded-sm hover:bg-ink/85 active:scale-[0.99] transition-all disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-pulse">Giriş yapılıyor…</span>
              ) : (
                <>
                  <LogIn size={14} strokeWidth={1.5} />
                  Giriş Yap
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-[10px] text-ink/25 mt-6 tracking-wider">
          Fazilet Secgin Art Project Consultancy
        </p>
      </div>
    </div>
  );
}
