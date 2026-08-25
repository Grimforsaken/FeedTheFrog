package com.feedthefrog.game

import android.os.Bundle
import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.random.Random

private val PondDark = Color(0xFF0B5960)
private val PondLight = Color(0xFF48B9B4)
private val PondSky = Color(0xFF9DE4E0)
private val FrogGreen = Color(0xFF86C91D)
private val FrogLight = Color(0xFFB6DF41)
private val FrogDark = Color(0xFF3A731B)
private val Cream = Color(0xFFFFF2C9)
private val Wood = Color(0xFF7A4A22)
private val WoodDark = Color(0xFF4E2E17)
private val Gold = Color(0xFFFFC94D)
private val Tongue = Color(0xFFF16F7B)
private val Ink = Color(0xFF25321C)
private val ShopPaper = Color(0xFFFFF7DE)
private val BeeYellow = Color(0xFFF3C623)
private val MothTan = Color(0xFFD8C29E)
private val SkyWing = Color(0xFFD9F4FF)

private const val FLY_REWARD = 25
private const val SECOND_DIE_COST = 10_000
private const val BEE_PENALTY = -40
private val DIE_SIDES = intArrayOf(3, 4, 6, 8, 12, 20)
private val DIE_UPGRADE_COSTS = intArrayOf(200, 500, 1_200, 3_000, 7_500)
private val RANGE_COSTS = intArrayOf(150, 350, 750, 1_500, 3_000, 6_000)
private val RANGE_REACH_DP = intArrayOf(48, 66, 84, 102, 120, 138, 156)

private enum class BugType(
    val label: String,
    val reward: Int,
    val scale: Float,
    val movementAmplitude: Float,
    val speedMultiplier: Float,
    val wanderStep: Float,
    val harmful: Boolean,
    val unlockAtCaught: Int,
    val guideName: String
) {
    COMMON_FLY("Fly", FLY_REWARD, 1.0f, 7f, 1.0f, 2.2f, false, 0, "Fly +25"),
    MOSQUITO("Mosquito", 15, 0.78f, 10f, 1.45f, 4.0f, false, 8, "Mosquito +15"),
    FAST_FLY("Fast Fly", 35, 0.92f, 13f, 1.7f, 5.3f, false, 18, "Fast Fly +35"),
    MOTH("Moth", 45, 1.15f, 6f, 0.72f, 1.5f, false, 35, "Moth +45"),
    BEE("Bee", BEE_PENALTY, 0.95f, 10f, 1.15f, 3.1f, true, 55, "Bee -40"),
    GOLDEN_FLY("Golden Fly", 100, 1.08f, 9f, 1.18f, 4.4f, false, 80, "Golden Fly +100")
}

private data class Fly(
    val id: Int,
    val position: Offset,
    val type: BugType,
    val buzzSeed: Float = Random.nextFloat() * 8f
)

private class GameAudio(context: Context) {
    private val audioAttributes = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_GAME)
        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
        .build()

    private val soundPool = SoundPool.Builder()
        .setMaxStreams(7)
        .setAudioAttributes(audioAttributes)
        .build()

    private val diceRoll = soundPool.load(context, R.raw.dice_roll, 1)
    private val grab = soundPool.load(context, R.raw.grab, 1)
    private val tongueSnap = soundPool.load(context, R.raw.tongue_snap, 1)
    private val catch = soundPool.load(context, R.raw.catch_sound, 1)
    private val golden = soundPool.load(context, R.raw.golden, 1)
    private val beeBad = soundPool.load(context, R.raw.bee_bad, 1)
    private val upgrade = soundPool.load(context, R.raw.upgrade, 1)
    private val unlock = soundPool.load(context, R.raw.unlock, 1)

    private val buzzPlayer = MediaPlayer.create(context, R.raw.buzz_loop).apply {
        isLooping = true
        setVolume(0f, 0f)
    }

    private var enabled = true
    private var desiredBuzzVolume = 0f

    fun setEnabled(value: Boolean) {
        enabled = value
        refreshBuzzPlayback()
    }

    fun updateBuzz(flies: List<Fly>) {
        if (flies.isEmpty()) {
            desiredBuzzVolume = 0f
        } else {
            val beeBoost = flies.count { it.type == BugType.BEE } * 0.025f
            val fastBoost = flies.count { it.type == BugType.FAST_FLY || it.type == BugType.MOSQUITO } * 0.012f
            desiredBuzzVolume = (0.07f + flies.size * 0.018f + beeBoost + fastBoost).coerceAtMost(0.42f)
        }
        refreshBuzzPlayback()
    }

    private fun refreshBuzzPlayback() {
        if (!enabled || desiredBuzzVolume <= 0f) {
            if (buzzPlayer.isPlaying) buzzPlayer.pause()
            return
        }
        buzzPlayer.setVolume(desiredBuzzVolume, desiredBuzzVolume)
        if (!buzzPlayer.isPlaying) buzzPlayer.start()
    }

    private fun play(soundId: Int, volume: Float = 0.8f, rate: Float = 1f) {
        if (enabled) soundPool.play(soundId, volume, volume, 1, 0, rate)
    }

    fun playRoll() = play(diceRoll, 0.72f)
    fun playGrab() = play(grab, 0.55f, 1.04f)
    fun playTongue() = play(tongueSnap, 0.78f)
    fun playCatch() = play(catch, 0.72f, 1.03f)
    fun playGolden() = play(golden, 0.88f)
    fun playBeeBad() = play(beeBad, 0.88f)
    fun playUpgrade() = play(upgrade, 0.72f)
    fun playUnlock() = play(unlock, 0.82f)

    fun release() {
        buzzPlayer.stop()
        buzzPlayer.release()
        soundPool.release()
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                FeedTheFrogGame()
            }
        }
    }
}

