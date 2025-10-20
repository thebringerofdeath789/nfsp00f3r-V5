package com.nf_sp00f.app.data

import java.util.Locale

/**
 * Lightweight BER-TLV parser used by Android UI code.
 * Parses primitive and constructed TLV and returns a map of tag -> list of values
 * (many EMV responses contain repeated tags).
 *
 * This central implementation avoids duplicating parsing logic across UI screens
 * and is intentionally small and robust for the Compose UI to consume.
 */
object EmvTlvParser {

    fun parseAll(data: ByteArray): Map<String, List<ByteArray>> {
        val out = mutableMapOf<String, MutableList<ByteArray>>()

        fun add(tag: String, value: ByteArray) {
            val list = out.getOrPut(tag) { mutableListOf() }
            list.add(value)
        }

        fun parseRecursive(buffer: ByteArray, start: Int, end: Int) {
            var idx = start
            while (idx < end) {
                // Tag
                if (idx >= end) break
                val tagBytes = mutableListOf<Byte>()
                var b = buffer[idx++]
                tagBytes.add(b)
                if ((b.toInt() and 0x1F) == 0x1F) {
                    while (idx < end) {
                        b = buffer[idx++]
                        tagBytes.add(b)
                        if ((b.toInt() and 0x80) == 0) break
                    }
                }
                val tagHex = tagBytes.joinToString("") { String.format(Locale.US, "%02X", it) }

                if (idx >= end) break
                // Length
                var lenByte = buffer[idx++].toInt() and 0xFF
                var length = 0
                if ((lenByte and 0x80) != 0) {
                    val num = lenByte and 0x7F
                    var l = 0
                    for (k in 0 until num) {
                        if (idx >= end) break
                        l = (l shl 8) + (buffer[idx++].toInt() and 0xFF)
                    }
                    length = l
                } else {
                    length = lenByte
                }

                if (idx + length > end) length = (end - idx).coerceAtLeast(0)
                val value = buffer.copyOfRange(idx, idx + length)
                add(tagHex, value)

                // If constructed (bit 6 set), parse nested TLV
                val constructed = (tagBytes.firstOrNull()?.toInt() ?: 0) and 0x20 != 0
                if (constructed && value.isNotEmpty()) {
                    parseRecursive(value, 0, value.size)
                }

                idx += length
            }
        }

        if (data.isNotEmpty()) parseRecursive(data, 0, data.size)
        return out
    }

    fun toHex(bytes: ByteArray?): String {
        if (bytes == null) return ""
        return bytes.joinToString("") { String.format(Locale.US, "%02X", it) }
    }

    fun hexStringToBytes(hex: String): ByteArray {
        val clean = hex.replace("[^0-9A-Fa-f]".toRegex(), "")
        val len = clean.length
        val result = ByteArray(len / 2)
        var i = 0
        while (i < len) {
            result[i / 2] = ((Character.digit(clean[i], 16) shl 4) + Character.digit(clean[i + 1], 16)).toByte()
            i += 2
        }
        return result
    }
}
