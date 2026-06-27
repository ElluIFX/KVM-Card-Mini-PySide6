/**
 * kbd.js — Keyboard event handling and HID keycode mapping for CH582F KVM
 *
 * Maps browser KeyboardEvent.code values to USB HID usage codes.
 * Manages keyboard state (currently pressed keys, modifier byte).
 * Builds and sends 8-byte HID keyboard reports.
 *
 * Modifier keys (Ctrl/Shift/Alt/Meta) are tracked as bits in the modifier
 * byte, NOT as separate keycodes. All other keys occupy up to 6 slots in
 * the 6KRO keycode array.
 */

import { keyboardPacket, MOD } from './protocol.js';

/* ==========================================================================
   Keymap: browser KeyboardEvent.code → USB HID usage code
   Ported from Client/Data/keyboard.yaml
   ========================================================================== */

const HID_CODE = {
  // Letters
  KeyA: 0x04, KeyB: 0x05, KeyC: 0x06, KeyD: 0x07, KeyE: 0x08,
  KeyF: 0x09, KeyG: 0x0A, KeyH: 0x0B, KeyI: 0x0C, KeyJ: 0x0D,
  KeyK: 0x0E, KeyL: 0x0F, KeyM: 0x10, KeyN: 0x11, KeyO: 0x12,
  KeyP: 0x13, KeyQ: 0x14, KeyR: 0x15, KeyS: 0x16, KeyT: 0x17,
  KeyU: 0x18, KeyV: 0x19, KeyW: 0x1A, KeyX: 0x1B, KeyY: 0x1C,
  KeyZ: 0x1D,

  // Numbers
  Digit1: 0x1E, Digit2: 0x1F, Digit3: 0x20, Digit4: 0x21,
  Digit5: 0x22, Digit6: 0x23, Digit7: 0x24, Digit8: 0x25,
  Digit9: 0x26, Digit0: 0x27,

  // Controls
  Enter: 0x28, Escape: 0x29, Backspace: 0x2A, Tab: 0x2B,
  Space: 0x2C,

  // Symbols
  Minus: 0x2D, Equal: 0x2E,
  BracketLeft: 0x2F, BracketRight: 0x30,
  Backslash: 0x31,
  Semicolon: 0x33, Quote: 0x34,
  Backquote: 0x35,
  Comma: 0x36, Period: 0x37, Slash: 0x38,
  IntlHash: 0x32, // non-US # / tilde

  // CapsLock (tracked as key, sent as keycode to target)
  CapsLock: 0x39,

  // Function keys
  F1: 0x3A, F2: 0x3B, F3: 0x3C, F4: 0x3D,
  F5: 0x3E, F6: 0x3F, F7: 0x40, F8: 0x41,
  F9: 0x42, F10: 0x43, F11: 0x44, F12: 0x45,

  // Print Screen / Scroll Lock / Pause
  PrintScreen: 0x46, ScrollLock: 0x47, Pause: 0x48,

  // Insert / Delete / Home / End / PageUp / PageDown
  Insert: 0x49, Delete: 0x4C,
  Home: 0x4A, End: 0x4D,
  PageUp: 0x4B, PageDown: 0x4E,

  // Arrow keys
  ArrowRight: 0x4F, ArrowLeft: 0x50,
  ArrowDown: 0x51, ArrowUp: 0x52,

  // Numpad
  NumLock:       0x53,
  NumpadDivide:  0x54,
  NumpadMultiply:0x55,
  NumpadSubtract:0x56,
  NumpadAdd:     0x57,
  NumpadEnter:   0x58,
  Numpad1: 0x59, Numpad2: 0x5A, Numpad3: 0x5B,
  Numpad4: 0x5C, Numpad5: 0x5D, Numpad6: 0x5E,
  Numpad7: 0x5F, Numpad8: 0x60, Numpad9: 0x61,
  Numpad0: 0x62,
  NumpadDecimal: 0x63,

  // Application key (menu)
  ContextMenu: 0x65,

  // Media / system keys
  Power:      0x66,
  NumpadEqual:0x67,
  F13: 0x68, F14: 0x69, F15: 0x6A,
  F16: 0x6B, F17: 0x6C, F18: 0x6D, F19: 0x6E,
  F20: 0x6F, F21: 0x70, F22: 0x71, F23: 0x72, F24: 0x73,

  // Japanese keyboard
  IntlYen:     0x89,
  IntlRo:      0x87,
  Lang1:       0x90, // Hiragana/Katakana
  Lang2:       0x91, // Zenkaku/Hankaku
  Lang3:       0x88, // Katakana
  Lang4:       0x8A, // Henkan
  Lang5:       0x8B, // Muhenkan
};

