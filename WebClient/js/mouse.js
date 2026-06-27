/**
 * mouse.js — Mouse (absolute + relative) and touch event handling for CH582F KVM
 *
 * Two input modes:
 *   Absolute Mode (default): mousemove → absolute coords scaled to 0-0x7FFF.
 *     Also used for touch input.
 *   Relative Mode: Pointer Lock → movementX/Y deltas, clamped to ±127.
 *
 * Scroll wheel is handled in both modes.
 */

import { absMousePacket, relMousePacket, MBTN } from './protocol.js';

/** Clamp value to int8 range [-127, 127] */
function i8clamp(v) {
  return Math.max(-127, Math.min(127, Math.round(v)));
}

/** Linear interpolation */
function lerp(a, b, t) {
  return a + (b - a) * t;
}

export class MouseHandler {
  /**
   * @param {function(Uint8Array):Promise} sendFn
   * @param {HTMLElement} targetEl - element to receive mouse events on (video)
   */
  constructor(sendFn, targetEl) {
    this._send = sendFn;
    this._el = targetEl;

    /** Absolute mode state */
    this._absX = 0;
    this._absY = 0;
    this._buttons = 0;

    /** Relative mode state */
    this._relMode = false;
    this._relX = 0;
    this._relY = 0;
    this._relTimer = null;

    /** Wheel */
    this._wheel = 0;
    this._wheelTimer = null;

    /** Whether mouse capture is active */
    this._active = false;

    /** Touch state */
    this._touchCount = 0;
    this._touchStartTime = 0;
    this._touchStartPos = null;

    // Bind event handlers
    this._boundHandleMouseMove = this._handleMouseMove.bind(this);
    this._boundHandleMouseDown = this._handleMouseDown.bind(this);
    this._boundHandleMouseUp   = this._handleMouseUp.bind(this);
    this._boundHandleWheel     = this._handleWheel.bind(this);
    this._boundHandleContextMenu = this._handleContextMenu.bind(this);
    this._boundHandlePointerChange = this._handlePointerChange.bind(this);

    this._boundHandleTouchStart  = this._handleTouchStart.bind(this);
    this._boundHandleTouchMove   = this._handleTouchMove.bind(this);
    this._boundHandleTouchEnd    = this._handleTouchEnd.bind(this);
  }

  get active() { return this._active; }
  set active(v) {
    this._active = v;
    if (!v) {
      this._releasePointerLock();
      this.stopRelTimer();
    }
  }

  get relMode() { return this._relMode; }
  set relMode(v) { this._relMode = v; }

  /**
   * Bind all event listeners to the target element.
   */
  bind() {
    const el = this._el;
    el.addEventListener('mousemove',       this._boundHandleMouseMove);
    el.addEventListener('mousedown',       this._boundHandleMouseDown);
    el.addEventListener('mouseup',         this._boundHandleMouseUp);
    el.addEventListener('wheel',           this._boundHandleWheel);
    el.addEventListener('contextmenu',     this._boundHandleContextMenu);

    el.addEventListener('touchstart',      this._boundHandleTouchStart, { passive: false });
    el.addEventListener('touchmove',       this._boundHandleTouchMove,  { passive: false });
    el.addEventListener('touchend',        this._boundHandleTouchEnd,   { passive: false });

    document.addEventListener('pointerlockchange', this._boundHandlePointerChange);
  }

  /**
   * Unbind all event listeners.
   */
  unbind() {
    const el = this._el;
    el.removeEventListener('mousemove',       this._boundHandleMouseMove);
    el.removeEventListener('mousedown',       this._boundHandleMouseDown);
    el.removeEventListener('mouseup',         this._boundHandleMouseUp);
    el.removeEventListener('wheel',           this._boundHandleWheel);
    el.removeEventListener('contextmenu',     this._boundHandleContextMenu);

    el.removeEventListener('touchstart',      this._boundHandleTouchStart);
    el.removeEventListener('touchmove',       this._boundHandleTouchMove);
    el.removeEventListener('touchend',        this._boundHandleTouchEnd);

    document.removeEventListener('pointerlockchange', this._boundHandlePointerChange);
  }

