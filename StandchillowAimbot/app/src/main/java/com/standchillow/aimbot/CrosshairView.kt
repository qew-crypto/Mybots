package com.standchillow.aimbot

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.view.View

class CrosshairView(context: Context) : View(context) {

    private var targetX = -1
    private var targetY = -1
    private var fovRadius = 150

    private val crosshairPaint = Paint().apply {
        color = Color.parseColor("#80FFFFFF")
        strokeWidth = 2f
        style = Paint.Style.STROKE
        isAntiAlias = true
    }

    private val fovPaint = Paint().apply {
        color = Color.parseColor("#2000FF00")
        style = Paint.Style.STROKE
        strokeWidth = 1.5f
        isAntiAlias = true
    }

    private val targetPaint = Paint().apply {
        color = Color.parseColor("#FFFF0000")
        strokeWidth = 3f
        style = Paint.Style.STROKE
        isAntiAlias = true
    }

    private val targetFillPaint = Paint().apply {
        color = Color.parseColor("#30FF0000")
        style = Paint.Style.FILL
        isAntiAlias = true
    }

    private val linePaint = Paint().apply {
        color = Color.parseColor("#80FF4444")
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
        isAntiAlias = true
        pathEffect = android.graphics.DashPathEffect(floatArrayOf(10f, 5f), 0f)
    }

    fun setTarget(x: Int, y: Int, fov: Int) {
        targetX = x
        targetY = y
        fovRadius = fov
        postInvalidate()
    }

    fun clearTarget() {
        targetX = -1
        targetY = -1
        postInvalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val cx = width / 2f
        val cy = height / 2f

        // Draw crosshair at screen center
        val crossSize = 15f
        canvas.drawLine(cx - crossSize, cy, cx + crossSize, cy, crosshairPaint)
        canvas.drawLine(cx, cy - crossSize, cx, cy + crossSize, crosshairPaint)
        canvas.drawCircle(cx, cy, 4f, crosshairPaint)

        // Draw FOV circle
        canvas.drawCircle(cx, cy, fovRadius.toFloat(), fovPaint)

        // Draw target marker and line
        if (targetX >= 0 && targetY >= 0) {
            val tx = targetX.toFloat()
            val ty = targetY.toFloat()

            // Line from center to target
            canvas.drawLine(cx, cy, tx, ty, linePaint)

            // Target circle
            canvas.drawCircle(tx, ty, 20f, targetFillPaint)
            canvas.drawCircle(tx, ty, 20f, targetPaint)

            // Target crosshair
            canvas.drawLine(tx - 12f, ty, tx + 12f, ty, targetPaint)
            canvas.drawLine(tx, ty - 12f, tx, ty + 12f, targetPaint)
        }
    }
}
