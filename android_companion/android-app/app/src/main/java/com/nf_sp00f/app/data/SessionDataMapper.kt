package com.nf_sp00f.app.data

import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale

/**
 * SessionDataMapper
 *
 * Utility to convert the SessionExporter / SESSION_DATA JSON shape (which
 * typically nests card fields under "card_data") into the flat profile
 * JSON structure expected by CardProfileManager.saveProfile(). This keeps
 * desktop -> android exports interoperable without changing either side's
 * canonical JSON format.
 */
object SessionDataMapper {
    fun mapSessionToProfile(sessionJson: JSONObject): JSONObject {
        val profile = JSONObject()

        // Card data may be nested under "card_data" or provided at top-level.
        val cardData = if (sessionJson.has("card_data") && sessionJson.get("card_data") is JSONObject)
            sessionJson.getJSONObject("card_data")
        else
            sessionJson

        // PAN
        if (cardData.has("pan")) profile.put("pan", cardData.optString("pan"))

        // Expiry may be called "expiry" or "expiry_date"; normalize to expiry_date.
        if (cardData.has("expiry")) profile.put("expiry_date", cardData.optString("expiry"))
        else if (cardData.has("expiry_date")) profile.put("expiry_date", cardData.optString("expiry_date"))

        // Cardholder name
        if (cardData.has("cardholder_name")) profile.put("cardholder_name", cardData.optString("cardholder_name"))

        // Carry over common FCI/AFL structures to maintain parity for imports
        if (cardData.has("fci")) profile.put("fci_data", cardData.get("fci"))
        if (cardData.has("afl")) profile.put("afl_data", cardData.get("afl"))

        // Convert APDU trace into a simple apdu_log array compatible with UI lists
        val apduArr = JSONArray()
        if (sessionJson.has("apdu_trace") && sessionJson.get("apdu_trace") is JSONArray) {
            val traces = sessionJson.getJSONArray("apdu_trace")
            for (i in 0 until traces.length()) {
                val entry = traces.opt(i)
                if (entry is JSONObject) {
                    val ts = entry.optString("timestamp", "")
                    val cmd = entry.optString("command", "")
                    val resp = entry.optString("response", entry.optString("sw", ""))
                    val short = if (ts.isNotEmpty()) "$ts: CMD=$cmd RESP=$resp" else "CMD=$cmd RESP=$resp"
                    apduArr.put(short)
                } else {
                    apduArr.put(entry.toString())
                }
            }
        }
        profile.put("apdu_log", apduArr)

        // Simple card type heuristics (best-effort)
        val pan = profile.optString("pan", "")
        profile.put("card_type", if (pan.startsWith("4")) "VISA" else "GENERIC")

        // If the session contains additional security info, copy it verbatim
        if (sessionJson.has("security_data") && sessionJson.get("security_data") is JSONObject) {
            profile.put("security_data", sessionJson.getJSONObject("security_data"))
        }

        return profile
    }
}
