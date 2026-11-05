import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { FeedbackProvider } from './context/FeedbackContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Home from './pages/Home';
import Login from './pages/Login';

import Dashboard from './pages/admin/Dashboard';
import Students from './pages/admin/Students';
import AssignSubjects from './pages/admin/AssignSubjects';
import Exceptions from './pages/admin/Exceptions';
import AddDropRequests from './pages/admin/AddDropRequests';
import AdminTimetables from './pages/admin/Timetables';
import Subjects from './pages/admin/Subjects';
import Venues from './pages/admin/Venues';

import MySubjects from './pages/student/MySubjects';
import Progress from './pages/student/Progress';
import AddDrop from './pages/student/AddDrop';
import StudentTimetables from './pages/student/Timetables';
import Profile from './pages/student/Profile';

// Signed-out visitors land on the home page; signed-in users skip straight
// to their dashboard.
function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">Loading...</div>;
  if (!user) return <Home />;
  return <Navigate to={user.role === 'admin' ? '/admin' : '/student'} replace />;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <FeedbackProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<HomeRedirect />} />

            <Route path="/admin" element={
              <ProtectedRoute role="admin"><Layout /></ProtectedRoute>
            }>
              <Route index element={<Dashboard />} />
              <Route path="students" element={<Students />} />
              <Route path="assign" element={<AssignSubjects />} />
              <Route path="exceptions" element={<Exceptions />} />
              <Route path="add-drop" element={<AddDropRequests />} />
              <Route path="timetables" element={<AdminTimetables />} />
              <Route path="subjects" element={<Subjects />} />
              <Route path="venues" element={<Venues />} />
            </Route>

            <Route path="/student" element={
              <ProtectedRoute role="student"><Layout /></ProtectedRoute>
            }>
              <Route index element={<MySubjects />} />
              <Route path="progress" element={<Progress />} />
              <Route path="add-drop" element={<AddDrop />} />
              <Route path="timetables" element={<StudentTimetables />} />
              <Route path="profile" element={<Profile />} />
            </Route>
          </Routes>
        </FeedbackProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
