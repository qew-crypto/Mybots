package com.standchillow.aimbot

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView

class OverlayService : Service() {

    companion object {
        private const val CHANNEL_ID = "overlay_channel"
        private const val NOTIFICATION_ID = 1002
        private const val FRAME_INTERVAL_MS = 33L // ~30 FPS
    }

    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private var controlPanel: View? = null
    private var crosshairView: CrosshairView? = null

    private val handler = Handler(Looper.getMainLooper())
    private var engine: AimbotEngine? = null
    private var prefs: AimbotPrefs? = null
    private var isAiming = false
    private var screenWidth = 0
    private var screenHeight = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())

        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        prefs = AimbotPrefs(this)
        engine = AimbotEngine(prefs!!)

        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        windowManager.defaultDisplay.getRealMetrics(metrics)
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels

        createCrosshairOverlay()
        createControlPanel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startAimLoop()
        return START_STICKY
    }

    private fun createCrosshairOverlay() {
        crosshairView = CrosshairView(this)

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP or Gravity.START

        windowManager.addView(crosshairView, params)
        overlayView = crosshairView
    }

    @Suppress("ClickableViewAccessibility")
    private fun createControlPanel() {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.argb(200, 30, 30, 30))
            setPadding(16, 12, 16, 12)
        }

        val statusText = TextView(this).apply {
            text = "⊕ AIMBOT"
            setTextColor(Color.parseColor("#00FF00"))
            textSize = 14f
            gravity = Gravity.CENTER
        }
        panel.addView(statusText)

        val btnToggle = TextView(this).apply {
            text = "ON"
            setTextColor(Color.WHITE)
            textSize = 12f
            gravity = Gravity.CENTER
            setPadding(8, 8, 8, 8)
            setBackgroundColor(Color.parseColor("#4CAF50"))
            setOnClickListener {
                isAiming = !isAiming
                text = if (isAiming) "ON" else "OFF"
                setBackgroundColor(
                    if (isAiming) Color.parseColor("#4CAF50")
                    else Color.parseColor("#F44336")
                )
                statusText.setTextColor(
                    if (isAiming) Color.parseColor("#00FF00")
                    else Color.parseColor("#FF0000")
                )
                if (!isAiming) {
                    engine?.reset()
                    crosshairView?.clearTarget()
                }
            }
        }
        panel.addView(btnToggle, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = 8 })

        val btnClose = TextView(this).apply {
            text = "✕"
            setTextColor(Color.WHITE)
            textSize = 12f
            gravity = Gravity.CENTER
            setPadding(8, 8, 8, 8)
            setBackgroundColor(Color.parseColor("#880000"))
            setOnClickListener { stopSelf() }
        }
        panel.addView(btnClose, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = 4 })

        val params = WindowManager.LayoutParams(
            160,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP or Gravity.START
        params.x = 20
        params.y = 200

        // Drag support
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f

        panel.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = initialX + (event.rawX - initialTouchX).toInt()
                    params.y = initialY + (event.rawY - initialTouchY).toInt()
                    windowManager.updateViewLayout(panel, params)
                    true
                }
                else -> false
            }
        }

        windowManager.addView(panel, params)
        controlPanel = panel
        isAiming = true
    }

    private fun startAimLoop() {
        handler.post(object : Runnable {
            override fun run() {
                if (isAiming && ScreenCaptureService.isCapturing) {
                    processFrame()
                }
                handler.postDelayed(this, FRAME_INTERVAL_MS)
            }
        })
    }

    private fun processFrame() {
        val bitmap = ScreenCaptureService.lastBitmap ?: return
        val engineInstance = engine ?: return

        val result: AimbotEngine.AimResult
        synchronized(ScreenCaptureService) {
            result = engineInstance.processFrame(bitmap)
        }

        if (result.target != null) {
            val scaleFactor = 2
            crosshairView?.setTarget(
                result.target.centerX * scaleFactor,
                result.target.centerY * scaleFactor,
                prefs?.fovRadius?.times(scaleFactor) ?: 300
            )

            if (prefs?.aimEnabled == true) {
                AimAccessibilityService.instance?.performSwipe(
                    result.deltaX * scaleFactor,
                    result.deltaY * scaleFactor
                )
            }
        } else {
            crosshairView?.clearTarget()
        }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        overlayView?.let { windowManager.removeView(it) }
        controlPanel?.let { windowManager.removeView(it) }
        engine?.reset()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Оверлей аимбота",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Канал для оверлея"
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("Standchillow Aimbot")
                .setContentText("Оверлей активен")
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
                .setContentTitle("Standchillow Aimbot")
                .setContentText("Оверлей активен")
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .build()
        }
    }
}