@Composable
private fun FeedTheFrogGame() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("feed_the_frog_save", 0) }
    val audio = remember(context) { GameAudio(context.applicationContext) }

    var coins by remember { mutableIntStateOf(prefs.getInt("coins", 0)) }
    var dieIndex by remember { mutableIntStateOf(prefs.getInt("dieIndex", 0).coerceIn(0, DIE_SIDES.lastIndex)) }
    var rangeLevel by remember { mutableIntStateOf(prefs.getInt("rangeLevel", 0).coerceIn(0, RANGE_COSTS.size)) }
    var secondDie by remember { mutableStateOf(prefs.getBoolean("secondDie", false)) }
    var secondDieIndex by remember { mutableIntStateOf(prefs.getInt("secondDieIndex", 0).coerceIn(0, DIE_SIDES.lastIndex)) }
    var totalCaught by remember { mutableIntStateOf(prefs.getInt("totalCaught", 0)) }
    var soundOn by remember { mutableStateOf(prefs.getBoolean("soundOn", true)) }
    var started by remember { mutableStateOf(false) }
    var showShop by remember { mutableStateOf(false) }
    var latestEvent by remember { mutableStateOf("Catch flies, unlock new bugs, and avoid bees!") }

    var lastRoll by remember { mutableIntStateOf(0) }
    var lastDieOne by remember { mutableIntStateOf(0) }
    var lastDieTwo by remember { mutableIntStateOf(0) }

    val flies = remember { mutableStateListOf<Fly>() }
    var nextFlyId by remember { mutableIntStateOf(1) }

    LaunchedEffect(coins, dieIndex, rangeLevel, secondDie, secondDieIndex, totalCaught, soundOn) {
        prefs.edit()
            .putInt("coins", coins)
            .putInt("dieIndex", dieIndex)
            .putInt("rangeLevel", rangeLevel)
            .putBoolean("secondDie", secondDie)
            .putInt("secondDieIndex", secondDieIndex)
            .putInt("totalCaught", totalCaught)
            .putBoolean("soundOn", soundOn)
            .apply()
    }

    LaunchedEffect(soundOn) {
        audio.setEnabled(soundOn)
    }

    LaunchedEffect(flies.size, soundOn) {
        audio.updateBuzz(flies)
    }

    DisposableEffect(audio) {
        onDispose { audio.release() }
    }

    if (!started) {
        StartScreen(
            coins = coins,
            dieSides = DIE_SIDES[dieIndex],
            secondDie = secondDie,
            secondDieSides = DIE_SIDES[secondDieIndex],
            rangeLevel = rangeLevel,
            totalCaught = totalCaught,
            soundOn = soundOn,
            onToggleSound = { soundOn = !soundOn },
            onPlay = { started = true }
        )
        return
    }

    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFFE9F6DB)) {
        Box(Modifier.fillMaxSize()) {
            Column(Modifier.fillMaxSize()) {
                Header(
                    coins = coins,
                    dieSides = DIE_SIDES[dieIndex],
                    secondDie = secondDie,
                    secondDieSides = DIE_SIDES[secondDieIndex],
                    lastRoll = lastRoll,
                    lastDieOne = lastDieOne,
                    lastDieTwo = lastDieTwo,
                    rangeLevel = rangeLevel,
                    totalCaught = totalCaught,
                    latestEvent = latestEvent,
                    soundOn = soundOn,
                    onToggleSound = { soundOn = !soundOn },
                    onShop = { showShop = true }
                )

                GameBoard(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    flies = flies,
                    rangeLevel = rangeLevel,
                    onFlyGrabbed = { audio.playGrab() },
                    onTongueSnap = { audio.playTongue() },
                    onFlyResolved = { fly ->
                        val index = flies.indexOfFirst { it.id == fly.id }
                        if (index >= 0) flies.removeAt(index)

                        if (fly.type.harmful) {
                            coins = maxOf(0, coins + fly.type.reward)
                            audio.playBeeBad()
                            latestEvent = "Ouch! The frog ate a bee. ${fly.type.reward} coins."
                        } else {
                            val oldCaught = totalCaught
                            totalCaught++
                            coins += fly.type.reward
                            val unlockMessage = newlyUnlockedBugMessage(oldCaught, totalCaught)
                            if (fly.type == BugType.GOLDEN_FLY) audio.playGolden() else audio.playCatch()
                            if (unlockMessage != null) audio.playUnlock()
                            latestEvent = unlockMessage ?: "${fly.type.label} eaten! +${fly.type.reward} coins."
                        }
                    },
                    onFlyMoved = { flyId, newPosition ->
                        val index = flies.indexOfFirst { it.id == flyId }
                        if (index >= 0) flies[index] = flies[index].copy(position = newPosition)
                    }
                )

                RollBar(
                    enabled = flies.isEmpty(),
                    dieSides = DIE_SIDES[dieIndex],
                    secondDie = secondDie,
                    secondDieSides = DIE_SIDES[secondDieIndex],
                    remainingFlies = flies.size,
                    totalCaught = totalCaught,
                    onRoll = {
                        audio.playRoll()
                        val first = Random.nextInt(1, DIE_SIDES[dieIndex] + 1)
                        val second = if (secondDie) Random.nextInt(1, DIE_SIDES[secondDieIndex] + 1) else 0
                        val total = first + second
                        lastDieOne = first
                        lastDieTwo = second
                        lastRoll = total
                        repeat(total) {
                            flies += Fly(
                                id = nextFlyId++,
                                position = Offset.Unspecified,
                                type = randomBugType(totalCaught)
                            )
                        }
                        latestEvent = if (bugTypesUnlocked(totalCaught).contains(BugType.BEE)) {
                            "A new swarm is out. Catch the good bugs and avoid bees!"
                        } else {
                            "A new swarm is out. Drag bugs close to the frog's tongue."
                        }
                    }
                )
            }

            AnimatedVisibility(
                visible = showShop,
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {
                UpgradeShopOverlay(
                    coins = coins,
                    dieIndex = dieIndex,
                    rangeLevel = rangeLevel,
                    secondDie = secondDie,
                    secondDieIndex = secondDieIndex,
                    totalCaught = totalCaught,
                    onClose = { showShop = false },
                    onBuyRange = {
                        if (rangeLevel < RANGE_COSTS.size) {
                            val cost = RANGE_COSTS[rangeLevel]
                            if (coins >= cost) {
                                coins -= cost
                                rangeLevel++
                                audio.playUpgrade()
                            }
                        }
                    },
                    onBuyDie = {
                        if (dieIndex < DIE_SIDES.lastIndex) {
                            val cost = DIE_UPGRADE_COSTS[dieIndex]
                            if (coins >= cost) {
                                coins -= cost
                                dieIndex++
                                audio.playUpgrade()
                            }
                        }
                    },
                    onBuySecondDie = {
                        if (!secondDie && coins >= SECOND_DIE_COST) {
                            coins -= SECOND_DIE_COST
                            secondDie = true
                            secondDieIndex = 0
                            audio.playUpgrade()
                        }
                    },
                    onBuySecondDieUpgrade = {
                        if (secondDie && secondDieIndex < DIE_SIDES.lastIndex) {
                            val cost = DIE_UPGRADE_COSTS[secondDieIndex]
                            if (coins >= cost) {
                                coins -= cost
                                secondDieIndex++
                                audio.playUpgrade()
                            }
                        }
                    }
                )
            }
        }
    }
}

