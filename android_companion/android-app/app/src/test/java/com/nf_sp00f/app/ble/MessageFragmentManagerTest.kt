package com.nf_sp00f.app.ble

import org.junit.Assert.*
import org.junit.Test

class MessageFragmentManagerTest {

    @Test
    fun testReassemblyOutOfOrder() {
        val manager = MessageFragmentManager(mtu = 20)

        val payload = ByteArray(123) { i -> (i % 256).toByte() }
        val seq = manager.nextSequenceId()

        val fragments = manager.fragmentMessage(BLEMessageType.SESSION_DATA, payload, sequenceId = seq)

        // Simulate out-of-order arrival
        val shuffled = fragments.shuffled()

        var result: Pair<BLEMessageType, ByteArray>? = null
        for (frag in shuffled) {
            val r = manager.onReceiveFragment(frag)
            if (r != null) result = r
        }

        assertNotNull("Message should reassemble", result)
        assertEquals(BLEMessageType.SESSION_DATA, result!!.first)
        assertArrayEquals(payload, result.second)
    }

    @Test
    fun testFragmentationCountAndPayloadIntegrity() {
        val manager = MessageFragmentManager(mtu = 20)
        val payload = ("hello-world".repeat(15)).toByteArray() // 150 bytes
        val seq = manager.nextSequenceId()

        val fragments = manager.fragmentMessage(BLEMessageType.SESSION_DATA, payload, sequenceId = seq)
        val expected = (payload.size + 20 - 1) / 20
        assertEquals(expected, fragments.size)

        // Reconstruct by parsing the wire-format fragments
        val reconstructed = fragments.map { manager.parseFragment(it).payload }.fold(ByteArray(0)) { acc, bytes -> acc + bytes }
        assertArrayEquals(payload, reconstructed)
    }
}
