import * as ws from './ws.mjs';
import * as kb from './kb.mjs';
import * as mouse from './mouse.mjs';

new Vue({
  el: '#app',
  data: {
    serviceHost: location.hostname,
    port: location.port || 80,
    secret: location.search.replace('?s=', ''),
    streamSrc: '',
    $channel: null,
    isKeyCaptureActive: false,
    isPointorLocked: false,
    mouseMoveSlice: [0, 0],
    mouseAbsPos: [0, 0],
    mouseAbsChanged: false,
    activeDialog: '',
    pasteContent: '',
    screenWidth: 0,
    screenHeight: 0,
    screenQuality: 0,
    showFps: false,
    mouseSpeed: 15,
    keyAltPressed: false,
    keyCtrlPressed: false,
    toolbarVisible: true,
    set_width: 0,
    set_height: 0,
    set_show_fps: false,
    set_quality: 0,
    set_mouse_speed: 0,
    isSeqSending: false,
  },
  mounted() {
    this.init();
  },
  methods: {
    async init() {
      if (this.secret) {
        console.debug('Secret: ' + this.secret);
      }
      try {
        const config = await this.fetchConfig();
        document.title = config.web_title;

        const streamOk = await this.pingStream(this.port);
        if (!streamOk) {
          alert('Video stream seems not ready, check terminal for more info.');
        }
        this.$channel = await ws.init(
          `ws://${this.serviceHost}:${this.port}/websocket`
        );
        this.bindKeyHandler();
        this.bindMouseHandler();

        this.streamSrc = `http://${this.serviceHost}:${this.port}/stream`;
        if (this.secret) {
          this.streamSrc += `?s=${this.secret}`;
        }
        this.screenWidth = config.video.width;
        this.screenHeight = config.video.height;
        this.screenQuality = config.video.quality;
        this.showFps = config.video.show_fps;
        this.set_width = config.video.width;
        this.set_height = config.video.height;
        this.set_show_fps = config.video.show_fps;
        this.set_quality = config.video.quality;
        this.set_mouse_speed = this.mouseSpeed;
      } catch (e) {
        alert(e.toString());
      }
    },
    async pingStream(port) {
      try {
        let pingAddr = `http://${this.serviceHost}:${port}/snapshot`;
        if (this.secret) {
          pingAddr += `?s=${this.secret}`;
        }
        const pingRes = await fetch(pingAddr);
        return pingRes.status === 200;
      } catch (e) {
        return false;
      }
    },
    async fetchConfig() {
      try {
        if (this.secret) {
          const res = await fetch(`/config?s=${this.secret}`);
          return res.json();
        }
        const res = await fetch('/config');
        return res.json();
      } catch (e) {
        return null;
      }
    },
    async applySettings() {
      try {
        this.mouseSpeed = this.set_mouse_speed;
        let resAddr = `/config?res=${this.set_width}x${this.set_height}&show_fps=${this.set_show_fps}&quality=${this.set_quality}`;
        if (this.secret) {
          resAddr += `&s=${this.secret}`;
        }
        const res = await fetch(resAddr);
        if (res.status === 200) {
          const config = await res.json();
          this.screenWidth = config.video.width;
          this.screenHeight = config.video.height;
          this.screenQuality = config.video.quality;
          this.showFps = config.video.show_fps;
          this.set_width = config.video.width;
          this.set_height = config.video.height;
          this.set_show_fps = config.video.show_fps;
          this.set_quality = config.video.quality;
        } else {
          alert('Apply config failed');
        }
      } catch (e) {
        alert(e.toString());
      }
    },
    cancelSettings() {
      this.set_width = this.screenWidth;
      this.set_height = this.screenHeight;
      this.set_show_fps = this.showFps;
      this.set_quality = this.screenQuality;
      this.set_mouse_speed = this.mouseSpeed;
    },
    bindKeyHandler() {
      document.addEventListener('keydown', (evt) => {
        if (evt.key === 'Control') {
          this.keyCtrlPressed = true;
        }
        if (evt.key === 'Alt') {
          this.keyAltPressed = true;
        }
        if (!this.isKeyCaptureActive) {
          if (evt.key === 'Enter' && !this.activeDialog) {
            this.setScreenFocus(true);
          }
          return;
        }

        evt.preventDefault();

        if (evt.repeat) {
          return;
        }

        if (evt.key === 'Escape' && evt.shiftKey) {
          this.setScreenFocus(false);
          return;
        }
        kb.sendEvent(this.$channel, evt.key, 'keydown');
      });

      document.addEventListener('keyup', (evt) => {
        if (evt.key === 'Control') {
          this.keyCtrlPressed = false;
        }
        if (evt.key === 'Alt') {
          this.keyAltPressed = false;
        }
        if (!this.isKeyCaptureActive) {
          return;
        }
        kb.sendEvent(this.$channel, evt.key, 'keyup');
      });
    },
    bindMouseHandler() {
      const mouseMoveSlice = this.mouseMoveSlice;


      document.addEventListener('pointerlockchange', (evt) => {
        this.isPointorLocked =
          document.pointerLockElement &&
          document.pointerLockElement.classList.contains('screen');
        mouse.sendEvent(this.$channel, '', 'reset');
      });

      window.setInterval(() => {
        if (mouseMoveSlice[0] !== 0 || mouseMoveSlice[1] !== 0) {
          mouse.sendEvent(this.$channel, mouseMoveSlice, 'move');
          mouseMoveSlice[0] = 0;
          mouseMoveSlice[1] = 0;
        }
        if (this.mouseAbsChanged) {
          mouse.sendEvent(this.$channel, this.mouseAbsPos, 'abs');
          this.mouseAbsChanged = false;
        }
      }, 60);

      mouse.sendEvent(this.$channel, 1, 'config-move-factor');
    },
    onScreenBlur() {
      this.isKeyCaptureActive = false;
      if (this.isPointorLocked) {
        this.setPointerLock(false);
      }
      kb.sendEvent(this.$channel, '', 'reset');
      this.toolbarVisible = true;
    },
    onScreenFocus() {
      this.setDialog();
      this.isKeyCaptureActive = true;
      kb.sendEvent(this.$channel, '', 'reset');
      setTimeout(() => {
        if (this.isKeyCaptureActive) {
          this.toolbarVisible = false;
        }
      }, 2000);
    },
    setScreenFocus(bool) {
      const screen = document.querySelector('.screen');
      screen[bool ? 'focus' : 'blur']();
      // if (bool) {
      //   setTimeout(() => {
      //     this.toolbarVisible = false;
      //   }, 1000);
      // }else{
      //   this.toolbarVisible = true;
      // }
    },
    setPointerLock(bool) {
      const screen = document.querySelector('.screen');
      if (bool) {
        try {
          this.setDialog();
          screen.requestPointerLock();
        } catch (e) { }
      } else {
        document.exitPointerLock();
      }
    },
    onScreenMouseMove(evt) {
      if (!this.isKeyCaptureActive) {
        return;
      }
      // get absolute position
      this.mouseAbsPos[0] = evt.clientX;
      this.mouseAbsPos[1] = evt.clientY;
      // get window size
      const winWidth = window.innerWidth;
      const winHeight = window.innerHeight;
      // notice: screen is in the top of window
      const screenRatio = this.screenWidth / this.screenHeight;
      const winRatio = winWidth / winHeight;
      // calc Y
      if (winHeight > this.screenHeight) {
        // black border on bottom
        this.mouseAbsPos[1] = Math.floor(this.mouseAbsPos[1] / this.screenHeight * 0x7fff)
        if (this.mouseAbsPos[1] > 0x7fff) {
          this.mouseAbsPos[1] = 0x7fff
        }
      } else if (winRatio < screenRatio) {
        // black border on bottom
        const blackHeight = winHeight - winWidth / screenRatio
        if (this.mouseAbsPos[1] > winHeight - blackHeight) {
          this.mouseAbsPos[1] = winHeight - blackHeight
        }
        this.mouseAbsPos[1] = Math.floor((this.mouseAbsPos[1]) / (winHeight - blackHeight) * 0x7fff)
      } else {
        this.mouseAbsPos[1] = Math.floor((this.mouseAbsPos[1]) / (winHeight) * 0x7fff)
      }
      // calc X
      if (winRatio > screenRatio) {
        var blackWidth = 0
        if (winHeight > this.screenHeight) {
          blackWidth = winWidth - this.screenHeight * screenRatio
        }
        else {
          blackWidth = winWidth - winHeight * screenRatio
        }
        this.mouseAbsPos[0] -= blackWidth / 2
        if (this.mouseAbsPos[0] < 0) {
          this.mouseAbsPos[0] = 0
        }
        this.mouseAbsPos[0] = Math.floor((this.mouseAbsPos[0]) / (winWidth - blackWidth) * 0x7fff)
        if (this.mouseAbsPos[0] > 0x7fff) {
          this.mouseAbsPos[0] = 0x7fff
        }
      } else {
        this.mouseAbsPos[0] = Math.floor((this.mouseAbsPos[0]) / (winWidth) * 0x7fff)
      }

      if (!this.isPointorLocked) {
        this.mouseAbsChanged = true;
        return;
      }
      this.mouseMoveSlice[0] += evt.movementX * this.mouseSpeed;
      this.mouseMoveSlice[1] += evt.movementY * this.mouseSpeed;
    },
    onScreenMouseDown(evt) {
      if (!this.isKeyCaptureActive) {
        this.setScreenFocus(true);
        return;
      }
      evt.preventDefault();
      if (!this.isPointorLocked && this.keyCtrlPressed && this.keyAltPressed) {
        if (evt.button === 0) {
          this.setPointerLock(true);
        }
        return;
      }
      mouse.sendEvent(this.$channel, evt.button, 'mousedown');
    },
    onScreenMouseUp(evt) {
      if (!this.isKeyCaptureActive) {
        return;
      }
      evt.preventDefault();
      mouse.sendEvent(this.$channel, evt.button, 'mouseup');
    },
    onScreenMouseWheel(evt) {
      if (!this.isKeyCaptureActive) {
        return;
      }
      evt.preventDefault();
      mouse.sendEvent(this.$channel, evt.wheelDeltaY, 'wheel');
    },
    async doRemotePaste() {
      if (this.isSeqSending) {
        return;
      }
      this.isSeqSending = true;
      await kb.sendSequence(this.$channel, this.pasteContent);
      this.pasteContent = '';
      this.isSeqSending = false;
    },
    setDialog(name) {
      if (name) {
        this.setPointerLock(false);
        this.setScreenFocus(false);
        this.activeDialog = name;
      } else {
        this.activeDialog = '';
      }
    },
  },
});