@Composable
private fun StartScreen(
    coins: Int,
    dieSides: Int,
    secondDie: Boolean,
    secondDieSides: Int,
    rangeLevel: Int,
    totalCaught: Int,
    soundOn: Boolean,
    onToggleSound: () -> Unit,
    onPlay: () -> Unit
) {
    Surface(Modifier.fillMaxSize(), color = PondLight) {
        Box(Modifier.fillMaxSize()) {
            Canvas(Modifier.fillMaxSize()) {
                drawRect(PondSky)
                drawCircle(Color.White.copy(alpha = 0.18f), size.width * 0.42f, Offset(size.width * 0.18f, size.height * 0.16f))
                drawCircle(PondDark.copy(alpha = 0.08f), size.width * 0.36f, Offset(size.width * 0.88f, size.height * 0.28f))
                drawOval(Color(0xFF4E9824), Offset(size.width * 0.12f, size.height * 0.57f), Size(size.width * 0.76f, size.height * 0.20f))
                drawOval(Color(0xFF6DBD2E), Offset(size.width * 0.18f, size.height * 0.59f), Size(size.width * 0.64f, size.height * 0.14f))
                drawFrog(Offset(size.width * 0.5f, size.height * 0.55f))
                drawBug(Offset(size.width * 0.20f, size.height * 0.34f), BugType.COMMON_FLY, 1f)
                drawBug(Offset(size.width * 0.78f, size.height * 0.38f), BugType.MOTH, 1f)
                drawBug(Offset(size.width * 0.68f, size.height * 0.24f), BugType.GOLDEN_FLY, 1f)
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 20.dp, vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Surface(
                    color = ShopPaper.copy(alpha = 0.92f),
                    shape = RoundedCornerShape(26.dp),
                    shadowElevation = 6.dp
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 24.dp, vertical = 14.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("FEED", color = FrogDark, fontWeight = FontWeight.Black, fontSize = 46.sp)
                        Text("THE FROG", color = WoodDark, fontWeight = FontWeight.Black, fontSize = 34.sp)
                        Text("ROLL • DRAG • SNAP!", color = Color(0xFF9A6A00), fontWeight = FontWeight.Black, fontSize = 13.sp)
                    }
                }

                Spacer(Modifier.height(10.dp))
                Text(
                    "Drag buzzing bugs close enough for the frog to strike.",
                    color = Ink,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center
                )

                Spacer(Modifier.weight(1f))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = ShopPaper.copy(alpha = 0.96f)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
                ) {
                    Column(Modifier.padding(14.dp)) {
                        Text("YOUR POND", color = WoodDark, fontWeight = FontWeight.Black, fontSize = 13.sp)
                        Spacer(Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(7.dp)
                        ) {
                            ProgressChip("🪙", coins.toString(), "COINS", Modifier.weight(1f))
                            ProgressChip("🎲", if (secondDie) "D$dieSides + D$secondDieSides" else "D$dieSides", "DICE", Modifier.weight(1f))
                            ProgressChip("👅", "Lv ${rangeLevel + 1}", "TONGUE", Modifier.weight(1f))
                            ProgressChip("🐞", totalCaught.toString(), "CAUGHT", Modifier.weight(1f))
                        }
                    }
                }

                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        onClick = onToggleSound,
                        modifier = Modifier.height(54.dp).weight(0.32f),
                        shape = RoundedCornerShape(18.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Wood)
                    ) {
                        Text(if (soundOn) "🔊" else "🔇", fontSize = 20.sp)
                    }
                    Button(
                        onClick = onPlay,
                        modifier = Modifier.height(54.dp).weight(0.68f),
                        shape = RoundedCornerShape(18.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
                    ) {
                        Text("PLAY", fontSize = 20.sp, fontWeight = FontWeight.Black)
                    }
                }
            }
        }
    }
}

@Composable
private fun ProgressChip(icon: String, text: String, label: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        color = Cream,
        shape = RoundedCornerShape(14.dp)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 5.dp, vertical = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(icon, fontSize = 17.sp)
            Text(text, fontWeight = FontWeight.Black, color = WoodDark, fontSize = 12.sp, textAlign = TextAlign.Center)
            Text(label, fontWeight = FontWeight.Bold, color = FrogDark, fontSize = 8.sp)
        }
    }
}

@Composable
private fun Header(
    coins: Int,
    dieSides: Int,
    secondDie: Boolean,
    secondDieSides: Int,
    lastRoll: Int,
    lastDieOne: Int,
    lastDieTwo: Int,
    rangeLevel: Int,
    totalCaught: Int,
    latestEvent: String,
    soundOn: Boolean,
    onToggleSound: () -> Unit,
    onShop: () -> Unit
) {
    Column(Modifier.fillMaxWidth().background(WoodDark)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text("FEED THE FROG", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Black)
                Text(nextUnlockText(totalCaught), color = Cream, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            }
            Button(
                onClick = onToggleSound,
                modifier = Modifier.size(42.dp),
                contentPadding = ButtonDefaults.ContentPadding,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Wood)
            ) {
                Text(if (soundOn) "🔊" else "🔇", fontSize = 15.sp)
            }
            Spacer(Modifier.width(6.dp))
            Button(
                onClick = onShop,
                modifier = Modifier.height(42.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
            ) {
                Text("UPGRADES", fontWeight = FontWeight.Black, fontSize = 11.sp)
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 2.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            HudChip("🪙", coins.toString(), Modifier.weight(1f))
            HudChip("🎲", if (secondDie) "D$dieSides + D$secondDieSides" else "D$dieSides", Modifier.weight(1f))
            HudChip("👅", "${RANGE_REACH_DP[rangeLevel]} dp", Modifier.weight(1f))
            HudChip("🐞", totalCaught.toString(), Modifier.weight(1f))
        }

        val rollText = if (lastRoll > 0) {
            if (secondDie) "Last roll: $lastDieOne + $lastDieTwo = $lastRoll" else "Last roll: $lastDieOne"
        } else "Ready for the first roll"
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(latestEvent, color = Gold, fontSize = 10.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            Text(rollText, color = Cream, fontSize = 9.sp, textAlign = TextAlign.End)
        }
    }
}