  /* ========================================================================
     Mouse Events (Absolute Mode)
     ======================================================================== */

  _handleMouseMove(e) {
    if (!this._active) return;
    if (this._relMode) return; // handled by pointer lock

    const rect = this._el.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    // Scale mouse position to [0, 1] relative to element
    const rx = (e.clientX - rect.left) / rect.width;
    const ry = (e.clientY - rect.top)  / rect.height;

    // Scale to 0..0x7FFF (32767)
    this._absX = Math.max(0, Math.min(0x7FFF, Math.round(rx * 0x7FFF)));
    this._absY = Math.max(0, Math.min(0x7FFF, Math.round(ry * 0x7FFF)));

    this._sendAbs();
  }

  _handleMouseDown(e) {
    if (!this._active) return;
    if (this._relMode) {
      this._el.requestPointerLock({ unadjustedMovement: true });
      return;
    }
    e.preventDefault();
    this._buttons = e.buttons & 0x1F; // 5 button bits
    this._sendAbs();
  }

  _handleMouseUp(e) {
    if (!this._active) return;
    if (this._relMode) return;
    this._buttons = e.buttons & 0x1F;
    this._sendAbs();
  }

  _handleContextMenu(e) {
    // Prevent context menu on right-click in the video area
    if (this._active) e.preventDefault();
  }

  /** Send absolute mouse report */
  async _sendAbs() {
    const packet = absMousePacket(this._buttons, this._absX, this._absY, this._wheel);
    try {
      await this._send(packet);
      // Clear wheel after one report
      if (this._wheel !== 0) {
        this._wheel = 0;
      }
    } catch (err) {
      console.error('[mouse] Send error:', err);
    }
  }

  /* ========================================================================
     Wheel
     ======================================================================== */

  _handleWheel(e) {
    if (!this._active) return;
    e.preventDefault();

    const delta = e.deltaY > 0 ? 0xFF : (e.deltaY < 0 ? 0x01 : 0);
    if (delta === 0) return;

    this._wheel = delta;
    this._sendCurrent();

    // Auto-clear wheel after 100ms
    if (this._wheelTimer) clearTimeout(this._wheelTimer);
    this._wheelTimer = setTimeout(() => {
      this._wheel = 0;
      this._wheelTimer = null;
    }, 100);
  }

  /** Send whichever packet type is current */
  _sendCurrent() {
    if (this._relMode) {
      return this._sendRel();
    }
    return this._sendAbs();
  }

  /* ========================================================================
     Pointer Lock (Relative Mode)
     ======================================================================== */

  _handlePointerChange() {
    if (document.pointerLockElement === this._el) {
      // Pointer locked — relative mode active
      this._relMode = true;
      this._relX = 0;
      this._relY = 0;
      document.addEventListener('mousemove', this._boundPointerMove = (e) => {
        this._relX += e.movementX;
        this._relY += e.movementY;
      });
      document.addEventListener('mousedown', this._boundPointerBtnDown = (e) => {
        this._buttons = e.buttons & 0x1F;
      });
      document.addEventListener('mouseup', this._boundPointerBtnUp = (e) => {
        this._buttons = e.buttons & 0x1F;
      });
      this._startRelTimer();
    } else {
      // Pointer unlocked — back to absolute mode
      this._relMode = false;
      document.removeEventListener('mousemove', this._boundPointerMove);
      document.removeEventListener('mousedown', this._boundPointerBtnDown);
      document.removeEventListener('mouseup', this._boundPointerBtnUp);
      this.stopRelTimer();
      this._buttons = 0;
      // Send empty relative packet to finalize
    }
  }

  _startRelTimer() {
    this.stopRelTimer();
    this._relTimer = setInterval(() => {
      if (this._relX !== 0 || this._relY !== 0 || this._buttons !== 0 || this._wheel !== 0) {
        this._sendRel();
      }
    }, 10); // ~100Hz
  }

