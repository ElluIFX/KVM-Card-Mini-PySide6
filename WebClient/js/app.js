/**
 * app.js — KVM Web Client — Main Application
 *
 * Chinese UI, independent subsystem toggles,
 * extended MCU status polling, debug panel.
 */

import { KVMDevice } from './webusb.js';
import { CMD, buildCommand, resetPacket, parseLEDResponse } from './protocol.js';
import { KeyboardHandler } from './kbd.js';
import { MouseHandler } from './mouse.js';

/* ==========================================================================
   DOM Refs
   ========================================================================== */
const $ = (id) => document.getElementById(id);

const $monitor   = $('$monitor');
const $overlay   = $('$overlay');
const $status    = $('$status');
const $connect   = $('$connect');
const $disconnect= $('$disconnect');
const $resetMc   = $('$resetMc');

const $kbdToggle = $('$kbdToggle');
const $mouseToggle = $('$mouseToggle');
const $mouseAbs  = $('$mouseAbs');
const $mouseRel  = $('$mouseRel');
const $kbdStat   = $('$kbdStat');
const $mouseStat = $('$mouseStat');

const $cameraSelect = $('$cameraSelect');
const $cameraRefresh = $('$cameraRefresh');
const $fullscreen = $('$fullscreen');
const $keyToggle  = $('$keyToggle');
const $keyPanel   = $('$keyPanel');
const $clipArea   = $('$clipArea');
const $clipSend   = $('$clipSend');

const $ledNum    = $('$ledNum');
const $ledCaps   = $('$ledCaps');
const $ledScroll = $('$ledScroll');
const $modCtrl   = $('$modCtrl');
const $modShift  = $('$modShift');
const $modAlt    = $('$modAlt');
const $modMeta   = $('$modMeta');
const $switchLabel = $('$switchLabel');
const $rgbColor  = $('$rgbColor');
const $rgbSend   = $('$rgbSend');
const $debugPanel= $('$debugPanel');
const $debugLog  = $('$debugLog');
const $debugToggle = $('$debugToggle');

/* ==========================================================================
   State
   ========================================================================== */
const kvm = new KVMDevice();
let keyboard = null;
let mouse = null;
let kbdEnabled = true;
let mouseEnabled = true;
let currentStream = null;
let ledTimer = null;

/* ==========================================================================
   Debug Log (on-page + console)
   ========================================================================== */
function debugLog(msg, level) {
  const cls = {warn:'warn', err:'err'}[level] || '';
  const el = document.createElement('div');
  el.className = 'debug-line' + (cls ? ' ' + cls : '');
  const ts = new Date().toLocaleTimeString('zh-CN', {hour12: false});
  el.textContent = ts + ' ' + msg;
  $debugLog.appendChild(el);
  $debugPanel.scrollTop = $debugPanel.scrollHeight;
  (level === 'warn') ? console.warn(msg) : (level === 'err') ? console.error(msg) : console.log(msg);
}

$debugToggle.addEventListener('click', () => {
  $debugPanel.classList.toggle('visible');
});

/* ==========================================================================
   Status UI
   ========================================================================== */
function setStatus(state, text) {
  $status.textContent = text;
  $status.className = 'stat-val status-' + state;
}

function updateKbdStat() {
  $kbdStat.className = 'stat-val ' + (kbdEnabled ? 'stat-on' : 'stat-off');
  $kbdToggle.className = 'btn ' + (kbdEnabled ? 'toggle-on' : 'toggle-off');
  $kbdToggle.textContent = kbdEnabled ? '⌨ 键盘' : '⌨ 键盘(关)';
}

function updateMouseStat() {
  $mouseStat.className = 'stat-val ' + (mouseEnabled ? 'stat-on' : 'stat-off');
  $mouseToggle.className = 'btn ' + (mouseEnabled ? 'toggle-on' : 'toggle-off');
  $mouseToggle.textContent = mouseEnabled ? '🖱 鼠标' : '🖱 鼠标(关)';
}

function updateLEDsUI(leds) {
  $ledNum.classList.toggle('on', leds.numLock);
  $ledCaps.classList.toggle('on', leds.capsLock);
  $ledScroll.classList.toggle('on', leds.scrollLock);
}

