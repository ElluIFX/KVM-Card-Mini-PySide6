# KVM Card Mini — WebUSB 客户端

## About

**修改自 [ElluIFX/KVM-Card-Mini-PySide6](https://github.com/ElluIFX/KVM-Card-Mini-PySide6)**

基于 CH582F + MS2131 的 USB KVM 解决方案（向日葵 Q0.5）。在浏览器中直接控制目标机器的键盘、鼠标和视频，无需安装任何软件。

```
┌──────────────┐    USB1 (WebUSB)    ┌──────────────┐    USB2 (HID)    ┌──────────────┐
│  主控设备     │◄──────────────────►│  CH582F MCU   │◄───────────────►│  被控机器     │
│ (浏览器)     │    Vendor-Specific  │  (键盘鼠标桥)  │  Keyboard+Mouse │ (目标计算机)  │
│              │                     │               │                 │              │
│ 视频采集 ◄───┼─────────────────────┼── MS2131 ────┼── HDMI IN ─────┤              │
│ (getUserMedia)│       UVC          │  (独立芯片)    │                 │              │
└──────────────┘                     └──────────────┘                 └──────────────┘
```

## 硬件

| 芯片 | 功能 |
|------|------|
| **CH582F** | RISC-V MCU，双 USB 控制器。USB1↔主控端（WebUSB），USB2↔被控端（标准 HID 键鼠） |
| **MS2131** | HDMI→USB 采集芯片，独立 UVC 设备，在主控端显示为摄像头 |
| **WS2812B** | RGB LED，指示 MCU 工作状态 |

### LED 状态指示

| 颜色 | 含义 |
|------|------|
| 🔴 红 | MCU 启动中，或 USB1 未连接 |
| 🟡 黄 | USB1 已连接，USB2 未连接 |
| 🟢 绿 | USB1 + USB2 均已就绪，空闲 |
| 🔵 蓝 | 键鼠数据正在转发 |

## 固件

### 编译

```bash
cd Firmware/HID_CompliantDev
bash build.sh
```

工具链：MounRiver Studio 2 自带 RISC-V GCC 8.2.0  
产物：`build/KVM-Card-Mini.hex`

### 烧录

使用 WCHISPTool 烧录 `KVM-Card-Mini.hex` 到 CH582F。

### 主要修改（相比原始固件）

- 添加 WebUSB BOS 描述符（Platform Capability Descriptor）
- USB1 接口类从 HID 改为 Vendor-Specific，确保 WebUSB 可独占接口
- 扩展命令 0x03 响应，包含 MCU 状态标志
- LED 事件驱动状态指示（适配 WS2812B 的 GRB 颜色顺序）

**注意：**由于技术路线调整（WebUSB），不再兼容原版Python客户端

## Web 客户端

### 部署

```bash
cd WebClient
python -m http.server 8000
```

在 Chrome/Edge 中打开 `http://localhost:8000`（桌面端）。

### 浏览器要求

- **桌面端：** Chrome 61+ / Edge 79+（WebUSB + getUserMedia）
- **Android 平板：** Chrome 61+（WebUSB 键鼠透传，不支持视频）
- **不支持：** Firefox、Safari（无 WebUSB）

### 功能

| 功能 | 说明 |
|------|------|
| MCU 连接/断开/重置 | WebUSB 设备管理 |
| 键盘透传 | 6KRO，支持所有标准按键。可独立开关 |
| 鼠标透传 | 绝对模式（默认）+ 相对模式（指针锁定）。可独立开关 |
| 触摸支持 | 单指=移动+左键，双指=右键，三指=中键 |
| 特殊键面板 | F1-F12、Ctrl/Alt/Win、方向键、Esc/Tab/Del 等 |
| 剪贴板 | 文本逐字发送到被控端 |
| 视频采集 | 通过浏览器摄像头 API，支持设备选择 |
| 状态栏 | Num/Caps/Scroll 锁定状态、修饰键状态、MCU 工作状态 |
| 调试面板 | 点击"调试"按钮查看运行日志 |

### 协议

WebUSB 通过 EP1 发送/接收 10 字节数据包：

| 字节0 | 命令 | 数据 |
|-------|------|------|
| 0x01 | 键盘 | 字节2=修饰键, 字节4-9=6个键码 |
| 0x02 | 绝对鼠标 | 字节2=按键, 3-4=X(LE), 5-6=Y(LE), 7=滚轮 |
| 0x03 | 读状态 | 回复: 字节2=键盘LED, 字节3=MCU标志, 字节4=LED模式 |
| 0x04 | 复位MCU | 软件复位 |
| 0x05 | 设置RGB | 字节2-4=R,G,B |
| 0x07 | 相对鼠标 | 字节2=按键, 3=dX(i8), 4=dY(i8), 5=滚轮(i8) |

### 文件结构

```
WebClient/
├── index.html          # 主页面（中文界面）
├── css/style.css        # 深色主题样式
├── js/
│   ├── protocol.js      # 10字节协议打包/解析
│   ├── webusb.js        # WebUSB 连接层（设备发现、收发）
│   ├── kbd.js           # 键盘 HID 映射 + 事件处理
│   ├── mouse.js         # 鼠标（绝对/相对）+ 触摸处理
│   └── app.js           # 主入口 + UI 编排 + 视频采集
└── README.md
```

## 已知限制

- **Android 视频采集：** Chrome for Android 不支持通过 `getUserMedia` 访问外部 USB UVC 摄像头。视频仅在桌面端 Chrome 可用。Android 平板上键鼠透传正常工作。
- **6KRO 限制：** USB HID 键盘协议最多同时按下 6 个普通键。
- **首次连接：** 烧录新固件后首次 WebUSB 连接可能需要点击"重置MCU"让设备重新枚举。

## License

MIT — 原始项目 [Jackadminx/KVM-Card-Mini](https://github.com/Jackadminx/KVM-Card-Mini)
