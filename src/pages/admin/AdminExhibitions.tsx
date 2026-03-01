import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, X, Check, Trash2, UploadCloud, Calendar, MapPin, Edit2, Eye, EyeOff } from 'lucide-react';

interface Exhibition {
  id: number;
  title: string;
  subtitle: string;
  artists: string;
  location: string;
  venue: string;
  start_date: string;
  end_date: string;
  status: 'upcoming' | 'current' | 'past';
  cover_url: string | null;
  description: string;
  is_public: number;
}

const STATUS_COLORS: Record<string, string> = {
  upcoming: 'bg-blue-50 text-blue-700 border-blue-200',
  current:  'bg-green-50 text-green-700 border-green-200',
  past:     'bg-gray-100 text-gray-500 border-gray-200',
};

const emptyForm = (): Omit<Exhibition, 'id' | 'cover_url' | 'is_public'> & { is_public: boolean } => ({
  title: '', subtitle: '', artists: '', location: '', venue: '',
  start_date: '', end_date: '', status: 'upcoming', description: '', is_public: false,
});

export default function AdminExhibitions() {
  const [exhibitions, setExhibitions] = useState<Exhibition[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [view,        setView]        = useState<'list' | 'form'>('list');
  const [editId,      setEditId]      = useState<number | null>(null);
  const [form,        setForm]        = useState(emptyForm());
  const [coverFile,   setCoverFile]   = useState<File | null>(null);
  const [coverPreview,setCoverPreview]= useState<string | null>(null);
  const [submitting,  setSubmitting]  = useState(false);
  const [saving,      setSaving]      = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/exhibitions');
      if (res.ok) setExhibitions(await res.json());
    } finally { setLoading(false); }
  };

  const openNew = () => {
    setEditId(null);
    setForm(emptyForm());
    setCoverFile(null);
    setCoverPreview(null);
    setView('form');
  };

  const openEdit = (ex: Exhibition) => {
    setEditId(ex.id);
    setForm({
      title: ex.title, subtitle: ex.subtitle, artists: ex.artists,
      location: ex.location, venue: ex.venue, start_date: ex.start_date,
      end_date: ex.end_date, status: ex.status, description: ex.description,
      is_public: ex.is_public === 1,
    });
    setCoverFile(null);
    setCoverPreview(ex.cover_url || null);
    setView('form');
  };

  const handleCoverChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCoverFile(file);
    const r = new FileReader();
    r.onloadend = () => setCoverPreview(r.result as string);
    r.readAsDataURL(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, String(v)));
      if (coverFile) fd.append('cover', coverFile);

      const url    = editId ? `/api/exhibitions/${editId}` : '/api/exhibitions';
      const method = editId ? 'PUT' : 'POST';
      const res    = await fetch(url, { method, body: fd });
      if (res.ok) { await fetchAll(); setView('list'); }
    } finally { setSubmitting(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this exhibition?')) return;
    await fetch(`/api/exhibitions/${id}`, { method: 'DELETE' });
    setExhibitions(prev => prev.filter(e => e.id !== id));
  };

  const togglePublic = async (ex: Exhibition) => {
    setSaving(ex.id);
    const fd = new FormData();
    Object.entries({
      title: ex.title, subtitle: ex.subtitle, artists: ex.artists,
      location: ex.location, venue: ex.venue, start_date: ex.start_date,
      end_date: ex.end_date, status: ex.status, description: ex.description,
      is_public: String(ex.is_public === 1 ? 'false' : 'true'),
    }).forEach(([k, v]) => fd.append(k, v));
    const res = await fetch(`/api/exhibitions/${ex.id}`, { method: 'PUT', body: fd });
    if (res.ok) await fetchAll();
    setSaving(null);
  };

  const Field = ({
    label, name, type = 'text', placeholder = '', rows,
  }: { label: string; name: keyof typeof form; type?: string; placeholder?: string; rows?: number }) => (
    <div>
      <label className="block text-[10px] tracking-[0.25em] uppercase text-ink/50 mb-1.5">{label}</label>
      {rows ? (
        <textarea
          rows={rows}
          value={form[name] as string}
          onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
          placeholder={placeholder}
          className="w-full px-3 py-2.5 bg-[#F9F9F9] border border-transparent rounded text-sm focus:outline-none focus:border-ink/20 focus:bg-white transition-colors resize-none"
        />
      ) : (
        <input
          type={type}
          value={form[name] as string}
          onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
          placeholder={placeholder}
          className="w-full px-3 py-2.5 bg-[#F9F9F9] border border-transparent rounded text-sm focus:outline-none focus:border-ink/20 focus:bg-white transition-colors"
        />
      )}
    </div>
  );

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      className="space-y-8">

      <header className="flex justify-between items-end pb-6 border-b border-ink/5">
        <div>
          <h1 className="text-3xl font-serif tracking-tight">Exhibitions</h1>
          <p className="text-ink/50 text-sm mt-1">Manage upcoming, current and past exhibitions.</p>
        </div>
        {view === 'list' ? (
          <button onClick={openNew}
            className="flex items-center gap-2 bg-ink text-white text-xs tracking-[0.2em] uppercase px-5 py-2.5 hover:bg-ink/90 transition-colors">
            <Plus size={14} /> New Exhibition
          </button>
        ) : (
          <button onClick={() => setView('list')}
            className="flex items-center gap-2 border border-ink/15 text-sm px-5 py-2.5 hover:bg-ink/5 transition-colors">
            <X size={14} /> Cancel
          </button>
        )}
      </header>

      <AnimatePresence mode="wait">
        {/* ── LIST ── */}
        {view === 'list' && (
          <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="space-y-3">

            {loading && (
              <div className="bg-white border border-ink/5 p-10 text-center text-xs text-ink/30 tracking-widest uppercase">Loading…</div>
            )}

            {!loading && exhibitions.length === 0 && (
              <div className="bg-white border border-ink/5 p-16 text-center">
                <Calendar size={28} className="mx-auto text-ink/20 mb-4" />
                <p className="text-xs text-ink/40 tracking-widest uppercase mb-4">No exhibitions yet</p>
                <button onClick={openNew}
                  className="text-xs tracking-[0.2em] uppercase border border-ink/15 px-5 py-2.5 hover:bg-ink hover:text-white transition-colors">
                  Add First Exhibition
                </button>
              </div>
            )}

            {!loading && exhibitions.map((ex, i) => (
              <motion.div key={ex.id}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
                className="bg-white border border-ink/5 hover:border-ink/10 transition-colors group">
                <div className="flex items-stretch">

                  {/* Cover thumbnail */}
                  <div className="w-28 flex-shrink-0 bg-ink/5 overflow-hidden">
                    {ex.cover_url ? (
                      <img src={ex.cover_url} alt={ex.title}
                        className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-500" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Calendar size={20} className="text-ink/20" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 px-6 py-4 flex items-center gap-6 min-w-0">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className={`text-[9px] tracking-[0.22em] uppercase px-2 py-0.5 border rounded-sm font-medium ${STATUS_COLORS[ex.status] || STATUS_COLORS.past}`}>
                          {ex.status}
                        </span>
                        {!ex.is_public && (
                          <span className="text-[9px] tracking-[0.22em] uppercase text-ink/30">Draft</span>
                        )}
                      </div>
                      <h3 className="font-serif text-lg leading-tight truncate">{ex.title}</h3>
                      {ex.subtitle && <p className="text-xs text-ink/50 mt-0.5 truncate">{ex.subtitle}</p>}
                    </div>

                    <div className="flex-shrink-0 text-right">
                      {(ex.start_date || ex.end_date) && (
                        <p className="text-xs text-ink/60 flex items-center gap-1.5 justify-end mb-1">
                          <Calendar size={11} className="text-ink/30" />
                          {ex.start_date}{ex.end_date ? ` — ${ex.end_date}` : ''}
                        </p>
                      )}
                      {(ex.location || ex.venue) && (
                        <p className="text-xs text-ink/50 flex items-center gap-1.5 justify-end">
                          <MapPin size={11} className="text-ink/30" />
                          {ex.venue ? `${ex.venue}, ` : ''}{ex.location}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex-shrink-0 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => togglePublic(ex)} title={ex.is_public ? 'Make draft' : 'Publish'}
                        className={`p-2 rounded transition-colors ${ex.is_public ? 'text-green-600 hover:bg-green-50' : 'text-ink/30 hover:bg-ink/5'} ${saving === ex.id ? 'opacity-40' : ''}`}>
                        {ex.is_public ? <Eye size={15} /> : <EyeOff size={15} />}
                      </button>
                      <button onClick={() => openEdit(ex)}
                        className="p-2 text-blue-500 hover:bg-blue-50 rounded transition-colors">
                        <Edit2 size={15} />
                      </button>
                      <button onClick={() => handleDelete(ex.id)}
                        className="p-2 text-red-400 hover:bg-red-50 rounded transition-colors">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* ── FORM ── */}
        {view === 'form' && (
          <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <form onSubmit={handleSubmit} className="space-y-6">

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Cover image */}
                <div>
                  <label className="block text-[10px] tracking-[0.25em] uppercase text-ink/50 mb-1.5">Cover Image</label>
                  <div onClick={() => fileRef.current?.click()}
                    className="border-2 border-dashed border-ink/10 rounded-lg aspect-[4/3] flex flex-col items-center justify-center cursor-pointer hover:border-ink/25 hover:bg-ink/[0.02] transition-all relative overflow-hidden">
                    {coverPreview ? (
                      <img src={coverPreview} alt="" className="absolute inset-0 w-full h-full object-cover" />
                    ) : (
                      <>
                        <UploadCloud size={24} className="text-ink/30 mb-2" />
                        <p className="text-xs text-ink/40">Upload cover</p>
                      </>
                    )}
                  </div>
                  <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleCoverChange} />
                </div>

                {/* Main fields */}
                <div className="lg:col-span-2 space-y-4">
                  <div className="bg-white border border-ink/5 rounded-xl p-6 space-y-4">
                    <Field label="Title *" name="title" placeholder="Exhibition title" />
                    <Field label="Subtitle / Theme" name="subtitle" placeholder="e.g. A group exhibition on materiality" />
                    <Field label="Artists" name="artists" placeholder="e.g. TBA / Artist Name, Artist Name" />

                    <div className="grid grid-cols-2 gap-4">
                      <Field label="Location (City)" name="location" placeholder="London" />
                      <Field label="Venue" name="venue" placeholder="Gallery / Museum name" />
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <Field label="Start Date" name="start_date" type="text" placeholder="Spring 2026" />
                      <Field label="End Date" name="end_date" type="text" placeholder="Jun 2026" />
                      <div>
                        <label className="block text-[10px] tracking-[0.25em] uppercase text-ink/50 mb-1.5">Status</label>
                        <select value={form.status}
                          onChange={e => setForm(f => ({ ...f, status: e.target.value as Exhibition['status'] }))}
                          className="w-full px-3 py-2.5 bg-[#F9F9F9] border border-transparent rounded text-sm focus:outline-none focus:border-ink/20 focus:bg-white transition-colors">
                          <option value="upcoming">Upcoming</option>
                          <option value="current">Current</option>
                          <option value="past">Past</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white border border-ink/5 rounded-xl p-6 space-y-4">
                    <Field label="Description" name="description" placeholder="Exhibition description…" rows={4} />

                    <label className="flex items-center gap-3 cursor-pointer group pt-2 border-t border-ink/5">
                      <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${form.is_public ? 'bg-ink border-ink' : 'border-ink/20 group-hover:border-ink/40'}`}>
                        {form.is_public && <Check size={14} className="text-white" />}
                      </div>
                      <input type="checkbox" checked={form.is_public}
                        onChange={e => setForm(f => ({ ...f, is_public: e.target.checked }))} className="hidden" />
                      <div>
                        <p className="text-sm font-medium">Publish to Website</p>
                        <p className="text-xs text-ink/40">Show on Exhibitions page</p>
                      </div>
                    </label>
                  </div>
                </div>
              </div>

              {/* Submit */}
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setView('list')}
                  className="px-6 py-2.5 text-sm text-ink/60 hover:text-ink transition-colors">Cancel</button>
                <button type="submit" disabled={submitting || !form.title}
                  className="flex items-center gap-2 bg-ink text-white text-sm px-8 py-2.5 hover:bg-ink/90 disabled:opacity-50 transition-colors">
                  <Check size={15} />
                  {submitting ? 'Saving…' : editId ? 'Update Exhibition' : 'Create Exhibition'}
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
