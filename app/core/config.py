import yaml
from pathlib import Path
from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    '''
    所有的变量必须预定义，否则，从yaml或者.env导入会报错。
    '''

    # 从 .env 加载敏感配置
    # DATABASE_URL: str = "sqlite+aiosqlite:///./tweet.sqlite3"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/mydb"  # 默认 SQLite
    IMAGES_DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/mydb"  # 默认 SQLite
    SECRET_KEY: str = "default-your-secret-key"
    APP_NAME: str = "My FastAPI Project"
    config_type = 'default_config'

    # 从 app_config.yaml 加载非敏感配置
    log_level: str = "INFO"
    static_dir: str = str(Path(__file__).parent.parent / "static")
    template_dir: str = str(Path(__file__).parent.parent / "templates")

    static_dir2: str = str(Path(__file__).parent.parent.parent / "frontend" / "static")
    assets_dir: str = str(Path(__file__).parent.parent.parent / "frontend" / "assets")
    webui_dir: str = str(Path(__file__).parent.parent.parent / "frontend")


    class Config:
        extra = "ignore"  # 忽略未定义字段
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"Loaded .env from {env_file}")
        else:
            print("No .env file found")
        env_file_encoding = "utf-8"

    @classmethod
    def load_yaml_config(cls):
        config_path = Path(str(Path(__file__).parent.parent.parent / "config/app_config.yaml"))
        if config_path.exists():
            print(f'从{config_path}配置文件读取配置！')
            cls.is_default = 0
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f)
            return yaml_config
        else:
            print(f'{config_path}配置文件不存在，使用默认配置！')
            pass
        return {}


# 加载配置
settings = Settings(**Settings.load_yaml_config())



# 检查静态目录是否存在
static_path = Path(settings.static_dir)
if not static_path.exists():
    static_path.mkdir(parents=True, exist_ok=True)
    raise FileNotFoundError(f"静态目录 '{settings.static_dir}' 不存在，正在app下创建...，请确认")

template_path = Path(settings.template_dir)
if not template_path.exists():
    template_path.mkdir(parents=True, exist_ok=True)
    raise FileNotFoundError(f"静态目录 '{settings.template_dir}' 不存在，正在app下创建...，请确认")


