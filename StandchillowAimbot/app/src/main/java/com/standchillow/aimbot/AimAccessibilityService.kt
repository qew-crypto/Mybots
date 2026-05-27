package com.standchillow.aimbot

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Build
import android.view.accessibility.AccessibilityEvent

class AimAccessibilityService : AccessibilityService() {

    companion object {
        var instance: AimAccessibilityService? = null
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Not used — we only need gesture dispatch
    }

    override fun onInterrupt() {
        // Required override
    }

    override fun onDestroy() {
        instance = null
        super.onDestroy()
    }

    fun performSwipe(deltaX: Float, deltaY: Float) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return

        val display = resources.displayMetrics
        val centerX = display.widthPixels / 2f
        val centerY = display.heightPixels / 2f

        val swipeCenterX = centerX + display.widthPixels * 0.25f
        val swipeCenterY = centerY

        val startX = swipeCenterX
        val startY = swipeCenterY
        val endX = (swipeCenterX + deltaX).coerceIn(0f, display.widthPixels.toFloat())
        val endY = (swipeCenterY + deltaY).coerceIn(0f, display.heightPixels.toFloat())

        val path = Path().apply {
            moveTo(startX, startY)
            lineTo(endX, endY)
        }

        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 50))
            .build()

        dispatchGesture(gesture, null, null)
    }
}
