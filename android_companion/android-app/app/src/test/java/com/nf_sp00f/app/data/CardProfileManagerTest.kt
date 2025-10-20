package com.nf_sp00f.app.data

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.File

@RunWith(RobolectricTestRunner::class)
@Config(maxSdk = 34)
class CardProfileManagerTest {

    @Test
    fun saveListReadExportSetActiveAndDeleteProfile() {
        val context = ApplicationProvider.getApplicationContext<Context>()

        // Ensure a clean start
        val profilesDir = File(context.filesDir, "card_profiles")
        if (profilesDir.exists()) profilesDir.deleteRecursively()
        val exportsDir = File(context.filesDir, "exports")
        if (exportsDir.exists()) exportsDir.deleteRecursively()

        // Build a sample profile JSON
        val profile = JSONObject()
        profile.put("cardholder_name", "Unit Test User")
        profile.put("pan", "4111111111111111")
        profile.put("expiry_date", "2512")

        // Save profile
        val id = CardProfileManager.saveProfile(context, profile)
        assertNotNull("Saved profile ID should not be null", id)

        // List profiles
        val listed = CardProfileManager.listProfiles(context)
        assertTrue("Listed profiles should contain the saved profile", listed.any { it.profileId == id })

        // Read profile
        val read = CardProfileManager.readProfile(context, id)
        assertNotNull("Read profile should not be null", read)
        assertEquals("PAN should match", "4111111111111111", read!!.optString("pan"))

        // Export profile
        val exported = CardProfileManager.exportProfile(context, id)
        assertNotNull("Exported file should not be null", exported)
        assertTrue("Exported file should exist", exported!!.exists())
        val exportedContent = exported.readText()
        assertTrue("Exported content should contain PAN", exportedContent.contains("4111111111111111"))

        // Set active profile
        val okActive = CardProfileManager.setActiveProfile(context, id)
        assertTrue("Setting active profile should succeed", okActive)
        val active = CardProfileManager.getActiveProfile(context)
        assertNotNull("Active profile should be present", active)
        assertEquals("Active profile must have matching card_id", id, active!!.optString("card_id"))

        // Delete profile
        val deleted = CardProfileManager.deleteProfile(context, id)
        assertTrue("Profile deletion should return true", deleted)
        val shouldBeNull = CardProfileManager.readProfile(context, id)
        assertNull("Profile should not be readable after deletion", shouldBeNull)

        // Clear active profile
        val cleared = CardProfileManager.setActiveProfile(context, null)
        assertTrue("Clearing active profile should succeed", cleared)
        val activeAfterClear = CardProfileManager.getActiveProfile(context)
        assertNull("No active profile should be present after clear", activeAfterClear)
    }
}
