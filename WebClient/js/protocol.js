/**
 * protocol.js — CH582F KVM 10-byte vendor protocol packet builder
 *
 * The firmware (Firmware/HID_CompliantDev/src/Main.c DevEP1_OUT_Deal)
 * parses a 10-byte report sent via EP1 OUT (endpoint 0x01):
 *   buf[0]  = command code
 *   buf[1-9] = payload (command-dependent)
 *
 * Responses arrive on EP1 IN (endpoint 0x81) as 10-byte packets.
 */

/** Command codes — must match firmware DevEP1_OUT_Deal switch cases */
export const CMD = {
  KEYBOARD:   0x01,  // 8-byte standard HID keyboard report at bytes 2-9
  MOUSE_ABS:  0x02,  // 6-byte absolute mouse report at bytes 2-7
  READ_LEDS:  0x03,  // Read keyboard LED lights (response: byte 2 = LEDs)
  RESET_MCU:  0x04,  // Software reset MCU
  SET_RGB:    0x05,  // Set WS2812B RGB LED (R,G,B at bytes 2-4)
  MOUSE_REL:  0x07,  // 4-byte relative mouse report at bytes 2-5
  USB_SWITCH: 0x6F,  // USB switch control (sub-cmd at byte 2)
};

/** USB switch sub-commands */
export const SWITCH_SUB = {
  FLOAT:  0,  // Disconnect, power off
  MASTER: 1,  // Switch to controlling host
  TARGET: 2,  // Switch to controlled (target) machine
  QUERY:  3,  // Query GPIO state
};

/** Modifier bit positions for the keyboard modifier byte */
export const MOD = {
  LCTRL:  0x01,
  LSHIFT: 0x02,
  LALT:   0x04,
  LGUI:   0x08,  // Left Meta / Windows key
  RCTRL:  0x10,
  RSHIFT: 0x20,
  RALT:   0x40,
  RGUI:   0x80,
};

/** Mouse button bitmask */
export const MBTN = {
  LEFT:    0x01,
  RIGHT:   0x02,
  MIDDLE:  0x04,
  X1:      0x08,  // Back
  X2:      0x10,  // Forward
};

/**
 * Build a 10-byte command packet.
 * @param {number} cmd - Command code from CMD
 * @param {...number} payload - Up to 9 payload bytes (positions 1-9)
 * @returns {Uint8Array} 10-byte buffer
 */
export function buildCommand(cmd, ...payload) {
  const buf = new Uint8Array(10);
  buf[0] = cmd;
  for (let i = 0; i < payload.length && i < 9; i++) {
    buf[i + 1] = payload[i] & 0xFF;
  }
  return buf;
}

/**
 * Build a keyboard report packet.
 *
 * The 8-byte HID keyboard report (placed at bytes 2-9 of the 10-byte packet):
 *   [0] = modifier bits
 *   [1] = reserved (0x00)
 *   [2..7] = up to 6 simultaneous key codes
 *
 * @param {number} modifiers - OR'd modifier bits from MOD
 * @param {number[]} keyCodes - Array of HID key codes (max 6, zero-padded)
 * @returns {Uint8Array}
 */
export function keyboardPacket(modifiers, keyCodes) {
  const buf = new Uint8Array(10);
  buf[0] = CMD.KEYBOARD;
  buf[1] = 0x00;       // reserved
  buf[2] = modifiers;   // modifier byte
  buf[3] = 0x00;        // reserved (OEM)
  // populate up to 6 keycodes starting at buf[4]
  for (let i = 0; i < 6; i++) {
    buf[4 + i] = (i < keyCodes.length) ? (keyCodes[i] & 0xFF) : 0x00;
  }
  // buf[2] through buf[9] form the 8-byte HID keyboard report
  return buf;
}

/**
 * Build an absolute mouse report packet.
 *
 * The 6-byte mouse report (placed at bytes 2-7):
 *   [0] = button bits (MBTN flags)
 *   [1] = X low byte
 *   [2] = X high byte
 *   [3] = Y low byte
 *   [4] = Y high byte
 *   [5] = wheel (signed int8, -127..127)
 *
 * @param {number} buttons - OR'd MBTN flags
 * @param {number} x - X coordinate (0..0x7FFF)
 * @param {number} y - Y coordinate (0..0x7FFF)
 * @param {number} [wheel=0] - Wheel delta (-127..127)
 * @returns {Uint8Array}
 */
