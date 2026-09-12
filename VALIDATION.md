# 本机验证记录

2026-09-12，Windows x64。

- Python 3.13.12；PySide6-Essentials / shiboken6 6.11.2。
- `check.py`：78 帧透明图像、六帧走路动作、置顶和透明属性、点击、拖动、睡眠、缩放和屏幕边缘互动均通过。
- `check_edges.py`：四边贴边动作、拖出恢复、透明裁切、缩放锚点和角落选择均通过。
- `check_reminders.py`：提醒持久化、到期提示、完成、延后、删除和提醒中心页面均通过。
- `main.py --smoke-test`：Qt 窗口启动和退出成功，退出码 0。
- `main.py --export-assets`：按当前帧数导出状态 PNG。
- 重新打包后的 `release\\小新桌宠.exe --smoke-test`：退出码 0。

自动交互检查已通过；未人工验证所有多显示器与缩放组合。
