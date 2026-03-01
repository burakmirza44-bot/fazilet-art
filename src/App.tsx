/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Artists from './pages/Artists';
import Exhibitions from './pages/Exhibitions';
import Contact from './pages/Contact';

// Admin Imports
import AdminLayout from './components/admin/AdminLayout';
import AdminDashboard from './pages/admin/Dashboard';
import ArtistManagement from './pages/admin/ArtworkManagement';
import ArtworkManagement from './pages/admin/ArtworksList';
import Publications from './pages/admin/Publications';
import AdminViewingRooms from './pages/admin/AdminViewingRooms';
import AdminExhibitions  from './pages/admin/AdminExhibitions';
import AdminUsers       from './pages/admin/AdminUsers';

// Private/Unlisted Imports
import PrivateArtistView from './pages/PrivateArtistView';

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="artists" element={<Artists />} />
          <Route path="exhibitions" element={<Exhibitions />} />
          <Route path="contact" element={<Contact />} />
        </Route>

        {/* Private/Unlisted Routes (No global layout/navigation) */}
        <Route path="/shared/artist/:id" element={<PrivateArtistView />} />

        {/* Admin Routes */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="artworks" element={<ArtworkManagement />} />
          <Route path="artists" element={<ArtistManagement />} />
          <Route path="publications" element={<Publications />} />
          <Route path="viewing-rooms"  element={<AdminViewingRooms />} />
          <Route path="exhibitions"    element={<AdminExhibitions />} />
          <Route path="users"          element={<AdminUsers />} />
        </Route>
      </Routes>
    </Router>
  );
}