@Composable
private fun HudChip(icon: String, value: String, modifier: Modifier = Modifier) {
    Surface(modifier = modifier, color = Wood, shape = RoundedCornerShape(12.dp)) {
        Row(
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(icon, fontSize = 12.sp)
            Spacer(Modifier.width(3.dp))
            Text(value, color = Color.White, fontWeight = FontWeight.Black, fontSize = 10.sp, maxLines = 1)
        }
    }
}

@Composable
private fun GameBoard(
    modifier: Modifier,
    flies: List<Fly>,
    rangeLevel: Int,
    onFlyGrabbed: () -> Unit,
    onTongueSnap: () -> Unit,
    onFlyResolved: (Fly) -> Unit,
    onFlyMoved: (Int, Offset) -> Unit
) {
    val density = LocalDensity.current
    var boardSize by remember { mutableStateOf(IntSize.Zero) }
    var draggingFlyId by remember { mutableStateOf<Int?>(null) }
    var pendingCatchId by remember { mutableStateOf<Int?>(null) }
    var tongueTarget by remember { mutableStateOf(Offset.Zero) }
    val tongueProgress = remember { Animatable(0f) }

    val buzzTransition = rememberInfiniteTransition(label = "buzz")
    val buzzPhase by buzzTransition.animateFloat(
        initialValue = 0f,
        targetValue = (2f * PI).toFloat(),
        animationSpec = infiniteRepeatable(
            animation = tween(720, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "buzzPhase"
    )

    val catchRadiusPx = with(density) { RANGE_REACH_DP[rangeLevel].dp.toPx() }
    val hitRadiusPx = with(density) { 36.dp.toPx() }

    fun mouthPosition(): Offset = Offset(boardSize.width * 0.5f, boardSize.height * 0.70f)

    LaunchedEffect(boardSize, flies.size) {
        if (boardSize == IntSize.Zero) return@LaunchedEffect
        flies.toList().forEach { fly ->
            if (fly.position == Offset.Unspecified) {
                val x = Random.nextFloat() * boardSize.width * 0.76f + boardSize.width * 0.12f
                val y = Random.nextFloat() * boardSize.height * 0.40f + boardSize.height * 0.08f
                onFlyMoved(fly.id, Offset(x, y))
            }
        }
    }

    // Autonomous bug movement. Each species gets its own speed and wandering pattern.
    // Movement pauses while a bug is being dragged or while the tongue is snapping at it.
    LaunchedEffect(boardSize, flies.size, draggingFlyId, pendingCatchId) {
        if (boardSize == IntSize.Zero) return@LaunchedEffect
        var tick = 0f
        while (true) {
            delay(70)
            tick += 0.10f
            flies.toList().forEach { fly ->
                if (fly.position == Offset.Unspecified) return@forEach
                if (fly.id == draggingFlyId || fly.id == pendingCatchId) return@forEach

                val step = fly.type.wanderStep
                val phase = tick * fly.type.speedMultiplier + fly.buzzSeed

                // Fast flies and mosquitoes zig-zag harder. Moths drift in broad, slow arcs.
                val zig = when (fly.type) {
                    BugType.FAST_FLY -> sin(phase * 3.7f) * step * 1.5f
                    BugType.MOSQUITO -> sin(phase * 4.6f) * step
                    BugType.MOTH -> sin(phase * 0.7f) * step * 0.45f
                    else -> sin(phase * 1.5f) * step * 0.65f
                }

                var dx = cos(phase) * step + zig
                var dy = sin(phase * 1.12f) * step

                // Bees fly in straighter, more deliberate sweeps.
                if (fly.type == BugType.BEE) {
                    dx = cos(phase * 0.72f) * step * 1.15f
                    dy = sin(phase * 0.72f) * step * 0.75f
                }

                // Golden flies are quick and slightly evasive.
                if (fly.type == BugType.GOLDEN_FLY) {
                    dx += sin(phase * 2.8f) * 2.6f
                    dy += cos(phase * 2.3f) * 2.1f
                }

                val margin = 26f
                val newX = (fly.position.x + dx).coerceIn(margin, boardSize.width - margin)
                val newY = (fly.position.y + dy).coerceIn(margin, boardSize.height * 0.61f)
                onFlyMoved(fly.id, Offset(newX, newY))
            }
        }
    }

    LaunchedEffect(pendingCatchId) {
        val id = pendingCatchId ?: return@LaunchedEffect
        val fly = flies.firstOrNull { it.id == id } ?: run {
            pendingCatchId = null
            return@LaunchedEffect
        }
        tongueProgress.snapTo(0f)
        tongueProgress.animateTo(1f, tween(115))
        delay(70)
        onFlyResolved(fly)
        tongueProgress.animateTo(0f, tween(150))
        pendingCatchId = null
    }

    Canvas(
        modifier = modifier
            .onSizeChanged { boardSize = it }
            .pointerInput(flies, pendingCatchId, catchRadiusPx) {
                detectDragGestures(
                    onDragStart = { touch ->
                        if (pendingCatchId != null) return@detectDragGestures
                        val grabbedId = flies
                            .filter { it.position != Offset.Unspecified }
                            .minByOrNull { distance(it.position, touch) }
                            ?.takeIf { distance(it.position, touch) <= hitRadiusPx * 1.65f }
                            ?.id
                        draggingFlyId = grabbedId
                        if (grabbedId != null) onFlyGrabbed()
                    },
                    onDrag = { change, dragAmount ->
                        if (pendingCatchId != null) return@detectDragGestures
                        val id = draggingFlyId ?: return@detectDragGestures
                        change.consume()
                        val fly = flies.firstOrNull { it.id == id } ?: return@detectDragGestures
                        val newX = (fly.position.x + dragAmount.x).coerceIn(20f, size.width - 20f)
                        val newY = (fly.position.y + dragAmount.y).coerceIn(20f, size.height - 20f)
                        val newPosition = Offset(newX, newY)
                        onFlyMoved(id, newPosition)

                        if (distance(newPosition, mouthPosition()) <= catchRadiusPx) {
                            tongueTarget = newPosition
                            onTongueSnap()
                            pendingCatchId = id
                            draggingFlyId = null
                        }
                    },
                    onDragCancel = { draggingFlyId = null },
                    onDragEnd = {
                        val id = draggingFlyId
                        draggingFlyId = null
                        if (id != null && pendingCatchId == null) {
                            val fly = flies.firstOrNull { it.id == id }
                            if (fly != null && distance(fly.position, mouthPosition()) <= catchRadiusPx) {
                                tongueTarget = fly.position
                                onTongueSnap()
                                pendingCatchId = id
                            }
                        }
                    }
                )
            }
    ) {
        drawRect(PondLight)
        drawPondBackground()

        val mouth = Offset(size.width * 0.5f, size.height * 0.70f)
        drawCatchRing(mouth, catchRadiusPx, draggingFlyId != null)
        drawFrog(mouth)

        if (pendingCatchId != null) {
            val end = Offset(
                mouth.x + (tongueTarget.x - mouth.x) * tongueProgress.value,
                mouth.y + (tongueTarget.y - mouth.y) * tongueProgress.value
            )
            drawLine(Tongue, mouth, end, strokeWidth = 16f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
            drawCircle(Tongue, radius = 11f, center = end)
        }

        flies.forEach { fly ->
            if (fly.position == Offset.Unspecified || fly.id == pendingCatchId) return@forEach
            val isDragged = fly.id == draggingFlyId
            val phase = buzzPhase * fly.type.speedMultiplier + fly.buzzSeed
            val amp = fly.type.movementAmplitude
            val buzz = if (isDragged) Offset.Zero else Offset(cos(phase) * amp, sin(phase * 1.6f) * (amp * 0.68f))
            val center = fly.position + buzz
            if (!isDragged) {
                val highlightColor = if (fly.type == BugType.GOLDEN_FLY) Gold.copy(alpha = 0.20f) else Color.White.copy(alpha = 0.18f)
                drawCircle(highlightColor, 24f * fly.type.scale, center)
            }
            drawBug(center, fly.type, if (isDragged) 1.2f else 1f)
        }

        if (flies.isEmpty()) {
            val bannerWidth = size.width * 0.68f
            drawRoundRect(
                color = Color.White.copy(alpha = 0.88f),
                topLeft = Offset((size.width - bannerWidth) / 2f, size.height * 0.08f),
                size = Size(bannerWidth, 60f),
                cornerRadius = CornerRadius(20f, 20f)
            )
        }
    }
}

private fun DrawScope.drawPondBackground() {
    drawCircle(PondDark.copy(alpha = 0.12f), radius = size.width * 0.42f, center = Offset(size.width * 0.08f, size.height * 0.24f))
    drawCircle(Color.White.copy(alpha = 0.13f), radius = size.width * 0.31f, center = Offset(size.width * 0.92f, size.height * 0.15f))

    repeat(7) { i ->
        val x = size.width * (0.05f + i * 0.15f)
        val y = size.height * (0.85f + (i % 2) * 0.025f)
        drawLine(FrogDark, Offset(x, y), Offset(x - 8f, y - 58f - i * 2f), 6f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
        drawLine(FrogDark, Offset(x, y), Offset(x + 11f, y - 50f), 5f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
    }

    repeat(3) { i ->
        drawOval(
            color = Color.White.copy(alpha = 0.18f),
            topLeft = Offset(size.width * (0.12f + i * 0.28f), size.height * (0.48f + i * 0.05f)),
            size = Size(size.width * 0.17f, 18f),
            style = Stroke(3f)
        )
    }

    drawOval(Color(0xFF4E9824), Offset(size.width * 0.25f, size.height * 0.72f), Size(size.width * 0.50f, size.height * 0.19f))
    drawOval(Color(0xFF6DBD2E), Offset(size.width * 0.29f, size.height * 0.735f), Size(size.width * 0.42f, size.height * 0.15f))
}

private fun DrawScope.drawCatchRing(center: Offset, radius: Float, active: Boolean) {
    if (!active) return
    drawCircle(color = Gold.copy(alpha = 0.18f), radius = radius, center = center)
    drawCircle(color = Gold.copy(alpha = 0.88f), radius = radius, center = center, style = Stroke(width = 5f))
}

private fun DrawScope.drawFrog(mouth: Offset) {
    val cx = mouth.x
    val cy = mouth.y
    val bodyY = cy + 55f

    drawOval(FrogDark, Offset(cx - 120f, bodyY - 25f), Size(80f, 100f))
    drawOval(FrogDark, Offset(cx + 40f, bodyY - 25f), Size(80f, 100f))
    drawOval(FrogGreen, Offset(cx - 92f, bodyY - 35f), Size(184f, 135f))
    drawOval(Cream, Offset(cx - 50f, bodyY + 5f), Size(100f, 72f))

    drawCircle(FrogGreen, 83f, Offset(cx, cy - 38f))
    drawCircle(FrogLight, 38f, Offset(cx - 52f, cy - 96f))
    drawCircle(FrogLight, 38f, Offset(cx + 52f, cy - 96f))
    drawCircle(Color.White, 28f, Offset(cx - 52f, cy - 98f))
    drawCircle(Color.White, 28f, Offset(cx + 52f, cy - 98f))
    drawCircle(Ink, 13f, Offset(cx - 48f, cy - 96f))
    drawCircle(Ink, 13f, Offset(cx + 48f, cy - 96f))
    drawCircle(Color.White, 4f, Offset(cx - 43f, cy - 101f))
    drawCircle(Color.White, 4f, Offset(cx + 53f, cy - 101f))

    drawOval(Color(0xFF6D2726), Offset(cx - 49f, cy - 7f), Size(98f, 39f))
    drawOval(Tongue, Offset(cx - 22f, cy + 8f), Size(44f, 18f))
    drawCircle(FrogDark, 4f, Offset(cx - 18f, cy - 50f))
    drawCircle(FrogDark, 4f, Offset(cx + 18f, cy - 50f))
}

private fun DrawScope.drawBug(center: Offset, type: BugType, boostScale: Float) {
    when (type) {
        BugType.COMMON_FLY -> drawStandardFly(center, 1.0f * boostScale, bodyColor = Color(0xFF48504B), headColor = Color(0xFF202520), wingColor = Color.White.copy(alpha = 0.82f))
        BugType.FAST_FLY -> {
            drawStandardFly(center, 0.92f * boostScale, bodyColor = Color(0xFF4A5870), headColor = Color(0xFF212A35), wingColor = SkyWing.copy(alpha = 0.9f))
            drawLine(Color.White.copy(alpha = 0.45f), Offset(center.x - 24f, center.y - 6f), Offset(center.x - 38f, center.y - 10f), 3f)
            drawLine(Color.White.copy(alpha = 0.35f), Offset(center.x - 24f, center.y + 4f), Offset(center.x - 40f, center.y + 8f), 2f)
        }
        BugType.MOSQUITO -> {
            val scale = 0.8f * boostScale
            drawOval(Color.White.copy(alpha = 0.78f), Offset(center.x - 18f * scale, center.y - 15f * scale), Size(18f * scale, 9f * scale))
            drawOval(Color.White.copy(alpha = 0.78f), Offset(center.x - 2f * scale, center.y - 15f * scale), Size(18f * scale, 9f * scale))
            drawOval(Color(0xFF4D4A56), Offset(center.x - 15f * scale, center.y - 4f * scale), Size(23f * scale, 8f * scale))
            drawCircle(Color(0xFF22222A), 7f * scale, Offset(center.x + 10f * scale, center.y))
            drawLine(Color.Black, Offset(center.x + 16f * scale, center.y - 1f * scale), Offset(center.x + 28f * scale, center.y - 4f * scale), 2f)
            repeat(3) { i ->
                val x = center.x - 8f * scale + i * 6f * scale
                drawLine(Color.Black, Offset(x, center.y + 2f * scale), Offset(x - 6f * scale, center.y + 13f * scale), 1.5f)
            }
        }
        BugType.MOTH -> {
            val scale = 1.12f * boostScale
            drawOval(Color(0xFF5A4938), Offset(center.x - 8f * scale, center.y - 10f * scale), Size(16f * scale, 26f * scale))
            rotate(-18f, pivot = center) {
                drawOval(MothTan.copy(alpha = 0.95f), Offset(center.x - 42f * scale, center.y - 20f * scale), Size(40f * scale, 26f * scale))
            }
            rotate(18f, pivot = center) {
                drawOval(MothTan.copy(alpha = 0.95f), Offset(center.x + 2f * scale, center.y - 20f * scale), Size(40f * scale, 26f * scale))
            }
            drawCircle(Color(0xFF8F7961), 5f * scale, Offset(center.x - 18f * scale, center.y - 8f * scale))
            drawCircle(Color(0xFF8F7961), 5f * scale, Offset(center.x + 18f * scale, center.y - 8f * scale))
        }
        BugType.BEE -> {
            val scale = 0.95f * boostScale
            drawOval(Color.White.copy(alpha = 0.78f), Offset(center.x - 17f * scale, center.y - 19f * scale), Size(21f * scale, 12f * scale))
            drawOval(Color.White.copy(alpha = 0.78f), Offset(center.x + 0f * scale, center.y - 19f * scale), Size(21f * scale, 12f * scale))
            drawOval(BeeYellow, Offset(center.x - 18f * scale, center.y - 7f * scale), Size(34f * scale, 18f * scale))
            drawLine(Color.Black, Offset(center.x - 9f * scale, center.y - 6f * scale), Offset(center.x - 9f * scale, center.y + 10f * scale), 3f)
            drawLine(Color.Black, Offset(center.x, center.y - 6f * scale), Offset(center.x, center.y + 10f * scale), 3f)
            drawLine(Color.Black, Offset(center.x + 9f * scale, center.y - 6f * scale), Offset(center.x + 9f * scale, center.y + 10f * scale), 3f)
            drawCircle(Color.Black, 8f * scale, Offset(center.x + 16f * scale, center.y + 1f * scale))
            drawLine(Color.Black, Offset(center.x - 18f * scale, center.y + 2f * scale), Offset(center.x - 28f * scale, center.y + 0f * scale), 2f)
            drawLine(Color.Black, Offset(center.x - 18f * scale, center.y + 2f * scale), Offset(center.x - 28f * scale, center.y + 5f * scale), 2f)
        }
        BugType.GOLDEN_FLY -> {
            drawStandardFly(center, 1.05f * boostScale, bodyColor = Color(0xFFC38C00), headColor = Color(0xFF8F6700), wingColor = Color(0xFFFFF3BC))
            drawCircle(Gold.copy(alpha = 0.9f), 3.8f * boostScale, Offset(center.x - 20f, center.y - 20f))
            drawCircle(Gold.copy(alpha = 0.7f), 2.8f * boostScale, Offset(center.x + 22f, center.y - 16f))
        }
    }
}

private fun DrawScope.drawStandardFly(center: Offset, scale: Float, bodyColor: Color, headColor: Color, wingColor: Color) {
    val bodyR = 12f * scale
    val wingW = 23f * scale
    val wingH = 13f * scale

    drawOval(wingColor, Offset(center.x - 20f * scale, center.y - 18f * scale), Size(wingW, wingH))
    drawOval(wingColor, Offset(center.x + 1f * scale, center.y - 18f * scale), Size(wingW, wingH))
    drawOval(bodyColor, Offset(center.x - 16f * scale, center.y - 7f * scale), Size(32f * scale, 17f * scale))
    drawCircle(headColor, bodyR, center = Offset(center.x + 11f * scale, center.y))
    drawCircle(Color.White, 6f * scale, Offset(center.x + 15f * scale, center.y - 5f * scale))
    drawCircle(Color.Black, 3f * scale, Offset(center.x + 17f * scale, center.y - 5f * scale))

    repeat(3) { i ->
        val x = center.x - 8f * scale + i * 8f * scale
        drawLine(Color.Black, Offset(x, center.y + 5f * scale), Offset(x - 7f * scale, center.y + 15f * scale), 2.2f * scale)
    }
}

@Composable
private fun RollBar(
    enabled: Boolean,
    dieSides: Int,
    secondDie: Boolean,
    secondDieSides: Int,
    remainingFlies: Int,
    totalCaught: Int,
    onRoll: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFFF1F7E6),
        shadowElevation = 8.dp
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    DiceBadge("D$dieSides")
                    if (secondDie) DiceBadge("D$secondDieSides")
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        if (enabled) "Ready to roll" else "Feed the whole swarm",
                        fontWeight = FontWeight.Black,
                        color = Ink,
                        fontSize = 14.sp
                    )
                    val helper = if (enabled) {
                        if (bugTypesUnlocked(totalCaught).contains(BugType.BEE)) "Good bugs earn coins • avoid bees" else "Roll to release the next swarm"
                    } else {
                        "$remainingFlies ${if (remainingFlies == 1) "bug" else "bugs"} remaining"
                    }
                    Text(helper, fontSize = 10.sp, color = FrogDark, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(Modifier.height(8.dp))
            Button(
                onClick = onRoll,
                enabled = enabled,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = FrogDark,
                    disabledContainerColor = Color(0xFF9CAD88)
                )
            ) {
                Text(
                    if (enabled) {
                        if (secondDie) "ROLL D$dieSides + D$secondDieSides" else "ROLL D$dieSides"
                    } else "FEED $remainingFlies MORE",
                    fontWeight = FontWeight.Black,
                    fontSize = 15.sp
                )
            }
        }
    }
}

@Composable
private fun DiceBadge(label: String) {
    Surface(
        modifier = Modifier.size(42.dp),
        shape = RoundedCornerShape(13.dp),
        color = Cream,
        shadowElevation = 2.dp
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(label, color = WoodDark, fontWeight = FontWeight.Black, fontSize = 13.sp)
        }
    }
}

