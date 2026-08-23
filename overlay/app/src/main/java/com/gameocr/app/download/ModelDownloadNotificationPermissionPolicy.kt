package com.gameocr.app.download

import android.os.Build

internal fun shouldRequestModelDownloadNotificationPermission(
    sdkInt: Int,
    permissionGranted: Boolean,
): Boolean = sdkInt >= Build.VERSION_CODES.TIRAMISU && !permissionGranted
