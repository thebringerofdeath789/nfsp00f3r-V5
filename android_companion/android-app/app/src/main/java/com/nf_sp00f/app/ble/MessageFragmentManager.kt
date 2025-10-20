package com.nf_sp00f.app.ble

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Cross-platform BLE message framing used by the desktop (python) and Android
 * companion app. Format mirrors bluetooth_manager_ble.BLEMessage in the
 * Python codebase so messages are byte-for-byte compatible.
 *
 * Wire format (little-endian):
 *  - uint16_t payload_len
 *  - uint8_t message_type
 *  - uint8_t sequence_id
 *  - uint16_t total_fragments
 *  - uint16_t fragment_index
 *  - payload (payload_len bytes)
 */
enum class BLEMessageType(val code: Int) {
    HELLO(0x01),
    SESSION_DATA(0x02),
    APDU_TRACE(0x03),
    CARD_DATA(0x04),
    TRANSACTION_DATA(0x05),
    ACK(0x06),
    ERROR(0x07);

    companion object {
        fun fromCode(c: Int): BLEMessageType? = values().find { it.code == c }
    }
}

data class BLEMessage(
    val messageType: BLEMessageType,
    val sequenceId: Int,
    val totalFragments: Int,
    val fragmentIndex: Int,
    val payload: ByteArray
) {
    fun toBytes(): ByteArray {
        val payloadLen = payload.size
        // 2 (payload len) + 1 +1 +2 +2 header + payload
        val buf = ByteBuffer.allocate(2 + 1 + 1 + 2 + 2 + payloadLen)
        buf.order(ByteOrder.LITTLE_ENDIAN)
        buf.putShort(payloadLen.toShort())
        buf.put(messageType.code.toByte())
        buf.put(sequenceId.toByte())
        buf.putShort(totalFragments.toShort())
        buf.putShort(fragmentIndex.toShort())
        buf.put(payload)
        return buf.array()
    }

    companion object {
        fun fromBytes(data: ByteArray): BLEMessage {
            if (data.size < 8) throw IllegalArgumentException("Message too short")
            val buf = ByteBuffer.wrap(data)
            buf.order(ByteOrder.LITTLE_ENDIAN)
            val payloadLen = (buf.short.toInt() and 0xffff)
            val msgType = (buf.get().toInt() and 0xff)
            val seq = (buf.get().toInt() and 0xff)
            val total = (buf.short.toInt() and 0xffff)
            val idx = (buf.short.toInt() and 0xffff)
            val payload = ByteArray(payloadLen)
            buf.get(payload)
            val mt = BLEMessageType.fromCode(msgType) ?: throw IllegalArgumentException("Unknown message type: $msgType")
            return BLEMessage(mt, seq, total, idx, payload)
        }
    }
}

/**
 * Helper to fragment and re-assemble BLE messages according to the project's
 * Nordic-UART style framing. This class is pure JVM and unit-testable.
 */
class MessageFragmentManager(val mtu: Int = 20) {
    private val pending: MutableMap<Int, Array<BLEMessage?>> = mutableMapOf()
    private var sequenceCounter = 0

    @Synchronized
    fun nextSequenceId(): Int {
        sequenceCounter = (sequenceCounter + 1) and 0xFF
        if (sequenceCounter == 0) sequenceCounter = 1
        return sequenceCounter
    }

    /**
     * Fragment a payload into wire-format fragments. The "mtu" parameter
     * controls the maximum payload bytes per fragment (kept aligned with the
     * python code which slices by payload-chunk size rather than total packet size).
     */
    fun fragmentMessage(messageType: BLEMessageType, payload: ByteArray, sequenceId: Int? = null): List<ByteArray> {
        val seq = sequenceId ?: nextSequenceId()
        val totalFragments = (payload.size + mtu - 1) / mtu
        val fragments = mutableListOf<ByteArray>()
        for (i in 0 until totalFragments) {
            val start = i * mtu
            val end = minOf((i + 1) * mtu, payload.size)
            val piece = payload.copyOfRange(start, end)
            val msg = BLEMessage(messageType, seq, totalFragments, i, piece)
            fragments.add(msg.toBytes())
        }
        return fragments
    }

    /**
     * Feed an incoming wire fragment (as received from a GATT write/notification)
     * into the reassembly buffer. When a full message is reconstructed the
     * resulting (type, payload) pair is returned; otherwise null is returned.
     */
    @Synchronized
    fun onReceiveFragment(fragmentBytes: ByteArray): Pair<BLEMessageType, ByteArray>? {
        val msg = BLEMessage.fromBytes(fragmentBytes)
        val seq = msg.sequenceId
        if (!pending.containsKey(seq)) {
            pending[seq] = arrayOfNulls(msg.totalFragments)
        }
        val arr = pending[seq]!!
        if (msg.fragmentIndex >= arr.size) {
            // malformed fragment - ignore
            return null
        }
        arr[msg.fragmentIndex] = msg

        if (arr.all { it != null }) {
            val complete = arr.filterNotNull().flatMap { it.payload.toList() }.toByteArray()
            pending.remove(seq)
            return Pair(msg.messageType, complete)
        }
        return null
    }

    /**
     * Helper to parse a raw fragment into a BLEMessage without changing
     * internal state (useful for inspection in unit tests).
     */
    fun parseFragment(fragmentBytes: ByteArray): BLEMessage = BLEMessage.fromBytes(fragmentBytes)
}