@Composable
private fun UpgradeShopOverlay(
    coins: Int,
    dieIndex: Int,
    rangeLevel: Int,
    secondDie: Boolean,
    secondDieIndex: Int,
    totalCaught: Int,
    onClose: () -> Unit,
    onBuyRange: () -> Unit,
    onBuyDie: () -> Unit,
    onBuySecondDie: () -> Unit,
    onBuySecondDieUpgrade: () -> Unit
) {
    val scroll = rememberScrollState()
    Surface(
        modifier = Modifier.fillMaxWidth().fillMaxHeight(0.90f),
        color = ShopPaper,
        shadowElevation = 20.dp,
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
    ) {
        Column(Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier.fillMaxWidth().background(WoodDark).padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text("FROG SHOP", fontWeight = FontWeight.Black, color = Color.White, fontSize = 21.sp)
                    Text("Spend coins to improve each upgrade track.", color = Cream, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                }
                Surface(color = Gold, shape = RoundedCornerShape(14.dp)) {
                    Text("🪙 $coins", modifier = Modifier.padding(horizontal = 10.dp, vertical = 7.dp), color = WoodDark, fontWeight = FontWeight.Black, fontSize = 13.sp)
                }
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = onClose,
                    modifier = Modifier.height(40.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Wood)
                ) {
                    Text("DONE", fontWeight = FontWeight.Black, fontSize = 10.sp)
                }
            }

            Column(
                modifier = Modifier.fillMaxSize().verticalScroll(scroll).padding(horizontal = 12.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                ShopSectionTitle("UPGRADES", "Each track advances independently.")

                val rangeMaxed = rangeLevel >= RANGE_COSTS.size
                UpgradeRowCard(
                    icon = "👅",
                    title = "Tongue Distance",
                    levelText = "Level ${rangeLevel + 1} / ${RANGE_REACH_DP.size}",
                    currentText = "${RANGE_REACH_DP[rangeLevel]} dp reach",
                    nextText = if (rangeMaxed) "Maximum reach" else "Next: ${RANGE_REACH_DP[rangeLevel + 1]} dp",
                    progress = rangeLevel.toFloat() / RANGE_COSTS.size.toFloat(),
                    cost = if (rangeMaxed) null else RANGE_COSTS[rangeLevel],
                    affordable = !rangeMaxed && coins >= RANGE_COSTS[rangeLevel],
                    buttonText = if (rangeMaxed) "MAXED" else "EXTEND",
                    onClick = onBuyRange
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex
                UpgradeRowCard(
                    icon = "🎲",
                    title = "Die #1",
                    levelText = "Stage ${dieIndex + 1} / ${DIE_SIDES.size}",
                    currentText = "Current: D${DIE_SIDES[dieIndex]}",
                    nextText = if (dieMaxed) "Maximum die" else "Next: D${DIE_SIDES[dieIndex + 1]}",
                    progress = dieIndex.toFloat() / DIE_SIDES.lastIndex.toFloat(),
                    cost = if (dieMaxed) null else DIE_UPGRADE_COSTS[dieIndex],
                    affordable = !dieMaxed && coins >= DIE_UPGRADE_COSTS[dieIndex],
                    buttonText = if (dieMaxed) "MAXED" else "UPGRADE",
                    onClick = onBuyDie
                )

                if (!secondDie) {
                    UpgradeRowCard(
                        icon = "🎲+",
                        title = "Second Die",
                        levelText = "Locked premium track",
                        currentText = "Adds a separate D3",
                        nextText = "Then upgrade D3 → D4 → D6 → D8 → D12 → D20",
                        progress = 0f,
                        cost = SECOND_DIE_COST,
                        affordable = coins >= SECOND_DIE_COST,
                        buttonText = "UNLOCK D3",
                        onClick = onBuySecondDie
                    )
                } else {
                    val secondMaxed = secondDieIndex >= DIE_SIDES.lastIndex
                    UpgradeRowCard(
                        icon = "🎲²",
                        title = "Die #2",
                        levelText = "Stage ${secondDieIndex + 1} / ${DIE_SIDES.size}",
                        currentText = "Current: D${DIE_SIDES[secondDieIndex]}",
                        nextText = if (secondMaxed) "Maximum die" else "Next: D${DIE_SIDES[secondDieIndex + 1]}",
                        progress = secondDieIndex.toFloat() / DIE_SIDES.lastIndex.toFloat(),
                        cost = if (secondMaxed) null else DIE_UPGRADE_COSTS[secondDieIndex],
                        affordable = !secondMaxed && coins >= DIE_UPGRADE_COSTS[secondDieIndex],
                        buttonText = if (secondMaxed) "MAXED" else "UPGRADE",
                        onClick = onBuySecondDieUpgrade
                    )
                }

                Spacer(Modifier.height(4.dp))
                ShopSectionTitle("BUG GUIDE", "Unlocked by total successful catches.")
                BugGuideSection(totalCaught)
                Spacer(Modifier.height(14.dp))
            }
        }
    }
}

