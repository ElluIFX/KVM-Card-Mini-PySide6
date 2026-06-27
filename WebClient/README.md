# KVM Card Mini — Web Client

Browser-based KVM client for the CH582F-based KVM hardware. Works on **Chrome for Android** (WebUSB + USB-OTG) and desktop Chrome/Edge.

## Requirements

- **Browser:** Chrome 61+ or Edge 79+ (WebUSB support required)
- **Hardware:** CH582F KVM Card Mini with **WebUSB-enabled firmware** (this branch)
- **Android:** USB-OTG cable + Chrome for Android
- **Video:** MS2131 HDMI capture chip (UVC) — Chrome 128+ on Android for external camera support

## Quick Start

1. Flash the WebUSB-enabled firmware to the CH582F hardware (`Firmware/` directory)
2. Serve the web client:

```bash
cd WebClient
python -m http.server 8000
```

3. Open `http://localhost:8000` in Chrome
4. Click **Connect** and select the KVM Card Mini device
5. Click on the video area to capture keyboard/mouse

For Android tablet access, serve via a local network:

```bash
python -m http.server 8000 --bind 0.0.0.0
```

Then open `http://<your-pc-ip>:8000` in Chrome on the tablet.

## Usage

### Keyboard
- Click the video area to capture keyboard focus
- All keys are forwarded to the target machine
- Max 6 simultaneous keys (USB HID 6KRO limit)
- Click outside the video to release keyboard focus

### Mouse
- **Absolute mode (default):** Move mouse over video to position cursor on target
- **Relative mode:** Click "Rel" → pointer lock → move to send deltas
- Scroll wheel supported in both modes

### Touch (Android tablet)
- Single finger = move + left click
- Two-finger tap = right click
- Three-finger tap = middle click

### Special Keys Panel
- Tap **Keys** to show/hide the on-screen special keys panel
- Provides Ctrl, Alt, Win, F1-F12, arrows, etc.
- Hold a key down, release to send key-up

### USB Switch
- **Float:** Disconnect (power off)
- **Master:** Connect to controlling host
- **Target:** Connect to controlled machine

### Paste
- Type or paste text in the paste area, click **Send**
- Characters are typed one-by-one with configurable delay

### RGB LED
- Use the color picker to set the onboard WS2812B LED color

## Mobile / PWA

For a better mobile experience, add to home screen:
- Chrome menu → "Add to Home screen"
- Works fullscreen with toolbar overlay

## Troubleshooting

### "WebUSB not supported"
Use Chrome 61+ or Edge 79+. WebUSB is not supported in Firefox, Safari, or WebView.

### Device not appearing in chooser
- Verify firmware is flashed with WebUSB support (this branch)
- Check USB cable connection
- On Android: ensure OTG is enabled

### Video not showing
- MS2131 is a separate UVC device; ensure it's connected via the same USB hub
- Chrome 128+ on Android has experimental external USB camera support
- Keyboard/mouse passthrough works independently of video
