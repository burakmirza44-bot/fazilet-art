import { Link, Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Layout() {
  const location = useLocation();
  const isHome = location.pathname === '/';
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';

  // Sayfa değişince menüyü kapat
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Scroll takibi — home'da beyaz bölüme geçince nav rengini değiştir
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const navLinks = [
    { name: 'ARTISTS', path: '/artists' },
    { name: 'EXHIBITIONS', path: '/exhibitions' },
    { name: 'CONTACT', path: '/contact' },
  ];

  // Header arka plan — CSS değişkenlerini kullan
  const headerBg =
    scrolled || !isHome
      ? isDark
        ? 'rgba(14,14,14,0.95)'
        : 'rgba(255,255,255,0.96)'
      : 'transparent';

  const headerBorder =
    scrolled || !isHome
      ? isDark
        ? '1px solid rgba(255,255,255,0.06)'
        : '1px solid rgba(0,0,0,0.07)'
      : 'none';

  // Nav metin rengi
  const navColor =
    isHome && !scrolled
      ? 'text-white/80 hover:text-white'
      : isDark
        ? 'text-white/70 hover:text-white'
        : 'text-ink/70 hover:text-ink';

  return (
    <div className={`min-h-screen flex flex-col relative ${isDark ? 'bg-[#0e0e0e] text-[#e8e8e8]' : 'bg-white text-ink'}`}>
      {/* Global Vertical Line — sadece iç sayfalarda */}
      {!isHome && (
        <div className={`fixed left-8 md:left-16 top-0 bottom-0 w-[1px] z-40 pointer-events-none ${isDark ? 'bg-white/6' : 'bg-ink/8'}`}></div>
      )}

      <header
        className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
        style={{
          padding: scrolled || !isHome ? '14px 0' : '40px 0',
          background: headerBg,
          backdropFilter: scrolled || !isHome ? 'blur(12px)' : 'none',
          borderBottom: headerBorder,
        }}
      >
        <div className="px-8 md:px-16 flex justify-between items-center">
          {/* Logo — sadece iç sayfalarda göster, home sayfasında hero logosu var */}
          <div className="flex-1">
            {(!isHome || scrolled) && (
              <Link to="/" className="inline-block h-5 md:h-6 hover:opacity-70 transition-opacity z-50">
                <img
                  src="/logo.png"
                  alt="FAZILET SECGIN"
                  className={`h-full w-auto object-contain ${isDark ? 'brightness-0 invert' : ''}`}
                />
              </Link>
            )}
          </div>

          <nav className="hidden md:flex items-center space-x-8">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                to={link.path}
                className={`text-xs tracking-[0.2em] transition-colors duration-300 relative group ${navColor}`}
              >
                {link.name}
                <span className="absolute -bottom-2 left-0 w-0 h-[1px] bg-current transition-all duration-300 group-hover:w-full"></span>
              </Link>
            ))}

            {/* Gece/Gündüz Toggle — desktop */}
            <button
              onClick={toggle}
              aria-label={isDark ? 'Gündüz moduna geç' : 'Gece moduna geç'}
              className={`p-1.5 rounded-full transition-all duration-300 ${
                isHome && !scrolled
                  ? 'text-white/70 hover:text-white'
                  : isDark
                    ? 'text-white/60 hover:text-white'
                    : 'text-ink/50 hover:text-ink'
              }`}
            >
              {isDark
                ? <Sun size={15} strokeWidth={1.5} />
                : <Moon size={15} strokeWidth={1.5} />
              }
            </button>
          </nav>

          {/* Mobile: Toggle + Hamburger */}
          <div className="md:hidden flex items-center gap-3">
            <button
              onClick={toggle}
              aria-label={isDark ? 'Gündüz moduna geç' : 'Gece moduna geç'}
              className={`p-1.5 transition-opacity hover:opacity-60 ${isHome && !scrolled ? 'text-white' : isDark ? 'text-white/70' : 'text-ink'}`}
            >
              {isDark
                ? <Sun size={16} strokeWidth={1.5} />
                : <Moon size={16} strokeWidth={1.5} />
              }
            </button>

            <button
              onClick={() => setMenuOpen(prev => !prev)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              className={`flex flex-col justify-center space-y-1.5 p-2 transition-opacity hover:opacity-60 ${isHome && !scrolled ? 'text-white' : isDark ? 'text-white' : 'text-ink'}`}
            >
              <span
                className="w-6 h-[1px] bg-current block transition-transform duration-300"
                style={{ transform: menuOpen ? 'translateY(5px) rotate(45deg)' : 'none' }}
              />
              <span
                className="w-6 h-[1px] bg-current block transition-all duration-300"
                style={{ opacity: menuOpen ? 0 : 1, transform: menuOpen ? 'scaleX(0)' : 'none' }}
              />
              <span
                className="w-6 h-[1px] bg-current block transition-transform duration-300"
                style={{ transform: menuOpen ? 'translateY(-11px) rotate(-45deg)' : 'none' }}
              />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Full-Screen Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="fixed inset-0 z-40 md:hidden flex flex-col items-center justify-center"
            style={{
              background: isHome
                ? 'rgba(10,10,10,0.97)'
                : isDark
                  ? 'rgba(14,14,14,0.97)'
                  : 'rgba(255,255,255,0.97)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <nav className="flex flex-col items-center space-y-8">
              {navLinks.map((link, i) => (
                <motion.div
                  key={link.name}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                >
                  <Link
                    to={link.path}
                    className={`text-xl tracking-[0.25em] font-light transition-opacity hover:opacity-60 ${
                      isHome || isDark ? 'text-white' : 'text-ink'
                    }`}
                  >
                    {link.name}
                  </Link>
                </motion.div>
              ))}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="flex-grow flex flex-col">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="flex-grow flex flex-col"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className={`py-12 md:py-16 px-6 md:px-24 border-t relative z-30 ${isDark ? 'bg-[#0e0e0e] border-white/6' : 'bg-white border-ink/10'}`}>
        <div className={`max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-12 text-xs tracking-wider leading-relaxed md:pl-24 ${isDark ? 'text-white/50' : 'text-ink/60'}`}>
          <div>
            <p className={`font-medium mb-4 tracking-[0.2em] ${isDark ? 'text-white/80' : 'text-ink'}`}>UK OFFICE</p>
            <p>4th Floor, Addey Gardens, St,</p>
            <p>RG1 3BA UK</p>
            <p className={`mt-4 cursor-pointer transition-colors ${isDark ? 'hover:text-white' : 'hover:text-ink'}`}>+44 7962339451</p>
          </div>
          <div>
            <p className={`font-medium mb-4 tracking-[0.2em] ${isDark ? 'text-white/80' : 'text-ink'}`}>TURKEY OFFICE</p>
            <p>Süzer plaza, Harbiye, Asker Ocağı Cd.</p>
            <p>No:6 34367 İstanbul, Turkey</p>
            <p className={`mt-4 cursor-pointer transition-colors ${isDark ? 'hover:text-white' : 'hover:text-ink'}`}>+90 538 772 92 30</p>
          </div>
          <div className="flex flex-col space-y-4">
            <p className={`font-medium mb-0 tracking-[0.2em] ${isDark ? 'text-white/80' : 'text-ink'}`}>SOCIAL</p>
            <a href="https://www.instagram.com/faziletksecgin/" target="_blank" rel="noopener noreferrer" className={`transition-colors block w-fit ${isDark ? 'hover:text-white' : 'hover:text-ink'}`}>Instagram</a>
            <a href="https://www.linkedin.com/in/faziletkilic/?originalSubdomain=uk" target="_blank" rel="noopener noreferrer" className={`transition-colors block w-fit ${isDark ? 'hover:text-white' : 'hover:text-ink'}`}>LinkedIn</a>
            <a href="#" className={`transition-colors block w-fit ${isDark ? 'hover:text-white' : 'hover:text-ink'}`}>Artsy</a>
          </div>
        </div>
        <div className={`max-w-7xl mx-auto md:pl-24 mt-10 md:mt-16 pt-8 border-t flex justify-end text-[10px] uppercase tracking-widest ${isDark ? 'border-white/5 text-white/25' : 'border-ink/5 text-ink/40'}`}>
          <Link to="/admin" className={`transition-colors ${isDark ? 'hover:text-white' : 'hover:text-ink'}`}>Admin</Link>
        </div>
      </footer>
    </div>
  );
}
