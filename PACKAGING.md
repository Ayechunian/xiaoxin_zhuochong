# 单文件 EXE 打包说明

## 使用成品

双击 `release\小新桌宠.exe` 即可启动。程序已经包含 Python、PySide6、角色图片和边缘互动素材，不需要额外安装运行环境。

右键桌宠可打开功能菜单或退出。提醒和偏好数据保存在：

```text
%LOCALAPPDATA%\XiaoxinDesktopPet
```

替换或移动 EXE 不会删除这些数据。

## 重新打包

项目目录中双击 `build_exe.bat`。脚本会使用项目的独立 Python 环境安装固定版本的 PyInstaller，并把结果写入 `release\小新桌宠.exe`。走路素材是 `assets\poses\walk_1.png` 到 `walk_8.png`，当前顺序对应用户合成图的原图帧 `1、2、3、6、7、8、5、4`。

打包配置位于 `desktop_pet.spec`。其中包含角色素材、边缘动作素材、图标、声音辅助脚本和 Qt 运行库。配置会排除构建机搜索路径里可能出现的第三方 ICU DLL，避免其覆盖 Windows 自带 ICU 并导致 `QtWidgets` 无法加载。

## 验证

正式版已执行：

```text
release\小新桌宠.exe --smoke-test
```

程序会依次创建窗口、载入素材和状态，约 1.6 秒后自动退出；退出码为 0 表示启动检查通过。
