import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';

import Dashboard from './pages/admin/Dashboard';
import Students from './pages/admin/Students';
import AssignSubjects from './pages/admin/AssignSubjects';
import Exceptions from './pages/admin/Exceptions';
import AddDropRequests from './pages/admin/AddDropRequests';
import AdminTimetables from './pages/admin/Timetables';
import Subjects from './pages/admin/Subjects';

import MySubjects from './pages/student/MySubjects';
import Progress from './pages/student/Progress';
import AddDrop from './pages/student/AddDrop';
import StudentTimetables from './pages/student/Timetables';

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === 'admin' ? '/admin' : '/student'} replace />;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
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
          </Route>

          <Route path="/student" element={
            <ProtectedRoute role="student"><Layout /></ProtectedRoute>
          }>
            <Route index element={<MySubjects />} />
            <Route path="progress" element={<Progress />} />
            <Route path="add-drop" element={<AddDrop />} />
            <Route path="timetables" element={<StudentTimetables />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
