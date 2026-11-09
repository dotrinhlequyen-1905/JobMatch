import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireRole } from './auth'
import Layout from './components/Layout'
import { AdminAudit, AdminDashboard, AdminModeration, AdminPayments, AdminReports, AdminUsers } from './pages/admin/AdminPages'
import MyApplications from './pages/candidate/MyApplications'
import MyCVs from './pages/candidate/MyCVs'
import Recommendations from './pages/candidate/Recommendations'
import Evaluation from './pages/candidate/Evaluation'
import HRJobDetail from './pages/hr/HRJobDetail'
import { HRCompany, HRDashboard, HRJobs } from './pages/hr/HRPages'
import { ForgotPassword, Login, Register, ResetPassword, VerifyEmail } from './pages/public/Auth'
import { Companies, CompanyDetail } from './pages/public/Companies'
import Home from './pages/public/Home'
import JobDetail from './pages/public/JobDetail'
import Jobs from './pages/public/Jobs'
import { Checkout, Orders, Packages } from './pages/shared/Payments'
import Profile from './pages/shared/Profile'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="jobs/:id" element={<JobDetail />} />
            <Route path="companies" element={<Companies />} />
            <Route path="companies/:id" element={<CompanyDetail />} />
            <Route path="login" element={<Login />} />
            <Route path="register" element={<Register />} />
            <Route path="forgot-password" element={<ForgotPassword />} />
            <Route path="reset-password" element={<ResetPassword />} />
            <Route path="verify-email" element={<VerifyEmail />} />
            <Route path="premium" element={<RequireRole roles={['CANDIDATE', 'HR']}><Packages /></RequireRole>} />

            <Route path="profile" element={<RequireRole roles={['CANDIDATE', 'HR', 'ADMIN']}><Profile /></RequireRole>} />
            <Route path="orders" element={<RequireRole roles={['CANDIDATE', 'HR']}><Orders /></RequireRole>} />
            <Route path="orders/:id" element={<RequireRole roles={['CANDIDATE', 'HR', 'ADMIN']}><Checkout /></RequireRole>} />

            <Route path="candidate/cvs" element={<RequireRole roles={['CANDIDATE']}><MyCVs /></RequireRole>} />
            <Route path="candidate/recommendations" element={<RequireRole roles={['CANDIDATE']}><Recommendations /></RequireRole>} />
            <Route path="candidate/evaluation" element={<RequireRole roles={['CANDIDATE']}><Evaluation /></RequireRole>} />
            <Route path="candidate/applications" element={<RequireRole roles={['CANDIDATE']}><MyApplications /></RequireRole>} />

            <Route path="hr" element={<RequireRole roles={['HR']}><HRDashboard /></RequireRole>} />
            <Route path="hr/company" element={<RequireRole roles={['HR']}><HRCompany /></RequireRole>} />
            <Route path="hr/jobs" element={<RequireRole roles={['HR']}><HRJobs /></RequireRole>} />
            <Route path="hr/jobs/:id" element={<RequireRole roles={['HR']}><HRJobDetail /></RequireRole>} />
            <Route path="hr/packages" element={<RequireRole roles={['HR']}><Packages /></RequireRole>} />

            <Route path="admin" element={<RequireRole roles={['ADMIN']}><AdminDashboard /></RequireRole>} />
            <Route path="admin/moderation" element={<RequireRole roles={['ADMIN']}><AdminModeration /></RequireRole>} />
            <Route path="admin/users" element={<RequireRole roles={['ADMIN']}><AdminUsers /></RequireRole>} />
            <Route path="admin/payments" element={<RequireRole roles={['ADMIN']}><AdminPayments /></RequireRole>} />
            <Route path="admin/audit" element={<RequireRole roles={['ADMIN']}><AdminAudit /></RequireRole>} />
            <Route path="admin/reports" element={<RequireRole roles={['ADMIN']}><AdminReports /></RequireRole>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
