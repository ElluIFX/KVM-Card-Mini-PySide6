package com.webusbkvm.camera

import android.hardware.usb.UsbConstants
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbEndpoint
import android.hardware.usb.UsbInterface
import android.hardware.usb.UsbManager
import android.util.Log
import fi.iki.elonen.NanoHTTPD
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean

/**
 * NanoHTTPd-based MJPEG stream server.
 *
 * Serves:
 *   GET /          — Simple status page
 *   GET /stream    — MJPEG multipart stream
 *
 * Uses Android UsbManager directly for UVC device control.
 * MS2131 uses MJPEG format on a bulk IN endpoint.
 */
class StreamServer(private val port: Int) : NanoHTTPD(port) {

    private var uvcReader: UVCReader? = null
    private var connection: UsbDeviceConnection? = null
    private var claimedInterface: UsbInterface? = null
    private val frameQueue = ConcurrentLinkedQueue<ByteArray>()
    private val maxQueueSize = 4
    private var isStreaming = AtomicBoolean(false)

    // -- MJPEG boundary --
    private val BOUNDARY = "--myboundary"

    override fun serve(session: IHTTPSession): Response {
        return when (session.uri) {
            "/" -> serveStatusPage()
            "/stream" -> serveStream()
            else -> newFixedLengthResponse(
                Response.Status.NOT_FOUND,
                MIME_PLAINTEXT,
                "Not found. Try / or /stream"
            )
        }
    }

    // ================================================================
    // Status page
    // ================================================================
    private fun serveStatusPage(): Response {
        val html = """
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>USB Camera Server</title>
            <style>body{font-family:sans-serif;margin:40px;background:#111;color:#eee}
            h1{color:#4af}a{color:#4af}code{color:#ff0}</style></head>
            <body>
            <h1>USB Camera Server</h1>
            <p>状态: ${if (isStreaming.get()) "● 运行中" else "○ 等待设备"}</p>
            <p><strong>MJPEG 流:</strong> <a href="/stream"><code>/stream</code></a></p>
            <p>队列帧: ${frameQueue.size}</p>
            </body></html>
        """.trimIndent()
        return newFixedLengthResponse(html)
    }

    // ================================================================
    // MJPEG stream
    // ================================================================
    private fun serveStream(): Response {
        return object : Response(
            Response.Status.OK,
            "multipart/x-mixed-replace; boundary=$BOUNDARY",
            ChunkedMJPEGInputStream()
        ) {
            override fun close() {
                isStreaming.set(false)
            }
        }
    }

    private inner class ChunkedMJPEGInputStream : java.io.InputStream() {
        override fun read(): Int = -1

        override fun read(b: ByteArray, off: Int, len: Int): Int {
            isStreaming.set(true)
            while (isStreaming.get()) {
                val frame = frameQueue.poll()
                if (frame != null) {
                    val header = buildString {
                        append("$BOUNDARY\r\n")
                        append("Content-Type: image/jpeg\r\n")
                        append("Content-Length: ${frame.size}\r\n")
                        append("\r\n")
                    }.toByteArray()
                    val total = header.size + frame.size + 2 // +2 for trailing \r\n
                    if (total > len) return -1
                    System.arraycopy(header, 0, b, off, header.size)
                    System.arraycopy(frame, 0, b, off + header.size, frame.size)
                    b[off + header.size + frame.size] = '\r'.code.toByte()
                    b[off + header.size + frame.size + 1] = '\n'.code.toByte()
                    return total
                }
                try { Thread.sleep(10) } catch (e: InterruptedException) { break }
            }
            return -1
        }
    }

    // ================================================================
    // UVC connection management
    // ================================================================
    fun connectMS2131(manager: UsbManager, device: UsbDevice): Boolean {
        // Find the video streaming interface (usually interface 0 for MS2131)
        val usbIface: UsbInterface? = device.getInterface(0)
        if (usbIface == null) {
            Log.e(TAG, "No USB interface found")
            return false
        }

        val conn = manager.openDevice(device)
        if (conn == null) {
            Log.e(TAG, "Failed to open USB device")
            return false
        }

        if (!conn.claimInterface(usbIface, true)) {
            Log.e(TAG, "Failed to claim interface")
            conn.close()
            return false
        }

        connection = conn
        claimedInterface = usbIface

        // Find bulk IN endpoint
        val bulkInEp: UsbEndpoint? = usbIface.endpoints.find {
            it.type == UsbConstants.USB_ENDPOINT_XFER_BULK &&
            it.direction == UsbConstants.USB_DIR_IN
        }

        if (bulkInEp == null) {
            Log.e(TAG, "No bulk IN endpoint found — trying interrupt")
        }

        val endpoint = bulkInEp ?: usbIface.endpoints.firstOrNull {
            it.direction == UsbConstants.USB_DIR_IN
        }

        if (endpoint == null) {
            Log.e(TAG, "No usable IN endpoint")
            conn.releaseInterface(usbIface)
            conn.close()
            return false
        }

        Log.d(TAG, "Using endpoint 0x${endpoint.address.toString(16)}, maxPacket=${endpoint.maxPacketSize}")

        // Start reading frames
        uvcReader = UVCReader(conn, endpoint, usbIface, frameQueue, maxQueueSize)
        uvcReader?.start()
        Log.d(TAG, "UVC reader started")

        return true
    }

    fun disconnect() {
        uvcReader?.stop()
        uvcReader = null
        claimedInterface?.let { iface ->
            try { connection?.releaseInterface(iface) } catch (_: Exception) {}
        }
        claimedInterface = null
        connection?.close()
        connection = null
        frameQueue.clear()
    }
}