@Composable
private fun ShopSectionTitle(title: String, subtitle: String) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 2.dp, vertical = 2.dp)) {
        Text(title, color = WoodDark, fontWeight = FontWeight.Black, fontSize = 14.sp)
        Text(subtitle, color = FrogDark, fontWeight = FontWeight.Bold, fontSize = 10.sp)
    }
}

@Composable
private fun UpgradeRowCard(
    icon: String,
    title: String,
    levelText: String,
    currentText: String,
    nextText: String,
    progress: Float,
    cost: Int?,
    affordable: Boolean,
    buttonText: String,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF4)),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(color = Cream, shape = RoundedCornerShape(14.dp)) {
                    Text(icon, modifier = Modifier.padding(10.dp), fontSize = 23.sp)
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(title, fontWeight = FontWeight.Black, color = WoodDark, fontSize = 16.sp)
                    Text(levelText, fontWeight = FontWeight.Bold, color = FrogDark, fontSize = 10.sp)
                }
                if (cost == null) {
                    Surface(color = Color(0xFFDCEFC8), shape = RoundedCornerShape(12.dp)) {
                        Text("MAX", modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp), color = FrogDark, fontWeight = FontWeight.Black, fontSize = 10.sp)
                    }
                } else {
                    Text("🪙 $cost", color = Color(0xFF9A6A00), fontWeight = FontWeight.Black, fontSize = 13.sp)
                }
            }

            Spacer(Modifier.height(9.dp))
            Text(currentText, color = Ink, fontWeight = FontWeight.Black, fontSize = 12.sp)
            Text(nextText, color = FrogDark, fontWeight = FontWeight.Bold, fontSize = 10.sp)
            Spacer(Modifier.height(8.dp))
            ProgressTrack(progress)
            Spacer(Modifier.height(10.dp))
            Button(
                onClick = onClick,
                enabled = affordable,
                modifier = Modifier.fillMaxWidth().height(42.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = FrogDark,
                    disabledContainerColor = if (cost == null) Color(0xFF9CAD88) else Color(0xFFD0C6A9),
                    disabledContentColor = if (cost == null) Color.White else WoodDark
                )
            ) {
                Text(
                    if (!affordable && cost != null) "NEED 🪙 $cost" else buttonText,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Black
                )
            }
        }
    }
}

