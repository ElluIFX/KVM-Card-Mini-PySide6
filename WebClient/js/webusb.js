/**
 * webusb.js — WebUSB device connection and transfer layer for CH582F KVM
 *
 * Handles device discovery, connection, endpoint management and data transfers
 * via the WebUSB API (navigator.usb).
 *
 * Device filters:
 *   vendorId:  0x413D
 *   productId: 0x2107
 *
 * Endpoints (USB1, Interface 0):
 *   EP1 OUT (0x01): host → device, 64 bytes max (we send 10-byte packets)
 *   EP1 IN  (0x81): device → host, 64 bytes max
 */

import { buildCommand, CMD, switchPacket, SWITCH_SUB, parseSwitchResponse, parseLEDResponse } from './protocol.js';

const VENDOR_ID  = 0x413D;
const PRODUCT_ID = 0x2107;

const EP_OUT = 1;    // endpoint 0x01 (host to device)
const EP_IN  = 1;    // Chrome WebUSB uses raw number, NOT 0x81

export class KVMDevice {
  constructor() {
    this.device = null;
    this.epOut = null;
    this.epIn = null;
    this._connected = false;
  }

  /** Whether a device is currently opened and claimed. */
  get connected() {
    return this._connected;
  }

  /**
   * Prompt the user to select a KVM device and connect.
   * Must be called from a user-gesture (click) handler.
   */
  async connect() {
    if (this._connected) {
      console.warn('[KVMDevice] Already connected');
      return;
    }

    // Request device
    let device;
    try {
      device = await navigator.usb.requestDevice({
        filters: [{ vendorId: VENDOR_ID, productId: PRODUCT_ID }]
      });
    } catch (err) {
      if (err.name === 'NotFoundError') {
        throw new Error('No device selected');
      }
      throw err;
    }

    await this._openDevice(device);
  }

  /**
   * Reconnect to a previously paired device (no chooser dialog).
   */
  async reconnect() {
    const devices = await navigator.usb.getDevices();
    const kvm = devices.find(
      d => d.vendorId === VENDOR_ID && d.productId === PRODUCT_ID
    );
    if (!kvm) {
      throw new Error('No paired KVM device found. Use Connect first.');
    }
    await this._openDevice(kvm);
  }

  /** @private */
  async _openDevice(device) {
    this.device = device;

    try {
      await device.open();
    } catch (err) {
      this.device = null;
      throw new Error(`Failed to open device: ${err.message}`);
    }

    console.log('[KVMDevice] Device opened');

    // Select configuration #1
    if (device.configuration === null) {
      await device.selectConfiguration(1);
    }
    console.log('[KVMDevice] Configuration selected, config:', device.configuration?.configurationValue);

    // Claim interface #0
    try {
      await device.claimInterface(0);
    } catch (err) {
      await device.close();
      this.device = null;
      throw new Error(`Failed to claim interface: ${err.message}. The device may be in use by another application.`);
    }
    console.log('[KVMDevice] Interface claimed');

    // Verify endpoints exist (debug dump)
    const iface = device.configuration.interfaces[0];
    const alt = iface.alternate;
    const eps = alt.endpoints;
    console.log('[KVMDevice] Found', eps.length, 'endpoints:',
      eps.map(e => `0x${e.endpointNumber.toString(16)}/${e.direction}/${e.type}`).join(', '));

    this.epOut = eps.find(e => e.endpointNumber === 1 && e.direction === 'out');
    this.epIn  = eps.find(e => e.endpointNumber === 1 && e.direction === 'in');

    if (!this.epOut || !this.epIn) {
      // Try without direction filter in case vendor-specific reports differently
      this.epOut = eps.find(e => (e.endpointNumber & 0x7F) === 1 && e.direction === 'out');
      this.epIn  = eps.find(e => (e.endpointNumber & 0x7F) === 1 && e.direction === 'in');
    }

    if (!this.epOut || !this.epIn) {
      await device.releaseInterface(0);
      await device.close();
      this.device = null;
      throw new Error('Device endpoints not found. Firmware may need updating.');
    }

    this._connected = true;
    console.log('[KVMDevice] Connected successfully. EP OUT:', this.epOut, 'EP IN:', this.epIn);
  }

  /**
   * Send raw data to EP1 OUT.
   * @param {Uint8Array|ArrayBuffer} data - Data to send (10 bytes for our protocol)
   */
  async send(data) {
    if (!this._connected) throw new Error('Device not connected');
    const result = await this.device.transferOut(EP_OUT, data);
    if (result.status !== 'ok') {
      console.warn('[KVMDevice] transferOut status:', result.status);
    }
    return result;
  }

  /**
   * Read a response from EP1 IN (up to 64 bytes).
   * Note: Chrome WebUSB uses the raw endpoint number (1), NOT the full address (0x81).
   * @returns {Promise<DataView>} Response data
   */
  async recv() {
    if (!this._connected) throw new Error('Device not connected');
    const result = await this.device.transferIn(EP_IN, 64);
    if (result.status !== 'ok') {
      console.warn('[KVMDevice] transferIn status:', result.status);
    }
    return result.data;
  }

  /**
   * Send a command and optionally read the response.
   * @param {Uint8Array} cmdBuffer - 10-byte command packet
   * @param {boolean} [expectResponse=false]
   * @returns {Promise<DataView|null>} Response data or null
   */
  async sendCommand(cmdBuffer, expectResponse = false) {
    await this.send(cmdBuffer);
    if (expectResponse) {
      return await this.recv();
    }
    return null;
  }

  /**
   * Query USB switch state.
   * @returns {Promise<{pb4: number, pb7: number, pa12: number}|null>}
   */
  async querySwitchState() {
    const buf = switchPacket(SWITCH_SUB.QUERY);
    await this.send(buf);
    const data = await this.recv();
    return parseSwitchResponse(data);
  }

  /**
   * Query keyboard LED state.
   * @returns {Promise<{numLock: boolean, capsLock: boolean, scrollLock: boolean}|null>}
   */
  async queryLEDs() {
    const buf = buildCommand(CMD.READ_LEDS, 0x00);
    await this.send(buf);
    const data = await this.recv();
    return parseLEDResponse(data);
  }

  /**
   * Disconnect and release the device.
   */
  async disconnect() {
    if (!this._connected) return;
    try {
      await this.device.releaseInterface(0);
    } catch (e) { /* ignore */ }
    try {
      await this.device.close();
    } catch (e) { /* ignore */ }
    this.device = null;
    this.epOut = null;
    this.epIn = null;
    this._connected = false;
    console.log('[KVMDevice] Disconnected');
  }

  /**
   * Reset device connection (disconnect + reconnect attempt).
   */
  async reset() {
    const hadDevice = !!this.device;
    await this.disconnect();
    if (hadDevice) {
      // small delay to let USB settle
      await new Promise(r => setTimeout(r, 500));
      try {
        await this.reconnect();
      } catch (e) {
        console.warn('[KVMDevice] Auto-reconnect after reset failed, will need manual connect');
      }
    }
  }
}
