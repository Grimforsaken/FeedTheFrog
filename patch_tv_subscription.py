#!/usr/bin/env python3
from pathlib import Path
import base64
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_tv_subscription.py <MainActivity.kt> <project_dir>")

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"tv patch failed: {label}")
    text = text.replace(old, new, 1)

# Android/Compose imports for the TV/video layer.
replace_once(
    "import android.media.SoundPool",
    "import android.media.SoundPool\nimport android.net.Uri\nimport android.widget.VideoView",
    "android video imports",
)
replace_once(
    "import androidx.compose.foundation.layout.Box",
    "import androidx.compose.foundation.layout.Box\nimport androidx.compose.foundation.layout.BoxWithConstraints",
    "BoxWithConstraints import",
)
replace_once(
    "import androidx.compose.foundation.layout.padding",
    "import androidx.compose.foundation.layout.padding\nimport androidx.compose.foundation.layout.offset",
    "offset import",
)
replace_once(
    "import androidx.compose.ui.layout.onSizeChanged",
    "import androidx.compose.ui.layout.onSizeChanged\nimport androidx.compose.ui.layout.ContentScale",
    "ContentScale import",
)
replace_once(
    "import androidx.compose.ui.unit.sp",
    "import androidx.compose.ui.unit.sp\nimport androidx.compose.ui.viewinterop.AndroidView",
    "AndroidView import",
)

replace_once(
    "private const val POISON_MINIMUM_LOSS = 25",
    "private const val POISON_MINIMUM_LOSS = 25\nprivate const val TV_MODE_COMMERCIAL = 0\nprivate const val TV_MODE_POND_LIFE = 1",
    "TV constants",
)

# Persist subscription state and selected TV content.
replace_once(
    '    var showShop by remember { mutableStateOf(false) }',
    '    var showShop by remember { mutableStateOf(false) }\n'
    '    var subscriptionPurchased by remember { mutableStateOf(prefs.getBoolean("subscriptionPurchased", false)) }\n'
    '    var tvMode by remember { mutableIntStateOf(prefs.getInt("tvMode", TV_MODE_COMMERCIAL).coerceIn(TV_MODE_COMMERCIAL, TV_MODE_POND_LIFE)) }',
    "TV state",
)
replace_once(
    "LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, secondDie, secondDieIndex, totalCaught, soundOn)",
    "LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)",
    "save effect key",
)
replace_once(
    '            .putBoolean("soundOn", soundOn)',
    '            .putBoolean("soundOn", soundOn)\n'
    '            .putBoolean("subscriptionPurchased", subscriptionPurchased)\n'
    '            .putInt("tvMode", tvMode)',
    "save TV prefs",
)

# Add TV state/callbacks to the GameBoard call.
replace_once(
    "                    catchCapacity = capacityLevel + 1,\n                    onTongueSnap = { audio.playTongue() },",
    "                    catchCapacity = capacityLevel + 1,\n"
    "                    subscriptionPurchased = subscriptionPurchased,\n"
    "                    tvMode = tvMode,\n"
    "                    onAdvertiser = { latestEvent = \"Advertiser link will activate when a campaign is loaded.\" },\n"
    "                    onPurchaseSubscription = {\n"
    "                        subscriptionPurchased = true\n"
    "                        tvMode = TV_MODE_POND_LIFE\n"
    "                        latestEvent = \"Subscription service unlocked for testing. Pond Life is now playing.\"\n"
    "                    },\n"
    "                    onSelectTvMode = { tvMode = it },\n"
    "                    onTongueSnap = { audio.playTongue() },",
    "GameBoard TV arguments",
)

# Transform the patched GameBoard into a layered TV + video + transparent gameplay canvas.
start = text.find("@Composable\nprivate fun GameBoard(")
end = text.find("\nprivate fun DrawScope.drawPondBackground()", start)
if start < 0 or end < 0:
    raise SystemExit("tv patch failed: GameBoard block")
board = text[start:end]

old_sig = "    catchCapacity: Int,\n    onTongueSnap: () -> Unit,"
new_sig = (
    "    catchCapacity: Int,\n"
    "    subscriptionPurchased: Boolean,\n"
    "    tvMode: Int,\n"
    "    onAdvertiser: () -> Unit,\n"
    "    onPurchaseSubscription: () -> Unit,\n"
    "    onSelectTvMode: (Int) -> Unit,\n"
    "    onTongueSnap: () -> Unit,"
)
if old_sig not in board:
    raise SystemExit("tv patch failed: GameBoard signature")
board = board.replace(old_sig, new_sig, 1)

canvas_marker = "    Canvas(\n        modifier = modifier\n            .onSizeChanged { boardSize = it }"
if canvas_marker not in board:
    raise SystemExit("tv patch failed: canvas marker")
