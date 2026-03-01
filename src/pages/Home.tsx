import { Link }                      from 'react-router-dom';
import { motion, AnimatePresence }    from 'motion/react';
import { useEffect, useState, useRef } from 'react';
// import InteractiveLines from './Interactivelines'; // Ebru — arşivde, istediğinde geri al
import IslamicGeometric              from './IslamicGeometric';

// ─── Font stack ────────────────────────────────────────────
const PX  = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const SER = "'Cormorant Garamond','Didot','Georgia',serif";

// ─── Logo ─────────────────────────────────────────────────
const logoImage = '/logo-white.png';

// ─── Types ────────────────────────────────────────────────
type Artist = {
  id: string;
  name: string;
  medium?: string;
  bio?: string;
  image_url?: string | null;
  artworks_count?: number;
  featured?: number | boolean;
};

// ─── Ticker strip ─────────────────────────────────────────
const TICKER_ITEMS = [
  'ART PROJECT CONSULTANCY',
  'ISTANBUL',
  'LONDON',
  'CONTEMPORARY ART',
  'FAZILET SECGIN',
];

function Ticker() {
  const items = [...TICKER_ITEMS, ...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <div style={{
      overflow: 'hidden', whiteSpace: 'nowrap',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      borderBottom: '1px solid rgba(255,255,255,0.08)',
      padding: '10px 0',
    }}>
      <motion.div
        animate={{ x: ['0%', '-33.33%'] }}
        transition={{ duration: 28, ease: 'linear', repeat: Infinity }}
        style={{ display: 'inline-flex', gap: 0 }}
      >
        {items.map((t, i) => (
          <span key={i} style={{
            fontFamily: PX, fontSize: 9, fontWeight: 300,
            letterSpacing: '0.4em', textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.22)', padding: '0 40px',
          }}>
            {t} <span style={{ opacity: 0.3, marginLeft: 40 }}>—</span>
          </span>
        ))}
      </motion.div>
    </div>
  );
}