export function absMousePacket(buttons, x, y, wheel = 0) {
  const buf = new Uint8Array(10);
  buf[0] = CMD.MOUSE_ABS;
  buf[1] = 0x00;
  buf[2] = buttons & 0xFF;    // buttons
  buf[3] = x & 0xFF;          // X low
  buf[4] = (x >> 8) & 0xFF;   // X high
  buf[5] = y & 0xFF;          // Y low
  buf[6] = (y >> 8) & 0xFF;   // Y high
  buf[7] = wheel & 0xFF;      // wheel (signed byte)
  return buf;
}

/**
 * Build a relative mouse report packet.
 *
 * The 4-byte report (placed at bytes 2-5):
 *   [0] = button bits (MBTN flags)
 *   [1] = dX (signed int8, -127..127)
 *   [2] = dY (signed int8, -127..127)
 *   [3] = wheel (signed int8, -127..127)
 *
 * @param {number} buttons - OR'd MBTN flags
 * @param {number} dx - X delta (signed byte clamped to -127..127)
 * @param {number} dy - Y delta (signed byte clamped to -127..127)
 * @param {number} [wheel=0] - Wheel delta (-127..127)
 * @returns {Uint8Array}
 */
export function relMousePacket(buttons, dx, dy, wheel = 0) {
  const buf = new Uint8Array(10);
  buf[0] = CMD.MOUSE_REL;
  buf[1] = 0x00;
  buf[2] = buttons & 0xFF;
  buf[3] = dx & 0xFF;
  buf[4] = dy & 0xFF;
  buf[5] = wheel & 0xFF;
  return buf;
}

/**
 * Build a USB switch control / query packet.
 * @param {number} subCmd - 0=float, 1=master, 2=target, 3=query
 * @returns {Uint8Array}
 */
export function switchPacket(subCmd) {
  return buildCommand(CMD.USB_SWITCH, 0x00, subCmd);
}

/**
 * Build a read-LEDs query packet.
 * @returns {Uint8Array}
 */
export function readLEDsPacket() {
  return buildCommand(CMD.READ_LEDS, 0x00);
}

/**
 * Build an RGB LED color packet.
 * @param {number} r - Red (0-255)
 * @param {number} g - Green (0-255)
 * @param {number} b - Blue (0-255)
 * @returns {Uint8Array}
 */
export function rgbPacket(r, g, b) {
  return buildCommand(CMD.SET_RGB, 0x00, r, g, b);
}

/**
 * Build a reset-MCU packet (sends software reset).
 * @returns {Uint8Array}
 */
export function resetPacket() {
  return buildCommand(CMD.RESET_MCU, 0x00);
}

/**
 * Parse a USB switch query response.
 * @param {DataView} data - 10-byte response packet
 * @returns {{pb4: number, pb7: number, pa12: number}|null}
 */
export function parseSwitchResponse(data) {
  if (data.getUint8(0) !== CMD.USB_SWITCH) return null;
  if (data.getUint8(2) !== 3) return null;
  return {
    pb4: data.getUint8(3),  // power
    pb7: data.getUint8(4),  // direction (IN)
    pa12: data.getUint8(5), // enable (EN#, active low)
  };
}

/**
 * Parse keyboard LED response (extended).
 * Command 0x03 response:
 *   byte 0: 0x03 (command echo)
 *   byte 2: keyboard LED bits (bit0=Num, bit1=Caps, bit2=Scroll)
 *   byte 3: MCU status flags (bit0=ready, bit1=USB1, bit2=USB2, bit3=KBD, bit4=MS)
 *   byte 4: LED auto mode (1=auto, 0=manual)
 * @param {DataView} data - 10-byte response packet
 * @returns {{numLock: boolean, capsLock: boolean, scrollLock: boolean, flags: number, ledMode: number}|null}
 */
export function parseLEDResponse(data) {
  if (data.getUint8(0) !== 0x03) return null;
  const bits = data.getUint8(2);
  return {
    numLock:    !!(bits & 0x01),
    capsLock:   !!(bits & 0x02),
    scrollLock: !!(bits & 0x04),
    flags:      data.getUint8(3),   // MCU status flags
    ledMode:    data.getUint8(4),   // 1=auto, 0=manual
  };
}

/** MCU status flag bit definitions (byte 3 of command 0x03 response) */
export const MCU_FLAGS = {
  READY:    0x01,  // MCU init complete
  USB1_OK:  0x02,  // USB1 configured by host
  USB2_OK:  0x04,  // USB2 configured by target
  KBD_ACT:  0x08,  // USB2 keyboard active (target reading data)
  MS_ACT:   0x10,  // USB2 mouse active (target reading data)
};
