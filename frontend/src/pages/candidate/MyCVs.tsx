import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, d, errMsg, SENIORITY_VI, type CV } from '../../api'
import { Alert, Empty, Modal, PageTitle, SkillChips, Spinner } from '../../components/ui'

export default function MyCVs() {
  const [cvs, setCvs] = useState<CV[] | null>(null)
  const [mode, setMode] = useState<'file' | 'text'>('file')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [view, setView] = useState<CV | null>(null)
  const [edit, setEdit] = useState({ skills: '', years: 0, title: '' })

  const load = () => api.get('/cvs').then((r) => setCvs(r.data))
  useEffect(() => { load() }, [])
  const hasPending = cvs?.some((cv) => cv.processing_status === 'PENDING') ?? false
  useEffect(() => {
    if (!hasPending) return
    const timer = setInterval(() => { load().catch(() => {}) }, 4000)
    return () => clearInterval(timer)
  }, [hasPending])

  const upload = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setMsg(null)
    const fd = new FormData()
    if (mode === 'file' && file) fd.append('file', file)
    if (mode === 'text') fd.append('text', text)
    if (title) fd.append('title', title)
    try {
      const r = await api.post('/cvs', fd)
      setMsg({ kind: 'success', text: r.data.processing_status === 'PENDING' ? 'Đã nhận CV. Hệ thống đang chuẩn bị dữ liệu so khớp.' : `Đã phân tích CV: nhận diện ${r.data.skills.length} kỹ năng, ${r.data.years} năm kinh nghiệm.` })
      setFile(null); setText(''); setTitle(''); load(); openView(r.data)
    } catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
    setBusy(false)
  }

  const openView = async (cv: CV) => {
    const r = await api.get(`/cvs/${cv.id}`)
    setView(r.data); setEdit({ skills: r.data.skills.join(', '), years: r.data.years, title: r.data.title })
  }
  const save = async () => {
    if (!view) return
    await api.put(`/cvs/${view.id}`, { title: edit.title, years: edit.years, skills: edit.skills.split(',').map((s) => s.trim()).filter(Boolean) })
    setView(null); load()
  }
  const setDefault = async (cv: CV) => { await api.put(`/cvs/${cv.id}`, { is_default: true }); load() }
  const remove = async (cv: CV) => {
    if (!confirm('Xóa CV này?')) return
    try { await api.delete(`/cvs/${cv.id}`); load() } catch (x) { alert(errMsg(x)) }
  }
  const download = async (cv: CV) => {
    const r = await api.get(`/cvs/${cv.id}/file`, { responseType: 'blob' })
    window.open(URL.createObjectURL(r.data))
  }

  return (
    <div>
      <PageTitle title="CV của tôi" sub="Tải CV lên — AI tự trích xuất kỹ năng, kinh nghiệm và dùng để gợi ý việc làm phù hợp." />
      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <form className="card h-fit space-y-3 p-4" onSubmit={upload}>
          <div className="flex gap-1 border-b border-slate-200">
            <button type="button" className={`tab ${mode === 'file' ? 'tab-active' : ''}`} onClick={() => setMode('file')}>Tải file</button>
            <button type="button" className={`tab ${mode === 'text' ? 'tab-active' : ''}`} onClick={() => setMode('text')}>Dán nội dung</button>
          </div>
          {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
          <div><label className="label">Tên CV</label><input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="VD: CV Backend Java" /></div>
          {mode === 'file' ? (
            <label className="block cursor-pointer rounded-lg border-2 border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 hover:border-brand-500">
              <input type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              {file ? <span className="font-medium text-slate-800">{file.name}</span> : <>Chọn file <b>PDF / DOCX</b> (tối đa 5MB)</>}
            </label>
          ) : (
            <textarea className="input h-48" value={text} onChange={(e) => setText(e.target.value)} placeholder="Dán toàn bộ nội dung CV..." />
          )}
          <button className="btn-primary w-full" disabled={busy || (mode === 'file' ? !file : text.trim().length < 50)}>
            {busy ? 'AI đang phân tích...' : 'Tải lên & phân tích'}
          </button>
        </form>

        <div>
          {!cvs ? <Spinner /> : cvs.length === 0 ? <Empty>Bạn chưa có CV nào.</Empty> : (
            <div className="space-y-3">
              {cvs.map((cv) => (
                <div key={cv.id} className="card p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold">{cv.title} {cv.is_default && <span className="chip ml-1 bg-brand-100 text-brand-700">Mặc định</span>}</div>
                      <div className="text-xs text-slate-500">{cv.role_display} · {SENIORITY_VI[cv.seniority]} · {cv.years} năm KN · tải lên {d(cv.created_at)}</div>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <button className="btn-outline btn-sm" onClick={() => openView(cv)}>Xem / sửa</button>
                      <Link className="btn-outline btn-sm" to={`/candidate/evaluation?cv_id=${cv.id}`}>Đánh giá CV</Link>
                      {cv.has_file && <button className="btn-outline btn-sm" onClick={() => download(cv)}>File gốc</button>}
                      {!cv.is_default && <button className="btn-outline btn-sm" onClick={() => setDefault(cv)}>Đặt mặc định</button>}
                      <button className="btn-outline btn-sm text-rose-600" onClick={() => remove(cv)}>Xóa</button>
                    </div>
                  </div>
                  <div className="mt-2"><SkillChips skills={cv.skills} tone="blue" max={14} /></div>
                  {cv.processing_status === 'PENDING' && <p className="mt-2 text-xs text-slate-500">Đang xử lý để cập nhật gợi ý việc làm...</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Modal open={!!view} onClose={() => setView(null)} title="Kết quả trích xuất CV" wide>
        {view && (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <Alert kind="info">Kiểm tra lại thông tin AI đọc được. Nếu sai, sửa trực tiếp rồi lưu — gợi ý việc làm sẽ cập nhật theo.</Alert>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">Họ tên:</span> {view.parsed?.name || '—'}</div>
                <div><span className="text-slate-500">Email:</span> {view.parsed?.email || '—'}</div>
                <div><span className="text-slate-500">Điện thoại:</span> {view.parsed?.phone || '—'}</div>
                <div><span className="text-slate-500">Nhóm nghề:</span> {view.role_display}</div>
              </div>
              <div><label className="label">Tên CV</label><input className="input" value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></div>
              <div><label className="label">Số năm kinh nghiệm</label><input className="input" type="number" min={0} value={edit.years} onChange={(e) => setEdit({ ...edit, years: Number(e.target.value) })} /></div>
              <div><label className="label">Kỹ năng (phân tách bằng dấu phẩy)</label><textarea className="input h-28" value={edit.skills} onChange={(e) => setEdit({ ...edit, skills: e.target.value })} /></div>
              <div className="flex justify-end gap-2"><button className="btn-outline" onClick={() => setView(null)}>Đóng</button><button className="btn-primary" onClick={save}>Lưu</button></div>
            </div>
            <div>
              <div className="label">Nội dung CV</div>
              <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{view.raw_text}</pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