  stopRelTimer() {
    if (this._relTimer) {
      clearInterval(this._relTimer);
      this._relTimer = null;
    }
  }

  async _sendRel() {
    // Split large deltas into int8-sized chunks
    let x = this._relX;
    let y = this._relY;
    const w = this._wheel;
    this._wheel = 0;
    this._relX = 0;
    this._relY = 0;

    // Send in chunks of max 127 each
    while (Math.abs(x) > 127 || Math.abs(y) > 127) {
      const sx = i8clamp(x);
      const sy = i8clamp(y);
      const packet = relMousePacket(this._buttons, sx, sy, 0);
      try { await this._send(packet); } catch (err) { return; }
      x -= sx;
      y -= sy;
    }
    // Send remainder
    if (Math.abs(x) > 0 || Math.abs(y) > 0 || this._buttons !== 0 || w !== 0) {
      const packet = relMousePacket(this._buttons, i8clamp(x), i8clamp(y), i8clamp(w));
      try { await this._send(packet); } catch (err) { /* ignore */ }
    }
  }

  _releasePointerLock() {
    if (document.pointerLockElement === this._el) {
      document.exitPointerLock();
    }
  }

  /* ========================================================================
     Touch Events (Android tablet support)
     Mapping: 1 finger = move + left-click
              2 finger tap = right-click
              2 finger drag = scroll
              3 finger tap = middle-click
     ======================================================================== */

  _handleTouchStart(e) {
    if (!this._active) return;
    e.preventDefault();

    this._touchCount = e.touches.length;
    this._touchStartTime = Date.now();

    // Use primary touch for position
    const t = e.touches[0];
    this._touchStartPos = { x: t.clientX, y: t.clientY };
    this._updateAbsFromTouch(t);

    if (e.touches.length === 1) {
      // Single finger — left button down + position
      this._buttons |= MBTN.LEFT;
      this._sendAbs();
    } else if (e.touches.length === 2) {
      // Two finger — track for right-click or scroll
      this._buttons = 0;
    } else if (e.touches.length === 3) {
      // Three finger — middle button
      this._buttons = MBTN.MIDDLE;
      this._sendAbs();
    }
  }

  _handleTouchMove(e) {
    if (!this._active) return;
    e.preventDefault();

    const t = e.touches[0];
    this._updateAbsFromTouch(t);
    this._sendAbs();
  }

  _handleTouchEnd(e) {
    if (!this._active) return;
    e.preventDefault();

    const elapsed = Date.now() - this._touchStartTime;
    const wasShort = elapsed < 300; // Short tap threshold

    if (this._touchCount === 2 && wasShort) {
      // Two-finger short tap → right-click
      this._buttons = MBTN.RIGHT;
      this._sendAbs();
      // Release after a tick
      setTimeout(() => {
        this._buttons = 0;
        this._sendAbs();
      }, 50);
    } else if (this._touchCount === 3 && wasShort) {
      // Three-finger short tap → middle-click
      setTimeout(() => {
        this._buttons = 0;
        this._sendAbs();
      }, 50);
    } else {
      // Release all buttons
      this._buttons = 0;
      this._sendAbs();
    }

    this._touchCount = 0;
    this._touchStartTime = 0;
    this._touchStartPos = null;
  }

  _updateAbsFromTouch(touch) {
    const rect = this._el.getBoundingClientRect();
    const rx = Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width));
    const ry = Math.max(0, Math.min(1, (touch.clientY - rect.top) / rect.height));
    this._absX = Math.round(rx * 0x7FFF);
    this._absY = Math.round(ry * 0x7FFF);
  }

  /**
   * Reset mouse state (release all buttons).
   */
  reset() {
    this._buttons = 0;
    this._wheel = 0;
    this._relX = 0;
    this._relY = 0;
    this._relMode = false;
    this._releasePointerLock();
    this.stopRelTimer();
  }
}