function updateModifiersUI(modifiers) {
  const L = 0x01|0x10, S = 0x02|0x20, A = 0x04|0x40, M = 0x08|0x80;
  $modCtrl.classList.toggle('on', !!(modifiers & L));
  $modShift.classList.toggle('on', !!(modifiers & S));
  $modAlt.classList.toggle('on', !!(modifiers & A));
  $modMeta.classList.toggle('on', !!(modifiers & M));
}

function updateMCUStatusUI(flags) {
  if (!flags) return;
  const parts = [];
  if (flags & 0x01) parts.push('就绪');
  if (flags & 0x02) parts.push('USB1✓');
  else parts.push('USB1✗');
  if (flags & 0x04) parts.push('USB2✓');
  else parts.push('USB2✗');
  if (flags & 0x08) parts.push('键盘活动');
  if (flags & 0x10) parts.push('鼠标活动');
  $switchLabel.textContent = parts.join(' ');
}

/* ==========================================================================
   Connection
   ========================================================================== */
async function doConnect() {
  setStatus('connecting', '连接中...');
  try {
    await kvm.connect();

    // Init keyboard
    keyboard = new KeyboardHandler((buf) => { if (kbdEnabled) return kvm.send(buf); });
    keyboard.active = true;

    // Init mouse
    mouse = new MouseHandler((buf) => { if (mouseEnabled) return kvm.send(buf); }, $monitor);
    mouse.active = true;
    mouse.bind();

    // Query extended status
    debugLog('查询MCU状态...');
    const buf = buildCommand(CMD.READ_LEDS, 0x00);
    await kvm.send(buf);
    const data = await kvm.recv();
    const leds = parseLEDResponse(data);
    const flags = data.getUint8(3);
    if (leds) updateLEDsUI(leds);
    updateMCUStatusUI(flags);
    debugLog(`MCU状态: flags=0x${flags.toString(16)} ${leds ? 'LEDs: N='+leds.numLock+' C='+leds.capsLock+' S='+leds.scrollLock : ''}`);

    // Update UI
    setStatus('connected', '已连接');
    $connect.classList.add('hidden');
    $disconnect.classList.remove('hidden');
    $overlay.classList.add('hidden');
    $monitor.classList.add('capture-active');
    updateKbdStat();
    updateMouseStat();

    // Start LED poll
    startLEDPoll();

  } catch (err) {
    setStatus('error', '连接失败: ' + err.message);
    debugLog('连接失败: ' + err.message, 'err');
  }
}

async function doDisconnect() {
  stopLEDPoll();
  keyboard && await keyboard.reset();
  keyboard = null;
  mouse && mouse.unbind();
  mouse && mouse.reset();
  mouse = null;
  await kvm.disconnect();
  setStatus('disconnected', '未连接');
  $connect.classList.remove('hidden');
  $disconnect.classList.add('hidden');
  $monitor.classList.remove('capture-active');
  $overlay.classList.remove('hidden');
  updateLEDsUI({ numLock: false, capsLock: false, scrollLock: false });
  updateModifiersUI(0);
}

async function doResetMCU() {
  if (!kvm.connected) return;
  if (!confirm('确定要重置MCU吗？设备将重新启动。')) return;
  setStatus('connecting', '重置中...');
  try {
    await kvm.send(resetPacket());
    stopLEDPoll();
    await kvm.disconnect();
    keyboard = null; mouse = null;
    setStatus('disconnected', 'MCU已重置，请重新连接');
    $connect.classList.remove('hidden');
    $disconnect.classList.add('hidden');
    $monitor.classList.remove('capture-active');
  } catch (err) {
    setStatus('error', '重置失败: ' + err.message);
  }
}

/* ==========================================================================
   Keyboard/Mouse Toggles
   ========================================================================== */
$kbdToggle.addEventListener('click', () => {
  kbdEnabled = !kbdEnabled;
  updateKbdStat();
  if (keyboard) keyboard.active = kbdEnabled;
  if (!kbdEnabled && keyboard) keyboard.reset();
  debugLog(kbdEnabled ? '键盘: 启用' : '键盘: 禁用');
});

$mouseToggle.addEventListener('click', () => {
  mouseEnabled = !mouseEnabled;
  updateMouseStat();
  if (mouse) mouse.active = mouseEnabled;
  if (!mouseEnabled && mouse) mouse.reset();
  debugLog(mouseEnabled ? '鼠标: 启用' : '鼠标: 禁用');
});

