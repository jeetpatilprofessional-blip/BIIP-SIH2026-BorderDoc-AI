import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { Screening } from '@/pages/Screening'
import { CaseDetails } from '@/pages/CaseDetails'
import { IdentityGraph } from '@/pages/IdentityGraph'
import { EvidenceView } from '@/pages/EvidenceView'
import { AuditTrail } from '@/pages/AuditTrail'
import { SystemStatus } from '@/pages/SystemStatus'
import { DemoLab } from '@/pages/DemoLab'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/screening" replace />} />
      <Route element={<Layout />}>
        <Route path="/screening" element={<Screening />} />
        <Route path="/case/:caseId" element={<CaseDetails />} />
        <Route path="/case/:caseId/graph" element={<IdentityGraph />} />
        <Route path="/case/:caseId/evidence" element={<EvidenceView />} />
        <Route path="/case/:caseId/audit" element={<AuditTrail />} />
        <Route path="/system" element={<SystemStatus />} />
        <Route path="/demo" element={<DemoLab />} />
      </Route>
    </Routes>
  )
}

export default App