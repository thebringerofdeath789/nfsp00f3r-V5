package com.nf_sp00f.app.data

import java.util.Date

/**
 * Complete EMV Card Data Model - Matches Proxmark3 extraction capabilities Based on EMV 4.3
 * specification and Proxmark3 emvcore.c implementation
 */
data class EmvCardData(
        // Card Identification
        val applicationLabel: String? = null, // 0x50
        val applicationPreferredName: String? = null, // 0x9F12
        val applicationIdentifier: ByteArray? = null, // 0x4F (AID)
        val dedicatedFileName: ByteArray? = null, // 0x84
        val applicationPriorityIndicator: Int? = null, // 0x87

        // Primary Account Information
        val primaryAccountNumber: String? = null, // 0x5A (PAN)
        val panSequenceNumber: Int? = null, // 0x5F34
        val cardholderName: String? = null, // 0x5F20
        val languagePreference: String? = null, // 0x5F2D

        // Dates
        val applicationEffectiveDate: String? = null, // 0x5F25
        val applicationExpirationDate: String? = null, // 0x5F24

        // Track Data (Proxmark3 extracts these with full parsing)
        val track1Data: String? = null, // 0x56
        val track2Data: ByteArray? = null, // 0x9F6B
        val track2EquivalentData: ByteArray? = null, // 0x57
        val serviceCode: String? = null, // Extracted from Track2

        // Application Control
        val applicationInterchangeProfile: ByteArray? = null, // 0x82 (AIP)
        val applicationFileLocator: ByteArray? = null, // 0x94 (AFL)
        val applicationUsageControl: ByteArray? = null, // 0x9F07
        val applicationVersionNumber: ByteArray? = null, // 0x9F08

        // Transaction Processing
        val processingDataObjectList: ByteArray? = null, // 0x9F38 (PDOL)
        val cardRiskManagementDOL: ByteArray? = null, // 0x8C (CDOL1)
        val issuerAuthenticationDOL: ByteArray? = null, // 0x8D (CDOL2)
        val dynamicDataAuthenticationDOL: ByteArray? = null, // 0x9F49 (DDOL)

        // Cryptographic Information
        val applicationTransactionCounter: ByteArray? = null, // 0x9F36 (ATC)
        val applicationCryptogram: ByteArray? = null, // 0x9F26 (AC)
        val cryptogramInformationData: ByteArray? = null, // 0x9F27 (CID)
        val issuerApplicationData: ByteArray? = null, // 0x9F10 (IAD)
        val unpredictableNumber: ByteArray? = null, // 0x9F37

        // PKI & Authentication (Proxmark3 extracts full certificate chain)
        val caPublicKeyIndex: Int? = null, // 0x8F
        val issuerPublicKeyCertificate: ByteArray? = null, // 0x90
        val issuerPublicKeyRemainder: ByteArray? = null, // 0x92
        val iccPublicKeyCertificate: ByteArray? = null, // 0x9F46
        val iccPublicKeyExponent: ByteArray? = null, // 0x9F47
        val iccPublicKeyRemainder: ByteArray? = null, // 0x9F48
        val signedStaticApplicationData: ByteArray? = null, // 0x93
        val signedDynamicApplicationData: ByteArray? = null, // 0x9F4B

        // Terminal Transaction Qualifiers & Capabilities
        val terminalTransactionQualifiers: ByteArray? = null, // 0x9F66 (TTQ)
        val terminalCapabilities: ByteArray? = null, // 0x9F33
        val additionalTerminalCapabilities: ByteArray? = null, // 0x9F40
        val terminalType: Int? = null, // 0x9F35

        // Currency & Amount Information
        val transactionCurrencyCode: String? = null, // 0x5F2A
        val applicationCurrencyCode: String? = null, // 0x9F42
        val applicationCurrencyExponent: Int? = null, // 0x9F44

        // Card Verification Methods
        val cardholderVerificationMethodList: ByteArray? = null, // 0x8E (CVM List)
        val cardholderVerificationMethodResults: ByteArray? = null, // 0x9F34

        // Issuer & Acquirer Information
        val issuerCountryCode: String? = null, // 0x5F28
        val acquirerIdentifier: ByteArray? = null, // 0x9F01
        val merchantCategoryCode: String? = null, // 0x9F15
        val merchantIdentifier: String? = null, // 0x9F16
        val merchantNameAndLocation: String? = null, // 0x9F4E

        // Transaction Log Data (Proxmark3 reader mode extracts these)
        val transactionLogFormat: ByteArray? = null, // 0x9F4F
        val transactionLogEntry: ByteArray? = null, // 0x9F4D

        // Metadata
        val cardVendor: CardVendor = CardVendor.UNKNOWN,
        val readTimestamp: Date = Date(),
        val rawApduLog: List<ApduLogEntry> = emptyList(),
        val parsingErrors: List<String> = emptyList(),

        // Proxmark3-style analysis flags
        val supportsContactless: Boolean = false,
        val supportsContact: Boolean = false,
        val supportsMSD: Boolean = false,
        val supportsVSDC: Boolean = false,
        val supportsqVSDC: Boolean = false,
        val supportsCDA: Boolean = false,
        val supportsDDA: Boolean = false,
        val supportsSDA: Boolean = false,
        val vulnerableToROCA: Boolean? = null,

        // Complete TLV tree (for advanced analysis)
        val fullTlvData: Map<String, ByteArray> = emptyMap()
) {
  override fun equals(other: Any?): Boolean {
    if (this === other) return true
    if (javaClass != other?.javaClass) return false
    other as EmvCardData
    return primaryAccountNumber == other.primaryAccountNumber
  }

  override fun hashCode(): Int {
    return primaryAccountNumber?.hashCode() ?: 0
  }
}

