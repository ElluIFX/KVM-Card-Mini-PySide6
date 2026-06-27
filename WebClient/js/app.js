/**
 * app.js — KVM-Card-Mini WebUSB Client — Application Bootstrap
 *
 * Orchestrates: WebUSB connection, video capture, keyboard, mouse,
 *               USB switch, RGB LED, and UI state.
 */

import { KVMDevice } from './webusb.js';
import { CMD, buildCommand, resetPacket } from './protocol.js';
import { KeyboardHandler } from './kbd.js';
import { MouseHandler } from './mouse.js';
import { SwitchController } from './switch.js';
import { RGBController } from './rgb.js';

/* ==========================================================================
   DOM References (all IDs use $ prefix convention)
   ========================================================================== */

const $ = (id) => document.getElementById(id);

const $monitor    = $('$monitor');
const $overlay    = $('$overlay');
const $status     = $('$status');
const $connect    = $('$connect');
const $disconnect = $('$disconnect');
const $resetMc    = $('$resetMc');

const $switchFloat  = $('$switchFloat');
const $switchMaster = $('$switchMaster');
const $switchTarget = $('$switchTarget');
const $switchLabel  = $('$switchLabel');

const $mouseMode = $('$mouseMode');
const $mouseAbs  = $('$mouseAbs');
const $mouseRel  = $('$mouseRel');

const $fullscreen = $('$fullscreen');
const $pasteArea  = $('$pasteArea');
const $pasteSend  = $('$pasteSend');
const $rgbColor   = $('$rgbColor');
const $rgbSend    = $('$rgbSend');

const $keyPanel   = $('$keyPanel');
const $keyToggle  = $('$keyToggle');

const $ledNum    = $('$ledNum');
const $ledCaps   = $('$ledCaps');
const $ledScroll = $('$ledScroll');

const $modCtrl  = $('$modCtrl');
const $modShift = $('$modShift');
const $modAlt   = $('$modAlt');
const $modMeta  = $('$modMeta');

/* ==========================================================================
   Core Objects
   ========================================================================== */

const kvm    = new KVMDevice();
let keyboard = null;
let mouse    = null;
let swCtrl   = null;
let rgbCtrl  = null;
let mediaStream = null;

/* ==========================================================================
   Connection Management
   ========================================================================== */

async function doConnect() {
  setStatus('connecting', 'Connecting...');
  try {
    await kvm.connect();

    // Initialize sub-controllers
    keyboard = new KeyboardHandler((buf) => kvm.send(buf));
    keyboard.active = true;

    mouse = new MouseHandler((buf) => kvm.send(buf), $monitor);
    mouse.active = true;
    mouse.bind();

    swCtrl = new SwitchController(
      (buf) => kvm.send(buf),
      () => kvm.recv()
    );

    rgbCtrl = new RGBController((buf) => kvm.send(buf));

    // Query initial state
    const swState = await swCtrl.query();
    console.log('[app] Switch state:', JSON.stringify(swState), 'mode:', swCtrl.mode);
    updateSwitchUI();

    try {
      const leds = await kvm.queryLEDs();
      console.log('[app] LED state:', JSON.stringify(leds));
      if (leds) updateLEDsUI(leds);
    } catch (e) { console.warn('[app] LED query failed:', e.message); }

    // Update UI
    setStatus('connected', 'Connected');
    $connect.classList.add('hidden');
    $disconnect.classList.remove('hidden');
    $monitor.classList.add('capture-active');
    $overlay.classList.add('hidden');

  } catch (err) {
    setStatus('error', `Connection failed: ${err.message}`);
    console.error('[app] Connect error:', err);
  }
}

async function doDisconnect() {
  keyboard && await keyboard.reset();
  keyboard = null;

  mouse && mouse.unbind();
  mouse && mouse.reset();
  mouse = null;

  swCtrl = null;
  rgbCtrl = null;

  await kvm.disconnect();

  // Update UI
  setStatus('disconnected', 'Disconnected');
  $connect.classList.remove('hidden');
  $disconnect.classList.add('hidden');
  $monitor.classList.remove('capture-active');
  $overlay.classList.remove('hidden');
  updateLEDsUI({ numLock: false, capsLock: false, scrollLock: false });
  updateModifiersUI(0);
}

async function doResetMCU() {
  if (!kvm.connected) return;
  if (!confirm('Reset the MCU? The device will restart.')) return;
  setStatus('connecting', 'Resetting MCU...');
  try {
    const buf = resetPacket();
    await kvm.send(buf);
    // MCU resets; device will disconnect from USB
    await kvm.disconnect();
    keyboard = null; mouse = null; swCtrl = null; rgbCtrl = null;
    setStatus('disconnected', 'MCU reset. Please reconnect after device reappears.');
    $connect.classList.remove('hidden');
    $disconnect.classList.add('hidden');
    $monitor.classList.remove('capture-active');
  } catch (err) {
    setStatus('error', `Reset failed: ${err.message}`);
  }
}