@Composable
private fun ProgressTrack(progress: Float) {
    Box(
        Modifier.fillMaxWidth().height(8.dp).background(Color(0xFFE8DEC3), RoundedCornerShape(8.dp))
    ) {
        Box(
            Modifier.fillMaxWidth(progress.coerceIn(0f, 1f)).height(8.dp).background(FrogGreen, RoundedCornerShape(8.dp))
        )
    }
}

@Composable
private fun BugGuideSection(totalCaught: Int) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF4)),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            bugGuideRows().forEach { row ->
                val unlocked = totalCaught >= row.type.unlockAtCaught
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        modifier = Modifier.size(34.dp),
                        color = if (unlocked) Color(0xFFDCEFC8) else Color(0xFFE9E5D8),
                        shape = CircleShape
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(if (unlocked) "✓" else "?", color = if (unlocked) FrogDark else Wood, fontWeight = FontWeight.Black)
                        }
                    }
                    Spacer(Modifier.width(9.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            if (unlocked) row.type.label else "Locked bug",
                            color = if (unlocked) Ink else Ink.copy(alpha = 0.55f),
                            fontWeight = FontWeight.Black,
                            fontSize = 12.sp
                        )
                        Text(
                            if (unlocked) row.type.guideName else "Unlock at ${row.type.unlockAtCaught} catches",
                            color = if (unlocked && row.type.harmful) Color(0xFF9A5C00) else FrogDark.copy(alpha = if (unlocked) 1f else 0.6f),
                            fontWeight = FontWeight.Bold,
                            fontSize = 10.sp
                        )
                    }
                    if (unlocked) {
                        Text(
                            if (row.type.reward > 0) "+${row.type.reward}" else row.type.reward.toString(),
                            color = if (row.type.harmful) Color(0xFF9A3C22) else Color(0xFF4F7F1A),
                            fontWeight = FontWeight.Black,
                            fontSize = 12.sp
                        )
                    }
                }
            }
        }
    }
}

