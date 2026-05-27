package com.standchillow.aimbot

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.util.DisplayMetrics
import android.view.WindowManager

class ScreenCaptureService : Service() {

    companion object {
        var resultCode: Int = 0
        var resultData: Intent? = null

        var lastBitmap: Bitmap? = null
            private set

        var isCapturing = false
            private set

        private const val CHANNEL_ID = "capture_channel"
        private const val NOTIFICATION_ID = 1001
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var handlerThread: HandlerThread? = null
    private var handler: Handler? = null

    private var screenWidth = 0
    private var screenHeight = 0
    private var screenDensity = 0

    private val scaleFactor = 2

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        val notification = buildNotification()
        startForeground(NOTIFICATION_ID, notification)

        handlerThread = HandlerThread("CaptureThread").also { it.start() }
        handler = Handler(handlerThread!!.looper)

        val wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        wm.defaultDisplay.getRealMetrics(metrics)
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startCapture()
        return START_STICKY
    }

    private fun startCapture() {
        if (isCapturing) return

        val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val data = resultData ?: return
        mediaProjection = mpm.getMediaProjection(resultCode, data)

        val captureWidth = screenWidth / scaleFactor
        val captureHeight = screenHeight / scaleFactor

        imageReader = ImageReader.newInstance(
            captureWidth,
            captureHeight,
            PixelFormat.RGBA_8888,
            2
        )

        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "AimbotCapture",
            captureWidth,
            captureHeight,
            screenDensity / scaleFactor,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader!!.surface,
            null,
            handler
        )

        imageReader?.setOnImageAvailableListener({ reader ->
            var image: Image? = null
            try {
                image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
                val planes = image.planes
                val buffer = planes[0].buffer
                val pixelStride = planes[0].pixelStride
                val rowStride = planes[0].rowStride
                val rowPadding = rowStride - pixelStride * captureWidth

                val bmp = Bitmap.createBitmap(
                    captureWidth + rowPadding / pixelStride,
                    captureHeight,
                    Bitmap.Config.ARGB_8888
                )
                bmp.copyPixelsFromBuffer(buffer)

                val cropped = if (rowPadding > 0) {
                    Bitmap.createBitmap(bmp, 0, 0, captureWidth, captureHeight)
                } else {
                    bmp
                }

                synchronized(this) {
                    lastBitmap?.recycle()
                    lastBitmap = cropped
                    if (cropped !== bmp) bmp.recycle()
                }
            } catch (_: Exception) {
            } finally {
                image?.close()
            }
        }, handler)

        isCapturing = true

        mediaProjection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                stopCapture()
            }
        }, handler)
    }

    private fun stopCapture() {
        isCapturing = false
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
        mediaProjection?.stop()
        mediaProjection = null
        synchronized(this) {
            lastBitmap?.recycle()
            lastBitmap = null
        }
    }

    override fun onDestroy() {
        stopCapture()
        handlerThread?.quitSafely()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Захват экрана",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Канал для уведомления о захвате экрана"
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("Standchillow Aimbot")
                .setContentText("Захват экрана активен")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
                .setContentTitle("Standchillow Aimbot")
                .setContentText("Захват экрана активен")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .build()
        }
    }
}