/** Card Vendor Detection - Based on Proxmark3 AID list */
enum class CardVendor {
  VISA,
  MASTERCARD,
  AMERICAN_EXPRESS,
  DISCOVER,
  DINERS,
  JCB,
  MAESTRO,
  CIRRUS,
  PLUS,
  INTERAC,
  GIROCARD,
  CB,
  DANKORT,
  BANCOMAT,
  RUPAY,
  TROY,
  VERVE,
  ETRANZACT,
  GOOGLE_PAY,
  APPLE_PAY,
  SAMSUNG_PAY,
  UNKNOWN
}

/** EMV Transaction Type - Matches Proxmark3 modes */
enum class EmvTransactionType {
  MSD, // Magstripe Mode
  VSDC, // Visa Smart Debit/Credit
  QVSDC, // qVSDC (Quick VSDC)
  CDA, // Combined Data Authentication
  MCHIP // MasterCard M/Chip
}

/** APDU Log Entry with EMV-specific parsing */
data class EmvApduLogEntry(
        val timestamp: Long,
        val direction: ApduDirection,
        val rawCommand: ByteArray,
        val commandName: String,
        val parsedData: Map<String, String> = emptyMap(),
        val statusWord: String,
        val executionTimeMs: Long = 0
)

enum class ApduDirection {
  COMMAND, // → Terminal to Card
  RESPONSE // ← Card to Terminal
}

/** EMV Workflow State - Tracks reading progress */
data class EmvReadingSession(
        val sessionId: String,
        val startTime: Date,
        val device: NfcDevice,
        val currentWorkflow: EmvWorkflow,
        val completedSteps: List<EmvStep>,
        val cardData: EmvCardData,
        val apduLog: List<EmvApduLogEntry>,
        val errors: List<String>
)

enum class EmvWorkflow {
  PPSE_DISCOVERY, // PPSE → AID Selection → GPO → Read Records
  PSE_DISCOVERY, // PSE → AID Selection → GPO → Read Records
  DIRECT_AID_SEARCH, // Try known AIDs → GPO → Read Records
  QUICK_SCAN, // Fast data extraction (Proxmark3 scan mode)
  READER_MODE // Continuous monitoring (Proxmark3 reader mode)
}

enum class EmvStep {
  CARD_DETECTION,
  PPSE_SELECTION,
  PSE_SELECTION,
  AID_DISCOVERY,
  AID_SELECTION,
  GPO_PROCESSING,
  RECORD_READING,
  AUTHENTICATION,
  TRANSACTION_COMPLETE,
  ERROR_RECOVERY
}

/** Proxmark3-style EMV Analysis Results */
data class EmvAnalysisResult(
        val cardData: EmvCardData,
        val securityAnalysis: EmvSecurityAnalysis,
        val attackSurface: List<EmvAttackVector>,
        val recommendations: List<String>
)

data class EmvSecurityAnalysis(
        val authenticationMethods: List<String>,
        val cryptographicSupport: List<String>,
        val vulnerabilities: List<String>,
        val riskScore: Int, // 0-100
        val complianceLevel: String
)

enum class EmvAttackVector {
  REPLAY_ATTACK,
  RELAY_ATTACK,
  CLONING,
  CRYPTOGRAM_DOWNGRADE,
  CVM_BYPASS,
  TRACK2_SPOOFING,
  PPSE_POISONING,
  AIP_MANIPULATION
}
