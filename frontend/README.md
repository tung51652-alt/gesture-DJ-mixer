# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

backend/
│
├── main.py                  # Entry point: Khởi tạo app FastAPI, cấu hình CORS, mount router
├── requirements.txt         # Chứa: fastapi, uvicorn, websockets, pydantic, orjson (để parse JSON siêu tốc)
│
├── core/
│   └── config.py            # Chứa các hằng số cấu hình: Ngưỡng vuốt (SWIPE_THRESHOLD), hệ số làm mượt (EMA_ALPHA)
│
├── schemas/
│   └── payload.py           # Pydantic Model: Định nghĩa cấu trúc JSON nhận từ FE (tọa độ ngón cái, ngón trỏ) và JSON gửi về FE (lệnh volume, tempo)
│
├── api/
│   ├── websocket.py         # Router /ws/gesture: Quản lý vòng lặp kết nối mạng, nhận tọa độ, gọi Engine, và trả kết quả realtime
│   └── rest.py              # Router REST API dự phòng (Ví dụ: /api/upload-mix để lưu file ghi âm của user sau này)
│
└── engine/                  # 🧠 BỘ NÃO CỦA BACKEND (Thay thế thư mục src/ trong hình của em)
    ├── math_utils.py        # Các hàm toán học cơ bản: Tính khoảng cách Euclidean 2D/3D
    ├── smoothing.py         # Bộ lọc EMA (Exponential Moving Average): Làm mượt các con số để âm thanh không bị giật
    └── gesture_mapper.py    # Logic nghiệp vụ (Business Logic): Dịch khoảng cách ra phần trăm Volume, dịch tốc độ tay ra Tempo