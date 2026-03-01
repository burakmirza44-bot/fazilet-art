/**
 * AdminViewingRooms.tsx
 * Viewing Room kürasyon: hangi eserler görüntüleme odasında gösterilecek?
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MonitorPlay, ImageIcon, Check, ExternalLink } from 'lucide-react';

const PX = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const BTN = (bg = '#111', col = '#fff', bd = 'transparent'): React.CSSProperties => ({
  fontFamily: PX, fontSize: 9, fontWeight: 400,
  letterSpacing: '0.28em', textTransform: 'uppercase' as const,
  background: bg, color: col, border: `1px solid ${bd || bg}`,
  padding: '8px 18px', cursor: 'pointer', transition: 'all 0.2s',
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
  status: string;
  viewing_room: number;
  image_url: string | null;
}

interface Artist {
  id: string;
  name: string;
}

export default function AdminViewingRooms() {
  const [artworks,     setArtworks]     = useState<Artwork[]>([]);
  const [artists,      setArtists]      = useState<Artist[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [search,       setSearch]       = useState('');
  const [filterArtist, setFilterArtist] = useState('');
  const [toast,        setToast]        = useState('');
  const [saving,       setSaving]       = useState<Set<number>>(new Set());

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = () => {
    setLoading(true);
    Promise.all([
      fetch('/api/artworks').then(r => r.json()),
      fetch('/api/artists?limit=200&sort=name').then(r => r.json()),
    ]).then(([aw, ar]) => {
      const awList = Array.isArray(aw) ? aw : (aw.data ?? []);
      const arList = Array.isArray(ar) ? ar : (ar.data ?? []);
      setArtworks(awList);
      setArtists(arList);
    }).catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const toggleViewingRoom = async (aw: Artwork) => {
    const next = aw.viewing_room ? 0 : 1;
    setSaving(prev => new Set(prev).add(aw.id));
    setArtworks(prev => prev.map(a => a.id === aw.id ? { ...a, viewing_room: next } : a));
    try {
      const res = await fetch(`/api/artworks/${aw.id}/viewing-room`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ viewing_room: next }),
      });
      if (!res.ok) throw new Error();
      showToast(next ? `"${aw.title}" added to Viewing Room` : `"${aw.title}" removed`);
    } catch {
      setArtworks(prev => prev.map(a => a.id === aw.id ? { ...a, viewing_room: aw.viewing_room } : a));
      showToast('Failed to update');
    }
    setSaving(prev => { const s = new Set(prev); s.delete(aw.id); return s; });
  };

  const filtered = artworks.filter(aw => {
    const q = search.toLowerCase();
    const matchSearch  = !q || aw.title.toLowerCase().includes(q) || aw.artist.toLowerCase().includes(q);
    const matchArtist  = !filterArtist || aw.artist_id === filterArtist;
    return matchSearch && matchArtist;
  });

  const inRoom  = artworks.filter(a => a.viewing_room === 1);
  const pubInRoom = inRoom.filter(a => a.status === 'Public');

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      style={{ fontFamily: PX, minHeight: '100vh' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&display=swap');
        button:focus, input:focus, select:focus { outline: none; }
        input:focus, select:focus { border-color: #111 !important; background: #fff !important; }
        .vr-row { transition: background 0.15s; }
        .vr-row:hover { background: #fafafa !important; }
      `}</style>

      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
        paddingBottom: 24, borderBottom: '1px solid rgba(0,0,0,0.07)', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontFamily: PX, fontSize: 28, fontWeight: 300, color: '#111',
            letterSpacing: '0.08em', textTransform: 'uppercase', margin: '0 0 6px' }}>
            Viewing Room
          </h1>
          <p style={{ fontFamily: PX, fontSize: 11, fontWeight: 300, color: '#aaa',
            margin: 0, letterSpacing: '0.08em', lineHeight: 1.6 }}>
            Select which artworks appear in the public Viewing Room.
            {inRoom.length > 0 && ` ${inRoom.length} selected (${pubInRoom.length} public).`}
          </p>
        </div>
        <a href="/viewing-room" target="_blank" rel="noopener noreferrer"
          style={{ ...BTN('transparent', '#888', '#ddd'), display: 'flex', alignItems: 'center', gap: 6, textDecoration: 'none' }}>
          <ExternalLink size={12} />
          Preview
        </a>
      </header>

      {/* Summary strip */}
      {inRoom.length > 0 && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
          style={{ background: '#f0f7f0', border: '1px solid #c8e6c8', padding: '12px 18px',
            marginBottom: 24, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Check size={14} color="#2d7a2d" />
          <span style={{ fontFamily: PX, fontSize: 10, fontWeight: 400, letterSpacing: '0.22em',
            textTransform: 'uppercase', color: '#2d7a2d' }}>
            {inRoom.length} artwork{inRoom.length !== 1 ? 's' : ''} in Viewing Room
            {pubInRoom.length !== inRoom.length && ` (${inRoom.length - pubInRoom.length} private — not visible to public)`}
          </span>
        </motion.div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 220px' }}>
          <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#ccc', fontSize: 14 }}>⌕</span>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search title or artist…"
            style={{ width: '100%', fontFamily: PX, fontSize: 12, fontWeight: 300,
              color: '#111', background: '#fff', border: '1px solid #e0e0e0',
              padding: '9px 11px 9px 30px', outline: 'none' }} />
        </div>
        <select value={filterArtist} onChange={e => setFilterArtist(e.target.value)}
          style={{ fontFamily: PX, fontSize: 11, fontWeight: 300, color: filterArtist ? '#111' : '#bbb',
            background: '#fff', border: '1px solid #e0e0e0', padding: '9px 11px', minWidth: 160 }}>
          <option value="">All Artists</option>
          {artists.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <span style={{ ...LABEL, alignSelf: 'center' }}>{filtered.length} works</span>
      </div>

      {/* Two-column layout: selected | all */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>

        {/* Left: currently in room */}
        <div>
          <p style={{ ...LABEL, marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid #eee' }}>
            In Viewing Room ({inRoom.length})
          </p>
          {inRoom.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', border: '1px dashed #e0e0e0' }}>
              <MonitorPlay size={24} color="#ddd" style={{ margin: '0 auto 8px' }} />
              <p style={{ fontFamily: PX, fontSize: 9, color: '#ccc', letterSpacing: '0.3em',
                textTransform: 'uppercase', margin: 0 }}>No works selected</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <AnimatePresence initial={false}>
                {inRoom.map(aw => (
                  <motion.div key={aw.id} layout
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}
                    style={{ display: 'flex', alignItems: 'center', gap: 10,
                      background: '#fff', border: '1px solid #e8e8e8', padding: '8px 10px' }}>
                    <div style={{ width: 36, height: 44, background: '#eee', overflow: 'hidden', flexShrink: 0 }}>
                      {aw.image_url && <img src={aw.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontFamily: PX, fontSize: 11, fontWeight: 400, color: '#111',
                        margin: '0 0 2px', letterSpacing: '0.03em', overflow: 'hidden',
                        textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{aw.title}</p>
                      <p style={{ fontFamily: PX, fontSize: 8, fontWeight: 300, color: '#bbb',
                        margin: 0, letterSpacing: '0.18em', textTransform: 'uppercase' }}>
                        {aw.artist} {aw.status !== 'Public' && '· Private'}
                      </p>
                    </div>
                    <button onClick={() => toggleViewingRoom(aw)} disabled={saving.has(aw.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#c00',
                        fontSize: 16, lineHeight: 1, padding: 4, flexShrink: 0 }}>×</button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Right: all artworks */}
        <div>
          <p style={{ ...LABEL, marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid #eee' }}>
            All Artworks — click to add / remove
          </p>

          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', fontFamily: PX, fontSize: 9,
              letterSpacing: '0.3em', color: '#ccc', textTransform: 'uppercase' }}>Loading…</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', fontFamily: PX, fontSize: 9,
              letterSpacing: '0.3em', color: '#ccc', textTransform: 'uppercase' }}>No artworks</div>
          ) : (
            <div style={{ background: '#fff', border: '1px solid #e8e8e8' }}>
              {/* Head */}
              <div style={{ display: 'grid', gridTemplateColumns: '48px 1fr 100px 80px 80px',
                padding: '8px 14px', borderBottom: '1px solid #eee' }}>
                {['', 'Title / Artist', 'Medium', 'Status', 'Room'].map(h => (
                  <span key={h} style={LABEL}>{h}</span>
                ))}
              </div>
              {filtered.map(aw => {
                const inVR = aw.viewing_room === 1;
                return (
                  <div key={aw.id} className="vr-row"
                    style={{ display: 'grid', gridTemplateColumns: '48px 1fr 100px 80px 80px',
                      padding: '10px 14px', borderBottom: '1px solid #f2f2f2',
                      background: '#fff', alignItems: 'center', cursor: 'pointer' }}
                    onClick={() => !saving.has(aw.id) && toggleViewingRoom(aw)}>

                    {/* Thumb */}
                    <div style={{ width: 36, height: 44, background: '#eee', overflow: 'hidden' }}>
                      {aw.image_url
                        ? <img src={aw.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <ImageIcon size={14} color="#ccc" />
                          </div>
                      }
                    </div>

                    {/* Title */}
                    <div style={{ paddingLeft: 4 }}>
                      <p style={{ fontFamily: PX, fontSize: 11, fontWeight: 400, color: '#111',
                        margin: '0 0 2px', letterSpacing: '0.03em' }}>{aw.title}</p>
                      <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300, color: '#bbb',
                        margin: 0, letterSpacing: '0.18em', textTransform: 'uppercase' }}>{aw.artist || '—'}</p>
                    </div>

                    {/* Medium */}
                    <p style={{ fontFamily: PX, fontSize: 9, fontWeight: 300, color: '#999', margin: 0, letterSpacing: '0.1em' }}>
                      {aw.medium || '—'}
                    </p>

                    {/* Status */}
                    <div>
                      <span style={{
                        fontFamily: PX, fontSize: 8, fontWeight: 400, letterSpacing: '0.22em',
                        textTransform: 'uppercase',
                        color: aw.status === 'Public' ? '#2d7a2d' : '#bbb',
                      }}>
                        {aw.status}
                      </span>
                    </div>

                    {/* Toggle */}
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <div style={{
                        width: 22, height: 22, border: `2px solid ${inVR ? '#111' : '#ddd'}`,
                        background: inVR ? '#111' : 'transparent',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.2s',
                        opacity: saving.has(aw.id) ? 0.4 : 1,
                      }}>
                        {inVR && <Check size={12} color="#fff" />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            style={{ position: 'fixed', bottom: 28, right: 28, background: '#111', color: '#fff',
              fontFamily: PX, fontSize: 10, fontWeight: 300, letterSpacing: '0.25em',
              textTransform: 'uppercase', padding: '13px 24px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.18)', zIndex: 9999 }}>
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
