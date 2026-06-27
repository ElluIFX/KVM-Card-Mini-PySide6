package com.webusbkvm.camera

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.graphics.SurfaceTexture
import android.hardware.usb.UsbDevice
import android.os.Build
import android.os.IBinder
import android.util.Log

class CameraService : Service() {

    private var streamServer: StreamServer? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Start foreground notification
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("USB Camera Server")
                .setContentText("MJPEG 流: http://localhost:$HTTP_PORT/stream")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .setContentIntent(pendingIntent)
                .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
                .setContentTitle("USB Camera Server")
                .setContentText("MJPEG 流运行中")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .setContentIntent(pendingIntent)
                .build()
        }

        startForeground(1, notification)

        // Start the MJPEG HTTP server
        streamServer = StreamServer(HTTP_PORT).apply {
            start()
        }
        Log.d(TAG, "MJPEG server started on port $HTTP_PORT")
        isRunning = true

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        streamServer?.stop()
        streamServer = null
        isRunning = false
        Log.d(TAG, "Service destroyed")
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Camera Server",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "USB Camera MJPEG Stream Server"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    companion object {
        const val TAG = "CameraService"
        const val HTTP_PORT = 8080
        const val CHANNEL_ID = "camera_server_channel"
        @Volatile var isRunning = false
    }
}
