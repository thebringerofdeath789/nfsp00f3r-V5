package com.nf_sp00f.app.data

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

object CardProfileManager {
    private const val PROFILES_DIR = "card_profiles"
    private const val ACTIVE_PROFILE_FILE = "active_profile.json"
    private const val EXPORTS_DIR = "exports"

    // Simple change notifier for Compose screens to observe
    private val _updates = MutableStateFlow(0)
    val updates: StateFlow<Int> = _updates

    private fun profilesDir(context: Context): File {
        val dir = File(context.filesDir, PROFILES_DIR)
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    private fun exportsDir(context: Context): File {
        val dir = File(context.filesDir, EXPORTS_DIR)
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    fun listProfiles(context: Context): List<VirtualCard> {
        val list = mutableListOf<VirtualCard>()
        try {
            profilesDir(context).listFiles()?.forEach { f ->
                try {
                    val json = JSONObject(f.readText())
                    val cardholderName = json.optString("cardholder_name", "Unknown")
                    val pan = json.optString("pan", "****")
                    val expiry = json.optString("expiry_date", "")
                    val apduCount = json.optJSONArray("apdu_log")?.length() ?: 0
                    val cardType = json.optString("card_type", "Unknown")
                    val id = f.nameWithoutExtension
                    list.add(VirtualCard(cardholderName, pan, expiry, apduCount, cardType, id))
                } catch (_: Exception) {
                }
            }
        } catch (_: Exception) {
        }
        return list.sortedByDescending { it.apduCount }
    }

    /**
     * Save a profile JSON to disk. If profileId is null a new UUID will be assigned.
     * Returns the profile id (filename without extension)
     */
    fun saveProfile(context: Context, profileJson: JSONObject, profileId: String? = null): String {
        val dir = profilesDir(context)
        val id = profileId ?: profileJson.optString("card_id", UUID.randomUUID().toString())
        try {
            profileJson.put("card_id", id)
            val out = File(dir, "$id.json")
            out.writeText(profileJson.toString(2))
            _updates.value = _updates.value + 1
            return id
        } catch (ex: Exception) {
            throw ex
        }
    }

    fun readProfile(context: Context, profileId: String): JSONObject? {
        val f = File(profilesDir(context), "$profileId.json")
        return try {
            if (!f.exists()) return null
            JSONObject(f.readText())
        } catch (e: Exception) {
            null
        }
    }

    fun deleteProfile(context: Context, profileId: String): Boolean {
        val f = File(profilesDir(context), "$profileId.json")
        val ok = try { f.delete() } catch (_: Exception) { false }
        if (ok) _updates.value = _updates.value + 1
        return ok
    }

    fun exportProfile(context: Context, profileId: String): File? {
        val profile = readProfile(context, profileId) ?: return null
        val outDir = exportsDir(context)
        val outFile = File(outDir, "$profileId-export.json")
        return try {
            outFile.writeText(profile.toString(2))
            outFile
        } catch (e: Exception) {
            null
        }
    }

    fun setActiveProfile(context: Context, profileId: String?): Boolean {
        try {
            val target = File(context.filesDir, ACTIVE_PROFILE_FILE)
            if (profileId == null) {
                if (target.exists()) target.delete()
            } else {
                val profile = readProfile(context, profileId) ?: return false
                target.writeText(profile.toString(2))
            }
            _updates.value = _updates.value + 1
            return true
        } catch (e: Exception) {
            return false
        }
    }

    fun getActiveProfile(context: Context): JSONObject? {
        val target = File(context.filesDir, ACTIVE_PROFILE_FILE)
        return try {
            if (!target.exists()) return null
            JSONObject(target.readText())
        } catch (e: Exception) {
            null
        }
    }
}
