import { useState } from 'react'
import { api, errMsg } from '../api'
import { useAuth } from '../auth'
import { Alert, Modal } from './ui'

const LABEL = { JOB: 'tin tuyển dụng', COMPANY: 'công ty', USER: 'người dùng' }

export default function ReportButton({ type, id }: { type: 'JOB' | 'COMPANY' | 'USER'; id: number }) {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  if (!user || user.role === 'ADMIN') return null
  const send = async () => {
    try {
      await api.post('/reports', { target_type: type, target_id: id, reason })
      setMsg({ kind: 'success', text: 'Đã gửi báo cáo. Quản trị viên sẽ xem xét và phản hồi.' }); setReason('')
    } catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
  }
  return (
    <>
      <button className="text-xs text-slate-500 hover:text-rose-600 hover:underline" onClick={() => { setMsg(null); setOpen(true) }}>⚑ Báo cáo vi phạm</button>
      <Modal open={open} onClose={() => setOpen(false)} title={`Báo cáo ${LABEL[type]}`}>
        <div className="space-y-3">
          {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
          {msg?.kind !== 'success' && <>
            <div><label className="label">Mô tả vi phạm (tối thiểu 10 ký tự)</label>
              <textarea className="input h-28" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Ví dụ: yêu cầu ứng viên đóng phí, thông tin sai sự thật..." /></div>
            <div className="flex justify-end gap-2">
              <button className="btn-outline" onClick={() => setOpen(false)}>Hủy</button>
              <button className="btn-danger" disabled={reason.trim().length < 10} onClick={send}>Gửi báo cáo</button>
            </div>
          </>}
        </div>
      </Modal>
    </>
  )
}
