/**
 * rgb.js — WS2812B RGB LED control via CH582F firmware
 *
 * Sends CMD.SET_RGB packets to control the onboard RGB LED.
 */

import { rgbPacket } from './protocol.js';

export class RGBController {
  /**
   * @param {function(Uint8Array):Promise} sendFn
   */
  constructor(sendFn) {
    this._send = sendFn;
  }

  /** Set LED color by R, G, B components (0-255 each) */
  async setColor(r, g, b) {
    const buf = rgbPacket(r, g, b);
    await this._send(buf);
  }

  /** Turn LED off */
  async off() {
    return await this.setColor(0, 0, 0);
  }

  /** Turn LED red */
  async red() { return await this.setColor(255, 0, 0); }

  /** Turn LED green */
  async green() { return await this.setColor(0, 255, 0); }

  /** Turn LED blue */
  async blue() { return await this.setColor(0, 0, 255); }

  /** Turn LED white */
  async white() { return await this.setColor(255, 255, 255); }

  /** Set LED from CSS hex color string (e.g. "#ff8800") */
  async setHex(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return;
    return await this.setColor(r, g, b);
  }
}
