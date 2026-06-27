package com.webusbkvm.camera;

import android.app.PendingIntent;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.Toast;
import android.app.Activity;

public class MainActivity extends Activity {

    public static final int MS2131_VID = 0x534D;
    public static final int MS2131_PID = 0x2131;
    public static final String ACTION_USB_PERMISSION = "com.webusbkvm.camera.USB_PERMISSION";

    private UsbManager usbManager;
    private TextView statusText;
    private TextView urlText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        statusText = findViewById(R.id.statusText);
        urlText = findViewById(R.id.urlText);
        usbManager = (UsbManager) getSystemService(USB_SERVICE);

        startCameraServer();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateUI();
    }

    private void updateUI() {
        boolean running = CameraService.isRunning;
        statusText.setText(running ? "● 运行中" : "○ 已停止");
        urlText.setText(running
            ? "http://localhost:" + CameraService.HTTP_PORT + "/\nhttp://localhost:" + CameraService.HTTP_PORT + "/stream"
            : "等待 MS2131 设备连接...");
    }

    private void startCameraServer() {
        UsbDevice device = findMS2131();
        if (device == null) {
            Toast.makeText(this, "未检测到 MS2131 采集卡。请连接后重试。", Toast.LENGTH_LONG).show();
            return;
        }

        if (!usbManager.hasPermission(device)) {
            PendingIntent pi = PendingIntent.getBroadcast(
                this, 0,
                new Intent(ACTION_USB_PERMISSION),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
            );
            usbManager.requestPermission(device, pi);
            Toast.makeText(this, "请授权 USB 设备访问", Toast.LENGTH_SHORT).show();
            return;
        }

        Intent intent = new Intent(this, CameraService.class);
        intent.putExtra("device", device);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
        updateUI();
    }

    private UsbDevice findMS2131() {
        for (UsbDevice device : usbManager.getDeviceList().values()) {
            if (device.getVendorId() == MS2131_VID && device.getProductId() == MS2131_PID) {
                return device;
            }
        }
        return null;
    }
}
