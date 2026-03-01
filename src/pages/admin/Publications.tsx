/**
 * Publications.tsx — Admin
 * Yayın yönetimi: katalog, dergi, basın
 */
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, BookOpen, ExternalLink, Trash2, Edit2 } from 'lucide-react';

const PX = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const BTN = (bg = '#111', col = '#fff', bd = 'transparent'): React.CSSProperties => ({
  fontFamily: PX, fontSize: 9, fontWeight: 400,
  letterSpacing: '0.28em', textTransform: 'uppercase' as const,
  background: bg, color: col, border: `1px solid ${bd || bg}`,
  padding: '9px 20px', cursor: 'pointer', transition: 'all 0.2s',
});
const LABEL: React.CSSProperties = {
  fontFamily: PX, fontSize: 9, fontWeight: 400,
  letterSpacing: '0.32em', textTransform: 'uppercase' as const, color: '#999',
  display: 'block', marginBottom: 6,
};
const INPUT: React.CSSProperties = {
  width: '100%', fontFamily: PX, fontSize: 12, fontWeight: 300,
  color: '#111', background: '#fafafa', border: '1px solid #e0e0e0',
  padding: '9px 11px', outline: 'none', boxSizing: 'border-box' as const,
};

const TYPES = ['catalog', 'magazine', 'press', 'essay', 'other'];

interface Publication {
  id: number;
  title: string;
  description: string;
  type: string;
  year: string;
  cover_url: string | null;
  file_url: string | null;
  is_public: number;
  created_at: string;
}

