package com.nf_sp00f.app.data

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(maxSdk = 34)
class HceEmulatorTest {

    private fun makeSampleProfile(): JSONObject {
        val profile = JSONObject()
        val apps = JSONArray()
        val app = JSONObject()
        app.put("aid", "A0000000031010")
        app.put("fci", "6F10840A A0000000031010".replace(" ", ""))
        app.put("label", "VISA DEBIT")
        app.put("aip", "0200")
        // AFL: one entry, SFI=1, start=1, end=1, offlineAuth=0
        val aflBytes = byteArrayOf(((1 shl 3) and 0xFF).toByte(), 0x01.toByte(), 0x01.toByte(), 0x00.toByte())
        app.put("afl", EmvTlvParser.toHex(aflBytes))
        val records = JSONArray()
        val r = JSONObject()
        r.put("sfi", 1)
        r.put("record", 1)
        // small TLV record: tag 70 with 2 bytes of data 5A01 01
        r.put("data", "70025A0101")
        records.put(r)
        app.put("records", records)
        apps.put(app)
        profile.put("applications", apps)
        return profile
    }

    @Test
    fun selectPpseReturnsPpseFciContainingAids() {
        val profile = makeSampleProfile()
        val ppseApdu = EmvTlvParser.hexStringToBytes("00A404000E325041592E5359532E4444463031")
        val resp = HceEmulator.handleApdu(profile, ppseApdu)
        val (data, sw) = ApduUtils.extractResponseData(resp)
        assertEquals(0x9000, sw)
        val hex = EmvTlvParser.toHex(data)
        assertTrue(hex.contains("A0000000031010"))
    }

    @Test
    fun selectAidReturnsStoredFci() {
        val profile = makeSampleProfile()
        val selectAid = EmvTlvParser.hexStringToBytes("00A4040007A0000000031010")
        val resp = HceEmulator.handleApdu(profile, selectAid)
        val (data, sw) = ApduUtils.extractResponseData(resp)
        assertEquals(0x9000, sw)
        assertEquals("6F10840AA0000000031010", EmvTlvParser.toHex(data).toUpperCase())
    }

    @Test
    fun gpoReturnsAipAndAfl() {
        val profile = makeSampleProfile()
        val gpo = ApduUtils.buildGpoApdu(null)
        val resp = HceEmulator.handleApdu(profile, gpo)
        val (data, sw) = ApduUtils.extractResponseData(resp)
        assertEquals(0x9000, sw)
        // Response should start with AIP (0200) then AFL bytes
        val hex = EmvTlvParser.toHex(data)
        assertTrue(hex.startsWith("0200"))
        assertTrue(hex.contains("08010100"))
    }

    @Test
    fun readRecordReturnsStoredRecordData() {
        val profile = makeSampleProfile()
        val readRec = ApduUtils.buildReadRecordApdu(1, 1)
        val resp = HceEmulator.handleApdu(profile, readRec)
        val (data, sw) = ApduUtils.extractResponseData(resp)
        assertEquals(0x9000, sw)
        assertEquals("70025A0101", EmvTlvParser.toHex(data).toUpperCase())
    }
}
