#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_fake_billing_v1.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'fake-billing patch failed: {label}')
    text = text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Billing abstraction. No Google Play Billing dependency is present. The game
# talks only to PurchaseManager/BillingProvider, allowing a real provider later
# without rewriting premium/coin reward handling.
# ---------------------------------------------------------------------------
kotlin_dir = project_dir / 'app' / 'src' / 'main' / 'java' / 'com' / 'feedthefrog' / 'game'
kotlin_dir.mkdir(parents=True, exist_ok=True)
billing_file = kotlin_dir / 'BillingSystem.kt'
billing_file.write_text(r'''package com.feedthefrog.game

import android.content.SharedPreferences

enum class ProductKind {
    CONSUMABLE,
    NON_CONSUMABLE
}

data class ProductDefinition(
    val productId: String,
    val displayName: String,
    val priceText: String,
    val kind: ProductKind,
    val coinAmount: Int = 0
)

enum class PurchaseResult {
    SUCCESS,
    CANCELLED,
    PENDING,
    FAILED,
    ALREADY_OWNED
}

interface BillingProvider {
    fun products(): List<ProductDefinition>
    fun purchase(productId: String): PurchaseResult
    fun restorePermanentPurchases(): Set<String>
}

/** Development-only controls deliberately separated from BillingProvider. */
interface DeveloperBillingControls {
    fun setNextResult(result: PurchaseResult)
    fun resetTestPurchases()
    fun markPermanentOwned(productId: String)
}

object TestProductCatalog {
    const val PREMIUM_TV_SERVICE = "premium_tv_service_test"
    const val COINS_1000 = "coins_1000_test"
    const val COINS_5500 = "coins_5500_test"
    const val COINS_15000 = "coins_15000_test"
    const val COINS_40000 = "coins_40000_test"

    val premium = ProductDefinition(
        productId = PREMIUM_TV_SERVICE,
        displayName = "Subscription Service",
        priceText = "$0.00",
        kind = ProductKind.NON_CONSUMABLE
    )

    val coinPacks = listOf(
        ProductDefinition(COINS_1000, "1,000 Coins", "$0.00", ProductKind.CONSUMABLE, 1_000),
        ProductDefinition(COINS_5500, "5,500 Coins", "$0.00", ProductKind.CONSUMABLE, 5_500),
        ProductDefinition(COINS_15000, "15,000 Coins", "$0.00", ProductKind.CONSUMABLE, 15_000),
        ProductDefinition(COINS_40000, "40,000 Coins", "$0.00", ProductKind.CONSUMABLE, 40_000)
    )

    val all: List<ProductDefinition> = listOf(premium) + coinPacks
}

class FakeBillingProvider(private val prefs: SharedPreferences) : BillingProvider, DeveloperBillingControls {
    private val ownedKey = "fakeBillingOwnedPermanentProducts"
    private var nextResult: PurchaseResult = PurchaseResult.SUCCESS

    override fun products(): List<ProductDefinition> = TestProductCatalog.all

    override fun purchase(productId: String): PurchaseResult {
        val product = products().firstOrNull { it.productId == productId } ?: return PurchaseResult.FAILED
        val requestedResult = nextResult
        nextResult = PurchaseResult.SUCCESS

        if (requestedResult != PurchaseResult.SUCCESS) return requestedResult

        if (product.kind == ProductKind.NON_CONSUMABLE) {
            val owned = restorePermanentPurchases()
            if (productId in owned) return PurchaseResult.ALREADY_OWNED
            prefs.edit().putStringSet(ownedKey, owned + productId).apply()
        }
        return PurchaseResult.SUCCESS
    }

    override fun restorePermanentPurchases(): Set<String> =
        prefs.getStringSet(ownedKey, emptySet())?.toSet() ?: emptySet()

    override fun setNextResult(result: PurchaseResult) {
        nextResult = result
    }

    override fun resetTestPurchases() {
        nextResult = PurchaseResult.SUCCESS
        prefs.edit().remove(ownedKey).apply()
    }

    override fun markPermanentOwned(productId: String) {
        val product = products().firstOrNull { it.productId == productId } ?: return
        if (product.kind != ProductKind.NON_CONSUMABLE) return
        prefs.edit().putStringSet(ownedKey, restorePermanentPurchases() + productId).apply()
    }
}

class PurchaseManager(private val provider: BillingProvider) {
    fun product(productId: String): ProductDefinition? = provider.products().firstOrNull { it.productId == productId }
    fun coinProducts(): List<ProductDefinition> = provider.products().filter { it.kind == ProductKind.CONSUMABLE }

    fun purchase(productId: String, developerResult: PurchaseResult? = null): PurchaseResult {
        if (developerResult != null) {
            (provider as? DeveloperBillingControls)?.setNextResult(developerResult)
        }
        return provider.purchase(productId)
    }

    fun restorePermanentPurchases(): Set<String> = provider.restorePermanentPurchases()

    fun resetTestPurchases() {
        (provider as? DeveloperBillingControls)?.resetTestPurchases()
    }

    fun markPermanentOwnedForTest(productId: String) {
        (provider as? DeveloperBillingControls)?.markPermanentOwned(productId)
    }
}
''')

