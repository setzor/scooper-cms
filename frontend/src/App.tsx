import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';

// Paper (frontend) pages
import PaperLayout from './pages/paper/PaperLayout';
import PaperHome from './pages/paper/PaperHome';
import PaperStory from './pages/paper/PaperStory';

// CMS (backend) pages
import CMSLayout from './pages/cms/CMSLayout';
import CMSDashboard from './pages/cms/CMSDashboard';
import CMSStories from './pages/cms/CMSStories';
import CMSCreate from './pages/cms/CMSCreate';
import CMSEdit from './pages/cms/CMSEdit';
import CMSSettings from './pages/cms/CMSSettings';
import CMSLogin from './pages/cms/CMSLogin';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Routes>
          {/* Paper (public) routes */}
          <Route path="/" element={<PaperLayout />}>
            <Route index element={<PaperHome />} />
            <Route path="story/:slug" element={<PaperStory />} />
          </Route>

          {/* CMS routes */}
          <Route path="/cms" element={<CMSLayout />}>
            <Route index element={<Navigate to="/cms/dashboard" replace />} />
            <Route path="dashboard" element={<CMSDashboard />} />
            <Route path="stories" element={<CMSStories />} />
            <Route path="create" element={<CMSCreate />} />
            <Route path="edit/:id" element={<CMSEdit />} />
            <Route path="settings" element={<CMSSettings />} />
          </Route>

          {/* CMS Login */}
          <Route path="/cms/login" element={<CMSLogin />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
