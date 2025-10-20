package com.nf_sp00f.app.data

object EmvTestCard {
    fun getTestCard(): VirtualCard {
        return VirtualCard(
            cardholderName = "CARDHOLDER/VISA",
            pan = "4154904674973556",
            expiry = "29/02",
            apduCount = 0,
            cardType = "VISA"
        )
    }
}
