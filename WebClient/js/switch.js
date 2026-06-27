/**
 * switch.js — USB switch control UI component
 *
 * Controls the CH582F GPIO-based USB switch (PB4/PB7/PA12).
 * Three states: Float (disconnect), Master (connect to controlling host),
 *                Target (connect to controlled machine).
 */

import { switchPacket, SWITCH_SUB } from './protocol.js';

export class SwitchController {
  /**
   * @param {function(Uint8Array):Promise} sendFn
   * @param {function():Promise<DataView>} recvFn
   */
  constructor(sendFn, recvFn) {
    this._send = sendFn;
    this._recv = recvFn;

    /** Current GPIO state */
    this.state = {
      pb4:  0,  // Power (NMOS control)
      pb7:  0,  // Direction (IN signal)
      pa12: 0,  // Enable (EN#, active low)
    };

    /** Map GPIO to human-readable mode */
    this.mode = 'unknown';
  }

  /**
   * Interpret GPIO state to mode string.
   *   PB4=0, PB7=1, PA12=1 → Float (power off, high-Z)
   *   PB4=1, PB7=0, PA12=0 → Master (host)
   *   PB4=1, PB7=1, PA12=0 → Target (controlled)
   */
  _deriveMode() {
    const { pb4, pb7, pa12 } = this.state;
    if (pb4 === 0 && pb7 === 1 && pa12 === 1) return 'float';
    if (pb4 === 1 && pb7 === 0 && pa12 === 0) return 'master';
    if (pb4 === 1 && pb7 === 1 && pa12 === 0) return 'target';
    return 'unknown';
  }

  /** Query current switch state from device */
  async query() {
    const buf = switchPacket(SWITCH_SUB.QUERY);
    await this._send(buf);
    const data = await this._recv();
    if (data.getUint8(0) !== 0x6F || data.getUint8(2) !== 3) {
      console.warn('[switch] Invalid query response');
      return null;
    }
    this.state.pb4  = data.getUint8(3);
    this.state.pb7  = data.getUint8(4);
    this.state.pa12 = data.getUint8(5);
    this.mode = this._deriveMode();
    return this.state;
  }

  /** Switch to float (disconnect, power off) */
  async setFloat() {
    const buf = switchPacket(SWITCH_SUB.FLOAT);
    await this._send(buf);
    await new Promise(r => setTimeout(r, 50));
    return await this.query();
  }

  /** Switch to master (connect to controlling host) */
  async setMaster() {
    const buf = switchPacket(SWITCH_SUB.MASTER);
    await this._send(buf);
    await new Promise(r => setTimeout(r, 50));
    return await this.query();
  }

  /** Switch to target (connect to controlled machine) */
  async setTarget() {
    const buf = switchPacket(SWITCH_SUB.TARGET);
    await this._send(buf);
    await new Promise(r => setTimeout(r, 50));
    return await this.query();
  }
}
