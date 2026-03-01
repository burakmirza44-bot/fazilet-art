import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

const PX  = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const SER = "'Cormorant Garamond','Didot','Georgia',serif";

// ─── Types ─────────────────────────────────────────────
type Artwork = {
  id: string;
  title: string;
  year?: string;
  medium?: string;
  image_url?: string;
  artist_name?: string;
  tags?: string[];
  // canvas layout (assigned dynamically)
  x: number;
  y: number;
};

type Artist = {
  id: string;
  name: string;
};

// Assign deterministic positions from id hash
function hashPos(id: string, idx: number, total: number) {
  // Place in a spiral-ish grid away from center (50,52)
  const angle = (idx / total) * 2 * Math.PI + 0.4;
  const radius = 28 + (idx % 3) * 8;
  const cx = 50, cy = 52;
  return {
    x: Math.round(cx + Math.cos(angle) * radius * 1.1),
    y: Math.round(cy + Math.sin(angle) * radius * 0.7),
  };
}

const CORE = { x: 50, y: 52 };

export default function ViewingRoom() {
  const [artworks, setArtworks]     = useState<Artwork[]>([]);
  const [artists,  setArtists]      = useState<Artist[]>([]);
  const [loading,  setLoading]      = useState(true);
  const [selected, setSelected]     = useState<Artwork | null>(null);
  const [activeArtist, setActiveArtist] = useState<string>('All');
  const [activeTag, setActiveTag]   = useState<string>('All');

  // Fetch data — sadece admin'de Viewing Room'a seçilmiş eserler
  useEffect(() => {
    Promise.all([
      fetch('/api/viewing-room').then(r => r.ok ? r.json() : []),
      fetch('/api/artists?public=true').then(r => r.ok ? r.json() : []),
    ]).then(([awRes, arRes]) => {
      const awList: any[] = Array.isArray(awRes) ? awRes : (awRes.data ?? awRes.artworks ?? []);
      const arList: Artist[] = Array.isArray(arRes) ? arRes : (arRes.data ?? []);
      setArtists(arList);

      // Assign positions
      const placed: Artwork[] = awList.map((aw: any, i: number) => ({
        id:          String(aw.id),
        title:       aw.title ?? 'Untitled',
        year:        aw.year,
        medium:      aw.medium,
        image_url:   aw.image_url,
        artist_name: aw.artist_name ?? arList.find(a => a.id === String(aw.artist_id))?.name,
        tags:        aw.tags ? (typeof aw.tags === 'string' ? JSON.parse(aw.tags) : aw.tags) : [],
        ...hashPos(String(aw.id), i, awList.length),
      }));
      setArtworks(placed);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // All unique tags
  const allTags = useMemo(() => {
    const s = new Set<string>();
    artworks.forEach(a => (a.tags ?? []).forEach(t => s.add(t)));
    return ['All', ...Array.from(s).sort()];
  }, [artworks]);

  // Filtered artworks
  const visible = useMemo(() => {
    return artworks.filter(a => {
      const byArtist = activeArtist === 'All' || a.artist_name === activeArtist;
      const byTag    = activeTag    === 'All' || (a.tags ?? []).includes(activeTag);
      return byArtist && byTag;
    });
  }, [artworks, activeArtist, activeTag]);

  // SVG links: core → each visible artwork
  const links = useMemo(() =>
    visible.map(a => ({ id: a.id, from: CORE, to: { x: a.x, y: a.y } })),
    [visible]
  );

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#fff', fontFamily: PX }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&family=Cormorant+Garamond:wght@300;400&display=swap');
        .vr-node { transition: border-color 0.2s, background 0.2s; }
        .vr-node:hover { border-color: rgba(255,255,255,0.4) !important; background: rgba(255,255,255,0.08) !important; }
        .vr-node.selected { border-color: rgba(255,255,255,0.6) !important; background: rgba(255,255,255,0.1) !important; }
        .filter-btn { transition: all 0.2s; }
        .filter-btn:hover { border-color: rgba(255,255,255,0.3) !important; }
        .filter-btn.active { border-color: rgba(255,255,255,0.45) !important; background: rgba(255,255,255,0.1) !important; }
      `}</style>

      {/* ── Header ── */}
      <div className="vr-header" style={{ padding: '112px 48px 32px', maxWidth: 1400, margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
                   flexWrap: 'wrap', gap: 24, marginBottom: 32 }}
        >
          <div>
            <p style={{
              fontFamily: PX, fontSize: 9, fontWeight: 400,
              letterSpacing: '0.45em', color: 'rgba(255,255,255,0.25)',
              textTransform: 'uppercase', margin: '0 0 12px',
            }}>Private Access</p>
            <h1 style={{
              fontFamily: PX,
              fontSize: 'clamp(24px, 3.5vw, 42px)',
              fontWeight: 300, color: '#fff',
              letterSpacing: '0.1em', margin: 0,
              textTransform: 'uppercase',
            }}>Viewing Room</h1>
          </div>

          {/* Filter chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {/* Artist filter */}
            {artists.length > 0 && (
              <>
                {['All', ...artists.map(a => a.name)].map(name => (
                  <button key={name}
                    onClick={() => setActiveArtist(name)}
                    className={`filter-btn${activeArtist === name ? ' active' : ''}`}
                    style={{
                      fontFamily: PX, fontSize: 8, fontWeight: 300,
                      letterSpacing: '0.32em', textTransform: 'uppercase',
                      color: '#fff', background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.14)',
                      padding: '6px 14px', cursor: 'pointer',
                    }}
                  >{name === 'All' ? 'All Artists' : name}</button>
                ))}
              </>
            )}
            {/* Tag filter */}
            {allTags.length > 1 && allTags.map(t => (
              <button key={t}
                onClick={() => setActiveTag(t)}
                className={`filter-btn${activeTag === t ? ' active' : ''}`}
                style={{
                  fontFamily: PX, fontSize: 8, fontWeight: 300,
                  letterSpacing: '0.32em', textTransform: 'uppercase',
                  color: 'rgba(255,255,255,0.55)', background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.08)',
                  padding: '6px 14px', cursor: 'pointer',
                }}
              >{t}</button>
            ))}
          </div>
        </motion.div>
      </div>

      {/* ── Canvas + Panel ── */}
      <div className="vr-body" style={{ padding: '0 48px 80px', maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24 }}
          className="vr-grid">

          {/* Mind map canvas */}
          <div style={{
            position: 'relative', border: '1px solid rgba(255,255,255,0.07)',
            background: 'rgba(255,255,255,0.02)', overflow: 'hidden',
            height: '64vh', minHeight: 480,
          }}>
            {/* Vignette */}
            <div style={{
              position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 1,
              background: 'radial-gradient(ellipse at center, transparent 50%, rgba(10,10,10,0.6) 100%)',
            }} />

            {loading && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                fontFamily: PX, fontSize: 9, letterSpacing: '0.4em',
                textTransform: 'uppercase', color: 'rgba(255,255,255,0.2)',
              }}>Loading works…</div>
            )}

            {!loading && artworks.length === 0 && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex',
                flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
              }}>
                <p style={{
                  fontFamily: SER, fontSize: 20, fontWeight: 300,
                  color: 'rgba(255,255,255,0.2)', margin: 0,
                }}>No works yet</p>
                <p style={{
                  fontFamily: PX, fontSize: 9, letterSpacing: '0.35em',
                  textTransform: 'uppercase', color: 'rgba(255,255,255,0.12)', margin: 0,
                }}>Add artworks from the admin panel</p>
              </div>
            )}

            {/* SVG connection lines */}
            <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 2 }}
              viewBox="0 0 100 100" preserveAspectRatio="none">
              <AnimatePresence>
                {links.map(l => (
                  <motion.line
                    key={l.id}
                    x1={l.from.x} y1={l.from.y}
                    x2={l.to.x}   y2={l.to.y}
                    stroke="rgba(255,255,255,0.12)"
                    strokeWidth="0.2"
                    strokeDasharray="0.8 0.8"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  />
                ))}
              </AnimatePresence>
            </svg>

            {/* Core node */}
            <div style={{
              position: 'absolute', zIndex: 4,
              left: `${CORE.x}%`, top: `${CORE.y}%`,
              transform: 'translate(-50%, -50%)',
            }}>
              <div style={{
                fontFamily: PX, fontSize: 8, fontWeight: 400,
                letterSpacing: '0.3em', textTransform: 'uppercase',
                color: '#000', background: '#fff',
                padding: '5px 14px',
              }}>
                FSAPC
              </div>
            </div>

            {/* Artwork nodes */}
            <AnimatePresence>
              {visible.map(a => (
                <motion.button
                  key={a.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                  transition={{ duration: 0.3 }}
                  onClick={() => setSelected(selected?.id === a.id ? null : a)}
                  className={`vr-node${selected?.id === a.id ? ' selected' : ''}`}
                  style={{
                    position: 'absolute', zIndex: 4,
                    left: `${a.x}%`, top: `${a.y}%`,
                    transform: 'translate(-50%, -50%)',
                    background: 'rgba(10,10,10,0.8)',
                    border: '1px solid rgba(255,255,255,0.18)',
                    backdropFilter: 'blur(8px)',
                    padding: '8px 14px',
                    textAlign: 'left', cursor: 'pointer',
                    maxWidth: 180,
                  }}
                >
                  <div style={{
                    fontFamily: SER, fontSize: 13, fontWeight: 300,
                    color: '#fff', marginBottom: 2,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>{a.title}</div>
                  <div style={{
                    fontFamily: PX, fontSize: 9, fontWeight: 300,
                    letterSpacing: '0.18em', textTransform: 'uppercase',
                    color: 'rgba(255,255,255,0.4)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {a.artist_name ?? ''}
                    {a.year ? ` · ${a.year}` : ''}
                  </div>
                </motion.button>
              ))}
            </AnimatePresence>
          </div>

          {/* Detail panel */}
          <div style={{
            border: '1px solid rgba(255,255,255,0.07)',
            background: 'rgba(255,255,255,0.02)',
            height: '64vh', minHeight: 480,
            display: 'flex', flexDirection: 'column',
            overflow: 'hidden',
          }}>
            <AnimatePresence mode="wait">
              {!selected ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  style={{
                    flex: 1, display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 10,
                    padding: 32,
                  }}
                >
                  <div style={{
                    width: 1, height: 48, background: 'rgba(255,255,255,0.12)',
                    marginBottom: 8,
                  }} />
                  <p style={{
                    fontFamily: PX, fontSize: 9, fontWeight: 300,
                    letterSpacing: '0.38em', textTransform: 'uppercase',
                    color: 'rgba(255,255,255,0.2)', margin: 0, textAlign: 'center',
                  }}>
                    Select a work<br />to view details
                  </p>
                </motion.div>
              ) : (
                <motion.div
                  key={selected.id}
                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3 }}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto' }}
                >
                  {/* Image */}
                  <div style={{
                    flexShrink: 0, height: 220,
                    background: '#111', overflow: 'hidden',
                  }}>
                    {selected.image_url ? (
                      <img src={selected.image_url} alt={selected.title}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    ) : (
                      <div style={{
                        width: '100%', height: '100%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontFamily: PX, fontSize: 9, letterSpacing: '0.32em',
                        textTransform: 'uppercase', color: 'rgba(255,255,255,0.15)',
                      }}>
                        No image
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div style={{ padding: '24px 24px 0', flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                      <h2 style={{
                        fontFamily: SER,
                        fontSize: 'clamp(18px, 1.6vw, 24px)',
                        fontWeight: 300, color: '#fff',
                        letterSpacing: '0.02em', margin: '0 0 6px',
                      }}>{selected.title}</h2>
                      <button onClick={() => setSelected(null)} style={{
                        fontFamily: PX, fontSize: 8, fontWeight: 300,
                        letterSpacing: '0.32em', textTransform: 'uppercase',
                        color: 'rgba(255,255,255,0.3)', background: 'transparent',
                        border: '1px solid rgba(255,255,255,0.12)',
                        padding: '4px 10px', cursor: 'pointer', flexShrink: 0,
                      }}>✕</button>
                    </div>

                    {selected.artist_name && (
                      <p style={{
                        fontFamily: PX, fontSize: 10, fontWeight: 300,
                        letterSpacing: '0.22em', textTransform: 'uppercase',
                        color: 'rgba(255,255,255,0.35)', margin: '0 0 4px',
                      }}>{selected.artist_name}</p>
                    )}

                    <p style={{
                      fontFamily: PX, fontSize: 10, fontWeight: 300,
                      letterSpacing: '0.18em', color: 'rgba(255,255,255,0.22)',
                      margin: '0 0 20px',
                    }}>
                      {[selected.year, selected.medium].filter(Boolean).join(' · ')}
                    </p>

                    {(selected.tags ?? []).length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {(selected.tags ?? []).map(t => (
                          <span key={t} style={{
                            fontFamily: PX, fontSize: 8, fontWeight: 300,
                            letterSpacing: '0.28em', textTransform: 'uppercase',
                            color: 'rgba(255,255,255,0.3)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            padding: '4px 10px',
                          }}>{t}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* CTA */}
                  <div style={{ padding: 24 }}>
                    <a href="/contact" style={{
                      display: 'block', textAlign: 'center',
                      fontFamily: PX, fontSize: 8, fontWeight: 400,
                      letterSpacing: '0.4em', textTransform: 'uppercase',
                      color: '#000', background: '#fff',
                      padding: '12px 24px', textDecoration: 'none',
                      transition: 'opacity 0.2s',
                    }}
                      onMouseEnter={e => ((e.currentTarget as HTMLElement).style.opacity = '0.8')}
                      onMouseLeave={e => ((e.currentTarget as HTMLElement).style.opacity = '1')}
                    >
                      Enquire
                    </a>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <p style={{
          fontFamily: PX, fontSize: 8, letterSpacing: '0.3em',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.18)',
          marginTop: 16,
        }}>
          Click a node to view details — hover to preview
        </p>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .vr-grid { grid-template-columns: 1fr !important; }
          .vr-header { padding: 100px 20px 24px !important; }
          .vr-body { padding: 0 20px 56px !important; }
        }
      `}</style>
    </div>
  );
}
