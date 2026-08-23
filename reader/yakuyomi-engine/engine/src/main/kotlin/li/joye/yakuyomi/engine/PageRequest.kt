package li.joye.yakuyomi.engine

import android.graphics.Bitmap

/** Stable page-level request shared by Reader, Overlay adapters and LAN HQ clients. */
data class PageRequest(
    val image: Bitmap,
    val sourceLanguage: String = "auto",
    val targetLanguage: String = "THA",
    val qualityProfile: QualityProfile = QualityProfile.BALANCED,
    val readingOrder: ReadingOrder = ReadingOrder.RIGHT_TO_LEFT,
    val glossaryVersion: String = "default",
    val selectedSfx: Set<String> = emptySet(),
)

enum class QualityProfile { BALANCED, HQ }

enum class ReadingOrder { RIGHT_TO_LEFT, LEFT_TO_RIGHT, VERTICAL }

