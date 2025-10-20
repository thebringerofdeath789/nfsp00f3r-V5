package com.nf_sp00f.app.data

import org.junit.Assert.*
import org.junit.Test

class ApduUtilsTest {

    @Test
    fun buildSelectApduCreatesCorrectHeaderAndLc() {
        val aid = EmvTlvParser.hexStringToBytes("A0000000031010")
        val apdu = ApduUtils.buildSelectApdu(aid)
        // header 00 A4 04 00 + lc
        assertEquals(4 + 1 + aid.size, apdu.size)
        assertEquals(0x00.toByte(), apdu[0])
        assertEquals(0xA4.toByte(), apdu[1])
        assertEquals(0x04.toByte(), apdu[2])
        assertEquals(0x00.toByte(), apdu[3])
        val lc = apdu[4].toInt() and 0xFF
        assertEquals(aid.size, lc)
        val aidFromApdu = apdu.copyOfRange(5, 5 + lc)
        assertArrayEquals(aid, aidFromApdu)
    }

    @Test
    fun extractResponseDataParsesSwAndData() {
        val data = EmvTlvParser.hexStringToBytes("5A084215415401234567")
        val response = data + byteArrayOf(0x90.toByte(), 0x00.toByte())
        val (d, sw) = ApduUtils.extractResponseData(response)
        assertArrayEquals(data, d)
        assertEquals(0x9000, sw)
    }

    @Test
    fun buildReadRecordApduEncodesSfiAndRecordCorrectly() {
        val apdu = ApduUtils.buildReadRecordApdu(1, 1)
        // 00 B2 01 P2 00 where P2 = (SFI << 3) | 4
        assertEquals(5, apdu.size)
        assertEquals(0x00.toByte(), apdu[0])
        assertEquals(0xB2.toByte(), apdu[1])
        assertEquals(0x01.toByte(), apdu[2])
        assertEquals(((1 shl 3) or 4).toByte(), apdu[3])
    }

    @Test
    fun buildGpoApduWithNoPdolCreates83_00() {
        val apdu = ApduUtils.buildGpoApdu(null)
        // Expect header 80 A8 00 00 02 83 00
        assertTrue(apdu.size >= 7)
        assertEquals(0x80.toByte(), apdu[0])
        assertEquals(0xA8.toByte(), apdu[1])
        assertEquals(0x00.toByte(), apdu[2])
        assertEquals(0x00.toByte(), apdu[3])
        assertEquals(0x02.toByte(), apdu[4])
        assertEquals(0x83.toByte(), apdu[5])
        assertEquals(0x00.toByte(), apdu[6])
    }

    @Test
    fun buildDefaultPdolProducesExpectedLengthAndDefaults() {
        val pdolDef = EmvTlvParser.hexStringToBytes("9F02069F0306") // two entries: 9F02 len6, 9F03 len6
        val pdol = ApduUtils.buildDefaultPdol(pdolDef)
        assertEquals(12, pdol.size)
        // All default bytes should be zero for these tags
        for (b in pdol) assertEquals(0.toByte(), b)
    }

    @Test
    fun parseAflParsesSimpleAfl() {
        // SFI=1 start=1 end=1 offlineAuth=0 encoded as [SFI<<3, start, end, offline]
        val afl = byteArrayOf(((1 shl 3) and 0xFF).toByte(), 0x01.toByte(), 0x01.toByte(), 0x00.toByte())
        val entries = ApduUtils.parseAfl(afl)
        assertEquals(1, entries.size)
        assertEquals(1, entries[0].sfi)
        assertEquals(1, entries[0].startRecord)
        assertEquals(1, entries[0].endRecord)
    }
}
