import * as ws from './ws.mjs';
import * as kb from './kb.mjs';
import * as mouse from './mouse.mjs';

new Vue({
  el: '#app',
  data: {
    serviceHost: location.hostname,
    port: location.port,
    video_port: 0,
    secret: '',
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
    screenFormat: '',
    showFps: false,
    mouseSpeed: 15,
    keyAltPressed: false,
    keyCtrlPressed: false,
    toolbarVisible: true,
    set_show_fps: false,
    set_quality: 0,
    set_mouse_speed: 0,
    set_width: 0,
    set_height: 0,
    set_fmt: '',
    avail_fmt: ["YUYV", "UYVY", "RGB565", "RGB24", "MJPEG", "JPEG"],
  },
  mounted() {
    this.init();
  },
  methods: {
    async init() {
      const urlParams = new URLSearchParams(window.location.search);
      this.secret = urlParams.get('s') || '';
      if (this.secret) {
        console.debug('Secret: ' + this.secret);
      }
      try {
        const config = await this.fetchConfig();
        document.title = config.web_title;
        this.video_port = config.port;
        console.log('Video: ' + this.serviceHost + ":" + this.video_port)
        this.streamSrc = `http://${this.serviceHost}:${this.video_port}/stream`;

        // const streamOk = await this.pingStream(this.video_port);
        // if (!streamOk) {
        //   alert('Video stream seems not ready, check terminal for more info.');
        // }
        let wsAddr = `ws://${this.serviceHost}:${this.port}/websocket`;
        if (this.secret) {
          wsAddr += `?s=${this.secret}`;
        }
        this.$channel = await ws.init(wsAddr);
        this.bindKeyHandler();
        this.bindMouseHandler();

        this.screenWidth = config.video.width;
        this.screenHeight = config.video.height;
        this.screenQuality = config.video.quality;
        this.screenFormat = config.video.format;
        this.set_width = config.video.width;
        this.set_height = config.video.height;
        this.set_quality = config.video.quality;
        this.set_fmt = config.video.format;
        this.set_mouse_speed = this.mouseSpeed;
      } catch (e) {
        alert(e.toString());
      }
    },
    async pingStream(port) {
      try {
        let pingAddr = `http://${this.serviceHost}:${port}`;
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
        let resAddr = `/config?width=${this.set_width}&height=${this.set_height}&quality=${this.set_quality}&format=${this.set_fmt}`;
        if (this.secret) {
          resAddr += `&s=${this.secret}`;
        }
        const res = await fetch(resAddr);
        if (res.status === 200) {
          // reload window after 3s
          setTimeout(() => {
            window.location.reload();
          }, 3000);
        } else {
          alert('Apply config failed');
        }
      } catch (e) {
        alert(e.toString());
      }
    },
    cancelSettings() {
      this.set_mouse_speed = this.mouseSpeed;
      this.set_width = this.screenWidth;
      this.set_height = this.screenHeight;
      this.set_quality = this.screenQuality;
      this.set_fmt = this.screenFormat;
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
      this.mouseAbsPos[0] = evt.clientX;
      this.mouseAbsPos[1] = evt.clientY;
      const winWidth = window.innerWidth;
      const winHeight = window.innerHeight;
      const imageWidth = this.$refs.live.clientWidth;
      const imageHeight = this.$refs.live.clientHeight;
      if (winHeight > imageHeight) {
        const blackHeight = (winHeight - imageHeight) / 2
        if (this.mouseAbsPos[1] > winHeight - blackHeight) {
          this.mouseAbsPos[1] = winHeight - blackHeight
        } else if (this.mouseAbsPos[1] < blackHeight) {
          this.mouseAbsPos[1] = blackHeight
        }
        this.mouseAbsPos[1] = Math.floor((this.mouseAbsPos[1] - blackHeight) / imageHeight * 0x7fff)
      } else {
        this.mouseAbsPos[1] = Math.floor((this.mouseAbsPos[1]) / winHeight * 0x7fff)
      }
      if (winWidth > imageWidth) {
        const blackWidth = (winWidth - imageWidth) / 2
        if (this.mouseAbsPos[0] > winWidth - blackWidth) {
          this.mouseAbsPos[0] = winWidth - blackWidth
        } else if (this.mouseAbsPos[0] < blackWidth) {
          this.mouseAbsPos[0] = blackWidth
        }
        this.mouseAbsPos[0] = Math.floor((this.mouseAbsPos[0] - blackWidth) / imageWidth * 0x7fff)
      } else {
        this.mouseAbsPos[0] = Math.floor((this.mouseAbsPos[0]) / winWidth * 0x7fff)
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
      kb.sendSequence(this.$channel, this.pasteContent);
      this.pasteContent = '';
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
    toggleFullscreen() {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        document.documentElement.requestFullscreen();
      }
    }, resetDevice() {
      let payload = new Array(2);
      payload.fill(0);
      const msg = {
        type: 'reset_hid',
        payload
      };
      this.$channel.send(JSON.stringify(msg));
    }
  },
});
