package com.webusbkvm.camera;

import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.util.Log;
import fi.iki.elonen.NanoHTTPD;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * NanoHTTPd-based MJPEG stream server.
 * Serves GET / (status) and GET /stream (MJPEG multipart).
 */
public class StreamServer extends NanoHTTPD {

    private static final String TAG = "StreamServer";
    private static final String BOUNDARY = "--myboundary";

    private UVCReader uvcReader;
    private UsbDeviceConnection connection;
    private UsbInterface claimedInterface;
    private final ConcurrentLinkedQueue<byte[]> frameQueue = new ConcurrentLinkedQueue<>();

    public StreamServer(int port) {
        super(port);
    }

    @Override
    public Response serve(IHTTPSession session) {
        String uri = session.getUri();
        if ("/".equals(uri)) {
            return serveStatusPage();
        } else if ("/stream".equals(uri)) {
            return serveStream();
        }
        return newFixedLengthResponse(Response.Status.NOT_FOUND, MIME_PLAINTEXT,
            "Not found. Try / or /stream");
    }

    private Response serveStatusPage() {
        String body = "<!DOCTYPE html><html><head><meta charset=\"utf-8\">" +
            "<title>USB Camera Server</title>" +
            "<style>body{font-family:sans-serif;margin:40px;background:#111;color:#eee}" +
            "h1{color:#4af}a{color:#4af}code{color:#ff0}</style></head>" +
            "<body><h1>USB Camera Server</h1>" +
            "<p>状态: " + (uvcReader != null ? "● 运行中" : "○ 未连接") + "</p>" +
            "<p><strong>MJPEG 流:</strong> <a href=\"/stream\"><code>/stream</code></a></p>" +
            "<p>队列帧: " + frameQueue.size() + "</p></body></html>";
        return newFixedLengthResponse(body);
    }

    private Response serveStream() {
        return newChunkedResponse(Response.Status.OK,
            "multipart/x-mixed-replace; boundary=" + BOUNDARY, new MJPEGInputStream());
    }

    private class MJPEGInputStream extends InputStream {
        byte[] currentFrame = null;
        int pos = 0;
        ByteArrayOutputStream headerBuf = new ByteArrayOutputStream();

        @Override
        public int read() { return 0; }

        @Override
        public int read(byte[] b, int off, int len) {
            // Build header for current frame
            if (currentFrame == null) {
                byte[] frame = frameQueue.poll();
                if (frame == null) {
                    try { Thread.sleep(10); } catch (InterruptedException e) {}
                    return 0;
                }
                String header = BOUNDARY + "\r\n" +
                    "Content-Type: image/jpeg\r\n" +
                    "Content-Length: " + frame.length + "\r\n\r\n";
                byte[] hdr = header.getBytes();
                byte[] trailer = "\r\n".getBytes();
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                try {
                    bos.write(hdr);
                    bos.write(frame);
                    bos.write(trailer);
                } catch (Exception e) {}
                currentFrame = bos.toByteArray();
                pos = 0;
            }

            int remaining = currentFrame.length - pos;
            int toRead = Math.min(len, remaining);
            if (toRead > 0) {
                System.arraycopy(currentFrame, pos, b, off, toRead);
                pos += toRead;
            }
            if (pos >= currentFrame.length) {
                currentFrame = null;
            }
            return toRead;
        }
    }

    public boolean connectMS2131(UsbManager manager, UsbDevice device) {
        UsbInterface usbIface = null;
        for (int i = 0; i < device.getInterfaceCount(); i++) {
            UsbInterface iface = device.getInterface(i);
            for (int j = 0; j < iface.getEndpointCount(); j++) {
                UsbEndpoint ep = iface.getEndpoint(j);
                if (ep.getDirection() == UsbConstants.USB_DIR_IN) {
                    usbIface = iface;
                    break;
                }
            }
            if (usbIface != null) break;
        }

        if (usbIface == null) {
            Log.e(TAG, "No IN endpoint found");
            return false;
        }

        UsbDeviceConnection conn = manager.openDevice(device);
        if (conn == null) {
            Log.e(TAG, "Failed to open USB device");
            return false;
        }

        if (!conn.claimInterface(usbIface, true)) {
            Log.e(TAG, "Failed to claim interface");
            conn.close();
            return false;
        }

        connection = conn;
        claimedInterface = usbIface;

        UsbEndpoint bulkInEp = null;
        for (int j = 0; j < usbIface.getEndpointCount(); j++) {
            UsbEndpoint ep = usbIface.getEndpoint(j);
            if (ep.getType() == UsbConstants.USB_ENDPOINT_XFER_BULK &&
                ep.getDirection() == UsbConstants.USB_DIR_IN) {
                bulkInEp = ep;
                break;
            }
        }
        if (bulkInEp == null) {
            // Try interrupt endpoint
            for (int j = 0; j < usbIface.getEndpointCount(); j++) {
                UsbEndpoint ep = usbIface.getEndpoint(j);
                if (ep.getDirection() == UsbConstants.USB_DIR_IN) {
                    bulkInEp = ep;
                    break;
                }
            }
        }

        if (bulkInEp == null) {
            Log.e(TAG, "No usable IN endpoint");
            conn.releaseInterface(usbIface);
            conn.close();
            return false;
        }

        Log.d(TAG, "Using endpoint 0x" + Integer.toHexString(bulkInEp.getAddress()) +
            ", maxPacket=" + bulkInEp.getMaxPacketSize());

        int maxSize = Math.max(bulkInEp.getMaxPacketSize(), 16384);
        uvcReader = new UVCReader(conn, bulkInEp, usbIface, frameQueue, 4, maxSize);
        uvcReader.start();
        Log.d(TAG, "UVC reader started");
        return true;
    }

    public void disconnect() {
        if (uvcReader != null) {
            uvcReader.shutdown();
            uvcReader = null;
        }
        if (claimedInterface != null && connection != null) {
            try { connection.releaseInterface(claimedInterface); } catch (Exception e) {}
            claimedInterface = null;
        }
        if (connection != null) {
            connection.close();
            connection = null;
        }
        frameQueue.clear();
    }
}