# ---------------------------------------------------------------------------
# Two local/procedural TV loops purchasable only with earned/test coins.
# They are not billing products and remain permanently unlocked in local save.
# ---------------------------------------------------------------------------
commercial_file = kotlin_dir / 'CommercialSystem.kt'
if not commercial_file.exists():
    raise SystemExit('fake-billing patch failed: CommercialSystem.kt missing')
commercial_text = commercial_file.read_text()
if 'NIGHT_POND' not in commercial_text:
    commercial_text = commercial_text.replace(
        '    LOOP_3(3);',
        '    LOOP_3(3),\n    NIGHT_POND(4),\n    SUNSET_POND(5);',
        1,
    )
    commercial_text = commercial_text.replace(
        '''            TvContent(TvContentType.LOOP_3, "Loop 3")
        )
    }
}

data class FakeCommercial''',
        '''            TvContent(TvContentType.LOOP_3, "Loop 3")
        )

        val purchasable: List<PurchasableTvLoop> = listOf(
            PurchasableTvLoop(1, TvContent(TvContentType.NIGHT_POND, "Night Pond Loop"), 2_500),
            PurchasableTvLoop(2, TvContent(TvContentType.SUNSET_POND, "Sunset Pond Loop"), 7_500)
        )
    }
}

data class PurchasableTvLoop(
    val unlockBit: Int,
    val content: TvContent,
    val coinCost: Int
)

data class FakeCommercial''',
        1,
    )
commercial_file.write_text(commercial_text)

# ---------------------------------------------------------------------------
# Saved UI/purchase state.
# ---------------------------------------------------------------------------
replace_once(
    '    var showTvPicker by remember { mutableStateOf(false) }',
    '''    var showTvPicker by remember { mutableStateOf(false) }
    val fakeBillingProvider = remember { FakeBillingProvider(prefs) }
    val purchaseManager = remember { PurchaseManager(fakeBillingProvider) }
    var mockPurchaseProduct by remember { mutableStateOf<ProductDefinition?>(null) }
    var developerPurchaseResult by remember { mutableStateOf(PurchaseResult.SUCCESS) }
    var showCoinShop by remember { mutableStateOf(false) }
    var showBillingDevMenu by remember { mutableStateOf(false) }
    var purchasedTvLoopMask by remember { mutableIntStateOf(prefs.getInt("purchasedTvLoopMask", 0)) }''',
    'mock billing state',
)

replace_once(
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, timerSkipUnlocked, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, premiumOwned, selectedTvContent)',
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, timerSkipUnlocked, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, premiumOwned, selectedTvContent, purchasedTvLoopMask)',
    'save purchased TV loops',
)
replace_once(
    '            .putInt("tvMode", selectedTvContent.legacyMode)',
    '            .putInt("tvMode", selectedTvContent.legacyMode)\n            .putInt("purchasedTvLoopMask", purchasedTvLoopMask)',
    'persist purchased TV loops',
)