/* ==========================================================================
   USB Switch UI
   ========================================================================== */

function updateSwitchUI() {
  if (!swCtrl) return;
  const mode = swCtrl.mode;
  $switchFloat.classList.toggle('active',  mode === 'float');
  $switchMaster.classList.toggle('active', mode === 'master');
  $switchTarget.classList.toggle('active', mode === 'target');
  const labels = { float: 'Floating', master: 'Master (Host)', target: 'Target (Controlled)', unknown: 'Unknown' };
  $switchLabel.textContent = labels[mode] || 'Unknown';
}

async function setSwitch(mode) {
  if (!swCtrl) return;
  try {
    if (mode === 'float')  await swCtrl.setFloat();
    if (mode === 'master') await swCtrl.setMaster();
    if (mode === 'target') await swCtrl.setTarget();
    updateSwitchUI();
  } catch (err) {
    console.error('[app] Switch error:', err);
  }
}

/* ==========================================================================
   Mouse Mode
   ========================================================================== */

function setMouseMode(mode) {
  if (!mouse) return;
  if (mode === 'rel') {
    mouse.relMode = false; // Will be set true on pointer lock
    $mouseRel.classList.add('active');
    $mouseAbs.classList.remove('active');
    $monitor.style.cursor = 'none';
  } else {
    mouse.relMode = false;
    mouse.stopRelTimer();
    document.exitPointerLock();
    $mouseAbs.classList.add('active');
    $mouseRel.classList.remove('active');
    $monitor.style.cursor = 'crosshair';
  }
}

/* ==========================================================================
   Keyboard LEDs & Modifiers UI
   ========================================================================== */

function updateLEDsUI(leds) {
  $ledNum.classList.toggle('on', leds.numLock);
  $ledCaps.classList.toggle('on', leds.capsLock);
  $ledScroll.classList.toggle('on', leds.scrollLock);
}

function updateModifiersUI(modifiers) {
  const LCTRL = 0x01, LSHIFT = 0x02, LALT = 0x04, LGUI = 0x08;
  const RCTRL = 0x10, RSHIFT = 0x20, RALT = 0x40, RGUI = 0x80;
  $modCtrl.classList.toggle('on',  !!(modifiers & (LCTRL | RCTRL)));
  $modShift.classList.toggle('on', !!(modifiers & (LSHIFT | RSHIFT)));
  $modAlt.classList.toggle('on',   !!(modifiers & (LALT | RALT)));
  $modMeta.classList.toggle('on',  !!(modifiers & (LGUI | RGUI)));
}

/* ==========================================================================
   Paste
   ========================================================================== */

async function doPaste() {
  if (!keyboard) return;
  const text = $pasteArea.value;
  if (!text) return;
  $pasteSend.disabled = true;
  $pasteSend.textContent = 'Sending...';
  try {
    await keyboard.typeText(text, 5);
  } catch (err) {
    console.error('[app] Paste error:', err);
  }
  $pasteSend.disabled = false;
  $pasteSend.textContent = 'Send';
}

/* ==========================================================================
   Special Key Panel (for Android)
   ========================================================================== */

function setupKeyPanel() {
  const btns = $keyPanel.querySelectorAll('button[data-key]');
  btns.forEach(btn => {
    btn.addEventListener('pointerdown', async (e) => {
      e.preventDefault();
      if (!keyboard) return;
      const code = btn.dataset.key;
      await keyboard.holdModifier(code);
    });
    btn.addEventListener('pointerup', async (e) => {
      e.preventDefault();
      if (!keyboard) return;
      const code = btn.dataset.key;
      await keyboard.releaseModifier(code);
    });
    btn.addEventListener('pointerleave', async (e) => {
      if (!keyboard) return;
      const code = btn.dataset.key;
      await keyboard.releaseModifier(code);
    });
  });
}

/* ==========================================================================
   RGB LED
   ========================================================================== */

async function doSetRGB() {
  if (!rgbCtrl) return;
  const hex = $rgbColor.value;
  await rgbCtrl.setHex(hex);
}

/* ==========================================================================
   Fullscreen
   ========================================================================== */

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen();
  }
}

/* ==========================================================================
   Video Capture (MS2131 UVC via getUserMedia)
   ========================================================================== */

