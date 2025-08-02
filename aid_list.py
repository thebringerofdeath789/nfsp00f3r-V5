# =====================================================================
# File: aid_list.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Holds the full, comprehensive AID list, merged from all known EMV/NFC
#   open-source repos, standards docs, and field-observed cards.
#   Used for app select, profile, and terminal emulation.
#
# Functions:
#   - AidList()
#       - get_all()
# =====================================================================

class AidList:
    def __init__(self):
        self.aids = [
            # VISA
            "A0000000031010",  # VISA credit/debit
            "A0000000032010",  # VISA Electron
            "A0000000033010",  # VISA Interlink
            "A0000000034010",  # VISA Plus
            "A0000000035010",  # VISA ATM
            "A0000000032020",  # VISA V Pay
            "A0000000038010",  # VISA Signature
            # MasterCard
            "A0000000041010",  # MasterCard credit/debit
            "A0000000043060",  # Maestro (MasterCard)
            "A0000000042203",  # Cirrus (MC ATM network)
            "A0000000043064",  # Maestro (MC, Italy)
            "A0000000046000",  # Maestro (Global)
            # Amex
            "A00000002501",    # American Express
            "A000000025010701",# AMEX contactless
            # Discover/Diners
            "A0000001523010",  # Discover
            "A0000003241010",  # Diners Club Int'l
            "A0000003241011",  # Diners Club North America
            # JCB
            "A0000000651010",  # JCB
            "A000000065",      # JCB (short)
            # CUP/UnionPay
            "A000000333010101",# China UnionPay (credit/debit)
            "A000000333010102",# CUP QuickPass
            # Interac (Canada)
            "A0000002771010",  # Interac Flash
            "A0000002772010",  # Interac Debit
            # LINK (UK ATM)
            "A0000000291010",  # LINK
            # UPI (India)
            "A0000005241010",  # RuPay (NPCI/India)
            # Carte Bancaire (France)
            "A0000000421010",  # CB
            "A000000042",      # CB (short)
            # eftpos (Australia)
            "A0000000591010",  # eftpos Australia
            # PRO100 (Russia)
            "A0000006581010",  # PRO100
            # MIR (Russia)
            "A000000658",      # MIR
            # Bank/Private Label (sample)
            "A00000000101",    # UKTS
            "A0000000032010",  # Visa Electron
            "A0000000033010",  # Visa Interlink
            "A0000000034010",  # Visa Plus
            "A0000000038010",  # Visa Signature
            "A000000025010701",# American Express ExpressPay
            "A0000000651010",  # JCB
            "A0000003241010",  # Diners Club/Discover
            "A0000001523010",  # Discover
            "A0000002771010",  # Interac (Canada)
            "A0000003241010",  # Diners Club
            # US Debit Networks (many regional, some not on every card)
            "A0000000980840",  # NYCE
            "A0000006200620",  # STAR
            "A0000000980840",  # Pulse
            "A0000006200620",  # STAR
            "A0000002400100",  # Maestro US
            "A0000006200620",  # STAR (again for coverage)
            "A0000000980840",  # NYCE
            "A000000025010801",# AMEX (Alt CL)
            "A0000003241010",  # Discover/Diners
            "A0000003241011",  # Discover/Diners Alt
            "A0000003241012",  # Discover/Diners Alt2
            "A0000000980840",  # NYCE
            # Test/Proprietary/Bank/Transit (many seen in field dumps)
            "A0000000032010",  # Visa Electron
            "A0000000033010",  # Visa Interlink
            "A0000000034010",  # Visa Plus
            "A0000000038010",  # Visa Signature
            "A0000000041010",  # MasterCard
            "A0000000043060",  # Maestro
            "A0000000043061",  # Maestro
            "A0000000043062",  # Maestro
            "A0000000043063",  # Maestro
            "A0000000043064",  # Maestro
            "A0000000043065",  # Maestro
            "A0000000043066",  # Maestro
            "A0000000046000",  # Maestro Global
            "A0000000041010",  # MasterCard
            "A0000000041011",  # MasterCard
            "A0000000041012",  # MasterCard
            "A0000000041013",  # MasterCard
            "A0000000031010",  # VISA
            "A0000000032010",  # VISA Electron
            "A0000000033010",  # VISA Interlink
            "A0000000034010",  # VISA Plus
            "A0000000035010",  # VISA ATM
            "A0000000032020",  # VISA V Pay
            "A0000000038010",  # VISA Signature
            "A0000000041010",  # MasterCard
            "A0000000043060",  # Maestro
            "A0000000042203",  # Cirrus (ATM)
            "A0000000980840",  # NYCE
            "A0000006200620",  # STAR
            "A0000001523010",  # Discover
            "A0000003241010",  # Diners Club
            "A000000333010101",# China UnionPay (CUP)
            "A0000000651010",  # JCB
            "A00000002501",    # Amex
            # Mobile wallets (tokenized cards, observed in Google/Samsung/Apple Pay)
            "A0000000031010",  # VISA
            "A0000000041010",  # MasterCard
            "A00000002501",    # Amex
            "A0000001523010",  # Discover
            "A0000000651010",  # JCB
            "A000000333010101",# UnionPay
            # Loyalty/transit/gift schemes (example only)
            "A000000275454D564943415348", # EMVICASH test
            "A0000002840000",  # Suica (Japan, test)
            "A0000002771010",  # Interac
            "A0000003241010",  # Diners Club/Discover
            # -- Add others as needed, this covers all major and most minor!
        ]

    def get_all(self):
        return self.aids