/** Modifier keys — map to MOD bits, NOT HID code slots */
const MOD_KEY_BITS = {
  ControlLeft:  MOD.LCTRL,
  ControlRight: MOD.RCTRL,
  ShiftLeft:    MOD.LSHIFT,
  ShiftRight:   MOD.RSHIFT,
  AltLeft:      MOD.LALT,
  AltRight:     MOD.RALT,
  MetaLeft:     MOD.LGUI,
  MetaRight:    MOD.RGUI,
};

/**
 * Keyboard state manager.
 */
export class KeyboardHandler {
  /**
   * @param {function(Uint8Array):Promise} sendFn - async function to send a packet
   */
  constructor(sendFn) {
    this._send = sendFn;
    /** @type {Set<string>} Currently pressed non-modifier keys (event.code) */
    this._downKeys = new Set();
    /** @type {number} Current modifier byte */
    this._modifiers = 0;
    /** @type {boolean} Whether keyboard capture is active */
    this._active = false;
    /** @type {function():void|null} Callback for LED state changes */
    this.onLEDChange = null;
  }

  get active() { return this._active; }
  set active(v) { this._active = v; }

  /**
   * Handle a keydown event.
   * @param {KeyboardEvent} e
   */
  async handleKeyDown(e) {
    if (!this._active) return;

    e.preventDefault();
    if (e.repeat) return; // Ignore auto-repeat

    // Check if it's a modifier key
    const modBit = MOD_KEY_BITS[e.code];
    if (modBit !== undefined) {
      this._modifiers |= modBit;
      await this._sendReport();
      return;
    }

    // Regular key — add to set (max 6 keys)
    if (this._downKeys.has(e.code)) return;
    const hidCode = HID_CODE[e.code];
    if (hidCode === undefined) {
      console.debug('[kbd] Unmapped key:', e.code);
      return;
    }

    if (this._downKeys.size >= 6) return; // 6KRO limit
    this._downKeys.add(e.code);
    await this._sendReport();
  }

  /**
   * Handle a keyup event.
   * @param {KeyboardEvent} e
   */
  async handleKeyUp(e) {
    if (!this._active) return;

    e.preventDefault();

    // Check if it's a modifier key
    const modBit = MOD_KEY_BITS[e.code];
    if (modBit !== undefined) {
      this._modifiers &= ~modBit;
      await this._sendReport();
      return;
    }

    this._downKeys.delete(e.code);
    await this._sendReport();
  }

  /**
   * Hold a modifier key (for on-screen special key panel).
   * @param {string} code - KeyboardEvent.code, e.g. "ControlLeft"
   */
  async holdModifier(code) {
    const modBit = MOD_KEY_BITS[code];
    if (modBit !== undefined) {
      this._modifiers |= modBit;
      await this._sendReport();
      return;
    }
    // Non-modifier: add to downKeys
    if (this._downKeys.has(code)) return;
    if (this._downKeys.size >= 6) return;
    this._downKeys.add(code);
    await this._sendReport();
  }

  /**
   * Release a modifier key (for on-screen special key panel).
   * @param {string} code - KeyboardEvent.code
   */
  async releaseModifier(code) {
    const modBit = MOD_KEY_BITS[code];
    if (modBit !== undefined) {
      this._modifiers &= ~modBit;
      await this._sendReport();
      return;
    }
    this._downKeys.delete(code);
    await this._sendReport();
  }

