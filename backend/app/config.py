from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"), env_file_encoding="utf-8-sig", extra="ignore"
    )
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/recruit_ai"
    jwt_secret: str = "dev-secret-change-me-please-use-32-bytes-or-more"
    jwt_expire_minutes: int = 60
    upload_dir: Path = BACKEND_DIR / "uploads"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    embed_model: str = "intfloat/multilingual-e5-base"
    embed_device: str = "cpu"
    allow_hashing_fallback: bool = False
    cross_encoder_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    redis_url: str = "redis://127.0.0.1:6379/0"
    task_always_eager: bool = False
    auto_create_schema: bool = False
    score_w_semantic: float = 0.6
    score_w_skill: float = 0.3
    score_w_exp: float = 0.1
    score_cos_floor: float = 0.5
    slot_hold_minutes: int = 10
    order_expire_minutes: int = 15
    refund_window_days: int = 7
    free_job_posts: int = 2
    sepay_bank: str = "MBBank"
    sepay_account: str = "0000000000"
    sepay_account_name: str = "DO TRINH LE QUYEN"
    sepay_webhook_key: str = "dev-sepay-key"
    order_prefix: str = "QTD"
    # Demo: vẫn sinh VietQR SePay như thật, kèm nút giả lập SePay gửi webhook xác nhận (không cần chuyển khoản)
    payment_demo_enabled: bool = True
    enable_dev_tools: bool = False
    # Phiên đăng nhập, khôi phục mật khẩu, xác minh email
    refresh_token_days: int = 14
    reset_token_minutes: int = 30
    verify_token_hours: int = 48
    require_email_verification: bool = False
    frontend_url: str = "http://localhost:5173"
    # Email: để trống SMTP_HOST thì chỉ ghi log (môi trường dev/test)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True
    # Phỏng vấn
    interview_reminder_hours: int = 24
    interview_cancel_min_hours: int = 2
    # Đối soát với API SePay; để trống token thì chỉ đối soát nội bộ
    sepay_api_token: str = ""
    sepay_api_url: str = "https://my.sepay.vn/userapi/transactions/list"


settings = Settings()