// ─── Hero section ─────────────────────────────────────────
function Hero() {
  return (
    <div style={{
      width: '100%', height: '100vh', minHeight: 600,
      background: '#0a0a0a', position: 'relative', overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Islamic geometric background */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
        <IslamicGeometric />
      </div>

      {/* Gradient vignette — alt yumuşatma */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 2,
        background: 'linear-gradient(to bottom, transparent 40%, rgba(10,10,10,0.85) 100%)',
        pointerEvents: 'none',
      }} />

      {/* Sol dikey çizgi — üstten alta kadar (masaüstü) */}
      <div className="hero-vline" style={{
        position: 'absolute', left: 64, top: 72, bottom: 44,
        width: 1.5, background: 'rgba(255,255,255,0.22)', zIndex: 5,
        pointerEvents: 'none',
      }} />
      {/* Sol üst kare işareti */}
      <div className="hero-vline" style={{
        position: 'absolute', left: 58, top: 56,
        width: 12, height: 12,
        border: '1.5px solid rgba(255,255,255,0.22)',
        zIndex: 5, pointerEvents: 'none',
      }} />
      {/* Alt kontrast marker — çizginin bitiminde küçük beyaz kare */}
      <div className="hero-vline" style={{
        position: 'absolute', left: 57, bottom: 36,
        width: 15, height: 15,
        background: '#fff',
        zIndex: 5, pointerEvents: 'none',
      }} />

      {/* Merkez içerik */}
      <div style={{
        position: 'absolute', zIndex: 10,
        bottom: 0, left: 0, right: 0,
      }}>
        {/* Ticker */}
        <Ticker />

        {/* Logo + nav satırı */}
        <div className="hero-bottom-row" style={{
          padding: '28px 48px 36px 88px',
          display: 'flex', alignItems: 'flex-end',
          justifyContent: 'space-between', gap: 32,
        }}>
          {/* Logo — sol çizgiden 24px sağda, altındaki çizgiden de 24px */}
          <div>
            {logoImage ? (
              <Link to="/" style={{ display: 'inline-block', marginBottom: 24 }}>
              <img
                src={logoImage}
                alt="Fazilet Secgin Art Project Consultancy"
                style={{
                  height: 'clamp(18px, 2vw, 30px)',
                  width: 'auto', objectFit: 'contain', display: 'block',
                  opacity: 1, transition: 'opacity 0.25s',
                }}
                onMouseEnter={e => (e.currentTarget.style.opacity = '0.7')}
                onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
              />
              </Link>
            ) : (
              <div style={{ marginBottom: 12 }}>
                <span style={{
                  fontFamily: SER,
                  fontSize: 'clamp(18px, 3.2vw, 42px)',
                  letterSpacing: '0.3em', color: '#fff',
                  fontWeight: 300, textTransform: 'uppercase', display: 'block',
                }}>FAZILET SECGIN</span>
                <span style={{
                  fontFamily: PX, fontSize: 10, letterSpacing: '0.25em',
                  color: 'rgba(255,255,255,0.38)', textTransform: 'uppercase',
                  fontWeight: 300,
                }}>Art Project Consultancy</span>
              </div>
            )}
            <div style={{ height: 1.5, background: 'rgba(255,255,255,0.18)', width: '100%' }} />
          </div>

          {/* Sağ: lokasyon + CTA */}
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <p style={{
              fontFamily: PX, fontSize: 9, fontWeight: 300,
              letterSpacing: '0.35em', color: 'rgba(255,255,255,0.22)',
              textTransform: 'uppercase', margin: '0 0 12px',
            }}>
              Istanbul — London
            </p>
            <Link to="/artists" style={{
              display: 'inline-block',
              fontFamily: PX, fontSize: 9, fontWeight: 400,
              letterSpacing: '0.35em', textTransform: 'uppercase',
              color: '#fff', textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.3)',
              padding: '9px 22px',
              transition: 'all 0.3s',
            }}
              onMouseEnter={e => {
                (e.target as HTMLElement).style.background = '#fff';
                (e.target as HTMLElement).style.color = '#000';
              }}
              onMouseLeave={e => {
                (e.target as HTMLElement).style.background = 'transparent';
                (e.target as HTMLElement).style.color = '#fff';
              }}
            >
              View Artists
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Artist card ──────────────────────────────────────────
function ArtistCard({ artist, index }: { key?: string; artist: Artist; index: number }) {
  // Artlogic tarzı: ilk kart büyük (featured), diğerleri küçük
  const isBig = index === 0;
  const [loaded, setLoaded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 32 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, delay: isBig ? 0 : (index - 1) * 0.08, ease: [0.22, 1, 0.36, 1] }}
      style={{ gridColumn: isBig ? 'span 2' : 'span 1' }}
      className="artist-card-wrap"
    >
      <Link to={`/shared/artist/${artist.id}`} style={{ display: 'block', textDecoration: 'none' }}>
        {/* Image */}
        <div style={{
          position: 'relative', overflow: 'hidden',
          aspectRatio: isBig ? '16/9' : '3/4',
          background: '#e4e4e4',
        }}>
          {/* Skeleton */}
          {!loaded && (
            <div style={{
              position: 'absolute', inset: 0,
              background: 'linear-gradient(90deg,#ececec 25%,#f5f5f5 50%,#ececec 75%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 1.4s infinite',
            }} />
          )}
          <img
            src={artist.image_url || `https://picsum.photos/seed/${artist.id}/900/1100?grayscale`}
            alt={artist.name}
            referrerPolicy="no-referrer"
            onLoad={() => setLoaded(true)}
            className="artist-card-photo"
            style={{
              width: '100%', height: '100%', objectFit: 'cover', display: 'block',
              opacity: loaded ? 1 : 0,
              transition: 'opacity 0.5s, transform 0.8s cubic-bezier(0.25,0.46,0.45,0.94)',
            }}
          />

          {/* Hover overlay */}
          <div className="artist-card-overlay" style={{
            position: 'absolute', inset: 0,
            background: 'rgba(0,0,0,0)',
            transition: 'background 0.45s',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span className="artist-card-cta" style={{
              fontFamily: PX, fontSize: 9, fontWeight: 400,
              letterSpacing: '0.4em', textTransform: 'uppercase',
              color: '#fff', border: '1px solid rgba(255,255,255,0.7)',
              padding: '10px 24px', opacity: 0,
              transform: 'translateY(8px)',
              transition: 'opacity 0.35s, transform 0.35s',
            }}>
              View Portfolio
            </span>
          </div>

          {/* Featured badge */}
          {(artist.featured === 1 || artist.featured === true) && (
            <div style={{
              position: 'absolute', top: 16, left: 16,
              fontFamily: PX, fontSize: 8, fontWeight: 400,
              letterSpacing: '0.3em', textTransform: 'uppercase',
              color: '#fff', background: 'rgba(0,0,0,0.55)',
              backdropFilter: 'blur(4px)',
              padding: '5px 10px',
            }}>
              Featured
            </div>
          )}
        </div>

        {/* Info */}
        <div style={{
          padding: isBig ? '20px 0 0' : '16px 0 0',
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          gap: 16,
        }}>
          <div>
            <h3 style={{
              fontFamily: PX,
              fontSize: isBig ? 18 : 14,
              fontWeight: 400, color: '#111',
              letterSpacing: '0.08em', textTransform: 'uppercase',
              margin: '0 0 5px',
            }}>
              {artist.name}
            </h3>
            <p style={{
              fontFamily: PX, fontSize: 10, fontWeight: 300,
              letterSpacing: '0.22em', color: '#aaa',
              textTransform: 'uppercase', margin: 0,
            }}>
              {artist.medium || 'Contemporary Art'}
            </p>
          </div>
          {typeof artist.artworks_count === 'number' && (
            <span style={{
              fontFamily: PX, fontSize: 10, fontWeight: 300,
              letterSpacing: '0.18em', color: '#ccc',
              textTransform: 'uppercase', flexShrink: 0, paddingTop: 2,
            }}>
              {artist.artworks_count} work{artist.artworks_count !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </Link>
    </motion.div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────
function GridSkeleton() {
  return (
    <>
      {[0, 1, 2, 3].map(i => (
        <div key={i} style={{
          gridColumn: i === 0 ? 'span 2' : 'span 1',
          aspectRatio: i === 0 ? '16/9' : '3/4',
          background: '#ececec',
          animation: 'shimmer 1.4s infinite',
          backgroundSize: '200% 100%',
        }} />
      ))}
    </>
  );
}

// ─── Main ─────────────────────────────────────────────────
export default function Home() {
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  useEffect(() => {
    fetch('/api/artists?featured=true&limit=5&sort=name')
      .then(r => {
        if (!r.ok) throw new Error('API error');
        return r.json();
      })
      .then(json => {
        // API pagination formatına göre data dizisini al
        const list: Artist[] = Array.isArray(json) ? json : (json.data ?? []);
        // featured olanları öne al, max 5
        const sorted = [...list].sort((a, b) =>
          Number(b.featured ?? 0) - Number(a.featured ?? 0)
        ).slice(0, 5);
        setArtists(sorted);
        setLoading(false);
      })
      .catch(() => { setError(true); setLoading(false); });
  }, []);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column',
                  background: '#fff', fontFamily: PX }}>

      {/* ═══════════ HERO ═══════════ */}
      <Hero />

      {/* ═══════════ FEATURED ARTISTS ═══════════ */}
      <section style={{ background: '#fff', width: '100%' }}>
        <div className="home-section-pad" style={{ maxWidth: 1360, margin: '0 auto', padding: '96px 48px 120px' }}>

          {/* Section header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
            style={{
              display: 'flex', alignItems: 'flex-end',
              justifyContent: 'space-between', marginBottom: 64,
              paddingBottom: 28, borderBottom: '1px solid #ebebeb',
            }}
          >
            <div>
              <p style={{
                fontFamily: PX, fontSize: 9, fontWeight: 400,
                letterSpacing: '0.45em', color: '#bbb',
                textTransform: 'uppercase', margin: '0 0 12px',
              }}>
                Current Selection
              </p>
              <h2 style={{
                fontFamily: PX,
                fontSize: 'clamp(22px, 2.8vw, 38px)',
                fontWeight: 300, color: '#111',
                letterSpacing: '0.1em', margin: 0,
                textTransform: 'uppercase',
              }}>
                Featured Artists
              </h2>
            </div>

            <Link to="/artists" style={{
              fontFamily: PX, fontSize: 9, fontWeight: 400,
              letterSpacing: '0.38em', color: '#111',
              textTransform: 'uppercase', textDecoration: 'none',
              display: 'flex', alignItems: 'center', gap: 10,
              paddingBottom: 2, borderBottom: '1px solid #ccc',
            }}>
              All Artists
              <span style={{ fontSize: 12 }}>→</span>
            </Link>
          </motion.div>

          {/* Grid — Artlogic 2+3 layout */}
          <div className="artists-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '32px 28px',
          }}>
            {loading && <GridSkeleton />}

            {!loading && error && (
              <div style={{
                gridColumn: 'span 4', padding: '60px 0', textAlign: 'center',
                fontFamily: PX, fontSize: 11, letterSpacing: '0.3em',
                color: '#bbb', textTransform: 'uppercase',
              }}>
                Could not load artists
              </div>
            )}

            {!loading && !error && artists.length === 0 && (
              <div style={{
                gridColumn: 'span 4', padding: '60px 0', textAlign: 'center',
                fontFamily: PX, fontSize: 11, letterSpacing: '0.3em',
                color: '#bbb', textTransform: 'uppercase',
              }}>
                No artists yet — add some from the admin panel
              </div>
            )}

            {!loading && !error && artists.map((a, i) => (
              <ArtistCard key={a.id} artist={a} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ EDITORIAL STRIP ═══════════ */}
      <section className="editorial-strip" style={{
        background: '#0a0a0a', width: '100%',
        padding: '80px 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 48, flexWrap: 'wrap',
      }}>
        <div style={{ maxWidth: 540 }}>
          <p style={{
            fontFamily: PX, fontSize: 9, fontWeight: 300,
            letterSpacing: '0.4em', color: 'rgba(255,255,255,0.3)',
            textTransform: 'uppercase', margin: '0 0 16px',
          }}>
            About
          </p>
          <h3 style={{
            fontFamily: SER,
            fontSize: 'clamp(20px, 2.5vw, 32px)',
            fontWeight: 300, color: '#fff',
            letterSpacing: '0.04em', lineHeight: 1.5, margin: '0 0 24px',
          }}>
            Connecting collectors, institutions and artists through considered curation.
          </h3>
          <p style={{
            fontFamily: PX, fontSize: 12, fontWeight: 300,
            color: 'rgba(255,255,255,0.4)', lineHeight: 1.8,
            letterSpacing: '0.02em', margin: 0,
          }}>
            Fazilet Secgin Art Project Consultancy works at the intersection of contemporary art, private collecting and institutional programming.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'flex-end' }}>
          {[
            { label: 'Artists', to: '/artists' },
            { label: 'Exhibitions', to: '/exhibitions' },
            { label: 'Viewing Room', to: '/viewing-room' },
            { label: 'Contact', to: '/contact' },
          ].map(item => (
            <Link key={item.label} to={item.to} style={{
              fontFamily: PX, fontSize: 10, fontWeight: 300,
              letterSpacing: '0.35em', color: 'rgba(255,255,255,0.35)',
              textTransform: 'uppercase', textDecoration: 'none',
              transition: 'color 0.25s',
            }}
              onMouseEnter={e => ((e.target as HTMLElement).style.color = '#fff')}
              onMouseLeave={e => ((e.target as HTMLElement).style.color = 'rgba(255,255,255,0.35)')}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </section>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer style={{
        background: '#0a0a0a',
        borderTop: '1px solid rgba(255,255,255,0.07)',
        padding: '20px 48px',
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
      }}>
        <span style={{
          fontFamily: PX, fontSize: 9, fontWeight: 300,
          letterSpacing: '0.3em', color: 'rgba(255,255,255,0.18)',
          textTransform: 'uppercase',
        }}>
          © {new Date().getFullYear()} Fazilet Secgin Art Project Consultancy
        </span>
        <Link to="/admin" style={{
          fontFamily: PX, fontSize: 9, fontWeight: 300,
          letterSpacing: '0.3em', color: 'rgba(255,255,255,0.14)',
          textTransform: 'uppercase', textDecoration: 'none',
          transition: 'color 0.2s',
        }}
          onMouseEnter={e => ((e.target as HTMLElement).style.color = 'rgba(255,255,255,0.5)')}
          onMouseLeave={e => ((e.target as HTMLElement).style.color = 'rgba(255,255,255,0.14)')}
        >
          Admin
        </Link>
      </footer>

      {/* Global styles */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&family=Cormorant+Garamond:wght@300;400&display=swap');

        @keyframes shimmer {
          0%   { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }

        .artist-card-wrap:hover .artist-card-photo {
          transform: scale(1.04) !important;
        }
        .artist-card-wrap:hover .artist-card-overlay {
          background: rgba(0,0,0,0.28) !important;
        }
        .artist-card-wrap:hover .artist-card-cta {
          opacity: 1 !important;
          transform: translateY(0) !important;
        }

        /* ── Mobil responsive ── */
        @media (max-width: 768px) {
          .hero-vline { display: none !important; }

          .hero-bottom-row {
            padding: 20px 20px 28px 20px !important;
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 20px !important;
          }

          .home-section-pad {
            padding: 56px 20px 72px !important;
          }

          .artists-grid {
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 20px 14px !important;
          }

          .artist-card-wrap {
            grid-column: span 1 !important;
          }

          .editorial-strip {
            padding: 56px 20px !important;
            flex-direction: column !important;
            align-items: flex-start !important;
          }

          .editorial-strip > div:last-child {
            align-items: flex-start !important;
          }
        }
      `}</style>
    </div>
  );
}