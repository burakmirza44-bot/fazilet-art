import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Image as ImageIcon,
  BookOpen,
  MonitorPlay,
  Settings,
  ExternalLink,
  Users,
  CalendarDays,
  UserCog,
} from 'lucide-react';

export default function AdminLayout() {
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/admin', icon: LayoutDashboard },
    { name: 'Artworks', path: '/admin/artworks', icon: ImageIcon },
    { name: 'Artists & Links', path: '/admin/artists', icon: Users },
    { name: 'Publications', path: '/admin/publications', icon: BookOpen },
    { name: 'Exhibitions',   path: '/admin/exhibitions',   icon: CalendarDays },
    { name: 'Viewing Rooms', path: '/admin/viewing-rooms', icon: MonitorPlay },
    { name: 'Users',         path: '/admin/users',         icon: UserCog },
  ];

  return (
    <div className="min-h-screen flex bg-[#F9F9F9] text-ink font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-ink/5 fixed h-full flex flex-col">
        <div className="p-8">
          <Link to="/" className="block h-6 hover:opacity-80 transition-opacity">
            <img src="/logo.png" alt="FAZILET SECGIN" className="h-full w-auto object-contain" />
          </Link>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
                             (item.path !== '/admin' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-md transition-colors duration-200 ${
                  isActive 
                    ? 'bg-ink/5 text-ink font-medium' 
                    : 'text-ink/60 hover:bg-ink/5 hover:text-ink'
                }`}
              >
                <Icon size={18} strokeWidth={isActive ? 2 : 1.5} />
                <span className="text-sm tracking-wide">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-ink/5 space-y-1">
          <a
            href="/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-3 px-4 py-3 w-full rounded-md text-ink/60 hover:bg-ink/5 hover:text-ink transition-colors duration-200"
          >
            <ExternalLink size={18} strokeWidth={1.5} />
            <span className="text-sm tracking-wide">View Site</span>
          </a>
          <button className="flex items-center space-x-3 px-4 py-3 w-full text-left rounded-md text-ink/60 hover:bg-ink/5 hover:text-ink transition-colors duration-200">
            <Settings size={18} strokeWidth={1.5} />
            <span className="text-sm tracking-wide">Settings</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 p-10">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
