package com.nf_sp00f.app.data

import org.junit.Assert.*
import org.junit.Test

class EmvTlvParserTest {

    @Test
    fun parseNestedTlv() {
        val aid = EmvTlvParser.hexStringToBytes("A0000000031010")
        val aidTlv = byteArrayOf(0x84.toByte(), aid.size.toByte()) + aid
        val label = "VISA".toByteArray(Charsets.UTF_8)
        val labelTlv = byteArrayOf(0x50.toByte(), label.size.toByte()) + label
        val fciValue = aidTlv + labelTlv
        val fci = byteArrayOf(0x6F.toByte(), fciValue.size.toByte()) + fciValue

        val parsed = EmvTlvParser.parseAll(fci)
        assertTrue(parsed.containsKey("84"))
        assertTrue(parsed.containsKey("50"))
        assertArrayEquals(aid, parsed["84"]?.first())
        assertEquals("VISA", String(parsed["50"]?.first() ?: ByteArray(0), Charsets.UTF_8))
    }

    @Test
    fun hexRoundTrip() {
        val hex = "A0000000031010"
        val bytes = EmvTlvParser.hexStringToBytes(hex)
        val round = EmvTlvParser.toHex(bytes)
        assertEquals(hex, round)
    }
}