async function initVideo() {
  try {
    // Enumerate video devices
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    console.log('[app] Video devices:', videoDevices.map(d => d.label || '(no label)'));

    // Look for MS2131 or any external USB camera
    let deviceId = null;
    const ms2131 = videoDevices.find(d =>
      d.label && (d.label.toLowerCase().includes('ms2131') ||
                   d.label.toLowerCase().includes('usb video') ||
                   d.label.toLowerCase().includes('uvc'))
    );
    if (ms2131) {
      deviceId = ms2131.deviceId;
      console.log('[app] Found MS2131/UVC device:', ms2131.label);
    } else if (videoDevices.length > 0) {
      // Pick the last one (external cameras usually listed after built-in)
      deviceId = videoDevices[videoDevices.length - 1].deviceId;
      console.log('[app] Using video device:', videoDevices[videoDevices.length - 1].label || '(unnamed)');
    }

    if (deviceId) {
      const constraints = {
        video: {
          deviceId: { exact: deviceId },
          width:  { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      };

      // Need a user gesture for getUserMedia on some browsers
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      $monitor.srcObject = mediaStream;
      await $monitor.play();
      console.log('[app] Video stream started');
      $monitor.classList.add('has-video');
    } else {
      console.warn('[app] No video capture devices found. Keyboard/mouse will still work.');
      $monitor.style.background = '#1a1a2e url(\'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="%23444" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><polyline points="8 21 12 17 16 21"/></svg>\') center no-repeat';
    }
  } catch (err) {
    console.warn('[app] Video capture not available:', err.message);
    $monitor.style.background = '#1a1a2e';
    // Keyboard/mouse passthrough still works
  }
}

/* ==========================================================================
   Status Bar
   ========================================================================== */

function setStatus(state, text) {
  $status.textContent = text;
  $status.className = `status-${state}`;
}

/* ==========================================================================
   Keyboard Focus Management
   ========================================================================== */

$monitor.addEventListener('click', () => {
  $monitor.focus();
  // Update overlay hint
  if (!kvm.connected) {
    $overlay.textContent = 'Click "Connect" to start';
  }
});

// Reset keyboard on focus loss
$monitor.addEventListener('blur', () => {
  if (keyboard) {
    keyboard.reset().catch(() => {});
  }
});

// Capture keyboard events on the monitor element
$monitor.addEventListener('keydown', (e) => {
  if (!keyboard || !keyboard.active) return;
  keyboard.handleKeyDown(e);
});

$monitor.addEventListener('keyup', (e) => {
  if (!keyboard || !keyboard.active) return;
  keyboard.handleKeyUp(e);
});

// Poll keyboard LEDs every 2 seconds while connected
let ledTimer = null;
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
    } catch (e) { /* poll errors are expected occasionally */ }
  }, 2000);
}

function stopLEDPoll() {
  if (ledTimer) { clearInterval(ledTimer); ledTimer = null; }
}
// Import parseLEDResponse
import { parseLEDResponse } from './protocol.js';

/* ==========================================================================
   Event Bindings
   ========================================================================== */

$connect.addEventListener('click', doConnect);
$disconnect.addEventListener('click', doDisconnect);
$resetMc.addEventListener('click', doResetMCU);

$switchFloat.addEventListener('click',  () => setSwitch('float'));
$switchMaster.addEventListener('click', () => setSwitch('master'));
$switchTarget.addEventListener('click', () => setSwitch('target'));

$mouseAbs.addEventListener('click', () => setMouseMode('abs'));
$mouseRel.addEventListener('click', () => setMouseMode('rel'));

$fullscreen.addEventListener('click', toggleFullscreen);
$pasteSend.addEventListener('click', doPaste);
$rgbSend.addEventListener('click', doSetRGB);

$keyToggle.addEventListener('click', () => {
  $keyPanel.classList.toggle('visible');
});

setupKeyPanel();

// Global keyboard hook for fullscreen toggle and escape
document.addEventListener('keydown', (e) => {
  // Ctrl+Shift+F for fullscreen
  if (e.ctrlKey && e.shiftKey && e.code === 'KeyF') {
    e.preventDefault();
    toggleFullscreen();
  }
  // Escape to exit relative mouse mode
  if (e.code === 'Escape' && mouse && mouse.relMode) {
    setMouseMode('abs');
  }
});

/* ==========================================================================
   Initialization
   ========================================================================== */

async function init() {
  // Check WebUSB support
  if (!navigator.usb) {
    setStatus('error', 'WebUSB not supported in this browser. Use Chrome/Edge 61+.');
    $connect.disabled = true;
    return;
  }

  // Try to reconnect to a previously paired device
  try {
    const devices = await navigator.usb.getDevices();
    if (devices.some(d => d.vendorId === 0x413D && d.productId === 0x2107)) {
      $overlay.textContent = 'Click "Connect" to start, or click here to auto-reconnect';
    }
  } catch (e) { /* getDevices may fail silently */ }

  // Init video (may need user interaction, so defer to first click)
  $monitor.addEventListener('click', function initVideoOnce() {
    $monitor.removeEventListener('click', initVideoOnce);
    initVideo();
  }, { once: true });

  console.log('[app] KVM-Card-Mini Web Client initialized');
  console.log('[app] WebUSB:', !!navigator.usb);
  console.log('[app] getUserMedia:', !!navigator.mediaDevices?.getUserMedia);
}

init().catch(err => {
  console.error('[app] Init error:', err);
  setStatus('error', `Initialization error: ${err.message}`);
});
