# 屏幕边缘互动 · 2026-09-11

把桌宠拖到屏幕的某条边缘后松手，切换对应姿势；向桌面内拖出即可恢复普通动作。左侧和右侧是单手扶边探头，另一条胳膊隐藏在边缘外；底部双手扒边；顶部倒挂向下看。贴边时右键仍可调整大小或重置位置。

新素材在 `assets/poses/edge_v2/`，每个方向一张 1254×1254 透明 PNG。按用户提供的走路原图校准肤色与细线风格，去掉额外腮红；倒挂图只保留额头侧的一对眉弧。原走路四帧保持原文件。

程序依据 `manifest.json` 中的头宽等比显示和手部接触点贴边，不再把整张图片拉伸填满窗口。默认头部宽约 65 个逻辑像素，与普通姿势接近；用户主动放大缩小时按同一倍率变化。吸附后保持当前屏幕与边缘状态，避免睡眠、经过鼠标等改变贴边画面。轻度拖过边界仍能触发；在角落按释放鼠标更靠近的边选择。

工作区边界会实际裁切绘图，底部为任务栏上方的桌面工作区边缘。当前每条边使用一个专用关键姿势，不包含多帧攀爬动画。

实现参考 [Shimeji-ee 动作定义](https://github.com/TigerHix/shimeji-ee/blob/master/conf/actions.xml) 的独立姿势和 ImageAnchor，以及 [行为条件](https://github.com/TigerHix/shimeji-ee/blob/master/conf/behaviors.xml) 的墙、顶、地面区分。素材由内置图像生成工具制作，完整提示词保存在素材目录的 `generation.json`；`source/` 保留导出透明前的原图。

验证：运行 `runtime\python.exe check.py`、`runtime\python.exe check_edges.py` 和 `runtime\python.exe main.py --smoke-test`。