// ─── Modal ────────────────────────────────────────────────
function PubModal({
  pub, onClose, onSaved,
}: { pub: Publication | null; onClose: () => void; onSaved: () => void }) {
  const isEdit = !!pub;
  const [form, setForm] = useState({
    title:       pub?.title       ?? '',
    description: pub?.description ?? '',
    type:        pub?.type        ?? 'catalog',
    year:        pub?.year        ?? String(new Date().getFullYear()),
    file_url:    pub?.file_url    ?? '',
    is_public:   pub?.is_public   ?? 0,
  });
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string>(pub?.cover_url ?? '');
  const [pdfFile, setPdfFile]  = useState<File | null>(null);
  const [saving, setSaving]    = useState(false);
  const [error, setError]      = useState('');
  const coverRef = useRef<HTMLInputElement>(null);
  const pdfRef   = useRef<HTMLInputElement>(null);

  const handleCover = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return;
    setCoverFile(f);
    const reader = new FileReader();
    reader.onload = ev => setCoverPreview(ev.target!.result as string);
    reader.readAsDataURL(f);
  };

  const handleSave = async () => {
    if (!form.title.trim()) { setError('Title is required'); return; }
    setSaving(true); setError('');
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, String(v)));
      if (coverFile) fd.append('cover', coverFile);
      if (pdfFile)   fd.append('file', pdfFile);

      const url    = isEdit ? `/api/publications/${pub!.id}` : '/api/publications';
      const method = isEdit ? 'PUT' : 'POST';
      const res = await fetch(url, { method, body: fd });
      if (!res.ok) throw new Error((await res.json()).error || 'Save failed');
      onSaved(); onClose();
    } catch (e: any) { setError(e.message); }
    setSaving(false);
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex' }}>
      <div onClick={onClose} style={{ flex: 1, background: 'rgba(0,0,0,0.42)', cursor: 'pointer' }} />
      <motion.div
        initial={{ x: 560 }} animate={{ x: 0 }} exit={{ x: 560 }}
        transition={{ type: 'spring', stiffness: 300, damping: 32 }}
        style={{
          width: 560, height: '100%', overflowY: 'auto',
          background: '#fafafa', display: 'flex', flexDirection: 'column',
          boxShadow: '-24px 0 80px rgba(0,0,0,0.14)',
        }}
      >
        {/* Header */}
        <div style={{ background: '#fff', padding: '28px 32px', borderBottom: '1px solid #eee',
          flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ ...LABEL, margin: '0 0 4px' }}>{isEdit ? 'Edit' : 'New'} Publication</span>
            <h2 style={{ fontFamily: PX, fontSize: 18, fontWeight: 300, color: '#111',
              letterSpacing: '0.08em', textTransform: 'uppercase', margin: 0 }}>
              {isEdit ? form.title : 'Add Publication'}
            </h2>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 22, color: '#bbb', lineHeight: 1 }}>×</button>
        </div>

        <div style={{ padding: '24px 32px', flex: 1, display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* Cover image */}
          <div>
            <label style={LABEL}>Cover Image</label>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <div onClick={() => coverRef.current?.click()} style={{
                width: 80, height: 100, background: '#eee', overflow: 'hidden',
                cursor: 'pointer', border: '1px dashed #ccc', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {coverPreview ? (
                  <img src={coverPreview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <BookOpen size={20} color="#ccc" />
                )}
              </div>
              <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb', letterSpacing: '0.28em', textTransform: 'uppercase' }}>
                Click to upload cover
              </span>
              <input ref={coverRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleCover} />
            </div>
          </div>

          {/* Title */}
          <div>
            <label style={LABEL}>Title *</label>
            <input style={INPUT} value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Publication title" />
          </div>

          {/* Description */}
          <div>
            <label style={LABEL}>Description</label>
            <textarea style={{ ...INPUT, resize: 'vertical' as const }} rows={3}
              value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Short description…" />
          </div>

          {/* Type + Year */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={LABEL}>Type</label>
              <select style={{ ...INPUT, cursor: 'pointer' }} value={form.type}
                onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
                {TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label style={LABEL}>Year</label>
              <input style={INPUT} value={form.year} onChange={e => setForm(f => ({ ...f, year: e.target.value }))} placeholder="2025" />
            </div>
          </div>

          {/* PDF / File */}
          <div>
            <label style={LABEL}>PDF / File</label>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button onClick={() => pdfRef.current?.click()} style={BTN('transparent', '#888', '#ccc')}>
                {pdfFile ? `✓ ${pdfFile.name.slice(0, 20)}…` : 'Upload PDF'}
              </button>
              <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb', letterSpacing: '0.18em' }}>or</span>
              <input style={{ ...INPUT, flex: 1 }} value={form.file_url}
                onChange={e => setForm(f => ({ ...f, file_url: e.target.value }))}
                placeholder="https://link-to-file…" />
              <input ref={pdfRef} type="file" accept=".pdf,image/*" style={{ display: 'none' }}
                onChange={e => { const f = e.target.files?.[0]; if (f) setPdfFile(f); }} />
            </div>
          </div>

          {/* Public toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingTop: 8 }}>
            <button onClick={() => setForm(f => ({ ...f, is_public: f.is_public ? 0 : 1 }))}
              style={BTN(form.is_public ? '#2d7a2d' : 'transparent', form.is_public ? '#fff' : '#bbb', form.is_public ? '#2d7a2d' : '#ddd')}>
              {form.is_public ? '● Public' : '○ Private'}
            </button>
            <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
              Visibility
            </span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ background: '#fff', padding: '18px 32px', borderTop: '1px solid #eee',
          flexShrink: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
          {error && <span style={{ fontFamily: PX, fontSize: 10, color: '#c00', letterSpacing: '0.1em', flex: 1 }}>{error}</span>}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
            <button onClick={onClose} style={BTN('transparent', '#999', '#ddd')}>Cancel</button>
            <button onClick={handleSave} disabled={saving} style={{ ...BTN(saving ? '#ccc' : '#111'), minWidth: 120 }}>
              {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Publication'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────
export default function Publications() {
  const [pubs, setPubs]         = useState<Publication[]>([]);
  const [loading, setLoading]   = useState(true);
  const [modal, setModal]       = useState<Publication | 'new' | null>(null);
  const [delTarget, setDelTarget] = useState<Publication | null>(null);
  const [toast, setToast]       = useState('');

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = () => {
    setLoading(true);
    fetch('/api/publications')
      .then(r => r.json())
      .then(data => { setPubs(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const doDelete = async () => {
    if (!delTarget) return;
    const res = await fetch(`/api/publications/${delTarget.id}`, { method: 'DELETE' });
    if (res.ok) { setPubs(prev => prev.filter(p => p.id !== delTarget.id)); showToast('Deleted'); }
    else showToast('Delete failed');
    setDelTarget(null);
  };

  const typeColor: Record<string, string> = {
    catalog: '#111', magazine: '#4a76d4', press: '#2d7a2d', essay: '#7a4a2d', other: '#888',
  };

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      className="space-y-8" style={{ fontFamily: PX }}>
      <style>{`
        button:focus, input:focus, select:focus, textarea:focus { outline: none; }
        input:focus, select:focus, textarea:focus { border-color: #111 !important; background: #fff !important; }
      `}</style>

      {/* Header */}
      <header className="flex justify-between items-end pb-6 border-b border-ink/5">
        <div>
          <h1 className="text-3xl font-serif tracking-tight">Publications</h1>
          <p className="text-ink/50 text-sm mt-2">
            {pubs.length} publication{pubs.length !== 1 ? 's' : ''} — {pubs.filter(p => p.is_public).length} public
          </p>
        </div>
        <button onClick={() => setModal('new')} style={BTN()}
          className="flex items-center gap-2">
          + New Publication
        </button>
      </header>

      {/* Grid */}
      {loading ? (
        <div className="bg-white border border-ink/5 p-16 text-center text-xs tracking-widest uppercase text-ink/30">Loading…</div>
      ) : pubs.length === 0 ? (
        <div className="bg-white border border-ink/5 p-16 flex flex-col items-center justify-center gap-4">
          <BookOpen size={32} className="text-ink/15" />
          <p className="text-xs tracking-widest uppercase text-ink/30">No publications yet</p>
          <button onClick={() => setModal('new')} style={{ ...BTN('transparent', '#888', '#ddd') }}>
            + Add First Publication
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <AnimatePresence initial={false}>
            {pubs.map(pub => (
              <motion.div key={pub.id}
                initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                className="bg-white border border-ink/5 group overflow-hidden">

                {/* Cover */}
                <div style={{ background: '#f0f0f0', aspectRatio: '3/4', overflow: 'hidden', position: 'relative' }}>
                  {pub.cover_url ? (
                    <img src={pub.cover_url} alt={pub.title}
                      className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <BookOpen size={32} className="text-ink/15" />
                    </div>
                  )}
                  {/* Overlay actions */}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                    <button onClick={() => setModal(pub)}
                      className="p-2 bg-white/90 hover:bg-white transition-colors">
                      <Edit2 size={14} color="#111" />
                    </button>
                    {pub.file_url && (
                      <a href={pub.file_url} target="_blank" rel="noopener noreferrer"
                        className="p-2 bg-white/90 hover:bg-white transition-colors">
                        <ExternalLink size={14} color="#111" />
                      </a>
                    )}
                    <button onClick={() => setDelTarget(pub)}
                      className="p-2 bg-white/90 hover:bg-red-50 transition-colors">
                      <Trash2 size={14} color="#c00" />
                    </button>
                  </div>
                  {/* Public dot */}
                  <div style={{
                    position: 'absolute', top: 8, right: 8,
                    width: 8, height: 8, borderRadius: '50%',
                    background: pub.is_public ? '#2d7a2d' : 'rgba(0,0,0,0.2)',
                  }} />
                </div>

                {/* Info */}
                <div style={{ padding: '12px 14px' }}>
                  <p style={{
                    fontFamily: PX, fontSize: 8, fontWeight: 400,
                    letterSpacing: '0.3em', textTransform: 'uppercase',
                    color: typeColor[pub.type] ?? '#888', margin: '0 0 4px',
                  }}>
                    {pub.type} {pub.year ? `· ${pub.year}` : ''}
                  </p>
                  <p style={{ fontFamily: PX, fontSize: 12, fontWeight: 400, color: '#111',
                    margin: '0 0 4px', letterSpacing: '0.03em', lineHeight: 1.4 }}>
                    {pub.title}
                  </p>
                  {pub.description && (
                    <p style={{ fontFamily: PX, fontSize: 10, fontWeight: 300, color: '#aaa',
                      margin: 0, lineHeight: 1.5,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {pub.description}
                    </p>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Modal */}
      <AnimatePresence>
        {modal && (
          <PubModal
            pub={modal === 'new' ? null : modal as Publication}
            onClose={() => setModal(null)}
            onSaved={() => { load(); showToast('Saved'); }}
          />
        )}
      </AnimatePresence>

      {/* Delete confirm */}
      <AnimatePresence>
        {delTarget && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
              zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <motion.div initial={{ y: 12 }} animate={{ y: 0 }}
              style={{ background: '#fff', padding: '40px 44px', maxWidth: 400, width: '90%',
                boxShadow: '0 24px 60px rgba(0,0,0,0.15)' }}>
              <p style={{ fontFamily: PX, fontSize: 13, fontWeight: 300, color: '#111',
                lineHeight: 1.7, marginBottom: 28 }}>
                Delete <strong>"{delTarget.title}"</strong>? This cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button onClick={doDelete} style={BTN('#c00')}>Delete</button>
                <button onClick={() => setDelTarget(null)} style={BTN('transparent', '#111', '#ccc')}>Cancel</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            style={{
              position: 'fixed', bottom: 28, right: 28, background: '#111', color: '#fff',
              fontFamily: PX, fontSize: 10, fontWeight: 300, letterSpacing: '0.25em',
              textTransform: 'uppercase', padding: '13px 24px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.18)', zIndex: 9999,
            }}>
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
