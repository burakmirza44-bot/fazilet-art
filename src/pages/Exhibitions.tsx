import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Link } from 'react-router-dom';

const PX  = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const SER = "'Cormorant Garamond','Didot','Georgia',serif";

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
}

const STATUS_LABEL: Record<string, string> = {
  upcoming: 'Upcoming',
  current:  'Current',
  past:     'Past',
};

const STATUS_COLOR: Record<string, string> = {
  upcoming: '#111',
  current:  '#1a7a4a',
  past:     '#bbb',
};

export default function Exhibitions() {
  const [exhibitions, setExhibitions]   = useState<Exhibition[]>([]);
  const [loading, setLoading]           = useState(true);
  const [expandedId, setExpandedId]     = useState<number | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/exhibitions/public')
      .then(r => r.ok ? r.json() : [])
      .then(data => setExhibitions(data))
      .catch(() => setExhibitions([]))
      .finally(() => setLoading(false));
  }, []);

  // Dışarı tıklayınca kapat
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setExpandedId(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ESC ile kapat
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpandedId(null);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Status sırası: current → upcoming → past
  const ordered = [
    ...exhibitions.filter(e => e.status === 'current'),
    ...exhibitions.filter(e => e.status === 'upcoming'),
    ...exhibitions.filter(e => e.status === 'past'),
  ];

  return (
    <div className="dm-page" style={{ minHeight: '100vh', background: '#fff', fontFamily: PX }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&family=Cormorant+Garamond:wght@300;400&display=swap');
      `}</style>

      <div className="exhibitions-wrap" style={{ maxWidth: 1360, margin: '0 auto', padding: '120px 48px 100px' }}>

        {/* ── Header ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          style={{ marginBottom: 80, paddingBottom: 32, borderBottom: '1px solid rgba(0,0,0,0.08)' }}
        >
          <p style={{
            fontFamily: PX, fontSize: 9, fontWeight: 400,
            letterSpacing: '0.45em', color: '#bbb',
            textTransform: 'uppercase', margin: '0 0 14px',
          }}>
            Programme
          </p>
          <h1 style={{
            fontFamily: PX, fontSize: 'clamp(28px, 4vw, 48px)',
            fontWeight: 300, color: '#111',
            letterSpacing: '0.1em', margin: 0, textTransform: 'uppercase',
          }}>
            Exhibitions
          </h1>
        </motion.div>

        {/* ── Loading ── */}
        {loading && (
          <div style={{ padding: '80px 0', textAlign: 'center',
            fontFamily: PX, fontSize: 9, letterSpacing: '0.35em',
            textTransform: 'uppercase', color: '#ccc' }}>
            Loading…
          </div>
        )}

        {/* ── Empty ── */}
        {!loading && ordered.length === 0 && (
          <div style={{ padding: '80px 0', textAlign: 'center' }}>
            <p style={{ fontFamily: SER, fontSize: 22, fontWeight: 300, color: '#aaa', margin: '0 0 12px' }}>
              No exhibitions at this time
            </p>
            <p style={{ fontFamily: PX, fontSize: 10, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#ccc' }}>
              Check back soon
            </p>
          </div>
        )}

        {/* ── Sergi Listesi ── */}
        {!loading && ordered.length > 0 && (
          <div ref={wrapRef}>
            {ordered.map((ex, i) => {
              const isOpen = expandedId === ex.id;
              const hasDetail = !!(ex.description || ex.cover_url || ex.venue);

              return (
                <motion.div
                  key={ex.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.08 + i * 0.07, ease: [0.22, 1, 0.36, 1] }}
                >
                  {/* ── Satır (tıklanabilir) ── */}
                  <div
                    onClick={() => hasDetail && setExpandedId(isOpen ? null : ex.id)}
                    className="exhibition-row"
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '120px 1fr auto',
                      alignItems: 'start',
                      gap: '0 40px',
                      padding: '32px 0',
                      borderBottom: isOpen ? 'none' : '1px solid rgba(0,0,0,0.07)',
                      cursor: hasDetail ? 'pointer' : 'default',
                      transition: 'background 0.2s',
                    }}
                  >
                    {/* Status / Tarih */}
                    <div>
                      <span style={{
                        fontFamily: PX, fontSize: 8, fontWeight: 400,
                        letterSpacing: '0.38em', textTransform: 'uppercase',
                        color: STATUS_COLOR[ex.status] ?? '#bbb',
                        display: 'block', marginBottom: 6,
                        padding: '3px 0',
                        borderBottom: ex.status !== 'past' ? `1px solid ${STATUS_COLOR[ex.status]}` : 'none',
                      }}>
                        {STATUS_LABEL[ex.status] ?? ex.status}
                      </span>
                      {(ex.start_date || ex.end_date) && (
                        <span style={{
                          fontFamily: PX, fontSize: 10, fontWeight: 300,
                          letterSpacing: '0.15em', color: '#aaa',
                          textTransform: 'uppercase', display: 'block', marginTop: 8,
                        }}>
                          {ex.start_date}
                          {ex.end_date && ex.end_date !== ex.start_date ? ` — ${ex.end_date}` : ''}
                        </span>
                      )}
                    </div>

                    {/* İçerik */}
                    <div>
                      <h2 style={{
                        fontFamily: SER, fontSize: 'clamp(20px, 2vw, 30px)',
                        fontWeight: 300, color: '#111', letterSpacing: '0.02em',
                        margin: '0 0 8px', transition: 'opacity 0.3s',
                      }}>
                        {ex.title}
                      </h2>
                      {ex.subtitle && (
                        <p style={{
                          fontFamily: PX, fontSize: 12, fontWeight: 300,
                          color: '#888', letterSpacing: '0.04em',
                          margin: '0 0 8px', lineHeight: 1.6,
                        }}>
                          {ex.subtitle}
                        </p>
                      )}
                      {ex.artists && (
                        <p style={{
                          fontFamily: PX, fontSize: 10, fontWeight: 300,
                          color: '#aaa', letterSpacing: '0.15em',
                          margin: '0 0 6px', textTransform: 'uppercase',
                        }}>
                          {ex.artists}
                        </p>
                      )}
                      {(ex.venue || ex.location) && (
                        <p style={{
                          fontFamily: PX, fontSize: 9, fontWeight: 400,
                          letterSpacing: '0.28em', textTransform: 'uppercase',
                          color: '#ccc', margin: 0,
                        }}>
                          {ex.venue ? `${ex.venue}${ex.location ? ', ' : ''}` : ''}{ex.location}
                        </p>
                      )}
                    </div>

                    {/* Sağ — expand göstergesi */}
                    <div style={{ paddingTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                      {hasDetail && (
                        <span style={{
                          fontFamily: PX, fontSize: 9, fontWeight: 300,
                          letterSpacing: '0.28em', color: '#bbb',
                          textTransform: 'uppercase',
                          transition: 'color 0.25s',
                        }}>
                          {isOpen ? 'Close' : 'Details'}
                        </span>
                      )}
                      {/* Ok işareti */}
                      {hasDetail && (
                        <svg
                          width="14" height="14" viewBox="0 0 14 14" fill="none"
                          style={{
                            transition: 'transform 0.35s ease',
                            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                            color: '#bbb',
                          }}
                        >
                          <path d="M2 4.5L7 9.5L12 4.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </div>
                  </div>

                  {/* ── Accordion Paneli ── */}
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
                        style={{ overflow: 'hidden', borderBottom: '1px solid rgba(0,0,0,0.07)' }}
                      >
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: ex.cover_url ? '320px 1fr' : '1fr',
                          gap: '0 60px',
                          padding: '36px 0 48px',
                          background: '#fafafa',
                          marginLeft: -48,
                          marginRight: -48,
                          paddingLeft: 48,
                          paddingRight: 48,
                        }}>
                          {/* Kapak görseli */}
                          {ex.cover_url && (
                            <div style={{
                              width: '100%', aspectRatio: '4/3',
                              overflow: 'hidden', background: '#eee', flexShrink: 0,
                            }}>
                              <img
                                src={ex.cover_url}
                                alt={ex.title}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                              />
                            </div>
                          )}

                          {/* Detaylar */}
                          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 20 }}>

                            {/* Başlık tekrar (büyük) */}
                            <div>
                              <h3 style={{
                                fontFamily: SER,
                                fontSize: 'clamp(22px, 2.5vw, 36px)',
                                fontWeight: 300, color: '#111',
                                letterSpacing: '0.02em', margin: '0 0 6px',
                              }}>
                                {ex.title}
                              </h3>
                              {ex.subtitle && (
                                <p style={{
                                  fontFamily: PX, fontSize: 12,
                                  color: '#888', margin: 0, lineHeight: 1.7,
                                }}>
                                  {ex.subtitle}
                                </p>
                              )}
                            </div>

                            {/* Meta bilgiler */}
                            <div style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                              gap: '14px 32px',
                            }}>
                              {ex.artists && (
                                <div>
                                  <p style={{ fontFamily: PX, fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase', color: '#bbb', margin: '0 0 4px' }}>Artists</p>
                                  <p style={{ fontFamily: PX, fontSize: 12, color: '#555', margin: 0 }}>{ex.artists}</p>
                                </div>
                              )}
                              {ex.venue && (
                                <div>
                                  <p style={{ fontFamily: PX, fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase', color: '#bbb', margin: '0 0 4px' }}>Venue</p>
                                  <p style={{ fontFamily: PX, fontSize: 12, color: '#555', margin: 0 }}>{ex.venue}</p>
                                </div>
                              )}
                              {ex.location && (
                                <div>
                                  <p style={{ fontFamily: PX, fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase', color: '#bbb', margin: '0 0 4px' }}>Location</p>
                                  <p style={{ fontFamily: PX, fontSize: 12, color: '#555', margin: 0 }}>{ex.location}</p>
                                </div>
                              )}
                              {(ex.start_date || ex.end_date) && (
                                <div>
                                  <p style={{ fontFamily: PX, fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase', color: '#bbb', margin: '0 0 4px' }}>Dates</p>
                                  <p style={{ fontFamily: PX, fontSize: 12, color: '#555', margin: 0 }}>
                                    {ex.start_date}{ex.end_date && ex.end_date !== ex.start_date ? ` — ${ex.end_date}` : ''}
                                  </p>
                                </div>
                              )}
                            </div>

                            {/* Description */}
                            {ex.description && (
                              <div>
                                <p style={{ fontFamily: PX, fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase', color: '#bbb', margin: '0 0 10px' }}>About</p>
                                <p style={{
                                  fontFamily: PX, fontSize: 13, fontWeight: 300,
                                  color: '#555', lineHeight: 1.85,
                                  margin: 0, maxWidth: 560,
                                }}>
                                  {ex.description}
                                </p>
                              </div>
                            )}

                            {/* Kapat */}
                            <div>
                              <button
                                onClick={() => setExpandedId(null)}
                                style={{
                                  fontFamily: PX, fontSize: 9, fontWeight: 400,
                                  letterSpacing: '0.38em', textTransform: 'uppercase',
                                  color: '#aaa', background: 'none', border: 'none',
                                  cursor: 'pointer', padding: '8px 0',
                                  transition: 'color 0.2s',
                                }}
                                onMouseEnter={e => (e.currentTarget.style.color = '#111')}
                                onMouseLeave={e => (e.currentTarget.style.color = '#aaa')}
                              >
                                ↑ Close
                              </button>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* ── CTA Strip ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          style={{
            marginTop: 80, padding: '48px',
            background: '#0a0a0a',
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', gap: 32, flexWrap: 'wrap',
          }}
        >
          <p style={{
            fontFamily: SER, fontSize: 'clamp(16px, 2vw, 24px)',
            fontWeight: 300, color: '#fff', letterSpacing: '0.02em',
            lineHeight: 1.5, margin: 0,
          }}>
            Interested in collaborating<br />or proposing a project?
          </p>
          <Link to="/contact" style={{
            fontFamily: PX, fontSize: 9, fontWeight: 400,
            letterSpacing: '0.4em', textTransform: 'uppercase',
            color: '#fff', textDecoration: 'none',
            border: '1px solid rgba(255,255,255,0.3)',
            padding: '12px 28px', transition: 'all 0.3s', flexShrink: 0,
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#fff'; (e.currentTarget as HTMLElement).style.color = '#000'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = '#fff'; }}
          >
            Get in Touch
          </Link>
        </motion.div>
      </div>

      <style>{`
        .exhibition-row:hover h2 { opacity: 0.55 !important; }
        @media (max-width: 768px) {
          .exhibitions-wrap { padding: 100px 20px 64px !important; }
          .exhibition-row { grid-template-columns: 1fr !important; gap: 12px !important; padding: 24px 0 !important; }
        }
      `}</style>
    </div>
  );
}