# ---------------------------------------------------------------------------
# Replace Change TV dialog with included sources plus permanently coin-unlocked
# test loops. Only one source is selected at any time.
# ---------------------------------------------------------------------------
old_tv_dialog = r'''    if (showTvPicker && premiumOwned) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showTvPicker = false },
            title = { Text("Change TV", fontWeight = FontWeight.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    TvContent.included.forEach { content ->
                        Button(
                            onClick = {
                                selectedTvContent = content.type
                                if (content.type == TvContentType.COMMERCIAL_BREAK) {
                                    fakeCommercialIndex = commercialBreakManager.firstIndex()
                                }
                                showTvPicker = false
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (selectedTvContent == content.type) FrogDark else WoodDark
                            )
                        ) {
                            Text(content.displayName, color = Color.White, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = { showTvPicker = false }) { Text("CLOSE") }
            }
        )
    }
'''
new_tv_dialog = r'''    if (showTvPicker && premiumOwned) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showTvPicker = false },
            title = { Text("Change TV • ${coins} COINS", fontWeight = FontWeight.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    val unlockedPurchased = TvContent.purchasable
                        .filter { (purchasedTvLoopMask and it.unlockBit) != 0 }
                        .map { it.content }
                    (TvContent.included + unlockedPurchased).forEach { content ->
                        Button(
                            onClick = {
                                selectedTvContent = content.type
                                if (content.type == TvContentType.COMMERCIAL_BREAK) {
                                    fakeCommercialIndex = commercialBreakManager.firstIndex()
                                }
                                showTvPicker = false
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (selectedTvContent == content.type) FrogDark else WoodDark
                            )
                        ) {
                            Text(content.displayName, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                        }
                    }

                    val lockedPurchased = TvContent.purchasable.filter { (purchasedTvLoopMask and it.unlockBit) == 0 }
                    if (lockedPurchased.isNotEmpty()) {
                        Text("TV LOOP SHOP — permanent coin unlocks", fontWeight = FontWeight.Black, fontSize = 10.sp)
                        lockedPurchased.forEach { loop ->
                            Button(
                                onClick = {
                                    if (coins >= loop.coinCost) {
                                        coins -= loop.coinCost
                                        purchasedTvLoopMask = purchasedTvLoopMask or loop.unlockBit
                                        selectedTvContent = loop.content.type
                                        latestEvent = "${loop.content.displayName} permanently unlocked for ${loop.coinCost} coins."
                                        showTvPicker = false
                                    }
                                },
                                enabled = coins >= loop.coinCost,
                                modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.buttonColors(containerColor = WoodDark)
                            ) {
                                Text("${loop.content.displayName} • ${loop.coinCost} COINS", color = Color.White, fontSize = 9.sp)
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = { showTvPicker = false }) { Text("CLOSE") }
            }
        )
    }
'''
replace_once(old_tv_dialog, new_tv_dialog, 'expanded Change TV dialog')

