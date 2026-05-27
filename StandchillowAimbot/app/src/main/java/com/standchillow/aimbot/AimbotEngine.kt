package com.standchillow.aimbot

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Point
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

class AimbotEngine(private val prefs: AimbotPrefs) {

    data class Target(
        val centerX: Int,
        val centerY: Int,
        val distance: Double,
        val pixelCount: Int
    )

    data class AimResult(
        val target: Target?,
        val deltaX: Float,
        val deltaY: Float,
        val shouldShoot: Boolean
    )

    private var previousTargetX = -1f
    private var previousTargetY = -1f

    fun processFrame(bitmap: Bitmap): AimResult {
        val screenCenterX = bitmap.width / 2
        val screenCenterY = bitmap.height / 2
        val fov = prefs.fovRadius

        val targets = detectTargets(bitmap, screenCenterX, screenCenterY, fov)

        if (targets.isEmpty()) {
            previousTargetX = -1f
            previousTargetY = -1f
            return AimResult(null, 0f, 0f, false)
        }

        val best = targets.minByOrNull { it.distance } ?: return AimResult(null, 0f, 0f, false)

        var aimY = best.centerY
        if (prefs.headshotMode) {
            val estimatedBodyHeight = max(20, (best.pixelCount * 0.15).toInt())
            aimY = best.centerY - estimatedBodyHeight
        }

        var deltaX = (best.centerX - screenCenterX).toFloat()
        var deltaY = (aimY - screenCenterY).toFloat()

        deltaX *= prefs.sensitivity
        deltaY *= prefs.sensitivity

        if (prefs.smoothAim) {
            val factor = prefs.smoothFactor
            if (previousTargetX >= 0) {
                deltaX = previousTargetX + (deltaX - previousTargetX) * factor
                deltaY = previousTargetY + (deltaY - previousTargetY) * factor
            }
            previousTargetX = deltaX
            previousTargetY = deltaY
        }

        val shootDistance = hypot(deltaX.toDouble(), deltaY.toDouble())
        val shouldShoot = prefs.triggerBot && shootDistance < 30.0

        return AimResult(best, deltaX, deltaY, shouldShoot)
    }

    private fun detectTargets(
        bitmap: Bitmap,
        centerX: Int,
        centerY: Int,
        fov: Int
    ): List<Target> {
        val startX = max(0, centerX - fov)
        val endX = min(bitmap.width - 1, centerX + fov)
        val startY = max(0, centerY - fov)
        val endY = min(bitmap.height - 1, centerY + fov)

        val width = endX - startX + 1
        val height = endY - startY + 1
        if (width <= 0 || height <= 0) return emptyList()

        val pixels = IntArray(width * height)
        bitmap.getPixels(pixels, 0, width, startX, startY, width, height)

        val matchMask = BooleanArray(width * height)
        val step = 2

        for (y in 0 until height step step) {
            for (x in 0 until width step step) {
                val idx = y * width + x
                val pixel = pixels[idx]
                if (isTargetColor(pixel)) {
                    matchMask[idx] = true
                }
            }
        }

        return clusterTargets(matchMask, width, height, startX, startY, centerX, centerY, step)
    }

    private fun isTargetColor(pixel: Int): Boolean {
        val r = Color.red(pixel)
        val g = Color.green(pixel)
        val b = Color.blue(pixel)

        return when (prefs.targetColorMode) {
            AimbotPrefs.COLOR_RED -> {
                r > 180 && g < 80 && b < 80
            }
            AimbotPrefs.COLOR_GREEN -> {
                g > 180 && r < 80 && b < 80
            }
            AimbotPrefs.COLOR_YELLOW -> {
                r > 180 && g > 180 && b < 80
            }
            AimbotPrefs.COLOR_CUSTOM -> {
                val hsv = FloatArray(3)
                Color.colorToHSV(pixel, hsv)
                val hue = hsv[0]
                val sat = hsv[1]
                val value = hsv[2]
                val targetHue = prefs.customColorHue
                val range = prefs.customColorRange
                sat > 0.4f && value > 0.3f && abs(hue - targetHue) < range
            }
            else -> false
        }
    }

    private fun clusterTargets(
        mask: BooleanArray,
        width: Int,
        height: Int,
        offsetX: Int,
        offsetY: Int,
        screenCenterX: Int,
        screenCenterY: Int,
        step: Int
    ): List<Target> {
        val visited = BooleanArray(width * height)
        val targets = mutableListOf<Target>()
        val minClusterSize = 5

        for (y in 0 until height step step) {
            for (x in 0 until width step step) {
                val idx = y * width + x
                if (!mask[idx] || visited[idx]) continue

                var sumX = 0L
                var sumY = 0L
                var count = 0
                val queue = ArrayDeque<Int>()
                queue.add(idx)
                visited[idx] = true

                while (queue.isNotEmpty()) {
                    val ci = queue.removeFirst()
                    val cx = ci % width
                    val cy = ci / width
                    sumX += cx
                    sumY += cy
                    count++

                    for (dy in -step..step step step) {
                        for (dx in -step..step step step) {
                            if (dx == 0 && dy == 0) continue
                            val nx = cx + dx
                            val ny = cy + dy
                            if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue
                            val ni = ny * width + nx
                            if (ni < 0 || ni >= mask.size) continue
                            if (!mask[ni] || visited[ni]) continue
                            visited[ni] = true
                            queue.add(ni)
                        }
                    }
                }

                if (count >= minClusterSize) {
                    val avgX = (sumX / count).toInt() + offsetX
                    val avgY = (sumY / count).toInt() + offsetY
                    val dist = hypot(
                        (avgX - screenCenterX).toDouble(),
                        (avgY - screenCenterY).toDouble()
                    )
                    targets.add(Target(avgX, avgY, dist, count))
                }
            }
        }

        return targets
    }

    fun reset() {
        previousTargetX = -1f
        previousTargetY = -1f
    }
}
