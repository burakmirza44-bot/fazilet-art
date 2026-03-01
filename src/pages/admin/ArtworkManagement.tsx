/**
 * ArtistManagement.tsx
 *
 * Admin panel — Artists & Links
 * ─ Sanatçı listesi (arama, publish toggle, featured toggle)
 * ─ Add/Edit: drag-drop çoklu eser yükleme, tek kayıt
 * ─ Private link kopyalama + token yenileme
 */

import React, { useState, useEffect, useRef, useCallback, DragEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';

// ─── Types ────────────────────────────────────────────────
interface ArtworkDraft {
  uid: string;           // geçici frontend ID
  id?: number;           // DB ID (edit modunda)
  file: File | null;
  preview: string;       // object URL veya mevcut image_url/video_url
  title: string;
  year: string;
  medium: string;
  dimensions: string;
  status: 'Public' | 'Private';
  video_url?: string;    // mevcut video URL (edit modunda)
  isVideo?: boolean;     // bu eser bir video mu?
}

interface Artist {
  id: string;
  name: string;
  bio: string;
  medium: string;
  image_url: string | null;
  is_public: number;
  is_featured: number;
  private_token: string;
  artworks_count?: number;
  artworks?: ArtworkDraft[];
}

// ─── Constants ───────────────────────────────────────────
const PX = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const uid = () => Math.random().toString(36).slice(2, 9);
const ORIGIN = window.location.origin;

// ─── Helpers ─────────────────────────────────────────────
async function apiFetch(url: string, opts?: RequestInit) {
  const token = localStorage.getItem('admin_token');
  const headers: Record<string, string> = {
    ...((opts?.headers as Record<string, string>) ?? {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const r = await fetch(url, { ...opts, headers });
  if (r.status === 401) {
    localStorage.removeItem('admin_token');
    window.location.href = '/admin/login';
    throw new Error('Oturum süresi doldu');
  }
  if (!r.ok) {
    const err = await r.json().catch(() => ({ error: r.statusText }));
    throw new Error(err.error || 'API error');
  }
  return r.json();
}

function fileToPreview(file: File): Promise<string> {
  return new Promise(res => {
    const r = new FileReader();
    r.onload = e => res(e.target!.result as string);
    r.readAsDataURL(file);
  });
}

// ─── Shared UI ───────────────────────────────────────────
const LABEL: React.CSSProperties = {
  fontFamily: PX, fontSize: 9, fontWeight: 400,
  letterSpacing: '0.32em', textTransform: 'uppercase', color: '#999',
  display: 'block', marginBottom: 6,
};
const INPUT: React.CSSProperties = {
  width: '100%', fontFamily: PX, fontSize: 12, fontWeight: 300,
  color: '#111', background: '#fafafa',
  border: '1px solid #e0e0e0', padding: '9px 11px',
  outline: 'none', boxSizing: 'border-box', borderRadius: 0,
};
const BTN = (bg = '#111', col = '#fff', bd = 'transparent'): React.CSSProperties => ({
  fontFamily: PX, fontSize: 9, fontWeight: 400,
  letterSpacing: '0.28em', textTransform: 'uppercase',
  background: bg, color: col, border: `1px solid ${bd || bg}`,
  padding: '9px 20px', cursor: 'pointer',
  transition: 'all 0.2s', whiteSpace: 'nowrap' as const,
});

function Field({
  label, value, onChange, as, rows, options, required,
}: {
  label: string; value: string; onChange: (v: string) => void;
  as?: 'textarea' | 'select'; rows?: number; options?: string[];
  required?: boolean;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={LABEL}>{label}{required && <span style={{ color: '#c00' }}>*</span>}</label>
      {as === 'textarea' ? (
        <textarea rows={rows || 3} value={value} onChange={e => onChange(e.target.value)}
          style={{ ...INPUT, resize: 'vertical' }} />
      ) : as === 'select' ? (
        <select value={value} onChange={e => onChange(e.target.value)} style={INPUT}>
          {options!.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input value={value} onChange={e => onChange(e.target.value)}
          required={required} style={INPUT} />
      )}
    </div>
  );
}

// ─── Toggle button ───────────────────────────────────────
function Toggle({ on, onToggle, labelOn, labelOff, colorOn = '#111' }: {
  on: boolean; onToggle: () => void;
  labelOn: string; labelOff: string; colorOn?: string;
}) {
  return (
    <button onClick={onToggle} style={{
      ...BTN(on ? colorOn : 'transparent', on ? '#fff' : '#bbb', on ? colorOn : '#ddd'),
      fontSize: 8, padding: '6px 12px',
    }}>
      {on ? labelOn : labelOff}
    </button>
  );
}

// ─── Private link modal ──────────────────────────────────
function PrivateLinkModal({ token, artistName, onClose, onRegenerate }: {
  token: string; artistName: string;
  onClose: () => void; onRegenerate: () => Promise<void>;
}) {
  const [copied,       setCopied]       = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const link = `${ORIGIN}/shared/artist/${token}`;

  const copy = () => {
    navigator.clipboard.writeText(link).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    });
  };

  const regen = async () => {
    if (!confirm('Yeni link oluşturulacak. Eski link artık çalışmayacak. Devam edilsin mi?')) return;
    setRegenerating(true);
    await onRegenerate();
    setRegenerating(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
      }}
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
        style={{
          background: '#fff', width: '100%', maxWidth: 480,
          boxShadow: '0 20px 60px rgba(0,0,0,0.18)',
          fontFamily: PX,
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ padding: '22px 28px 18px', borderBottom: '1px solid #f0f0f0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p style={{ fontFamily: PX, fontSize: 13, fontWeight: 400, color: '#111', margin: 0 }}>
              {artistName}
            </p>
            <p style={{ fontFamily: PX, fontSize: 9, letterSpacing: '0.25em',
              textTransform: 'uppercase', color: '#bbb', margin: '4px 0 0' }}>
              Private Portfolio Link
            </p>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 20, color: '#ccc', lineHeight: 1, padding: 4,
          }}>×</button>
        </div>

        {/* Body */}
        <div style={{ padding: '24px 28px 28px' }}>
          {/* Green info */}
          <div style={{
            background: '#f0fdf4', border: '1px solid #bbf7d0',
            padding: '10px 14px', marginBottom: 20, display: 'flex', gap: 10,
          }}>
            <span style={{ color: '#16a34a', fontSize: 13 }}>🔒</span>
            <p style={{ fontFamily: PX, fontSize: 10, color: '#15803d', margin: 0, lineHeight: 1.6 }}>
              Bu link, sanatçının sayfası gizli olsa bile çalışır. Yalnızca müşterilerinizle paylaşın.
            </p>
          </div>

          {/* URL row */}
          <div style={{ marginBottom: 16 }}>
            <p style={{ fontFamily: PX, fontSize: 8, letterSpacing: '0.3em',
              textTransform: 'uppercase', color: '#bbb', margin: '0 0 8px' }}>Paylaşım Linki</p>
            <div style={{ display: 'flex', border: '1px solid #e8e8e8', overflow: 'hidden' }}>
              <div style={{
                flex: 1, padding: '10px 12px',
                fontFamily: 'monospace', fontSize: 11, color: '#666',
                background: '#fafafa', overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {link}
              </div>
              <button onClick={copy} style={{
                padding: '10px 16px', border: 'none', borderLeft: '1px solid #e8e8e8',
                background: copied ? '#f0fdf4' : '#fff',
                color: copied ? '#16a34a' : '#555',
                fontFamily: PX, fontSize: 10, letterSpacing: '0.15em',
                cursor: 'pointer', whiteSpace: 'nowrap', transition: 'all 0.2s',
                fontWeight: 400,
              }}>
                {copied ? '✓ Kopyalandı' : 'Kopyala'}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <a href={link} target="_blank" rel="noopener noreferrer" style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '10px 0', border: '1px solid #e0e0e0',
              fontFamily: PX, fontSize: 9, letterSpacing: '0.2em',
              textTransform: 'uppercase', color: '#555', textDecoration: 'none',
              transition: 'background 0.15s',
            }}>
              ↗ Önizle
            </a>
            <button onClick={regen} disabled={regenerating} style={{
              padding: '10px 0', border: '1px solid #fde68a',
              background: regenerating ? '#fef9c3' : '#fffbeb',
              fontFamily: PX, fontSize: 9, letterSpacing: '0.2em',
              textTransform: 'uppercase', color: '#b45309',
              cursor: regenerating ? 'default' : 'pointer', transition: 'all 0.15s',
            }}>
              {regenerating ? '…' : '↻ Yeni Link'}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Private link button ──────────────────────────────────
function PrivateLinkRow({ token, artistName, onRegenerate }: {
  token: string; artistName: string; onRegenerate: () => void;
}) {
  const [open, setOpen] = useState(false);

  const handleRegen = async () => {
    onRegenerate();
    // Give a small delay so the parent state updates, then the modal token refreshes
    await new Promise(r => setTimeout(r, 600));
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        style={{
          background: '#f5f5f5', border: '1px solid #e0e0e0',
          padding: '7px 14px', cursor: 'pointer',
          fontFamily: PX, fontSize: 9, letterSpacing: '0.2em',
          textTransform: 'uppercase', color: '#555',
          transition: 'all 0.15s', display: 'inline-flex', alignItems: 'center', gap: 6,
        }}
        onMouseEnter={e => { e.currentTarget.style.background = '#111'; e.currentTarget.style.color = '#fff'; }}
        onMouseLeave={e => { e.currentTarget.style.background = '#f5f5f5'; e.currentTarget.style.color = '#555'; }}
      >
        🔗 Link
      </button>
      <AnimatePresence>
        {open && (
          <PrivateLinkModal
            token={token}
            artistName={artistName}
            onClose={() => setOpen(false)}
            onRegenerate={handleRegen}
          />
        )}
      </AnimatePresence>
    </>
  );
}

// ─── Artwork draft card ───────────────────────────────────
function ArtworkCard({
  aw, index, onUpdate, onRemove,
}: {
  aw: ArtworkDraft; index: number;
  onUpdate: (uid: string, patch: Partial<ArtworkDraft>) => void;
  onRemove: (uid: string) => void;
}) {
  const up = (k: keyof ArtworkDraft) => (v: string) => onUpdate(aw.uid, { [k]: v } as any);

  return (
    <div style={{
      border: '1px solid #e8e8e8', background: '#fff',
      display: 'grid', gridTemplateColumns: '120px 1fr',
      gap: 0, position: 'relative',
    }}>
      {/* Thumbnail */}
      <div style={{ background: '#f0f0f0', overflow: 'hidden', minHeight: 120, position: 'relative' }}>
        {aw.isVideo || aw.video_url ? (
          <>
            <video
              src={aw.preview || aw.video_url}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              muted playsInline preload="metadata"
            />
            <div style={{
              position: 'absolute', inset: 0, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              background: 'rgba(0,0,0,0.25)',
            }}>
              <span style={{ fontSize: 22, lineHeight: 1 }}>▶</span>
            </div>
          </>
        ) : (
          <img src={aw.preview} alt=""
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
        )}
      </div>

      {/* Fields */}
      <div style={{ padding: '12px 14px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 12px' }}>
          <Field label="Title" value={aw.title} onChange={up('title')} required />
          <Field label="Year"  value={aw.year}  onChange={up('year')} />
          <Field label="Medium" value={aw.medium} onChange={up('medium')} />
          <Field label="Dimensions" value={aw.dimensions} onChange={up('dimensions')} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
          <Toggle
            on={aw.status === 'Public'}
            onToggle={() => onUpdate(aw.uid, { status: aw.status === 'Public' ? 'Private' : 'Public' })}
            labelOn="Public" labelOff="Private"
            colorOn="#2d7a2d"
          />
          <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb', letterSpacing: '0.2em' }}>
            #{index + 1}
          </span>
        </div>
      </div>

      {/* Remove */}
      <button onClick={() => onRemove(aw.uid)} style={{
        position: 'absolute', top: 6, right: 8,
        background: 'none', border: 'none', cursor: 'pointer',
        fontFamily: PX, fontSize: 16, color: '#ccc', lineHeight: 1,
        transition: 'color 0.2s',
      }}
        onMouseEnter={e => (e.currentTarget.style.color = '#c00')}
        onMouseLeave={e => (e.currentTarget.style.color = '#ccc')}
      >
        ×
      </button>
    </div>
  );
}

// ─── Drop zone ────────────────────────────────────────────
function DropZone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const ACCEPTED = 'image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm,video/quicktime';

  const handle = async (files: FileList | null) => {
    if (!files) return;
    onFiles(Array.from(files).filter(f =>
      f.type.startsWith('image/') || f.type.startsWith('video/')
    ));
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault(); setDrag(false);
    handle(e.dataTransfer.files);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      style={{
        border: `2px dashed ${drag ? '#111' : '#d8d8d8'}`,
        background: drag ? '#f8f8f8' : '#fdfdfd',
        padding: '36px 24px', textAlign: 'center',
        cursor: 'pointer', transition: 'all 0.2s', marginBottom: 20,
      }}
    >
      <div style={{ fontFamily: PX, fontSize: 9, letterSpacing: '0.35em',
        textTransform: 'uppercase', color: '#bbb', lineHeight: 2.2 }}>
        <div style={{ fontSize: 28, marginBottom: 4, color: '#ccc' }}>+</div>
        Görsel veya Video sürükleyin
        <br />
        <span style={{ color: '#d8d8d8' }}>ya da tıklayın — JPG, PNG, WEBP, MP4, WEBM</span>
        <br />
        <span style={{ color: '#ddd', fontSize: 8 }}>Birden fazla dosya desteklenir</span>
      </div>
      <input ref={inputRef} type="file" accept={ACCEPTED} multiple style={{ display: 'none' }}
        onChange={e => handle(e.target.files)} />
    </div>
  );
}

// ─── Add / Edit Drawer ────────────────────────────────────
const EMPTY_FORM = () => ({
  name: '', bio: '', medium: 'Oil on Canvas',
  is_public: 0, is_featured: 0,
});

function ArtistDrawer({
  artist, onClose, onSaved,
}: {
  artist: Artist | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!artist;
  const [form, setForm]         = useState(artist ? {
    name: artist.name, bio: artist.bio, medium: artist.medium || '',
    is_public: artist.is_public, is_featured: artist.is_featured,
  } : EMPTY_FORM());
  const [artistImg, setArtistImg]   = useState<{ file: File; preview: string } | null>(null);
  const [artworks, setArtworks]     = useState<ArtworkDraft[]>([]);
  const [deletedIds, setDeletedIds] = useState<number[]>([]);
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState('');
  const artistImgRef = useRef<HTMLInputElement>(null);

  // Edit: mevcut eserleri yükle
  useEffect(() => {
    if (!artist) return;
    apiFetch(`/api/artists/${artist.id}`)
      .then(data => {
        const existing: ArtworkDraft[] = (data.artworks || []).map((aw: any) => ({
          uid: uid(), id: aw.id,
          file: null,
          preview: aw.image_url || aw.video_url || '',
          title: aw.title || '', year: aw.year || '',
          medium: aw.medium || '', dimensions: aw.dimensions || '',
          status: aw.status === 'Public' ? 'Public' : 'Private',
          video_url: aw.video_url || '',
          isVideo: !!(aw.video_url && !aw.image_url),
        }));
        setArtworks(existing);
      });
  }, [artist]);

  const handleArtistImg = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = ev => setArtistImg({ file: f, preview: ev.target!.result as string });
    reader.readAsDataURL(f);
  };

  const handleDroppedFiles = useCallback(async (files: File[]) => {
    const newAws: ArtworkDraft[] = await Promise.all(
      files.map(async f => {
        const isVid = f.type.startsWith('video/');
        const preview = isVid ? URL.createObjectURL(f) : await fileToPreview(f);
        return {
          uid: uid(), file: f, preview,
          title: f.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' '),
          year: String(new Date().getFullYear()),
          medium: '', dimensions: '', status: 'Private' as const,
          isVideo: isVid,
        };
      })
    );
    setArtworks(prev => [...prev, ...newAws]);
  }, []);

  const updateArtwork = (id: string, patch: Partial<ArtworkDraft>) =>
    setArtworks(prev => prev.map(a => a.uid === id ? { ...a, ...patch } : a));

  const removeArtwork = (id: string) => {
    const aw = artworks.find(a => a.uid === id);
    if (aw?.id) setDeletedIds(prev => [...prev, aw.id!]);
    setArtworks(prev => prev.filter(a => a.uid !== id));
  };

  const handleSave = async () => {
    if (!form.name.trim()) { setError('Artist name is required.'); return; }
    setSaving(true); setError('');

    try {
      const fd = new FormData();
      fd.append('id',         artist?.id || '');
      fd.append('name',       form.name.trim());
      fd.append('bio',        form.bio);
      fd.append('medium',     form.medium);
      fd.append('is_public',  String(form.is_public));
      fd.append('is_featured',String(form.is_featured));
      fd.append('deletedArtworks', JSON.stringify(deletedIds));

      if (artistImg?.file) fd.append('artist_image', artistImg.file);

      // Eser meta verisi (JSON) ve dosyalar
      const meta = artworks.map(a => ({
        id: a.id || null,
        title: a.title, year: a.year,
        medium: a.medium, dimensions: a.dimensions,
        status: a.status,
      }));
      fd.append('artworks', JSON.stringify(meta));

      artworks.forEach((a, i) => {
        if (a.file && !a.isVideo) fd.append(`artwork_image_${i}`, a.file);
        if (a.file && a.isVideo)  fd.append(`artwork_video_${i}`, a.file);
      });

      await apiFetch('/api/artists/full', { method: 'POST', body: fd });
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex' }}>
      {/* Backdrop */}
      <div onClick={onClose}
        style={{ flex: 1, background: 'rgba(0,0,0,0.42)', cursor: 'pointer' }} />

      {/* Panel */}
      <motion.div
        initial={{ x: 640 }} animate={{ x: 0 }} exit={{ x: 640 }}
        transition={{ type: 'spring', stiffness: 300, damping: 32 }}
        style={{
          width: 640, height: '100%', overflowY: 'auto',
          background: '#fafafa', display: 'flex', flexDirection: 'column',
          boxShadow: '-24px 0 80px rgba(0,0,0,0.14)',
        }}
      >
        {/* Header */}
        <div style={{
          background: '#fff', padding: '28px 32px',
          borderBottom: '1px solid #eee', flexShrink: 0,
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        }}>
          <div>
            <p style={{ ...LABEL, margin: '0 0 6px' }}>
              {isEdit ? 'Edit Artist' : 'New Artist'}
            </p>
            <h2 style={{ fontFamily: PX, fontSize: 18, fontWeight: 300,
              color: '#111', letterSpacing: '0.08em',
              textTransform: 'uppercase', margin: 0 }}>
              {isEdit ? form.name : 'Add Artist'}
            </h2>
          </div>
          <button onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 22, color: '#bbb', lineHeight: 1, padding: 4 }}>
            ×
          </button>
        </div>

        <div style={{ padding: '24px 32px', flex: 1 }}>
          {/* ── Artist info ── */}
          <section style={{ marginBottom: 28 }}>
            <p style={{ ...LABEL, marginBottom: 16, borderBottom: '1px solid #eee', paddingBottom: 8 }}>
              Artist Information
            </p>

            {/* Artist photo */}
            <div style={{ marginBottom: 16 }}>
              <label style={LABEL}>Profile Photo</label>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <div
                  onClick={() => artistImgRef.current?.click()}
                  style={{
                    width: 80, height: 80, background: '#eee',
                    overflow: 'hidden', cursor: 'pointer', flexShrink: 0,
                    border: '1px dashed #ccc',
                  }}>
                  {(artistImg?.preview || artist?.image_url) && (
                    <img src={artistImg?.preview || artist!.image_url!} alt=""
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  )}
                </div>
                <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb',
                  letterSpacing: '0.28em', textTransform: 'uppercase' }}>
                  Click to change
                </span>
                <input ref={artistImgRef} type="file" accept="image/*"
                  style={{ display: 'none' }} onChange={handleArtistImg} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <div style={{ gridColumn: '1 / -1' }}>
                <Field label="Full Name" value={form.name}
                  onChange={v => setForm(f => ({ ...f, name: v }))} required />
              </div>
              <Field label="Primary Medium" value={form.medium}
                onChange={v => setForm(f => ({ ...f, medium: v }))}
                as="select"
                options={['Oil on Canvas','Photography','Mixed Media','Sculpture',
                  'Installation','Drawing','Printmaking','Watercolour',
                  'Digital','Ceramics','Textile','Video Art','Collage','Other']} />
              <div />
              <div style={{ gridColumn: '1 / -1' }}>
                <Field label="Biography" value={form.bio}
                  onChange={v => setForm(f => ({ ...f, bio: v }))}
                  as="textarea" rows={3} />
              </div>
            </div>

            {/* Publish toggles */}
            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              <Toggle
                on={!!form.is_public}
                onToggle={() => setForm(f => ({ ...f, is_public: f.is_public ? 0 : 1 }))}
                labelOn="Public — Artists Page"
                labelOff="Hidden — Artists Page"
                colorOn="#111"
              />
              <Toggle
                on={!!form.is_featured}
                onToggle={() => setForm(f => ({ ...f, is_featured: f.is_featured ? 0 : 1 }))}
                labelOn="★ Featured — Home"
                labelOff="☆ Not Featured"
                colorOn="#b5860d"
              />
            </div>
          </section>

          {/* ── Artworks ── */}
          <section>
            <p style={{ ...LABEL, marginBottom: 16, borderBottom: '1px solid #eee', paddingBottom: 8 }}>
              Artworks ({artworks.length})
            </p>

            <DropZone onFiles={handleDroppedFiles} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <AnimatePresence initial={false}>
                {artworks.map((aw, i) => (
                  <motion.div key={aw.uid}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0, overflow: 'hidden' }}
                    transition={{ duration: 0.22 }}>
                    <ArtworkCard
                      aw={aw} index={i}
                      onUpdate={updateArtwork}
                      onRemove={removeArtwork}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div style={{
          background: '#fff', padding: '18px 32px',
          borderTop: '1px solid #eee', flexShrink: 0,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          {error && (
            <span style={{ fontFamily: PX, fontSize: 10, color: '#c00',
              letterSpacing: '0.1em', flex: 1 }}>
              {error}
            </span>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
            <button onClick={onClose} style={BTN('transparent', '#999', '#ddd')}>
              Cancel
            </button>
            <button onClick={handleSave} disabled={saving} style={{
              ...BTN(saving ? '#999' : '#111'),
              minWidth: 120,
            }}>
              {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Artist'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

// ─── Confirm modal ───────────────────────────────────────
function Confirm({ msg, onOk, onCancel }: {
  msg: string; onOk: () => void; onCancel: () => void;
}) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        style={{ background: '#fff', padding: '40px 44px', maxWidth: 400,
          width: '90%', boxShadow: '0 24px 60px rgba(0,0,0,0.15)' }}>
        <p style={{ fontFamily: PX, fontSize: 13, fontWeight: 300, color: '#111',
          lineHeight: 1.7, marginBottom: 28 }}>{msg}</p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onOk} style={BTN()}>Confirm</button>
          <button onClick={onCancel} style={BTN('transparent', '#111', '#ccc')}>Cancel</button>
        </div>
      </motion.div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────
export default function ArtistManagement() {
  const [artists, setArtists]       = useState<Artist[]>([]);
  const [loading, setLoading]       = useState(true);
  const [search, setSearch]         = useState('');
  const [drawerArtist, setDrawer]   = useState<Artist | 'new' | null>(null);
  const [deleteTarget, setDelTarget]= useState<Artist | null>(null);
  const [toast, setToast]           = useState('');

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch('/api/artists?limit=200&sort=name');
      setArtists(Array.isArray(data) ? data : (data.data ?? []));
    } catch { /* silent */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const toggle = async (
    id: string,
    field: 'is_public' | 'is_featured',
    cur: number,
  ) => {
    const artist = artists.find(a => a.id === id);
    if (!artist) return;
    const payload = {
      is_public:   field === 'is_public'   ? (cur ? 0 : 1) : artist.is_public,
      is_featured: field === 'is_featured' ? (cur ? 0 : 1) : artist.is_featured,
    };
    setArtists(prev => prev.map(a => a.id === id ? { ...a, ...payload } : a));
    await apiFetch(`/api/artists/${id}/publish`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  };

  const regenerateToken = async (id: string) => {
    try {
      const res = await apiFetch(`/api/artists/${id}/regenerate-token`, { method: 'POST' });
      setArtists(prev =>
        prev.map(a => a.id === id ? { ...a, private_token: res.private_token } : a)
      );
      showToast('New private link generated');
    } catch { showToast('Failed to regenerate link'); }
  };

  const doDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiFetch(`/api/artists/${deleteTarget.id}`, { method: 'DELETE' });
      setArtists(prev => prev.filter(a => a.id !== deleteTarget.id));
      showToast(`"${deleteTarget.name}" deleted`);
    } catch { showToast('Delete failed'); }
    setDelTarget(null);
  };

  const filtered = artists.filter(a =>
    !search ||
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    (a.medium || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ fontFamily: PX, minHeight: '100vh', background: '#f7f7f7' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&display=swap');
        * { box-sizing: border-box; }
        button:focus, input:focus, select:focus, textarea:focus { outline: none; }
        input:focus, select:focus, textarea:focus {
          border-color: #111 !important; background: #fff !important;
        }
        .row:hover { background: #fafafa !important; }
        .act { opacity: 0; transition: opacity 0.18s; }
        .row:hover .act { opacity: 1; }
      `}</style>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '44px 32px 100px' }}>

        {/* Page header */}
        <div style={{
          display: 'flex', alignItems: 'flex-end',
          justifyContent: 'space-between', marginBottom: 36,
          paddingBottom: 22, borderBottom: '1px solid #e0e0e0',
        }}>
          <div>
            <p style={{ ...LABEL, margin: '0 0 8px' }}>Admin Panel</p>
            <h1 style={{ fontFamily: PX, fontSize: 28, fontWeight: 300,
              color: '#111', letterSpacing: '0.08em',
              textTransform: 'uppercase', margin: 0 }}>
              Artists & Links
            </h1>
            <p style={{ fontFamily: PX, fontSize: 11, fontWeight: 300,
              color: '#aaa', letterSpacing: '0.08em', margin: '8px 0 0',
              lineHeight: 1.6 }}>
              Manage artists, upload artworks, control what's visible on the public site,
              and share private portfolio links.
            </p>
          </div>
          <button
            onClick={() => setDrawer('new')}
            style={BTN()}
          >
            + Add Artist
          </button>
        </div>

        {/* Toolbar */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: '1 1 260px' }}>
            <span style={{ position: 'absolute', left: 10, top: '50%',
              transform: 'translateY(-50%)', color: '#ccc', fontSize: 14 }}>⌕</span>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search artists…"
              style={{ ...INPUT, paddingLeft: 30 }} />
          </div>
          <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb',
            letterSpacing: '0.28em', textTransform: 'uppercase',
            alignSelf: 'center', marginLeft: 'auto' }}>
            {filtered.length} artist{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* ── Artist rows ── */}
        <div style={{ background: '#fff', border: '1px solid #e8e8e8' }}>

          {/* Table head */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '52px 1fr 140px 140px 1fr 200px',
            padding: '10px 18px', borderBottom: '1px solid #eeee',
          }}>
            {['', 'Artist', 'Artists Page', 'Home Featured',
              'Private Link', 'Actions'].map(h => (
              <span key={h} style={{ fontFamily: PX, fontSize: 8,
                letterSpacing: '0.35em', textTransform: 'uppercase', color: '#ccc' }}>
                {h}
              </span>
            ))}
          </div>

          {loading && (
            <div style={{ padding: '48px', textAlign: 'center',
              fontFamily: PX, fontSize: 10, letterSpacing: '0.3em', color: '#ccc',
              textTransform: 'uppercase' }}>
              Loading…
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center',
              fontFamily: PX, fontSize: 10, letterSpacing: '0.3em', color: '#ccc',
              textTransform: 'uppercase' }}>
              No artists — click "+ Add Artist" to begin
            </div>
          )}

          <AnimatePresence initial={false}>
            {filtered.map(artist => (
              <motion.div key={artist.id}
                layout
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="row"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '52px 1fr 140px 140px 1fr 200px',
                  padding: '14px 18px', borderBottom: '1px solid #f2f2f2',
                  background: '#fff', transition: 'background 0.15s',
                  alignItems: 'center',
                }}
              >
                {/* Thumb */}
                <div style={{ width: 40, height: 48, overflow: 'hidden', background: '#eee' }}>
                  {artist.image_url && (
                    <img src={artist.image_url} alt={artist.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  )}
                </div>

                {/* Name */}
                <div>
                  <p style={{ fontFamily: PX, fontSize: 13, fontWeight: 400,
                    color: '#111', margin: '0 0 2px', letterSpacing: '0.04em' }}>
                    {artist.name}
                  </p>
                  <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300,
                    color: '#bbb', margin: 0, letterSpacing: '0.18em',
                    textTransform: 'uppercase' }}>
                    {artist.medium || '—'} · {artist.artworks_count ?? 0} works
                  </p>
                </div>

                {/* Public toggle */}
                <div>
                  <Toggle
                    on={!!artist.is_public}
                    onToggle={() => toggle(artist.id, 'is_public', artist.is_public)}
                    labelOn="Visible" labelOff="Hidden"
                  />
                </div>

                {/* Featured toggle */}
                <div>
                  <Toggle
                    on={!!artist.is_featured}
                    onToggle={() => toggle(artist.id, 'is_featured', artist.is_featured)}
                    labelOn="★ Featured" labelOff="☆ Not Featured"
                    colorOn="#b5860d"
                  />
                </div>

                {/* Private link */}
                <div style={{ overflow: 'hidden' }}>
                  {artist.private_token ? (
                    <PrivateLinkRow
                      token={artist.private_token}
                      artistName={artist.name}
                      onRegenerate={() => regenerateToken(artist.id)}
                    />
                  ) : (
                    <span style={{ fontFamily: PX, fontSize: 9, color: '#ddd',
                      letterSpacing: '0.2em' }}>—</span>
                  )}
                </div>

                {/* Actions */}
                <div className="act" style={{ display: 'flex', gap: 8,
                  justifyContent: 'flex-end' }}>
                  <button onClick={() => setDrawer(artist)}
                    style={BTN('transparent', '#888', '#ddd')}>
                    Edit
                  </button>
                  <button onClick={() => setDelTarget(artist)}
                    style={BTN('transparent', '#c00', '#eecece')}>
                    Delete
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Drawer ── */}
      <AnimatePresence>
        {drawerArtist && (
          <ArtistDrawer
            artist={drawerArtist === 'new' ? null : drawerArtist as Artist}
            onClose={() => setDrawer(null)}
            onSaved={() => { load(); showToast('Saved successfully'); }}
          />
        )}
      </AnimatePresence>

      {/* ── Delete confirm ── */}
      <AnimatePresence>
        {deleteTarget && (
          <Confirm
            msg={`Delete "${deleteTarget.name}"? All their artworks will also be removed. This cannot be undone.`}
            onOk={doDelete}
            onCancel={() => setDelTarget(null)}
          />
        )}
      </AnimatePresence>

      {/* ── Toast ── */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            style={{
              position: 'fixed', bottom: 28, right: 28,
              background: '#111', color: '#fff',
              fontFamily: PX, fontSize: 10, fontWeight: 300,
              letterSpacing: '0.25em', textTransform: 'uppercase',
              padding: '13px 24px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.18)',
              zIndex: 9999,
            }}
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}