# 保持文件为空或最小化以避免循环导入
# app/__init__.py 在导入 app 时加载，它应该尽量保持简洁。避免在此处导入 settings、logger 或 app。

__version__ = "0.1.0"
