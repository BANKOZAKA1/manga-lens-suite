package com.gameocr.app.ui

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrDebugImageRemovalContractTest {
    @Test
    fun runtimeSources_doNotCreateOrAttachOcrDebugImages_tableDriven() {
        data class Case(
            val path: String,
            val forbiddenMarkers: List<String>,
        )

        listOf(
            Case(
                "src/main/java/com/gameocr/app/service/CaptureService.kt",
                listOf("dumpCaptureFrameForDebug(", "dump.artifacts", "imagePath = artifact"),
            ),
            Case(
                "src/main/java/com/gameocr/app/ocr/MangaOcrEngine.kt",
                listOf("imagePath = artifact", "log_msg_manga_mask_debug_saved_format"),
            ),
            Case(
                "src/main/java/com/gameocr/app/ocr/PaddleOcrEngine.kt",
                listOf("imagePath = artifact", "log_msg_manga_mask_debug_saved_format"),
            ),
            Case(
                "src/main/java/com/gameocr/app/ocr/MangaDelayedMaskDebugSession.kt",
                listOf(
                    "CompressFormat.PNG",
                    "outputDirectory",
                    "saveDebugArtifacts",
                    "MangaMaskDebugArtifact",
                ),
            ),
        ).forEach { case ->
            val source = moduleFile(case.path).readText()
            case.forbiddenMarkers.forEach { marker ->
                assertFalse("${case.path}: still contains $marker", source.contains(marker))
            }
        }

        assertFalse(
            "capture-frame debug writer must be removed",
            moduleFileOrNull(
                "src/main/java/com/gameocr/app/service/CaptureFrameDebugDump.kt"
            )?.exists() == true,
        )

        val settingsScreen = moduleFile(
            "src/main/java/com/gameocr/app/ui/SettingsScreen.kt"
        ).readText()
        assertFalse(
            "removed debug image writer must not remain user-configurable",
            settingsScreen.contains("settings_ocr_screenshot_saving_label"),
        )

        val policy = moduleFile(
            "src/main/java/com/gameocr/app/ocr/MangaMaskDebugDump.kt"
        ).readText()
        assertTrue(policy.contains("val saveDebugArtifacts = false"))
    }

    private fun moduleFile(path: String): File =
        moduleFileOrNull(path)?.takeIf(File::isFile)
            ?: error("Module file not found: $path")

    private fun moduleFileOrNull(path: String): File? =
        listOf(File(path), File("app", path)).firstOrNull { it.exists() }
}
