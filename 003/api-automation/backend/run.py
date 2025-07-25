import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    log_config_path = current_dir / "uvicorn_loggin_config.json"

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9999,
        reload=True,
        log_config=str(log_config_path) if log_config_path.exists() else None
    )