/* ==========================================================================
   Mouse Mode
   ========================================================================== */
function setMouseMode(mode) {
  if (!mouse) return;
  if (mode === 'rel') {
    mouse.relMode = false;
    $mouseRel.classList.add('active');
    $mouseAbs.classList.remove('active');
    $monitor.style.cursor = 'none';
  } else {
    mouse.relMode = false;
    mouse.stopRelTimer();
    if (document.pointerLockElement) document.exitPointerLock();
    $mouseAbs.classList.add('active');
    $mouseRel.classList.remove('active');
    $monitor.style.cursor = 'crosshair';
  }
  debugLog('鼠标模式: ' + (mode === 'rel' ? '相对' : '绝对'));
}

$mouseAbs.addEventListener('click', () => setMouseMode('abs'));
$mouseRel.addEventListener('click', () => setMouseMode('rel'));

/* ==========================================================================
   LED Polling
   ========================================================================== */
function startLEDPoll() {
  stopLEDPoll();
  ledTimer = setInterval(async () => {
    if (!kvm.connected) return;
    try {
      const buf = buildCommand(CMD.READ_LEDS, 0x00);
      await kvm.send(buf);
      const data = await kvm.recv();
      const leds = parseLEDResponse(data);
      if (leds) updateLEDsUI(leds);
      const flags = data.getUint8(3);
      updateMCUStatusUI(flags);
    } catch (e) { /* ignore poll errors */ }
  }, 2000);
}

function stopLEDPoll() {
  if (ledTimer) { clearInterval(ledTimer); ledTimer = null; }
}

/* ==========================================================================
   Special Keys Panel
   ========================================================================== */
function setupKeyPanel() {
  $keyPanel.querySelectorAll('button[data-key]').forEach(btn => {
    btn.addEventListener('pointerdown', async (e) => {
      e.preventDefault();
      if (!keyboard || !kbdEnabled) return;
      await keyboard.holdModifier(btn.dataset.key);
    });
    btn.addEventListener('pointerup', async (e) => {
      e.preventDefault();
      if (!keyboard) return;
      await keyboard.releaseModifier(btn.dataset.key);
    });
    btn.addEventListener('pointerleave', async () => {
      if (!keyboard) return;
      keyboard.releaseModifier(btn.dataset.key);
    });
  });
}

$keyToggle.addEventListener('click', () => $keyPanel.classList.toggle('visible'));

/* ==========================================================================
   Clipboard
   ========================================================================== */
async function doPaste() {
  if (!keyboard || !kbdEnabled) return;
  const text = $clipArea.value;
  if (!text) return;
  $clipSend.disabled = true;
  $clipSend.textContent = '发送中...';
  try {
    await keyboard.typeText(text, 5);
    debugLog('剪贴板: 已发送 ' + text.length + ' 字符');
  } catch (err) {
    debugLog('剪贴板失败: ' + err.message, 'err');
  }
  $clipSend.disabled = false;
  $clipSend.textContent = '发送';
}

$clipSend.addEventListener('click', doPaste);

/* ==========================================================================
   RGB LED
   ========================================================================== */
async function doSetRGB() {
  if (!kvm.connected) return;
  const hex = $rgbColor.value;
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  if (isNaN(r)) return;
  const buf = buildCommand(CMD.SET_RGB, 0x00, r, g, b);
  await kvm.send(buf);
}

$rgbSend.addEventListener('click', doSetRGB);

/* ==========================================================================
   Video
   ========================================================================== */
