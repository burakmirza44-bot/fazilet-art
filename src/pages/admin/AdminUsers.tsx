/**
 * AdminUsers.tsx — Kullanıcı Yönetim Paneli
 * Kullanıcı oluşturma, düzenleme, rol atama, şifre değiştirme, silme
 */
import { apiFetch } from '../../utils/api';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  UserPlus, Pencil, Trash2, KeyRound, ShieldCheck,
  Eye, EyeOff, Check, X, Users,
} from 'lucide-react';

type Role = 'admin' | 'editor' | 'viewer';

interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  active: number;
  created_at: string;
  updated_at: string;
}

const ROLE_META: Record<Role, { label: string; bg: string; text: string }> = {
  admin:  { label: 'Admin',  bg: 'bg-red-50',    text: 'text-red-700'    },
  editor: { label: 'Editor', bg: 'bg-blue-50',   text: 'text-blue-700'  },
  viewer: { label: 'Viewer', bg: 'bg-green-50',  text: 'text-green-700' },
};

const ROLE_DESC: Record<Role, string> = {
  admin:  'Tam erişim: tüm verileri yönetebilir, kullanıcı oluşturabilir.',
  editor: 'İçerik düzenleme: sanatçı, eser, sergi ekleyip düzenleyebilir.',
  viewer: 'Sadece görüntüleme: verileri okuyabilir, değiştiremez.',
};

// ── Modal bileşeni ─────────────────────────────────────────────────────────
interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}
function Modal({ title, onClose, children }: ModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.35)', backdropFilter: 'blur(4px)' }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 12 }}
        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
        className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-ink/6">
          <h2 className="text-sm font-medium tracking-widest uppercase text-ink/80">{title}</h2>
          <button onClick={onClose} className="text-ink/40 hover:text-ink transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </motion.div>
    </div>
  );
}

