package com.webusbkvm.camera;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

public class CameraService extends Service {

    public static final String TAG = "CameraService";
    public static final int HTTP_PORT = 8080;
    private static final String CHANNEL_ID = "camera_server_channel";
    public static volatile boolean isRunning = false;

    private StreamServer streamServer;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, 0,
            new Intent(this, MainActivity.class),
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        Notification notification = builder
            .setContentTitle("USB Camera Server")
            .setContentText("MJPEG 流: http://localhost:" + HTTP_PORT + "/stream")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setContentIntent(pendingIntent)
            .build();

        startForeground(1, notification);

        // Start the MJPEG HTTP server
        UsbDevice device = intent != null ? intent.getParcelableExtra("device") : null;
        if (device != null) {
            UsbManager manager = (UsbManager) getSystemService(USB_SERVICE);
            streamServer = new StreamServer(HTTP_PORT);
            try {
                streamServer.start();
                boolean ok = streamServer.connectMS2131(manager, device);
                if (ok) {
                    Log.d(TAG, "MJPEG server started on port " + HTTP_PORT);
                    isRunning = true;
                } else {
                    Log.e(TAG, "Failed to connect MS2131");
                    streamServer.stop();
                }
            } catch (Exception e) {
                Log.e(TAG, "Server start error: " + e.getMessage());
            }
        }

        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        if (streamServer != null) {
            streamServer.disconnect();
            streamServer.stop();
            streamServer = null;
        }
        isRunning = false;
        Log.d(TAG, "Service destroyed");
        super.onDestroy();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Camera Server",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("USB Camera MJPEG Stream Server");
            NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            manager.createNotificationChannel(channel);
        }
    }
}