layer_prefix = '''    Box(modifier = modifier) {
        Image(
            painter = painterResource(R.drawable.ftf_tv_background),
            contentDescription = "Retro television",
            contentScale = ContentScale.FillBounds,
            modifier = Modifier.fillMaxSize()
        )

        TvScreenLayer(
            subscriptionPurchased = subscriptionPurchased,
            tvMode = tvMode,
            modifier = Modifier.fillMaxSize()
        )

        Canvas(
        modifier = Modifier.fillMaxSize()
            .onSizeChanged { boardSize = it }'''
board = board.replace(canvas_marker, layer_prefix, 1)

# The TV/video is now the background; keep only gameplay drawings on the canvas.
board = board.replace("        drawRect(PondLight)\n        drawPondBackground()\n\n", "", 1)

# Remove the old empty white banner so it cannot cover the television picture.
board = re.sub(
    r'\n        if \(flies\.isEmpty\(\)\) \{\n            val bannerWidth.*?\n        \}\n',
    '\n',
    board,
    count=1,
    flags=re.S,
)

# Add the protected advertiser/subscription controls inside the TV-frame area.
controls = r'''

        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(start = 6.dp, top = 6.dp),
            horizontalAlignment = Alignment.Start
        ) {
            Button(
                onClick = onAdvertiser,
                modifier = Modifier.height(32.dp),
                contentPadding = ButtonDefaults.ContentPadding,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = WoodDark.copy(alpha = 0.92f))
            ) {
                Text("ADVERTISER", color = Gold, fontWeight = FontWeight.Black, fontSize = 9.sp)
            }
            Spacer(Modifier.height(4.dp))
            Button(
                onClick = {
                    if (!subscriptionPurchased) {
                        onPurchaseSubscription()
                    } else {
                        onSelectTvMode(if (tvMode == TV_MODE_COMMERCIAL) TV_MODE_POND_LIFE else TV_MODE_COMMERCIAL)
                    }
                },
                modifier = Modifier.height(34.dp),
                contentPadding = ButtonDefaults.ContentPadding,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = FrogDark.copy(alpha = 0.94f))
            ) {
                Text(
                    if (!subscriptionPurchased) "SUBSCRIPTION SERVICE"
                    else if (tvMode == TV_MODE_POND_LIFE) "TV: POND LIFE • 1/3"
                    else "TV: COMMERCIAL BREAK",
                    color = Color.White,
                    fontWeight = FontWeight.Black,
                    fontSize = 8.sp
                )
            }
        }
    }'''

final_close = board.rfind("\n}")
if final_close < 0:
    raise SystemExit("tv patch failed: GameBoard closing brace")
board = board[:final_close] + controls + board[final_close:]

text = text[:start] + board + text[end:]

# Video content is positioned over the dark CRT glass region in the selected background art.
tv_layer = r'''

@Composable
private fun TvScreenLayer(
    subscriptionPurchased: Boolean,
    tvMode: Int,
    modifier: Modifier = Modifier
) {
    BoxWithConstraints(modifier) {
        val screenLeft = maxWidth * 0.083f
        val screenTop = maxHeight * 0.221f
        val screenWidth = maxWidth * 0.690f
        val screenHeight = maxHeight * 0.333f
        val screenModifier = Modifier
            .offset(x = screenLeft, y = screenTop)
            .size(width = screenWidth, height = screenHeight)

        if (subscriptionPurchased && tvMode == TV_MODE_POND_LIFE) {
            AndroidView(
                factory = { context ->
                    VideoView(context).apply {
                        setVideoURI(Uri.parse("android.resource://${context.packageName}/${R.raw.subscription_pond}"))
                        setOnPreparedListener { player ->
                            player.isLooping = true
                            player.setVolume(0f, 0f)
                            start()
                        }
                    }
                },
                update = { view -> if (!view.isPlaying) view.start() },
                modifier = screenModifier
            )
        } else {
            Surface(modifier = screenModifier, color = Color(0xFF101010)) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        "COMMERCIAL BREAK",
                        color = Gold,
                        fontWeight = FontWeight.Black,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}
'''
insert_at = text.find("\nprivate fun DrawScope.drawPondBackground()", start)
text = text[:insert_at] + tv_layer + text[insert_at:]

# Decode game assets stored as text in the repository.
drawable_dir = project_dir / "app" / "src" / "main" / "res" / "drawable-nodpi"
raw_dir = project_dir / "app" / "src" / "main" / "res" / "raw"
drawable_dir.mkdir(parents=True, exist_ok=True)
raw_dir.mkdir(parents=True, exist_ok=True)

tv_src = repo_root / "tv_assets" / "ftf_tv_background.b64"
if not tv_src.exists():
    raise SystemExit("missing TV background asset")
(drawable_dir / "ftf_tv_background.webp").write_bytes(base64.b64decode(tv_src.read_text().strip()))

video_src = repo_root / "tv_assets" / "pond_video_01.b64"
if not video_src.exists():
    raise SystemExit("missing Pond Life video asset")
(raw_dir / "subscription_pond.webm").write_bytes(base64.b64decode(video_src.read_text().strip()))


main_file.write_text(text)
print("added retro TV background, Commercial Break mode, subscription selector, and Pond Life video 1/3")
