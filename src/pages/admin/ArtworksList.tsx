/**
 * ArtworksList.tsx — Admin: Artworks
 * Tüm eserleri listeler, sanatçıya göre filtreler,
 * status toggle ve silme işlemleri yapılabilir.
 */

import { apiFetch } from '../../utils/api';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

const PX = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";

const BTN = (bg = '#111', col = '#fff', bd = 'transparent'): React.CSSProperties => ({
  fontFamily: PX, fontSize: 9, fontWeight: 400,
  letterSpacing: '0.28em', textTransform: 'uppercase' as const,
  background: bg, color: col, border: `1px solid ${bd || bg}`,
  padding: '7px 16px', cursor: 'pointer', transition: 'all 0.2s',
});

const LABEL: React.CSSProperties = {
  fontFamily: PX, fontSize: 8, fontWeight: 400,
  letterSpacing: '0.35em', textTransform: 'uppercase' as const, color: '#ccc',
};

interface Artwork {
  id: number;
  title: string;
  artist: string;
  artist_id: string;
  year: string;
  medium: string;
  dimensions: string;
  status: string;
  image_url: string | null;
  created_at: string;
}

interface Artist {
  id: string;
  name: string;
}

export default function ArtworksList() {
  const [artworks, setArtworks] = useState<Artwork[]>([]);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterArtist, setFilterArtist] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<Artwork | null>(null);
  const [toast, setToast] = useState('');
  const [lightbox, setLightbox] = useState<Artwork | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [awRes, arRes] = await Promise.all([
        apiFetch('/api/artworks'),
        apiFetch('/api/artists?limit=200&sort=name'),
      ]);
      const awData = await awRes.json();
      const arData = await arRes.json();
      setArtworks(Array.isArray(awData) ? awData : (awData.data ?? []));
      const arList = Array.isArray(arData) ? arData : (arData.data ?? []);
      setArtists(arList);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const toggleStatus = async (aw: Artwork) => {
    const newStatus = aw.status === 'Public' ? 'Private' : 'Public';
    setArtworks(prev => prev.map(a => a.id === aw.id ? { ...a, status: newStatus } : a));
    try {
      await fetch(`/api/artworks/${aw.id}/publish`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch {
      // revert on error
      setArtworks(prev => prev.map(a => a.id === aw.id ? { ...a, status: aw.status } : a));
      showToast('Failed to update status');
    }
  };

  const doDelete = async () => {
    if (!deleteTarget) return;
    try {
      const res = await fetch(`/api/artworks/${deleteTarget.id}`, { method: 'DELETE' });
      if (res.ok) {
        setArtworks(prev => prev.filter(a => a.id !== deleteTarget.id));
        showToast(`"${deleteTarget.title}" deleted`);
      } else {
        showToast('Delete failed');
      }
    } catch {
      showToast('Delete failed');
    }
    setDeleteTarget(null);
  };

  const filtered = artworks.filter(aw => {
    const q = search.toLowerCase();
    const matchSearch = !q ||
      aw.title.toLowerCase().includes(q) ||
      aw.artist.toLowerCase().includes(q) ||
      (aw.medium || '').toLowerCase().includes(q);
    const matchArtist = !filterArtist || aw.artist_id === filterArtist;
    const matchStatus = !filterStatus || aw.status === filterStatus;
    return matchSearch && matchArtist && matchStatus;
  });

  const publicCount = artworks.filter(a => a.status === 'Public').length;

  return (
    <div style={{ fontFamily: PX, minHeight: '100vh', background: '#f7f7f7' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&display=swap');
        * { box-sizing: border-box; }
        button:focus, input:focus, select:focus { outline: none; }
        input:focus, select:focus { border-color: #111 !important; background: #fff !important; }
        .aw-row:hover { background: #fafafa !important; }
        .aw-act { opacity: 0; transition: opacity 0.18s; }
        .aw-row:hover .aw-act { opacity: 1; }
      `}</style>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '44px 32px 100px' }}>

        {/* Header */}
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
              Artworks
            </h1>
            <p style={{ fontFamily: PX, fontSize: 11, fontWeight: 300,
              color: '#aaa', letterSpacing: '0.08em', margin: '8px 0 0', lineHeight: 1.6 }}>
              {artworks.length} total · {publicCount} public
            </p>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 24, flexWrap: 'wrap' }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: '1 1 220px' }}>
            <span style={{ position: 'absolute', left: 10, top: '50%',
              transform: 'translateY(-50%)', color: '#ccc', fontSize: 14 }}>⌕</span>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search title, artist, medium…"
              style={{
                width: '100%', fontFamily: PX, fontSize: 12, fontWeight: 300,
                color: '#111', background: '#fff', border: '1px solid #e0e0e0',
                padding: '9px 11px 9px 30px',
              }} />
          </div>

          {/* Artist filter */}
          <select value={filterArtist} onChange={e => setFilterArtist(e.target.value)}
            style={{
              fontFamily: PX, fontSize: 11, fontWeight: 300,
              color: filterArtist ? '#111' : '#bbb', background: '#fff',
              border: '1px solid #e0e0e0', padding: '9px 11px', minWidth: 160,
            }}>
            <option value="">All Artists</option>
            {artists.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>

          {/* Status filter */}
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            style={{
              fontFamily: PX, fontSize: 11, fontWeight: 300,
              color: filterStatus ? '#111' : '#bbb', background: '#fff',
              border: '1px solid #e0e0e0', padding: '9px 11px', minWidth: 130,
            }}>
            <option value="">All Statuses</option>
            <option value="Public">Public</option>
            <option value="Private">Private</option>
          </select>

          <span style={{ fontFamily: PX, fontSize: 9, color: '#bbb',
            letterSpacing: '0.28em', textTransform: 'uppercase',
            alignSelf: 'center', marginLeft: 'auto' }}>
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Table */}
        <div style={{ background: '#fff', border: '1px solid #e8e8e8' }}>
          {/* Head */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '64px 1fr 160px 100px 100px 140px',
            padding: '10px 18px', borderBottom: '1px solid #eee',
          }}>
            {['', 'Title / Artist', 'Medium', 'Year', 'Status', 'Actions'].map(h => (
              <span key={h} style={{ ...LABEL }}>{h}</span>
            ))}
          </div>

          {loading && (
            <div style={{ padding: 48, textAlign: 'center',
              fontFamily: PX, fontSize: 10, letterSpacing: '0.3em', color: '#ccc',
              textTransform: 'uppercase' }}>
              Loading…
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div style={{ padding: 48, textAlign: 'center',
              fontFamily: PX, fontSize: 10, letterSpacing: '0.3em', color: '#ccc',
              textTransform: 'uppercase' }}>
              No artworks found
            </div>
          )}

          <AnimatePresence initial={false}>
            {filtered.map(aw => (
              <motion.div
                key={aw.id}
                layout
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="aw-row"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '64px 1fr 160px 100px 100px 140px',
                  padding: '12px 18px', borderBottom: '1px solid #f2f2f2',
                  background: '#fff', transition: 'background 0.15s',
                  alignItems: 'center',
                }}
              >
                {/* Thumb */}
                <div
                  onClick={() => aw.image_url && setLightbox(aw)}
                  style={{
                    width: 48, height: 56, overflow: 'hidden',
                    background: '#eee', cursor: aw.image_url ? 'zoom-in' : 'default',
                    flexShrink: 0,
                  }}>
                  {aw.image_url && (
                    <img src={aw.image_url} alt={aw.title}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  )}
                </div>

                {/* Title / Artist */}
                <div style={{ paddingLeft: 4 }}>
                  <p style={{ fontFamily: PX, fontSize: 12, fontWeight: 400,
                    color: '#111', margin: '0 0 3px', letterSpacing: '0.03em' }}>
                    {aw.title}
                  </p>
                  <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300,
                    color: '#bbb', margin: 0, letterSpacing: '0.18em',
                    textTransform: 'uppercase' }}>
                    {aw.artist || '—'}
                  </p>
                </div>

                {/* Medium */}
                <p style={{ fontFamily: PX, fontSize: 10, fontWeight: 300,
                  color: '#888', margin: 0, letterSpacing: '0.1em' }}>
                  {aw.medium || '—'}
                </p>

                {/* Year */}
                <p style={{ fontFamily: PX, fontSize: 10, fontWeight: 300,
                  color: '#aaa', margin: 0, letterSpacing: '0.12em' }}>
                  {aw.year || '—'}
                </p>

                {/* Status toggle */}
                <div>
                  <button
                    onClick={() => toggleStatus(aw)}
                    style={{
                      ...BTN(
                        aw.status === 'Public' ? '#2d7a2d' : 'transparent',
                        aw.status === 'Public' ? '#fff' : '#bbb',
                        aw.status === 'Public' ? '#2d7a2d' : '#ddd',
                      ),
                      fontSize: 8, padding: '5px 10px',
                    }}>
                    {aw.status === 'Public' ? '● Public' : '○ Private'}
                  </button>
                </div>

                {/* Actions */}
                <div className="aw-act" style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => setDeleteTarget(aw)}
                    style={BTN('transparent', '#c00', '#eecece')}>
                    Delete
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Lightbox */}
      <AnimatePresence>
        {lightbox && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setLightbox(null)}
            style={{
              position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
              zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'zoom-out', padding: 32,
            }}
          >
            <motion.div
              initial={{ scale: 0.92 }} animate={{ scale: 1 }} exit={{ scale: 0.92 }}
              onClick={e => e.stopPropagation()}
              style={{ maxWidth: 800, width: '100%', cursor: 'default' }}
            >
              <img src={lightbox.image_url!} alt={lightbox.title}
                style={{ width: '100%', maxHeight: '80vh', objectFit: 'contain', display: 'block' }} />
              <div style={{ padding: '14px 4px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                  <p style={{ fontFamily: PX, fontSize: 13, color: '#fff', margin: '0 0 4px',
                    letterSpacing: '0.06em' }}>{lightbox.title}</p>
                  <p style={{ fontFamily: PX, fontSize: 10, color: 'rgba(255,255,255,0.5)',
                    margin: 0, letterSpacing: '0.18em', textTransform: 'uppercase' }}>
                    {lightbox.artist} · {lightbox.year} · {lightbox.medium}
                  </p>
                </div>
                <button onClick={() => setLightbox(null)}
                  style={{ ...BTN('transparent', 'rgba(255,255,255,0.5)', 'rgba(255,255,255,0.2)'),
                    fontSize: 8 }}>
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete confirm */}
      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
              zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <motion.div initial={{ y: 12 }} animate={{ y: 0 }}
              style={{ background: '#fff', padding: '40px 44px', maxWidth: 400,
                width: '90%', boxShadow: '0 24px 60px rgba(0,0,0,0.15)' }}>
              <p style={{ fontFamily: PX, fontSize: 13, fontWeight: 300, color: '#111',
                lineHeight: 1.7, marginBottom: 28 }}>
                Delete <strong>"{deleteTarget.title}"</strong>? This cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button onClick={doDelete} style={BTN('#c00')}>Delete</button>
                <button onClick={() => setDeleteTarget(null)}
                  style={BTN('transparent', '#111', '#ccc')}>Cancel</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast */}
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
            }}>
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
