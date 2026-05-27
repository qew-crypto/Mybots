package com.standchillow.aimbot

import android.content.Context
import android.content.SharedPreferences

class AimbotPrefs(context: Context) {

    companion object {
        private const val PREFS_NAME = "aimbot_prefs"
        const val COLOR_RED = 0
        const val COLOR_GREEN = 1
        const val COLOR_YELLOW = 2
        const val COLOR_CUSTOM = 3
    }

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var sensitivity: Float
        get() = prefs.getFloat("sensitivity", 1.0f)
        set(value) = prefs.edit().putFloat("sensitivity", value).apply()

    var fovRadius: Int
        get() = prefs.getInt("fov_radius", 150)
        set(value) = prefs.edit().putInt("fov_radius", value).apply()

    var smoothAim: Boolean
        get() = prefs.getBoolean("smooth_aim", true)
        set(value) = prefs.edit().putBoolean("smooth_aim", value).apply()

    var smoothFactor: Float
        get() = prefs.getFloat("smooth_factor", 0.3f)
        set(value) = prefs.edit().putFloat("smooth_factor", value).apply()

    var headshotMode: Boolean
        get() = prefs.getBoolean("headshot_mode", false)
        set(value) = prefs.edit().putBoolean("headshot_mode", value).apply()

    var triggerBot: Boolean
        get() = prefs.getBoolean("trigger_bot", false)
        set(value) = prefs.edit().putBoolean("trigger_bot", value).apply()

    var targetColorMode: Int
        get() = prefs.getInt("target_color_mode", COLOR_RED)
        set(value) = prefs.edit().putInt("target_color_mode", value).apply()

    var customColorHue: Float
        get() = prefs.getFloat("custom_color_hue", 0f)
        set(value) = prefs.edit().putFloat("custom_color_hue", value).apply()

    var customColorRange: Float
        get() = prefs.getFloat("custom_color_range", 15f)
        set(value) = prefs.edit().putFloat("custom_color_range", value).apply()

    var aimEnabled: Boolean
        get() = prefs.getBoolean("aim_enabled", true)
        set(value) = prefs.edit().putBoolean("aim_enabled", value).apply()
}