// ── Şifre input alanı ─────────────────────────────────────────────────────
function PasswordInput({ value, onChange, placeholder = 'Şifre', required = false }: {
  value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full px-3 py-2.5 pr-10 border border-ink/10 rounded-lg text-sm text-ink bg-white focus:outline-none focus:border-ink/30 transition-colors"
      />
      <button
        type="button"
        onClick={() => setShow(s => !s)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/30 hover:text-ink/60 transition-colors"
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

// ── Rol seçici ─────────────────────────────────────────────────────────────
function RolePicker({ value, onChange }: { value: Role; onChange: (r: Role) => void }) {
  return (
    <div className="space-y-2">
      {(Object.keys(ROLE_META) as Role[]).map(r => (
        <button
          key={r}
          type="button"
          onClick={() => onChange(r)}
          className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${
            value === r
              ? 'border-ink/30 bg-ink/4'
              : 'border-ink/8 hover:border-ink/20 bg-white'
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full mr-2 ${ROLE_META[r].bg} ${ROLE_META[r].text}`}>
                {ROLE_META[r].label}
              </span>
              <span className="text-xs text-ink/50">{ROLE_DESC[r]}</span>
            </div>
            {value === r && <Check size={16} className="text-ink/60 flex-shrink-0" />}
          </div>
        </button>
      ))}
    </div>
  );
}

// ── Ana sayfa ─────────────────────────────────────────────────────────────
export default function AdminUsers() {
  const [users, setUsers]         = useState<User[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');

  // Modaller
  const [showCreate, setShowCreate]       = useState(false);
  const [editUser, setEditUser]           = useState<User | null>(null);
  const [pwUser, setPwUser]               = useState<User | null>(null);
  const [deleteUser, setDeleteUser]       = useState<User | null>(null);
  const [deleting, setDeleting]           = useState(false);

  // Form state — yeni kullanıcı
  const [form, setForm] = useState({ name: '', email: '', role: 'viewer' as Role, password: '', confirm: '' });

  // Form state — düzenle
  const [editForm, setEditForm] = useState({ name: '', email: '', role: 'viewer' as Role, active: true });

  // Form state — şifre
  const [pwForm, setPwForm] = useState({ password: '', confirm: '' });

  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState('');

  // ── Yükleme ──────────────────────────────────────────────
  const fetchUsers = () => {
    setLoading(true);
    apiFetch('/api/users')
      .then(r => r.json())
      .then(data => { setUsers(data); setLoading(false); })
      .catch(() => { setError('Kullanıcılar yüklenemedi.'); setLoading(false); });
  };
  useEffect(fetchUsers, []);

  // ── Yeni kullanıcı oluştur ───────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErr('');
    if (form.password !== form.confirm) { setFormErr('Şifreler eşleşmiyor.'); return; }
    if (form.password.length < 6)       { setFormErr('Şifre en az 6 karakter olmalı.'); return; }
    setSaving(true);
    const res = await apiFetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: form.name, email: form.email, role: form.role, password: form.password }),
    });
    setSaving(false);
    if (res.ok) {
      setShowCreate(false);
      setForm({ name: '', email: '', role: 'viewer', password: '', confirm: '' });
      fetchUsers();
    } else {
      const d = await res.json();
      setFormErr(d.error || 'Bir hata oluştu.');
    }
  };

  // ── Kullanıcı düzenle ────────────────────────────────────
  const openEdit = (u: User) => {
    setEditUser(u);
    setEditForm({ name: u.name, email: u.email, role: u.role, active: u.active === 1 });
    setFormErr('');
  };
  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editUser) return;
    setFormErr('');
    setSaving(true);
    const res = await fetch(`/api/users/${editUser.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...editForm }),
    });
    setSaving(false);
    if (res.ok) { setEditUser(null); fetchUsers(); }
    else { const d = await res.json(); setFormErr(d.error || 'Hata.'); }
  };

  // ── Şifre değiştir ───────────────────────────────────────
  const handlePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pwUser) return;
    setFormErr('');
    if (pwForm.password !== pwForm.confirm) { setFormErr('Şifreler eşleşmiyor.'); return; }
    if (pwForm.password.length < 6)         { setFormErr('Şifre en az 6 karakter olmalı.'); return; }
    setSaving(true);
    const res = await fetch(`/api/users/${pwUser.id}/password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwForm.password }),
    });
    setSaving(false);
    if (res.ok) { setPwUser(null); setPwForm({ password: '', confirm: '' }); }
    else { const d = await res.json(); setFormErr(d.error || 'Hata.'); }
  };

  // ── Kullanıcı sil ────────────────────────────────────────
  const handleDelete = async () => {
    if (!deleteUser) return;
    setDeleting(true);
    const res = await fetch(`/api/users/${deleteUser.id}`, { method: 'DELETE' });
    setDeleting(false);
    if (res.ok) { setDeleteUser(null); fetchUsers(); }
    else { const d = await res.json(); alert(d.error || 'Silinemedi.'); }
  };

  // ── Active toggle ─────────────────────────────────────────
  const toggleActive = async (u: User) => {
    await fetch(`/api/users/${u.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: u.name, email: u.email, role: u.role, active: u.active ? 0 : 1 }),
    });
    fetchUsers();
  };

  // ─────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── Başlık ── */}
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-2xl font-light tracking-widest uppercase text-ink">Users</h1>
          <p className="text-xs text-ink/40 tracking-wide mt-1">Kullanıcılar ve yetki yönetimi</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setFormErr(''); }}
          className="flex items-center gap-2 px-5 py-2.5 bg-ink text-white text-xs tracking-widest uppercase rounded-lg hover:bg-ink/80 transition-colors"
        >
          <UserPlus size={15} />
          Yeni Kullanıcı
        </button>
      </div>

      {/* ── Özet kartlar ── */}
      <div className="grid grid-cols-3 gap-4 mb-10">
        {(Object.keys(ROLE_META) as Role[]).map(r => {
          const count = users.filter(u => u.role === r).length;
          return (
            <div key={r} className="bg-white border border-ink/6 rounded-xl p-5">
              <div className="flex items-center gap-3 mb-2">
                <ShieldCheck size={18} className="text-ink/30" />
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROLE_META[r].bg} ${ROLE_META[r].text}`}>
                  {ROLE_META[r].label}
                </span>
              </div>
              <p className="text-3xl font-light text-ink">{count}</p>
              <p className="text-xs text-ink/40 mt-0.5">kullanıcı</p>
            </div>
          );
        })}
      </div>

      {/* ── Kullanıcı tablosu ── */}
      {loading ? (
        <div className="text-center py-16 text-ink/30 text-sm">Yükleniyor…</div>
      ) : error ? (
        <div className="text-center py-16 text-red-400 text-sm">{error}</div>
      ) : (
        <div className="bg-white border border-ink/6 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-ink/5 bg-ink/2">
                <th className="text-left px-6 py-4 text-xs font-medium tracking-widest uppercase text-ink/40">Kullanıcı</th>
                <th className="text-left px-6 py-4 text-xs font-medium tracking-widest uppercase text-ink/40">Rol</th>
                <th className="text-left px-6 py-4 text-xs font-medium tracking-widest uppercase text-ink/40 hidden md:table-cell">Oluşturuldu</th>
                <th className="text-left px-6 py-4 text-xs font-medium tracking-widest uppercase text-ink/40">Durum</th>
                <th className="px-6 py-4" />
              </tr>
            </thead>
            <tbody>
              {users.map((u, idx) => (
                <motion.tr
                  key={u.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="border-b border-ink/4 last:border-0 hover:bg-ink/1 transition-colors"
                >
                  {/* Avatar + isim + email */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-ink/8 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-medium text-ink/60 uppercase">
                          {u.name.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-ink">{u.name}</p>
                        <p className="text-xs text-ink/40">{u.email}</p>
                      </div>
                    </div>
                  </td>

                  {/* Rol */}
                  <td className="px-6 py-4">
                    <span className={`inline-block text-xs font-medium px-2.5 py-1 rounded-full ${ROLE_META[u.role]?.bg ?? 'bg-gray-50'} ${ROLE_META[u.role]?.text ?? 'text-gray-600'}`}>
                      {ROLE_META[u.role]?.label ?? u.role}
                    </span>
                  </td>

                  {/* Tarih */}
                  <td className="px-6 py-4 hidden md:table-cell">
                    <span className="text-xs text-ink/40">
                      {new Date(u.created_at).toLocaleDateString('tr-TR')}
                    </span>
                  </td>

                  {/* Aktif toggle */}
                  <td className="px-6 py-4">
                    <button
                      onClick={() => toggleActive(u)}
                      className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full transition-colors ${
                        u.active
                          ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                          : 'bg-ink/5 text-ink/40 hover:bg-ink/10'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${u.active ? 'bg-emerald-500' : 'bg-ink/30'}`} />
                      {u.active ? 'Aktif' : 'Pasif'}
                    </button>
                  </td>

                  {/* Eylemler */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        onClick={() => openEdit(u)}
                        className="p-1.5 rounded-md text-ink/30 hover:text-ink hover:bg-ink/5 transition-colors"
                        title="Düzenle"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => { setPwUser(u); setPwForm({ password: '', confirm: '' }); setFormErr(''); }}
                        className="p-1.5 rounded-md text-ink/30 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                        title="Şifre değiştir"
                      >
                        <KeyRound size={15} />
                      </button>
                      <button
                        onClick={() => setDeleteUser(u)}
                        className="p-1.5 rounded-md text-ink/30 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Sil"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-16 text-ink/30">
                    <Users size={32} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">Henüz kullanıcı yok.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ────────────────────────────────────────────────────── */}
      {/* MODALLER                                              */}
      {/* ────────────────────────────────────────────────────── */}
      <AnimatePresence>

        {/* ── Yeni Kullanıcı ── */}
        {showCreate && (
          <Modal title="Yeni Kullanıcı" onClose={() => setShowCreate(false)}>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">Ad Soyad *</label>
                  <input
                    value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    required placeholder="Örn: Ayşe Kaya"
                    className="w-full px-3 py-2.5 border border-ink/10 rounded-lg text-sm text-ink focus:outline-none focus:border-ink/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">E-posta *</label>
                  <input
                    type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    required placeholder="ornek@mail.com"
                    className="w-full px-3 py-2.5 border border-ink/10 rounded-lg text-sm text-ink focus:outline-none focus:border-ink/30 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-ink/50 mb-2 tracking-wide uppercase">Rol *</label>
                <RolePicker value={form.role} onChange={r => setForm(f => ({ ...f, role: r }))} />
              </div>

              <div>
                <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">Şifre *</label>
                <PasswordInput value={form.password} onChange={v => setForm(f => ({ ...f, password: v }))} required />
              </div>
              <div>
                <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">Şifre Tekrar *</label>
                <PasswordInput value={form.confirm} onChange={v => setForm(f => ({ ...f, confirm: v }))} placeholder="Şifre tekrar" required />
              </div>

              {formErr && <p className="text-xs text-red-500">{formErr}</p>}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)}
                  className="flex-1 px-4 py-2.5 border border-ink/10 text-sm text-ink/60 rounded-lg hover:bg-ink/3 transition-colors">
                  İptal
                </button>
                <button type="submit" disabled={saving}
                  className="flex-1 px-4 py-2.5 bg-ink text-white text-sm rounded-lg hover:bg-ink/80 disabled:opacity-50 transition-colors">
                  {saving ? 'Kaydediliyor…' : 'Oluştur'}
                </button>
              </div>
            </form>
          </Modal>
        )}

        {/* ── Düzenle ── */}
        {editUser && (
          <Modal title={`Düzenle — ${editUser.name}`} onClose={() => setEditUser(null)}>
            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">Ad Soyad *</label>
                <input
                  value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                  required
                  className="w-full px-3 py-2.5 border border-ink/10 rounded-lg text-sm text-ink focus:outline-none focus:border-ink/30 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">E-posta *</label>
                <input
                  type="email" value={editForm.email} onChange={e => setEditForm(f => ({ ...f, email: e.target.value }))}
                  required
                  className="w-full px-3 py-2.5 border border-ink/10 rounded-lg text-sm text-ink focus:outline-none focus:border-ink/30 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-ink/50 mb-2 tracking-wide uppercase">Rol *</label>
                <RolePicker value={editForm.role} onChange={r => setEditForm(f => ({ ...f, role: r }))} />
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setEditForm(f => ({ ...f, active: !f.active }))}
                  className={`relative w-10 h-5 rounded-full transition-colors ${editForm.active ? 'bg-emerald-500' : 'bg-ink/20'}`}
                >
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${editForm.active ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
                <span className="text-sm text-ink/60">{editForm.active ? 'Aktif' : 'Pasif'}</span>
              </div>

              {formErr && <p className="text-xs text-red-500">{formErr}</p>}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setEditUser(null)}
                  className="flex-1 px-4 py-2.5 border border-ink/10 text-sm text-ink/60 rounded-lg hover:bg-ink/3 transition-colors">
                  İptal
                </button>
                <button type="submit" disabled={saving}
                  className="flex-1 px-4 py-2.5 bg-ink text-white text-sm rounded-lg hover:bg-ink/80 disabled:opacity-50 transition-colors">
                  {saving ? 'Kaydediliyor…' : 'Kaydet'}
                </button>
              </div>
            </form>
          </Modal>
        )}

        {/* ── Şifre Değiştir ── */}
        {pwUser && (
          <Modal title={`Şifre — ${pwUser.name}`} onClose={() => setPwUser(null)}>
            <form onSubmit={handlePassword} className="space-y-4">
              <p className="text-xs text-ink/50">
                <span className="font-medium text-ink">{pwUser.email}</span> için yeni şifre belirle.
              </p>
              <div>
                <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">Yeni Şifre *</label>
                <PasswordInput value={pwForm.password} onChange={v => setPwForm(f => ({ ...f, password: v }))} required />
              </div>
              <div>
                <label className="block text-xs text-ink/50 mb-1.5 tracking-wide uppercase">Tekrar *</label>
                <PasswordInput value={pwForm.confirm} onChange={v => setPwForm(f => ({ ...f, confirm: v }))} placeholder="Şifre tekrar" required />
              </div>

              {formErr && <p className="text-xs text-red-500">{formErr}</p>}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setPwUser(null)}
                  className="flex-1 px-4 py-2.5 border border-ink/10 text-sm text-ink/60 rounded-lg hover:bg-ink/3 transition-colors">
                  İptal
                </button>
                <button type="submit" disabled={saving}
                  className="flex-1 px-4 py-2.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
                  {saving ? 'Değiştiriliyor…' : 'Şifreyi Güncelle'}
                </button>
              </div>
            </form>
          </Modal>
        )}

        {/* ── Silme onayı ── */}
        {deleteUser && (
          <Modal title="Kullanıcı Sil" onClose={() => setDeleteUser(null)}>
            <div className="space-y-4">
              <div className="p-4 bg-red-50 rounded-lg border border-red-100">
                <p className="text-sm text-red-700">
                  <span className="font-medium">{deleteUser.name}</span> ({deleteUser.email}) adlı kullanıcıyı silmek istediğine emin misin?
                </p>
                <p className="text-xs text-red-500 mt-1">Bu işlem geri alınamaz.</p>
              </div>
              <div className="flex gap-3">
                <button onClick={() => setDeleteUser(null)}
                  className="flex-1 px-4 py-2.5 border border-ink/10 text-sm text-ink/60 rounded-lg hover:bg-ink/3 transition-colors">
                  İptal
                </button>
                <button onClick={handleDelete} disabled={deleting}
                  className="flex-1 px-4 py-2.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors">
                  {deleting ? 'Siliniyor…' : 'Sil'}
                </button>
              </div>
            </div>
          </Modal>
        )}

      </AnimatePresence>
    </div>
  );
}