private data class BugGuideRow(val type: BugType)

private fun bugGuideRows(): List<BugGuideRow> = listOf(
    BugGuideRow(BugType.COMMON_FLY),
    BugGuideRow(BugType.MOSQUITO),
    BugGuideRow(BugType.FAST_FLY),
    BugGuideRow(BugType.MOTH),
    BugGuideRow(BugType.BEE),
    BugGuideRow(BugType.GOLDEN_FLY)
)

private fun bugTypesUnlocked(totalCaught: Int): List<BugType> = BugType.entries.filter { totalCaught >= it.unlockAtCaught }

private fun nextUnlockText(totalCaught: Int): String {
    val next = BugType.entries.firstOrNull { totalCaught < it.unlockAtCaught }
    return if (next == null) {
        "all bug types unlocked"
    } else {
        "next: ${next.label} at ${next.unlockAtCaught}"
    }
}

private fun newlyUnlockedBugMessage(oldCaught: Int, newCaught: Int): String? {
    val unlocked = BugType.entries.firstOrNull { oldCaught < it.unlockAtCaught && newCaught >= it.unlockAtCaught }
    return unlocked?.let { "New bug unlocked: ${it.label}!" }
}

private fun randomBugType(totalCaught: Int): BugType {
    val roll = Random.nextInt(100)
    return when {
        totalCaught < 8 -> BugType.COMMON_FLY
        totalCaught < 18 -> if (roll < 70) BugType.COMMON_FLY else BugType.MOSQUITO
        totalCaught < 35 -> when {
            roll < 48 -> BugType.COMMON_FLY
            roll < 72 -> BugType.MOSQUITO
            else -> BugType.FAST_FLY
        }
        totalCaught < 55 -> when {
            roll < 38 -> BugType.COMMON_FLY
            roll < 56 -> BugType.MOSQUITO
            roll < 80 -> BugType.FAST_FLY
            else -> BugType.MOTH
        }
        totalCaught < 80 -> when {
            roll < 32 -> BugType.COMMON_FLY
            roll < 47 -> BugType.MOSQUITO
            roll < 69 -> BugType.FAST_FLY
            roll < 87 -> BugType.MOTH
            else -> BugType.BEE
        }
        else -> when {
            roll < 28 -> BugType.COMMON_FLY
            roll < 42 -> BugType.MOSQUITO
            roll < 62 -> BugType.FAST_FLY
            roll < 78 -> BugType.MOTH
            roll < 90 -> BugType.BEE
            else -> BugType.GOLDEN_FLY
        }
    }
}

private fun distance(a: Offset, b: Offset): Float {
    val dx = a.x - b.x
    val dy = a.y - b.y
    return sqrt(dx * dx + dy * dy)
}
