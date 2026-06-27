package com.webusbkvm.camera

import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbEndpoint
import android.hardware.usb.UsbInterface
import android.util.Log
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Reads MJPEG frames from a USB UVC device's bulk endpoint.
 *
 * Performs minimal UVC negotiation (PROBE/COMMIT) to start the MJPEG stream,
 * then continuously reads the bulk endpoint and extracts JPEG frames.
 */
class UVCReader(
    private val connection: UsbDeviceConnection,
    private val bulkInEp: UsbEndpoint,
    private val usbIface: UsbInterface,
    private val frameQueue: ConcurrentLinkedQueue<ByteArray>,
    private val maxQueue: Int
) : Thread("UVCReader") {

    private val running = AtomicBoolean(true)
    private val jpegBuffer = java.io.ByteArrayOutputStream(256 * 1024)
    private var inFrame = false

    companion object {
        const val TAG = "UVCReader"
        // UVC control request constants
        const val UVC_SET_CUR = 0x01
        const val UVC_GET_CUR = 0x81
        const val UVC_VS_PROBE_CONTROL  = 0x01
        const val UVC_VS_COMMIT_CONTROL = 0x02
        const val UVC_VS_STREAM_INTERFACE = 1
        // USB direction
        const val USB_DIR_OUT = 0
        const val USB_TYPE_CLASS = 0x20
        const val USB_RECIP_INTERFACE = 0x01
    }

    override fun run() {
        Log.d(TAG, "UVCReader started")

        if (!negotiateStream()) {
            Log.e(TAG, "UVC negotiation failed — device may not output data")
            // Continue anyway — some MS2131 firmware auto-starts
        }

        // Start reading from bulk endpoint
        val buf = ByteArray(bulkInEp.maxPacketSize.coerceAtLeast(16384))
        Log.d(TAG, "Reading from bulk EP, buffer size=${buf.size}")

        while (running.get()) {
            val len = connection.bulkTransfer(bulkInEp, buf, buf.size, 500)
            if (len > 0) {
                parseData(buf, len)
            } else if (len < 0) {
                // Timeout or error — that's fine for bulk
            }
        }
        Log.d(TAG, "UVCReader stopped")
    }

    /**
     * Parse raw USB bulk data looking for JPEG frames.
     * MS2131 outputs complete JPEG frames delimited by SOI (FF D8) and EOI (FF D9).
     */
    private fun parseData(data: ByteArray, len: Int) {
        for (i in 0 until len) {
            val b = data[i].toInt() and 0xFF

            if (!inFrame) {
                // Look for JPEG SOI marker: FF D8
                if (b == 0xD8 && jpegBuffer.size() > 0 && data.getOrElse(i - 1) { 0 }.toInt() and 0xFF == 0xFF) {
                    jpegBuffer.reset()
                    jpegBuffer.write(0xFF)
                    jpegBuffer.write(0xD8)
                    inFrame = true
                }
            }

            if (inFrame) {
                jpegBuffer.write(b)

                // Look for JPEG EOI marker: FF D9
                if (b == 0xD9 && jpegBuffer.size() >= 2) {
                    val buf = jpegBuffer.toByteArray()
                    val prev = buf[buf.size - 2].toInt() and 0xFF
                    if (prev == 0xFF) {
                        // Complete frame found
                        pushFrame(buf.clone())
                        jpegBuffer.reset()
                        inFrame = false
                    }
                }
            }
        }

        // Safety: if buffer gets too large, discard
        if (jpegBuffer.size() > 512 * 1024) {
            Log.w(TAG, "JPEG buffer overflow, resetting")
            jpegBuffer.reset()
            inFrame = false
        }
    }

    private fun pushFrame(data: ByteArray) {
        // Drop frames if queue is full (keep latest)
        while (frameQueue.size >= maxQueue) {
            frameQueue.poll()
        }
        frameQueue.offer(data)
    }

    /**
     * Send UVC probe/commit control requests to negotiate MJPEG format.
     *
     * MS2131 accepts standard MJPEG probe values:
     *   bFormatIndex=2 (MJPEG), bFrameIndex=1 (1080p 30fps)
     */
    private fun negotiateStream(): Boolean {
        try {
            // VS_PROBE_CONTROL: negotiate format
            val probeRequest = ByteBuffer.allocate(34).order(ByteOrder.LITTLE_ENDIAN).apply {
                putShort(0x0100)     // bmHint: 0x0001 = keep frame interval
                put(0x02)            // bFormatIndex: 2 = MJPEG
                put(0x01)            // bFrameIndex: 1 = first frame size (1080p)
                putInt(333333)       // dwFrameInterval: 30fps = 33.3333ms * 10000ns
                putShort(0)          // wKeyFrameRate
                putShort(0)          // wPFrameRate
                putShort(0)          // wCompQuality
                putShort(0)          // wCompWindowSize
                putShort(0)          // wDelay
                putInt(1920 * 1080 * 2 * 30) // dwMaxVideoFrameSize
                putInt(1)            // dwMaxPayloadTransferSize (set later)
                // bmControl / bmTransportHint etc filled with zeros
            }

            val result = connection.controlTransfer(
                USB_DIR_OUT or USB_TYPE_CLASS or USB_RECIP_INTERFACE,
                UVC_SET_CUR,
                UVC_VS_PROBE_CONTROL shl 8,
                UVC_VS_STREAM_INTERFACE,
                probeRequest.array(), probeRequest.array().size, 1000
            )
            Log.d(TAG, "VS_PROBE_CONTROL result: $result")

            if (result < 0) {
                // Probe failed — try without it (some devices auto-start)
                Log.w(TAG, "Probe failed ($result), attempting without negotiation")
                return false
            }

            // VS_COMMIT_CONTROL: commit the negotiated format
            val commitResult = connection.controlTransfer(
                USB_DIR_OUT or USB_TYPE_CLASS or USB_RECIP_INTERFACE,
                UVC_SET_CUR,
                UVC_VS_COMMIT_CONTROL shl 8,
                UVC_VS_STREAM_INTERFACE,
                probeRequest.array(), probeRequest.array().size, 1000
            )
            Log.d(TAG, "VS_COMMIT_CONTROL result: $commitResult")
            return commitResult >= 0
        } catch (e: Exception) {
            Log.e(TAG, "Negotiation error: ${e.message}")
            return false
        }
    }

    fun stop() {
        running.set(false)
        interrupt()
    }
}
