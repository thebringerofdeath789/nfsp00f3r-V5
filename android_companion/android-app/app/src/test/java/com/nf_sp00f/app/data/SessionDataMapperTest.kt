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
class SessionDataMapperTest {
    @Test
    fun mapSessionToProfile_handles_exported_format() {
        val session = JSONObject()
        val card = JSONObject()
        card.put("pan", "4111111111111111")
        card.put("expiry", "2512")
        card.put("cardholder_name", "TEST CARD")
        session.put("card_data", card)

        val apdu = JSONArray()
        val apduEntry = JSONObject()
        apduEntry.put("timestamp", "2025-10-18T00:00:00")
        apduEntry.put("command", "00A40400")
        apduEntry.put("response", "9000")
        apdu.put(apduEntry)
        session.put("apdu_trace", apdu)

        val profile = SessionDataMapper.mapSessionToProfile(session)

        assertEquals("4111111111111111", profile.optString("pan"))
        assertEquals("2512", profile.optString("expiry_date"))
        assertEquals("TEST CARD", profile.optString("cardholder_name"))

        val apduLog = profile.optJSONArray("apdu_log")
        assertNotNull(apduLog)
        assertTrue(apduLog!!.length() >= 1)
    }
}
