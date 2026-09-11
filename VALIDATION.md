# 本机验证记录

2026-09-10，Windows x64。

- Python 3.13.12；PySide6-Essentials / shiboken6 6.11.2。
- pip check：无依赖冲突。
- compileall：入口、角色、交互模块通过。
- check.py：40 帧透明图像、置顶和透明属性、点击、拖动和释放、睡眠和唤醒、走动、屏幕边界均通过。
- main.py --smoke-test：实际 Qt 窗口启动和退出成功，退出码 0。
- main.py --export-assets：导出 40 张 PNG。
- 已启动常驻桌宠进程供试用。

自动交互检查已通过；未人工验证所有多显示器与缩放组合。