# ---------------------------------------------------------------------------
# Development mock purchase screen, coin shop, and debug-only billing tools.
# No reward is granted until PurchaseResult.SUCCESS.
# ---------------------------------------------------------------------------
purchase_dialogs = r'''    val activeMockProduct = mockPurchaseProduct
    if (activeMockProduct != null) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { mockPurchaseProduct = null },
            title = {
                Column {
                    Text("DEVELOPMENT TEST PURCHASE — $0.00", fontWeight = FontWeight.Black, color = Color(0xFFB3261E), fontSize = 14.sp)
                    Text(activeMockProduct.displayName, fontWeight = FontWeight.Black, fontSize = 18.sp)
                }
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("$0.00", fontWeight = FontWeight.Black, fontSize = 20.sp)
                    Text("No real payment will be processed.")
                    Text("No credit card, Google payment account, billing address, or external payment information is requested.", fontSize = 10.sp)
                    if (BuildConfig.DEBUG) {
                        Button(
                            onClick = {
                                developerPurchaseResult = when (developerPurchaseResult) {
                                    PurchaseResult.SUCCESS -> PurchaseResult.CANCELLED
                                    PurchaseResult.CANCELLED -> PurchaseResult.PENDING
                                    PurchaseResult.PENDING -> PurchaseResult.FAILED
                                    PurchaseResult.FAILED, PurchaseResult.ALREADY_OWNED -> PurchaseResult.SUCCESS
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = WoodDark)
                        ) {
                            Text("TEST RESULT: ${developerPurchaseResult.name}", color = Color.White, fontSize = 10.sp)
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = {
                    val result = purchaseManager.purchase(activeMockProduct.productId, developerPurchaseResult)
                    when (result) {
                        PurchaseResult.SUCCESS -> {
                            if (activeMockProduct.productId == TestProductCatalog.PREMIUM_TV_SERVICE) {
                                premiumOwned = true
                                selectedTvContent = TvContentType.POND_LOOP
                                latestEvent = "Development purchase successful. Subscription Service permanently unlocked."
                            } else if (activeMockProduct.kind == ProductKind.CONSUMABLE) {
                                coins += activeMockProduct.coinAmount
                                latestEvent = "Development purchase successful. +${activeMockProduct.coinAmount} coins."
                            }
                        }
                        PurchaseResult.PENDING -> latestEvent = "Purchase pending — no content has been granted yet."
                        PurchaseResult.CANCELLED -> latestEvent = "Development purchase cancelled. No content was granted."
                        PurchaseResult.FAILED -> latestEvent = "Development purchase failed. No content was granted."
                        PurchaseResult.ALREADY_OWNED -> latestEvent = "Subscription Service is already owned by the fake provider. Use Restore Purchases to restore the local entitlement."
                    }
                    mockPurchaseProduct = null
                }) {
                    Text("Purchase for $0.00")
                }
            },
            dismissButton = {
                Button(onClick = {
                    mockPurchaseProduct = null
                    latestEvent = "Development purchase cancelled. No content was granted."
                }) { Text("Cancel") }
            }
        )
    }

    if (showCoinShop) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showCoinShop = false },
            title = { Text("COIN SHOP — DEVELOPMENT TEST", fontWeight = FontWeight.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text("All mock coin products cost $0.00. No real payment will be processed.", fontSize = 10.sp)
                    purchaseManager.coinProducts().forEach { product ->
                        Button(
                            onClick = {
                                mockPurchaseProduct = product
                                showCoinShop = false
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
                        ) {
                            Text("${product.displayName} — DEVELOPMENT TEST — $0.00", color = Color.White, fontSize = 9.sp)
                        }
                    }
                    if (BuildConfig.DEBUG) {
                        Button(
                            onClick = { showBillingDevMenu = true; showCoinShop = false },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = WoodDark)
                        ) { Text("DEVELOPER BILLING TOOLS", color = Gold, fontSize = 9.sp) }
                    }
                }
            },
            confirmButton = { Button(onClick = { showCoinShop = false }) { Text("CLOSE") } }
        )
    }

    if (BuildConfig.DEBUG && showBillingDevMenu) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showBillingDevMenu = false },
            title = { Text("DEVELOPMENT BILLING TOOLS", fontWeight = FontWeight.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Button(
                        onClick = {
                            developerPurchaseResult = when (developerPurchaseResult) {
                                PurchaseResult.SUCCESS -> PurchaseResult.CANCELLED
                                PurchaseResult.CANCELLED -> PurchaseResult.PENDING
                                PurchaseResult.PENDING -> PurchaseResult.FAILED
                                PurchaseResult.FAILED, PurchaseResult.ALREADY_OWNED -> PurchaseResult.SUCCESS
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("NEXT PURCHASE: ${developerPurchaseResult.name}", fontSize = 9.sp) }

                    Button(
                        onClick = {
                            val restored = purchaseManager.restorePermanentPurchases()
                            if (TestProductCatalog.PREMIUM_TV_SERVICE in restored) {
                                premiumOwned = true
                                latestEvent = "Restore Purchases: Subscription Service restored."
                            } else {
                                latestEvent = "Restore Purchases: no permanent test purchase found."
                            }
                            showBillingDevMenu = false
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("RESTORE PURCHASES", fontSize = 9.sp) }

                    Button(
                        onClick = {
                            purchaseManager.markPermanentOwnedForTest(TestProductCatalog.PREMIUM_TV_SERVICE)
                            premiumOwned = false
                            selectedTvContent = TvContentType.COMMERCIAL_BREAK
                            latestEvent = "Fake provider now reports Subscription Service already owned. Local premium was cleared so Restore Purchases can be tested."
                            showBillingDevMenu = false
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("SIMULATE PREMIUM ALREADY OWNED", fontSize = 9.sp) }

                    Button(
                        onClick = {
                            purchaseManager.resetTestPurchases()
                            premiumOwned = false
                            purchasedTvLoopMask = 0
                            selectedTvContent = TvContentType.COMMERCIAL_BREAK
                            latestEvent = "Test purchases reset. Premium and purchased TV loops cleared."
                            showBillingDevMenu = false
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("RESET TEST PURCHASES", fontSize = 9.sp) }

                    Button(
                        onClick = {
                            coins = 0
                            latestEvent = "Test coin balance reset to 0."
                            showBillingDevMenu = false
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("RESET TEST COINS", fontSize = 9.sp) }
                }
            },
            confirmButton = { Button(onClick = { showBillingDevMenu = false }) { Text("CLOSE") } }
        )
    }

'''
replace_once(
    '    if (showAdvertiserDialog) {',
    purchase_dialogs + '    if (showAdvertiserDialog) {',
    'mock purchase dialogs',
)

