package com.standchillow.aimbot

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.accessibility.AccessibilityManager
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.standchillow.aimbot.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val prefs by lazy { AimbotPrefs(this) }

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        updatePermissionStatus()
    }

    private val projectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            ScreenCaptureService.resultCode = result.resultCode
            ScreenCaptureService.resultData = result.data
            startCaptureService()
        } else {
            Toast.makeText(this, "Захват экрана отклонён", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setupUI()
    }

    override fun onResume() {
        super.onResume()
        updatePermissionStatus()
    }

    private fun setupUI() {
        binding.btnGrantOverlay.setOnClickListener {
            if (!Settings.canDrawOverlays(this)) {
                val intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")
                )
                overlayPermissionLauncher.launch(intent)
            }
        }

        binding.btnGrantAccessibility.setOnClickListener {
            if (!isAccessibilityEnabled()) {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
        }

        binding.sliderSensitivity.addOnChangeListener { _, value, _ ->
            prefs.sensitivity = value
            binding.tvSensitivityValue.text = String.format("%.1f", value)
        }

        binding.sliderFov.addOnChangeListener { _, value, _ ->
            prefs.fovRadius = value.toInt()
            binding.tvFovValue.text = "${value.toInt()}px"
        }

        binding.switchSmoothing.setOnCheckedChangeListener { _, checked ->
            prefs.smoothAim = checked
        }

        binding.sliderSmoothFactor.addOnChangeListener { _, value, _ ->
            prefs.smoothFactor = value
            binding.tvSmoothValue.text = String.format("%.2f", value)
        }

        binding.switchHeadshot.setOnCheckedChangeListener { _, checked ->
            prefs.headshotMode = checked
        }

        binding.switchTriggerbot.setOnCheckedChangeListener { _, checked ->
            prefs.triggerBot = checked
        }

        // Color target buttons
        binding.btnColorRed.setOnClickListener {
            prefs.targetColorMode = AimbotPrefs.COLOR_RED
            updateColorSelection()
        }
        binding.btnColorGreen.setOnClickListener {
            prefs.targetColorMode = AimbotPrefs.COLOR_GREEN
            updateColorSelection()
        }
        binding.btnColorYellow.setOnClickListener {
            prefs.targetColorMode = AimbotPrefs.COLOR_YELLOW
            updateColorSelection()
        }
        binding.btnColorCustom.setOnClickListener {
            prefs.targetColorMode = AimbotPrefs.COLOR_CUSTOM
            updateColorSelection()
        }

        binding.btnStart.setOnClickListener {
            if (!Settings.canDrawOverlays(this)) {
                Toast.makeText(this, "Нужно разрешение на оверлей", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            requestScreenCapture()
        }

        binding.btnStop.setOnClickListener {
            stopAimbot()
        }

        loadSettings()
    }

    private fun loadSettings() {
        binding.sliderSensitivity.value = prefs.sensitivity
        binding.tvSensitivityValue.text = String.format("%.1f", prefs.sensitivity)
        binding.sliderFov.value = prefs.fovRadius.toFloat()
        binding.tvFovValue.text = "${prefs.fovRadius}px"
        binding.switchSmoothing.isChecked = prefs.smoothAim
        binding.sliderSmoothFactor.value = prefs.smoothFactor
        binding.tvSmoothValue.text = String.format("%.2f", prefs.smoothFactor)
        binding.switchHeadshot.isChecked = prefs.headshotMode
        binding.switchTriggerbot.isChecked = prefs.triggerBot
        updateColorSelection()
    }

    private fun updateColorSelection() {
        val mode = prefs.targetColorMode
        binding.btnColorRed.alpha = if (mode == AimbotPrefs.COLOR_RED) 1f else 0.4f
        binding.btnColorGreen.alpha = if (mode == AimbotPrefs.COLOR_GREEN) 1f else 0.4f
        binding.btnColorYellow.alpha = if (mode == AimbotPrefs.COLOR_YELLOW) 1f else 0.4f
        binding.btnColorCustom.alpha = if (mode == AimbotPrefs.COLOR_CUSTOM) 1f else 0.4f
    }

    private fun updatePermissionStatus() {
        val overlayOk = Settings.canDrawOverlays(this)
        val accessOk = isAccessibilityEnabled()
        binding.tvOverlayStatus.text = if (overlayOk) "✓ Разрешено" else "✗ Не разрешено"
        binding.tvAccessibilityStatus.text = if (accessOk) "✓ Включено" else "✗ Не включено"
        binding.tvOverlayStatus.setTextColor(
            getColor(if (overlayOk) android.R.color.holo_green_dark else android.R.color.holo_red_dark)
        )
        binding.tvAccessibilityStatus.setTextColor(
            getColor(if (accessOk) android.R.color.holo_green_dark else android.R.color.holo_red_dark)
        )
        binding.btnStart.isEnabled = overlayOk
    }

    private fun isAccessibilityEnabled(): Boolean {
        val am = getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
        val enabled = am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
        return enabled.any {
            it.resolveInfo.serviceInfo.packageName == packageName &&
                it.resolveInfo.serviceInfo.name == AimAccessibilityService::class.java.name
        }
    }

    private fun requestScreenCapture() {
        val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        projectionLauncher.launch(mpm.createScreenCaptureIntent())
    }

    private fun startCaptureService() {
        val intent = Intent(this, ScreenCaptureService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }

        val overlayIntent = Intent(this, OverlayService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(overlayIntent)
        } else {
            startService(overlayIntent)
        }

        Toast.makeText(this, "Аимбот запущен!", Toast.LENGTH_SHORT).show()
    }

    private fun stopAimbot() {
        stopService(Intent(this, ScreenCaptureService::class.java))
        stopService(Intent(this, OverlayService::class.java))
        Toast.makeText(this, "Аимбот остановлен", Toast.LENGTH_SHORT).show()
    }
}