async function refreshCameraList() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevs = devices.filter(d => d.kind === 'videoinput');
    debugLog('摄像头: 找到 ' + videoDevs.length + ' 个');
    videoDevs.forEach(d => debugLog('  ' + (d.label || '(未命名)')));

    $cameraSelect.innerHTML = '<option value="">无摄像头</option>';
    videoDevs.forEach((d, i) => {
      const opt = document.createElement('option');
      opt.value = d.deviceId;
      const label = d.label || '摄像头 ' + (i+1);
      const isUVC = /ms2131|oray|q0\.5|usb video|uvc|hdmi|video\s*capture|collect/i.test(label);
      opt.textContent = isUVC ? '★ ' + label : label;
      $cameraSelect.appendChild(opt);
    });

    const uvcIdx = videoDevs.findIndex(d =>
      /ms2131|oray|q0\.5|usb video|uvc|hdmi|collect/i.test(d.label || '')
    );
    if (uvcIdx >= 0) {
      $cameraSelect.value = videoDevs[uvcIdx].deviceId;
    } else if (videoDevs.length > 0) {
      $cameraSelect.value = videoDevs[videoDevs.length - 1].deviceId;
    }
  } catch (err) {
    debugLog('摄像头枚举失败: ' + err.message, 'warn');
  }
}

async function startCamera(deviceId) {
  if (currentStream) {
    currentStream.getTracks().forEach(t => t.stop());
    currentStream = null;
  }
  if (!deviceId) {
    $monitor.srcObject = null;
    $monitor.classList.remove('has-video');
    return;
  }
  try {
    currentStream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: { exact: deviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    $monitor.srcObject = currentStream;
    await $monitor.play();
    const track = currentStream.getVideoTracks()[0];
    const s = track.getSettings();
    debugLog('视频: ' + track.label + ' ' + s.width + 'x' + s.height);
    $monitor.classList.add('has-video');
    $overlay.classList.add('hidden');
  } catch (err) {
    debugLog('视频启动失败: ' + err.message, 'warn');
  }
}

$cameraSelect.addEventListener('change', () => startCamera($cameraSelect.value));
$cameraRefresh.addEventListener('click', () => { refreshCameraList(); startCamera($cameraSelect.value); });

/* ==========================================================================
   Fullscreen
   ========================================================================== */
$fullscreen.addEventListener('click', () => {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(()=>{});
  else document.exitFullscreen();
});

/* ==========================================================================
   Keyboard/Mouse Events on Monitor
   ========================================================================== */
$monitor.addEventListener('click', () => { $monitor.focus(); });
$monitor.addEventListener('blur', () => { if (keyboard) keyboard.reset().catch(()=>{}); });
$monitor.addEventListener('keydown', (e) => { if (keyboard && kbdEnabled) keyboard.handleKeyDown(e); });
$monitor.addEventListener('keyup', (e) => { if (keyboard && kbdEnabled) keyboard.handleKeyUp(e); });

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.code === 'KeyF') { e.preventDefault(); $fullscreen.click(); }
  if (e.code === 'Escape' && mouse && mouse.relMode) setMouseMode('abs');
});

/* ==========================================================================
   Init
   ========================================================================== */
async function init() {
  if (!navigator.usb) {
    setStatus('error', '浏览器不支持WebUSB，请使用Chrome/Edge 61+');
    $connect.disabled = true;
    debugLog('WebUSB不支持', 'err');
    return;
  }

  setupKeyPanel();

  // Try camera init on first user interaction
  $monitor.addEventListener('click', async function initVideoOnce() {
    $monitor.removeEventListener('click', initVideoOnce);
    try {
      const tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      tmp.getTracks().forEach(t => t.stop());
      debugLog('摄像头权限已获取');
    } catch (e) {
      debugLog('摄像头权限被拒绝: ' + e.message, 'warn');
    }
    await refreshCameraList();
    const sel = $cameraSelect.value;
    if (sel) await startCamera(sel);
  }, { once: true });

  // Try reconnect
  try {
    const devices = await navigator.usb.getDevices();
    if (devices.some(d => d.vendorId === 0x413D && d.productId === 0x2107)) {
      $overlay.textContent = '点击"连接MCU"开始，或点击此处自动重连';
    }
  } catch (e) {}

  $connect.addEventListener('click', doConnect);
  $disconnect.addEventListener('click', doDisconnect);
  $resetMc.addEventListener('click', doResetMCU);

  debugLog('KVM-Card-Mini Web客户端就绪');
  debugLog('WebUSB: ' + (!!navigator.usb ? '支持' : '不支持'));
  debugLog('getUserMedia: ' + (!!navigator.mediaDevices?.getUserMedia ? '支持' : '不支持'));
}

init().catch(err => {
  debugLog('初始化错误: ' + err.message, 'err');
  setStatus('error', '初始化错误: ' + err.message);
});