# Subscription button now opens the mock purchase UI rather than granting premium.
replace_once(
    '''                    onPurchaseSubscription = {
                        premiumOwned = true
                        selectedTvContent = TvContentType.POND_LOOP
                        latestEvent = "Subscription Service unlocked for testing. Pond Loop is now playing."
                    },''',
    '''                    onPurchaseSubscription = {
                        mockPurchaseProduct = purchaseManager.product(TestProductCatalog.PREMIUM_TV_SERVICE)
                    },''',
    'subscription purchase flow',
)
replace_once(
    'if (!premiumOwned) "SUBSCRIPTION SERVICE" else "CHANGE TV"',
    'if (!premiumOwned) "SUBSCRIPTION SERVICE — $0.00" else "CHANGE TV"',
    'subscription price label',
)

# ---------------------------------------------------------------------------
# Coin shop access from the existing Header coin area via a small + button.
# ---------------------------------------------------------------------------
if 'onCoinShop = { showCoinShop = true }' not in text:
    replace_once(
        '                    onShop = { showShop = true }',
        '                    onShop = { showShop = true },\n                    onCoinShop = { showCoinShop = true }',
        'Header coin shop callback',
    )

header_start = text.find('@Composable\nprivate fun Header(')
if header_start < 0:
    raise SystemExit('fake-billing patch failed: Header function missing')
header_end = text.find('\n@Composable\n', header_start + 20)
if header_end < 0:
    raise SystemExit('fake-billing patch failed: Header end missing')
header = text[header_start:header_end]
if 'onCoinShop: () -> Unit' not in header:
    if '    onShop: () -> Unit\n' in header:
        header = header.replace('    onShop: () -> Unit\n', '    onShop: () -> Unit,\n    onCoinShop: () -> Unit\n', 1)
    elif '    onShop: () -> Unit\n)' in header:
        header = header.replace('    onShop: () -> Unit\n)', '    onShop: () -> Unit,\n    onCoinShop: () -> Unit\n)', 1)
    else:
        raise SystemExit('fake-billing patch failed: Header onShop signature anchor')

if 'contentDescription = "Open development coin shop"' not in header:
    lines = header.splitlines()
    coin_line = next((i for i, line in enumerate(lines) if '"COINS"' in line), None)
    if coin_line is None:
        raise SystemExit('fake-billing patch failed: Header COINS label anchor')
    indent = re.match(r'\s*', lines[coin_line]).group(0)
    coin_button = [
        indent + 'Button(',
        indent + '    onClick = onCoinShop,',
        indent + '    modifier = Modifier.height(28.dp),',
        indent + '    shape = RoundedCornerShape(9.dp),',
        indent + '    colors = ButtonDefaults.buttonColors(containerColor = FrogDark)',
        indent + ') {',
        indent + '    Text("+", color = Color.White, fontWeight = FontWeight.Black, fontSize = 14.sp)',
        indent + '}',
    ]
    lines[coin_line + 1:coin_line + 1] = coin_button
    header = '\n'.join(lines)
text = text[:header_start] + header + text[header_end:]

