package com.nf_sp00f.app.data

import java.util.Locale

/**
 * APDU helpers extracted to a small, testable utility so parsing and
 * APDU construction can be unit tested on the JVM without Android
 * instrumentation/device access.
 */
object ApduUtils {

    /** Build a SELECT AID APDU: CLA INS P1 P2 LC DATA */
    fun buildSelectApdu(aid: ByteArray): ByteArray {
        val header = byteArrayOf(0x00.toByte(), 0xA4.toByte(), 0x04.toByte(), 0x00.toByte())
        val lc = byteArrayOf(aid.size.toByte())
        return header + lc + aid
    }

    /**
     * Extract data and status word from a response APDU (data + SW1 SW2).
     * Returns Pair(data, statusWordAsInt)
     */
    fun extractResponseData(resp: ByteArray?): Pair<ByteArray, Int> {
        if (resp == null || resp.size < 2) return Pair(ByteArray(0), 0)
        val sw1 = resp[resp.size - 2].toInt() and 0xFF
        val sw2 = resp[resp.size - 1].toInt() and 0xFF
        val data = resp.copyOf(resp.size - 2)
        val sw = (sw1 shl 8) or sw2
        return Pair(data, sw)
    }

    // Build a READ RECORD APDU: CLA INS P1 P2 LE
    fun buildReadRecordApdu(record: Int, sfi: Int): ByteArray {
        val p1 = record.toByte()
        val p2 = (((sfi and 0x1F) shl 3) or 0x04).toByte()
        return byteArrayOf(0x00.toByte(), 0xB2.toByte(), p1, p2, 0x00.toByte())
    }

    /**
     * Build a GPO (GET PROCESSING OPTIONS) APDU from a PDOL value (raw PDOL value bytes).
     * If pdolData is null or empty, the PDOL Data Object (tag 0x83) will be encoded with length 0.
     */
    fun buildGpoApdu(pdolData: ByteArray?): ByteArray {
        val pdolEncoded = if (pdolData == null || pdolData.isEmpty()) {
            byteArrayOf(0x83.toByte(), 0x00.toByte())
        } else {
            byteArrayOf(0x83.toByte(), pdolData.size.toByte()) + pdolData
        }
        val header = byteArrayOf(0x80.toByte(), 0xA8.toByte(), 0x00.toByte(), 0x00.toByte(), pdolEncoded.size.toByte())
        return header + pdolEncoded
    }

    /**
     * Build default PDOL data for a PDOL definition (the value of tag 9F38 returned in SELECT AID FCI).
     * The PDOL definition is a sequence of tag-length pairs (tags may be multi-byte). For each entry
     * this method will attempt to provide a sensible default value (zeros for unknown tags).
     */
    fun buildDefaultPdol(pdolDefinition: ByteArray?): ByteArray {
        if (pdolDefinition == null || pdolDefinition.isEmpty()) return ByteArray(0)
        val out = mutableListOf<Byte>()
        var idx = 0
        while (idx < pdolDefinition.size) {
            // parse tag (1 or more bytes)
            var tagBytes = mutableListOf<Byte>()
            var b = pdolDefinition[idx++]
            tagBytes.add(b)
            if ((b.toInt() and 0x1F) == 0x1F) {
                while (idx < pdolDefinition.size) {
                    b = pdolDefinition[idx++] 
                    tagBytes.add(b)
                    if ((b.toInt() and 0x80) == 0) break
                }
            }
            if (idx >= pdolDefinition.size) break
            val length = pdolDefinition[idx++].toInt() and 0xFF
            // Provide sensible defaults for commonly-used PDOL tags
            val tagHex = tagBytes.joinToString("") { String.format(Locale.US, "%02X", it) }
            val defaultBytes = when (tagHex) {
                "9F02" -> ByteArray(length) // amount, default 0
                "9F03" -> ByteArray(length) // other amount, default 0
                "9F1A" -> byteArrayOf(0x08, 0x40).copyOf(length) // Terminal Country Code 0840
                "95" -> ByteArray(length) // TVR placeholder
                "9A" -> ByteArray(length) // Transaction date
                "9C" -> ByteArray(length) // Transaction type
                "5F2A" -> byteArrayOf(0x08, 0x40).copyOf(length) // Currency code default
                else -> ByteArray(length)
            }
            out.addAll(defaultBytes.toList())
        }
        return out.toByteArray()
    }

    data class AflEntry(val sfi: Int, val startRecord: Int, val endRecord: Int, val offlineAuthRecords: Int)

    /**
     * Parse raw AFL bytes into a list of AflEntry objects. AFL is a multiple of 4 bytes where
     * each 4-byte entry is: [SFI_byte, startRec, endRec, offlineAuthRecords]. The SFI value is
     * encoded in the top 5 bits of the first byte (>> 3).
     */
    fun parseAfl(afl: ByteArray?): List<AflEntry> {
        val out = mutableListOf<AflEntry>()
        if (afl == null || afl.isEmpty()) return out
        var i = 0
        while (i + 3 < afl.size) {
            val sfi = ((afl[i].toInt() and 0xFF) shr 3) and 0x1F
            val start = afl[i + 1].toInt() and 0xFF
            val end = afl[i + 2].toInt() and 0xFF
            val off = afl[i + 3].toInt() and 0xFF
            out.add(AflEntry(sfi, start, end, off))
            i += 4
        }
        return out
    }
}
