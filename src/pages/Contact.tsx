import { useState } from 'react';
import { motion } from 'motion/react';

const PX  = "'proxima-nova','Nunito Sans','Gill Sans MT',sans-serif";
const SER = "'Cormorant Garamond','Didot','Georgia',serif";

const OFFICES = [
  {
    city: 'London',
    address: ['4th Floor, Addey Gardens, St,', 'RG1 3BA — UK'],
    phone: '+44 7962 339 451',
    email: 'london@faziletksecgin.com',
  },
  {
    city: 'Istanbul',
    address: ['Süzer Plaza, Harbiye, Asker Ocağı Cd.', 'No:6 34367 İstanbul — Türkiye'],
    phone: '+90 538 772 92 30',
    email: 'istanbul@faziletksecgin.com',
  },
];

type FormState = 'idle' | 'sending' | 'sent' | 'error';

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [status, setStatus] = useState<FormState>('idle');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('sending');
    // Simulate send — replace with actual API call if backend email route exists
    await new Promise(r => setTimeout(r, 1200));
    setStatus('sent');
  };

  return (
    <div className="dm-page" style={{ minHeight: '100vh', background: '#fff', fontFamily: PX }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,300;6..12,400&family=Cormorant+Garamond:wght@300;400&display=swap');

        .contact-input {
          width: 100%; background: transparent;
          border: none; border-bottom: 1px solid rgba(0,0,0,0.14);
          padding: 12px 0; font-family: ${PX};
          font-size: 13px; font-weight: 300;
          color: #111; letter-spacing: 0.04em;
          outline: none; resize: none;
          transition: border-color 0.25s;
          appearance: none; -webkit-appearance: none;
        }
        .contact-input::placeholder { color: #bbb; }
        .contact-input:focus { border-bottom-color: #111; }
        select.contact-input { cursor: pointer; }
      `}</style>

      <div className="contact-wrap" style={{ maxWidth: 1360, margin: '0 auto', padding: '120px 48px 100px' }}>

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
            Get in Touch
          </p>
          <h1 style={{
            fontFamily: PX,
            fontSize: 'clamp(28px, 4vw, 48px)',
            fontWeight: 300, color: '#111',
            letterSpacing: '0.1em', margin: 0,
            textTransform: 'uppercase',
          }}>
            Contact
          </h1>
        </motion.div>

        {/* ── İki kolon: Ofisler + Form ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80 }}
          className="contact-grid">

          {/* ── Sol: Ofis bilgileri ── */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          >
            <p style={{
              fontFamily: SER,
              fontSize: 'clamp(18px, 2vw, 28px)',
              fontWeight: 300, color: '#111',
              lineHeight: 1.6, margin: '0 0 48px',
              letterSpacing: '0.02em',
            }}>
              For acquisitions, commissions, and<br />institutional inquiries.
            </p>

            {OFFICES.map((o, i) => (
              <motion.div
                key={o.city}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 + i * 0.1 }}
                style={{ marginBottom: 40 }}
              >
                <p style={{
                  fontFamily: PX, fontSize: 9, fontWeight: 400,
                  letterSpacing: '0.4em', textTransform: 'uppercase',
                  color: '#bbb', margin: '0 0 12px',
                }}>
                  {o.city} Office
                </p>
                {o.address.map((line, j) => (
                  <p key={j} style={{
                    fontFamily: PX, fontSize: 13, fontWeight: 300,
                    color: '#444', margin: '0 0 3px', letterSpacing: '0.03em',
                    lineHeight: 1.7,
                  }}>{line}</p>
                ))}
                <p style={{ margin: '10px 0 0' }}>
                  <a href={`tel:${o.phone.replace(/\s/g,'')}`} style={{
                    fontFamily: PX, fontSize: 12, fontWeight: 300,
                    color: '#111', textDecoration: 'none', letterSpacing: '0.06em',
                    borderBottom: '1px solid rgba(0,0,0,0.15)',
                    paddingBottom: 1, transition: 'border-color 0.2s',
                  }}>
                    {o.phone}
                  </a>
                </p>
              </motion.div>
            ))}

            {/* Social */}
            <div style={{ marginTop: 48, paddingTop: 32, borderTop: '1px solid rgba(0,0,0,0.07)' }}>
              <p style={{
                fontFamily: PX, fontSize: 9, fontWeight: 400,
                letterSpacing: '0.4em', textTransform: 'uppercase',
                color: '#bbb', margin: '0 0 16px',
              }}>
                Social
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { label: 'Instagram', href: 'https://www.instagram.com/faziletksecgin/' },
                  { label: 'LinkedIn', href: 'https://www.linkedin.com/in/faziletkilic/?originalSubdomain=uk' },
                ].map(s => (
                  <a key={s.label} href={s.href} target="_blank" rel="noopener noreferrer" style={{
                    fontFamily: PX, fontSize: 11, fontWeight: 300,
                    letterSpacing: '0.18em', textTransform: 'uppercase',
                    color: '#111', textDecoration: 'none',
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    transition: 'opacity 0.2s',
                  }}
                    onMouseEnter={e => ((e.currentTarget as HTMLElement).style.opacity = '0.4')}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.opacity = '1')}
                  >
                    <span style={{ fontSize: 9, color: '#ccc' }}>→</span>
                    {s.label}
                  </a>
                ))}
              </div>
            </div>
          </motion.div>

          {/* ── Sağ: Form ── */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            {status === 'sent' ? (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  padding: '48px 0',
                  borderLeft: '2px solid #111',
                  paddingLeft: 28,
                }}
              >
                <p style={{
                  fontFamily: SER, fontSize: 24, fontWeight: 300,
                  color: '#111', margin: '0 0 12px', letterSpacing: '0.02em',
                }}>
                  Thank you.
                </p>
                <p style={{
                  fontFamily: PX, fontSize: 12, fontWeight: 300,
                  color: '#888', letterSpacing: '0.04em', lineHeight: 1.8,
                }}>
                  We've received your message and will be in touch shortly.
                </p>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
                <div className="form-name-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                  <div>
                    <label style={{
                      fontFamily: PX, fontSize: 9, fontWeight: 400,
                      letterSpacing: '0.38em', color: '#bbb',
                      textTransform: 'uppercase', display: 'block', marginBottom: 8,
                    }}>Name</label>
                    <input
                      className="contact-input"
                      type="text" name="name" required
                      placeholder="Full name"
                      value={form.name} onChange={handleChange}
                    />
                  </div>
                  <div>
                    <label style={{
                      fontFamily: PX, fontSize: 9, fontWeight: 400,
                      letterSpacing: '0.38em', color: '#bbb',
                      textTransform: 'uppercase', display: 'block', marginBottom: 8,
                    }}>Email</label>
                    <input
                      className="contact-input"
                      type="email" name="email" required
                      placeholder="your@email.com"
                      value={form.email} onChange={handleChange}
                    />
                  </div>
                </div>

                <div>
                  <label style={{
                    fontFamily: PX, fontSize: 9, fontWeight: 400,
                    letterSpacing: '0.38em', color: '#bbb',
                    textTransform: 'uppercase', display: 'block', marginBottom: 8,
                  }}>Subject</label>
                  <select
                    className="contact-input"
                    name="subject" required
                    value={form.subject} onChange={handleChange}
                    style={{ color: form.subject ? '#111' : '#bbb' }}
                  >
                    <option value="" disabled>Select an inquiry type</option>
                    <option value="acquisition">Acquisition Inquiry</option>
                    <option value="commission">Commission</option>
                    <option value="exhibition">Exhibition Proposal</option>
                    <option value="press">Press & Media</option>
                    <option value="general">General</option>
                  </select>
                </div>

                <div>
                  <label style={{
                    fontFamily: PX, fontSize: 9, fontWeight: 400,
                    letterSpacing: '0.38em', color: '#bbb',
                    textTransform: 'uppercase', display: 'block', marginBottom: 8,
                  }}>Message</label>
                  <textarea
                    className="contact-input"
                    name="message" required rows={6}
                    placeholder="Your message…"
                    value={form.message} onChange={handleChange}
                    style={{ display: 'block', lineHeight: 1.7 }}
                  />
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={status === 'sending'}
                    style={{
                      fontFamily: PX, fontSize: 9, fontWeight: 400,
                      letterSpacing: '0.4em', textTransform: 'uppercase',
                      color: status === 'sending' ? '#bbb' : '#fff',
                      background: status === 'sending' ? '#ccc' : '#111',
                      border: 'none', padding: '14px 36px',
                      cursor: status === 'sending' ? 'default' : 'pointer',
                      transition: 'background 0.3s, color 0.3s',
                    }}
                    onMouseEnter={e => { if (status !== 'sending') (e.currentTarget.style.background = '#333'); }}
                    onMouseLeave={e => { if (status !== 'sending') (e.currentTarget.style.background = '#111'); }}
                  >
                    {status === 'sending' ? 'Sending…' : 'Send Message'}
                  </button>
                </div>
              </form>
            )}
          </motion.div>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .contact-wrap { padding: 100px 20px 64px !important; }
          .contact-grid { grid-template-columns: 1fr !important; gap: 48px !important; }
          .form-name-row { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
