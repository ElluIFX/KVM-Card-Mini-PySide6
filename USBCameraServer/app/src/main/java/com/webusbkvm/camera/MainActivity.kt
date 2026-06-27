package com.webusbkvm.camera

import android.app.PendingIntent
import android.content.Intent
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Build
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var usbManager: UsbManager
    private lateinit var statusText: TextView
    private lateinit var urlText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        urlText = findViewById(R.id.urlText)

        usbManager = getSystemService(USB_SERVICE) as UsbManager

        // Start service on launch
        startCameraServer()
    }

    override fun onResume() {
        super.onResume()
        updateUI()
    }

    private fun updateUI() {
        val running = CameraService.isRunning
        statusText.text = if (running) "● 运行中" else "○ 已停止"
        urlText.text = if (running) {
            "http://localhost:${CameraService.HTTP_PORT}/\nhttp://localhost:${CameraService.HTTP_PORT}/stream"
        } else {
            "等待 MS2131 设备连接..."
        }
    }

    private fun startCameraServer() {
        // Find MS2131 device
        val device = findMS2131()
        if (device == null) {
            Toast.makeText(this, "未检测到 MS2131 采集卡。请连接后重试。", Toast.LENGTH_LONG).show()
            return
        }

        // Check/request USB permission
        if (!usbManager.hasPermission(device)) {
            val pi = PendingIntent.getBroadcast(
                this, 0,
                Intent(ACTION_USB_PERMISSION),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            )
            usbManager.requestPermission(device, pi)
            Toast.makeText(this, "请授权 USB 设备访问", Toast.LENGTH_SHORT).show()
            return
        }

        // Start foreground service
        val intent = Intent(this, CameraService::class.java).apply {
            putExtra("device", device)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
        updateUI()
    }

    private fun findMS2131(): UsbDevice? {
        return usbManager.deviceList.values.find { device ->
            device.vendorId == MS2131_VID && device.productId == MS2131_PID
        }
    }

    companion object {
        const val MS2131_VID = 0x534D
        const val MS2131_PID = 0x2131
        const val ACTION_USB_PERMISSION = "com.webusbkvm.camera.USB_PERMISSION"
    }
}