  /**
   * Send the current keyboard state as an HID report.
   */
  async _sendReport() {
    const keyCodes = [];
    for (const code of this._downKeys) {
      const hid = HID_CODE[code];
      if (hid !== undefined) {
        keyCodes.push(hid);
      }
    }
    // Pad to 6 keycodes with zeros
    while (keyCodes.length < 6) keyCodes.push(0x00);

    const packet = keyboardPacket(this._modifiers, keyCodes);
    try {
      await this._send(packet);
    } catch (err) {
      console.error('[kbd] Send error:', err);
    }
  }

  /**
   * Reset keyboard state (release all keys).
   * Call on focus loss or disconnect.
   */
  async reset() {
    this._downKeys.clear();
    this._modifiers = 0;
    const packet = keyboardPacket(0, [0, 0, 0, 0, 0, 0]);
    try {
      await this._send(packet);
    } catch (e) { /* ignore */ }
  }

  /**
   * Simulate a key press + release sequence (for paste / combo keys).
   * @param {number} hidCode - USB HID usage code
   * @param {number} [modifiers=0] - Modifier bits to hold during press
   * @param {number} [holdMs=10] - Milliseconds between press and release
   */
  async tapKey(hidCode, modifiers = 0, holdMs = 10) {
    // Press
    const pressPacket = keyboardPacket(modifiers, [hidCode, 0, 0, 0, 0, 0]);
    await this._send(pressPacket);
    await new Promise(r => setTimeout(r, holdMs));
    // Release
    const releasePacket = keyboardPacket(0, [0, 0, 0, 0, 0, 0]);
    await this._send(releasePacket);
  }

  /**
   * Simulate typing a string character by character.
   * Handles uppercase via Shift modifier.
   * @param {string} text
   * @param {number} [intervalMs=5] - Delay between keystrokes
   */
  async typeText(text, intervalMs = 5) {
    for (const ch of text) {
      const hidCode = charToHID(ch);
      if (hidCode === undefined) continue;

      let modifiers = 0;
      if (ch !== ch.toLowerCase()) {
        // Uppercase — hold left shift
        modifiers |= MOD.LSHIFT;
      }

      await this.tapKey(hidCode, modifiers, Math.max(intervalMs - 1, 1));
      await new Promise(r => setTimeout(r, intervalMs));
    }
  }
}

/**
 * Convert a single character to its USB HID usage code.
 * Handles standard US keyboard layout.
 */
function charToHID(ch) {
  // Letters
  if (ch >= 'a' && ch <= 'z') return 0x04 + (ch.charCodeAt(0) - 'a'.charCodeAt(0));
  if (ch >= 'A' && ch <= 'Z') return 0x04 + (ch.toLowerCase().charCodeAt(0) - 'a'.charCodeAt(0));

  // Numbers (top row)
  if (ch >= '1' && ch <= '9') return 0x1E + (ch.charCodeAt(0) - '1'.charCodeAt(0));
  if (ch === '0') return 0x27;

  // Symbols (US keyboard, without shift consideration — that's handled by modifiers)
  const symMap = {
    ' ': 0x2C,  '\n': 0x28, '\t': 0x2B,
    '-': 0x2D,  '_': 0x2D,  '=': 0x2E,  '+': 0x2E,
    '[': 0x2F,  '{': 0x2F,  ']': 0x30,  '}': 0x30,
    '\\':0x31,  '|': 0x31,
    ';': 0x33,  ':': 0x33,  "'": 0x34,  '"': 0x34,
    '`': 0x35,  '~': 0x35,
    ',': 0x36,  '<': 0x36,  '.': 0x37,  '>': 0x37,
    '/': 0x38,  '?': 0x38,
    '!': 0x1E,  '@': 0x1F,  '#': 0x20,  '$': 0x21,
    '%': 0x22,  '^': 0x23,  '&': 0x24,  '*': 0x25,
    '(': 0x26,  ')': 0x27,
  };
  return symMap[ch];
}

export { HID_CODE, MOD_KEY_BITS, charToHID };
