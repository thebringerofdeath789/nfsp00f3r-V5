package com.nf_sp00f.app.data

import org.json.JSONObject

/**
 * Pure-JVM HCE emulation engine: given a saved card profile (JSON) and an incoming APDU
 * this engine produces the correct response bytes (data + SW). Keeping this logic
 * out of the Android HostApduService makes it unit-testable and easier to validate
 * in CI without requiring Android instrumentation.
 */
object HceEmulator {

    private val SW_OK = byteArrayOf(0x90.toByte(), 0x00.toByte())
    private val SW_FILE_NOT_FOUND = byteArrayOf(0x6A.toByte(), 0x82.toByte())
    private val SW_RECORD_NOT_FOUND = byteArrayOf(0x6A.toByte(), 0x83.toByte())
    private val SW_UNKNOWN = byteArrayOf(0x6F.toByte(), 0x00.toByte())

    fun handleApdu(profile: JSONObject?, apdu: ByteArray?): ByteArray {
        if (apdu == null || apdu.size < 4) return SW_UNKNOWN
        val ins = apdu[1].toInt() and 0xFF

        try {
            when (ins) {
                0xA4 -> { // SELECT by name
                    val p1 = apdu[2].toInt() and 0xFF
                    val p2 = apdu[3].toInt() and 0xFF
                    if (p1 == 0x04 && p2 == 0x00 && apdu.size >= 5) {
                        val lc = apdu[4].toInt() and 0xFF
                        if (apdu.size >= 5 + lc) {
                            val data = apdu.copyOfRange(5, 5 + lc)
                            val dataHex = EmvTlvParser.toHex(data)
                            val ppseHex = EmvTlvParser.toHex(EmvTlvParser.hexStringToBytes("325041592E5359532E4444463031"))
                            if (dataHex.equals(ppseHex, ignoreCase = true)) {
                                return buildPpseFci(profile) + SW_OK
                            } else {
                                val app = findApplicationByAid(profile, dataHex)
                                if (app != null) {
                                    val fciHex = app.optString("fci", "")
                                    if (fciHex.isNotEmpty()) {
                                        return EmvTlvParser.hexStringToBytes(fciHex) + SW_OK
                                    }
                                }
                                return SW_FILE_NOT_FOUND
                            }
                        }
                    }
                }
                0xA8, 0x80 -> { // GET PROCESSING OPTIONS (some terminals send CLA=0x80)
                    val app = pickPrimaryApplication(profile)
                    if (app != null) {
                        val aipHex = app.optString("aip", null)
                        val aflHex = app.optString("afl", null)
                        if (aipHex != null && aflHex != null) {
                            val aip = EmvTlvParser.hexStringToBytes(aipHex)
                            val afl = EmvTlvParser.hexStringToBytes(aflHex)
                            val out = aip + afl
                            return out + SW_OK
                        }
                    }
                    return SW_UNKNOWN
                }
                0xB2 -> { // READ RECORD
                    val recordNum = apdu[2].toInt() and 0xFF
                    val p2 = apdu[3].toInt() and 0xFF
                    val sfi = (p2 shr 3) and 0x1F
                    val app = pickPrimaryApplication(profile)
                    if (app != null) {
                        val records = app.optJSONArray("records")
                        if (records != null) {
                            for (i in 0 until records.length()) {
                                val rObj = records.getJSONObject(i)
                                if (rObj.optInt("sfi") == sfi && rObj.optInt("record") == recordNum) {
                                    val dataHex = rObj.optString("data", "")
                                    if (dataHex.isNotEmpty()) {
                                        return EmvTlvParser.hexStringToBytes(dataHex) + SW_OK
                                    }
                                }
                            }
                            return SW_RECORD_NOT_FOUND
                        }
                    }
                    return SW_UNKNOWN
                }
                else -> {
                    return SW_UNKNOWN
                }
            }
        } catch (e: Exception) {
            return SW_UNKNOWN
        }

        return SW_UNKNOWN
    }

    private fun findApplicationByAid(profile: JSONObject?, aidHex: String): JSONObject? {
        if (profile == null) return null
        val apps = profile.optJSONArray("applications") ?: return null
        for (i in 0 until apps.length()) {
            val a = apps.getJSONObject(i)
            if (a.optString("aid", "").equals(aidHex, ignoreCase = true)) return a
        }
        return null
    }

    private fun pickPrimaryApplication(profile: JSONObject?): JSONObject? {
        if (profile == null) return null
        val apps = profile.optJSONArray("applications") ?: return null
        if (apps.length() == 0) return null
        for (i in 0 until apps.length()) {
            val a = apps.getJSONObject(i)
            if (a.has("afl") && a.optJSONArray("records") != null && a.optJSONArray("records")!!.length() > 0) return a
        }
        return apps.getJSONObject(0)
    }

    private fun buildPpseFci(profile: JSONObject?): ByteArray {
        val entries = mutableListOf<Byte>()
        val apps = profile?.optJSONArray("applications")
        if (apps != null) {
            for (i in 0 until apps.length()) {
                val a = apps.getJSONObject(i)
                val aidHex = a.optString("aid", "")
                if (aidHex.isEmpty()) continue
                val aid = EmvTlvParser.hexStringToBytes(aidHex)
                val entry = mutableListOf<Byte>()
                entry.add(0x4F.toByte())
                entry.add(aid.size.toByte())
                entry.addAll(aid.toList())
                val label = a.optString("label", "")
                if (label.isNotEmpty()) {
                    val labelBytes = label.toByteArray(Charsets.UTF_8)
                    entry.add(0x50.toByte())
                    entry.add(labelBytes.size.toByte())
                    entry.addAll(labelBytes.toList())
                }
                val entryBytes = entry.toByteArray()
                val wrapped = mutableListOf<Byte>()
                wrapped.add(0x61.toByte())
                wrapped.add(entryBytes.size.toByte())
                wrapped.addAll(entryBytes.toList())
                entries.addAll(wrapped)
            }
        }
        val allEntries = entries.toByteArray()
        val a5Bytes = allEntries
        val fci = mutableListOf<Byte>()
        fci.add(0x6F.toByte())
        fci.add(a5Bytes.size.toByte())
        fci.addAll(a5Bytes.toList())
        return fci.toByteArray()
    }
}