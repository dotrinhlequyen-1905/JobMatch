# Frontend JobMatch

React + TypeScript + Vite + Tailwind, dùng API thống nhất `/api/v1`.

```powershell
npm.cmd ci
npm.cmd run dev
npm.cmd run lint
npm.cmd run build
```

Vite chuyển tiếp API đến `http://127.0.0.1:8000`; có thể đổi bằng biến môi trường `VITE_API_TARGET`. Các trang khách, ứng viên, HR và quản trị viên nằm trong `src/pages`. Đánh giá CV Premium nằm ở `src/pages/candidate/Evaluation.tsx`.

Xem [hướng dẫn toàn dự án](../README.md), [kiến trúc](../docs/architecture.md) và [triển khai](../docs/deployment.md).
