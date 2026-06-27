package com.webusbkvm.camera;

import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Reads MJPEG frames from a USB UVC device's bulk endpoint.
 */
public class UVCReader extends Thread {

    private static final String TAG = "UVCReader";
    private static final int UVC_SET_CUR = 0x01;
    private static final int UVC_VS_PROBE_CONTROL  = 0x01;
    private static final int UVC_VS_COMMIT_CONTROL = 0x02;
    private static final int UVC_VS_STREAM_INTERFACE = 1;
    private static final int USB_DIR_OUT = 0;
    private static final int USB_TYPE_CLASS = 0x20;
    private static final int USB_RECIP_INTERFACE = 0x01;

    private final UsbDeviceConnection connection;
    private final UsbEndpoint bulkInEp;
    private final UsbInterface usbIface;
    private final ConcurrentLinkedQueue<byte[]> frameQueue;
    private final int maxQueue;
    private final int bufferSize;
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final ByteArrayOutputStream jpegBuffer = new ByteArrayOutputStream(256 * 1024);
    private boolean inFrame = false;

    public UVCReader(UsbDeviceConnection connection, UsbEndpoint bulkInEp,
                     UsbInterface usbIface, ConcurrentLinkedQueue<byte[]> frameQueue,
                     int maxQueue, int bufferSize) {
        super("UVCReader");
        this.connection = connection;
        this.bulkInEp = bulkInEp;
        this.usbIface = usbIface;
        this.frameQueue = frameQueue;
        this.maxQueue = maxQueue;
        this.bufferSize = bufferSize;
    }

    @Override
    public void run() {
        Log.d(TAG, "UVCReader started");

        int negResult = negotiateStream();
        Log.d(TAG, "Negotiation result: " + negResult);

        byte[] buf = new byte[bufferSize];
        while (running.get()) {
            int len = connection.bulkTransfer(bulkInEp, buf, buf.length, 500);
            if (len > 0) {
                parseData(buf, len);
            }
        }
        Log.d(TAG, "UVCReader stopped");
    }

    private void parseData(byte[] data, int len) {
        for (int i = 0; i < len; i++) {
            int b = data[i] & 0xFF;

            if (!inFrame) {
                if (b == 0xD8 && jpegBuffer.size() > 0) {
                    int prev = jpegBuffer.size() > 0 ?
                        jpegBuffer.toByteArray()[jpegBuffer.size() - 1] & 0xFF : 0;
                    if (prev == 0xFF) {
                        jpegBuffer.reset();
                        jpegBuffer.write(0xFF);
                        jpegBuffer.write(0xD8);
                        inFrame = true;
                    }
                }
            }

            if (inFrame) {
                jpegBuffer.write(b);
                if (b == 0xD9 && jpegBuffer.size() >= 2) {
                    byte[] buf = jpegBuffer.toByteArray();
                    if ((buf[buf.length - 2] & 0xFF) == 0xFF) {
                        pushFrame(buf.clone());
                        jpegBuffer.reset();
                        inFrame = false;
                    }
                }
            }
        }

        if (jpegBuffer.size() > 512 * 1024) {
            Log.w(TAG, "JPEG buffer overflow, resetting");
            jpegBuffer.reset();
            inFrame = false;
        }
    }

    private void pushFrame(byte[] data) {
        while (frameQueue.size() >= maxQueue) {
            frameQueue.poll();
        }
        frameQueue.offer(data);
    }

    private int negotiateStream() {
        int requestType = USB_DIR_OUT | USB_TYPE_CLASS | USB_RECIP_INTERFACE;
        int wValue = UVC_VS_PROBE_CONTROL << 8;
        int wIndex = UVC_VS_STREAM_INTERFACE;

        // Build probe structure (26 bytes for UVC 1.1)
        byte[] probe = new byte[26];
        // bmHint (2 bytes): keep frame interval
        probe[0] = 0x00; probe[1] = 0x01;
        // bFormatIndex (1 byte): 2 = MJPEG
        probe[2] = 0x02;
        // bFrameIndex (1 byte): 1
        probe[3] = 0x01;
        // dwFrameInterval (4 bytes, LE): 333333 = 30fps
        probe[4] = 0x15; probe[5] = 0x16; probe[6] = 0x05; probe[7] = 0x00;

        int r1 = connection.controlTransfer(requestType, UVC_SET_CUR, wValue, wIndex, probe, probe.length, 1000);
        Log.d(TAG, "VS_PROBE_CONTROL: " + r1);

        if (r1 < 0) {
            Log.w(TAG, "Probe failed, trying without negotiation");
            return r1;
        }

        // Commit
        wValue = UVC_VS_COMMIT_CONTROL << 8;
        int r2 = connection.controlTransfer(requestType, UVC_SET_CUR, wValue, wIndex, probe, probe.length, 1000);
        Log.d(TAG, "VS_COMMIT_CONTROL: " + r2);
        return r2;
    }

    public void shutdown() {
        running.set(false);
        interrupt();
    }
}
