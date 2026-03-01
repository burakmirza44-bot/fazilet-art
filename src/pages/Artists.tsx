import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';

const PX = "'proxima-nova', 'Nunito Sans', 'Gill Sans MT', sans-serif";

interface Artist {
  id: string;
  name: string;
  image_url: string;
  medium?: string;
}

export default function Artists() {
  const [hovered, setHovered] = useState<Artist | null>(null);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/artists/public')
      .then(res => res.json())
      .then(data => {
        setArtists(Array.isArray(data) ? data : (data.data ?? []));
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch artists:', err);
        setLoading(false);
      });
  }, []);

  const grouped = artists.reduce<Record<string, Artist[]>>((acc, a) => {
    const l = a.name[0].toUpperCase();
    if (!acc[l]) acc[l] = [];
    acc[l].push(a);
    return acc;
  }, {});

  return (
    <div className="dm-page" style={{ minHeight: '100vh', background: '#fff', fontFamily: PX }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&family=Cormorant+Garamond:wght@300;400;500&display=swap');
      `}</style>

      <div className="artists-page-wrap" style={{
        maxWidth: 1400, margin: '0 auto',
        padding: '120px 48px 96px',
        display: 'flex', gap: 64,
      }}>

        {/* ── Sol: Liste ── */}
        <div style={{ flex: '1 1 60%', minWidth: 0 }}>

          {/* Sayfa başlığı */}
          <div style={{ marginBottom: 64, paddingBottom: 24, borderBottom: '1px solid rgba(0,0,0,0.08)' }}>
            <h1 style={{
              fontFamily: PX,
              fontSize: 'clamp(28px, 4vw, 48px)',
              fontWeight: 300, color: '#111',
              letterSpacing: '0.1em', margin: 0,
              textTransform: 'uppercase',
            }}>
              Artists
            </h1>
          </div>

          {/* Alfabetik gruplar */}
          {loading ? (
            <div style={{ padding: '40px 0', color: '#aaa', fontSize: 14 }}>Loading artists...</div>
          ) : artists.length === 0 ? (
            <div style={{ padding: '40px 0', color: '#aaa', fontSize: 14 }}>No artists found.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
              {Object.entries(grouped).sort().map(([letter, group]) => (
                <div key={letter} style={{ display: 'flex', gap: 32 }}>

                  {/* Harf */}
                  <div style={{
                    width: 28, flexShrink: 0, paddingTop: 4,
                    fontFamily: PX, fontSize: 11, fontWeight: 300,
                    letterSpacing: '0.18em', color: '#ccc',
                    textTransform: 'uppercase',
                  }}>
                    {letter}
                  </div>

                  {/* İsimler */}
                  <ul style={{ margin: 0, padding: 0, listStyle: 'none', flex: 1 }}>
                    {(group as Artist[]).map((artist) => (
                      <li key={artist.id} style={{ marginBottom: 2 }}>
                        <motion.div
                          whileHover={{ x: 8 }}
                          transition={{ type: 'spring', stiffness: 320, damping: 28 }}
                        >
                          <Link
                            to={`/shared/artist/${artist.id}`}
                            onMouseEnter={() => setHovered(artist)}
                            onMouseLeave={() => setHovered(null)}
                          className="artist-list-link"
                          style={{
                            display: 'inline-flex', flexDirection: 'column',
                            textDecoration: 'none', padding: '8px 0',
                          }}
                        >
                          <span style={{
                            fontFamily: PX,
                            fontSize: 'clamp(16px, 1.6vw, 22px)',
                            fontWeight: 300, color: '#111',
                            letterSpacing: '0.04em',
                            transition: 'color 0.25s, letter-spacing 0.3s',
                          }}
                            className="artist-name-text"
                          >
                            {artist.name}
                          </span>
                          <span style={{
                            fontFamily: PX, fontSize: 10, fontWeight: 300,
                            letterSpacing: '0.28em', color: '#bbb',
                            textTransform: 'uppercase', marginTop: 2,
                          }}>
                            {artist.medium}
                          </span>
                          {/* Alt çizgi animasyonu */}
                          <span className="artist-underline" style={{
                            display: 'block', height: 1,
                            background: '#111', width: 0,
                            transition: 'width 0.3s ease',
                            marginTop: 4,
                          }} />
                        </Link>
                      </motion.div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            </div>
          )}
        </div>

        {/* ── Sağ: Sticky önizleme ── */}
        <div style={{
          flex: '0 0 320px', display: 'none',
          // md ve üstünde görünür — CSS media query
        }} className="artist-preview-col">
          <div style={{ position: 'sticky', top: 120, height: '65vh' }}>
            <AnimatePresence mode="wait">
              {hovered ? (
                <motion.div
                  key={hovered.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                  style={{ width: '100%', height: '100%', position: 'relative' }}
                >
                  <img
                    src={hovered.image_url || `https://picsum.photos/seed/${hovered.id}/600/800?grayscale`}
                    alt={hovered.name}
                    referrerPolicy="no-referrer"
                    style={{
                      width: '100%', height: '100%',
                      objectFit: 'cover', display: 'block',
                    }}
                  />
                  {/* Alt bilgi şeridi */}
                  <div style={{
                    position: 'absolute', bottom: 0, left: 0, right: 0,
                    background: 'rgba(255,255,255,0.92)',
                    backdropFilter: 'blur(8px)',
                    padding: '14px 18px',
                    borderTop: '1px solid rgba(0,0,0,0.06)',
                  }}>
                    <p style={{
                      fontFamily: PX, fontSize: 11, fontWeight: 400,
                      letterSpacing: '0.22em', color: '#111',
                      textTransform: 'uppercase', margin: '0 0 3px',
                    }}>
                      {hovered.name}
                    </p>
                    <p style={{
                      fontFamily: PX, fontSize: 10, fontWeight: 300,
                      letterSpacing: '0.22em', color: '#aaa',
                      textTransform: 'uppercase', margin: 0,
                    }}>
                      {hovered.medium}
                    </p>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  style={{
                    width: '100%', height: '100%',
                    border: '1px solid rgba(0,0,0,0.08)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  <p style={{
                    fontFamily: PX, fontSize: 10, fontWeight: 300,
                    letterSpacing: '0.3em', color: '#ccc',
                    textTransform: 'uppercase',
                  }}>
                    Hover an artist
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Hover stilleri */}
      <style>{`
        .artist-list-link:hover .artist-name-text {
          color: #555;
          letter-spacing: 0.07em;
        }
        .artist-list-link:hover .artist-underline {
          width: 100% !important;
        }
        @media (min-width: 768px) {
          .artist-preview-col {
            display: block !important;
          }
        }
        @media (max-width: 768px) {
          .artists-page-wrap {
            padding: 100px 20px 64px !important;
            gap: 0 !important;
          }
        }
      `}</style>
    </div>
  );
}