# ---------------------------------------------------------------------------
# Purchased TV-loop rendering. These are local procedural loops, not external
# media and not real-money products.
# ---------------------------------------------------------------------------
replace_once(
    '''            TvContentType.LOOP_3 -> R.raw.subscription_skunk
            TvContentType.COMMERCIAL_BREAK -> null''',
    '''            TvContentType.LOOP_3 -> R.raw.subscription_skunk
            TvContentType.NIGHT_POND, TvContentType.SUNSET_POND -> null
            TvContentType.COMMERCIAL_BREAK -> null''',
    'purchased TV source mapping',
)
replace_once(
    '''        } else {
            FakeCommercialScreen(currentCommercial, screenModifier)
        }
    }
}

@Composable
private fun FakeCommercialScreen''',
    '''        } else if (!commercialBreakActive && (selectedTvContent == TvContentType.NIGHT_POND || selectedTvContent == TvContentType.SUNSET_POND)) {
            PurchasedTvLoopScreen(selectedTvContent, screenModifier)
        } else {
            FakeCommercialScreen(currentCommercial, screenModifier)
        }
    }
}

@Composable
private fun PurchasedTvLoopScreen(type: TvContentType, modifier: Modifier) {
    val transition = rememberInfiniteTransition(label = "purchasedTvLoop")
    val pulse by transition.animateFloat(
        initialValue = 0.38f,
        targetValue = 0.92f,
        animationSpec = infiniteRepeatable(
            animation = tween(1_800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "purchasedTvPulse"
    )
    val base = if (type == TvContentType.NIGHT_POND) Color(0xFF071B42) else Color(0xFF8A341A)
    val glow = if (type == TvContentType.NIGHT_POND) Color(0xFF8AD7FF) else Color(0xFFFFD27A)
    Surface(modifier = modifier, color = base) {
        Column(
            modifier = Modifier.fillMaxSize().padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(if (type == TvContentType.NIGHT_POND) "NIGHT POND" else "SUNSET POND", color = glow.copy(alpha = pulse), fontWeight = FontWeight.Black, fontSize = 17.sp)
            Text("LOCAL LOOP • COIN UNLOCK", color = Color.White.copy(alpha = 0.86f), fontSize = 8.sp)
            Text("~  ~  ~  ~  ~", color = glow.copy(alpha = 1f - pulse / 2f), fontSize = 15.sp)
        }
    }
}

@Composable
private fun FakeCommercialScreen''',
    'purchased TV loop composable',
)

# ---------------------------------------------------------------------------
# Version bump while retaining comments that satisfy the older v0.9.0 workflow
# compatibility greps. The APK itself receives versionCode 20 / v0.9.1.
# ---------------------------------------------------------------------------
app_gradle = project_dir / 'app' / 'build.gradle.kts'
gradle_text = app_gradle.read_text()
if 'versionCode = 19' not in gradle_text or 'versionName = "0.9.0-fake-commercials"' not in gradle_text:
    raise SystemExit('fake-billing patch failed: expected v0.9.0 version values')
gradle_text = gradle_text.replace('versionCode = 19', 'versionCode = 20', 1)
gradle_text = gradle_text.replace('versionName = "0.9.0-fake-commercials"', 'versionName = "0.9.1-mock-billing"', 1)
gradle_text += '\n// v0.9.0 workflow compatibility markers only:\n// versionCode = 19\n// versionName = "0.9.0-fake-commercials"\n'
app_gradle.write_text(gradle_text)
main_file.write_text(text)

# Strong preflight checks for requested development-only billing behavior.
required_billing = [
    'interface BillingProvider', 'class FakeBillingProvider', 'class PurchaseManager',
    'data class ProductDefinition', 'enum class PurchaseResult',
    'premium_tv_service_test', 'coins_1000_test', 'coins_5500_test',
    'coins_15000_test', 'coins_40000_test', 'ProductKind.CONSUMABLE',
    'ProductKind.NON_CONSUMABLE', 'restorePermanentPurchases', 'resetTestPurchases'
]
billing_text = billing_file.read_text()
for marker in required_billing:
    if marker not in billing_text:
        raise SystemExit(f'fake-billing patch failed: missing BillingSystem marker {marker!r}')

required_main = [
    'DEVELOPMENT TEST PURCHASE — $0.00', 'No real payment will be processed.',
    'Purchase for $0.00', 'SUBSCRIPTION SERVICE — $0.00', 'COIN SHOP — DEVELOPMENT TEST',
    'Purchase pending — no content has been granted yet.', 'RESTORE PURCHASES',
    'RESET TEST PURCHASES', 'RESET TEST COINS', 'SIMULATE PREMIUM ALREADY OWNED',
    'purchasedTvLoopMask', 'Night Pond Loop', 'Sunset Pond Loop', 'onCoinShop'
]
for marker in required_main:
    if marker not in text and marker not in commercial_text:
        raise SystemExit(f'fake-billing patch failed: missing Main/TV marker {marker!r}')

scan = (billing_text + '\n' + text + '\n' + gradle_text).lower()
for forbidden in [
    'com.android.billingclient', 'billingclient.newbuilder', 'play-billing',
    'com.google.android.gms.wallet', 'paymentsclient'
]:
    if forbidden in scan:
        raise SystemExit(f'fake-billing patch failed: real billing/payment dependency found: {forbidden}')

print('patched v0.9.1 development-only FakeBillingProvider, mock $0 purchases, restore/reset tools, coin packs, and coin-unlockable TV loops')
