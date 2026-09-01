from pathlib import Path

root = Path('extracted/FeedTheFrog')
main = root / 'app/src/main/java/com/feedthefrog/game/MainActivity.kt'
build = root / 'app/build.gradle.kts'

text = main.read_text()
start_marker = '@Composable\nprivate fun Header('
end_marker = '@Composable\nprivate fun HudChip('
start = text.index(start_marker)
end = text.index(end_marker, start)

new_header = r'''@Composable
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
    onShop: () -> Unit,
    onCoinShop: () -> Unit
) {
    Column(Modifier.fillMaxWidth().background(WoodDark).statusBarsPadding()) {
        Row(
            modifier = Modifier.fillMaxWidth().height(44.dp).padding(horizontal = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Button(
                onClick = onCoinShop,
                modifier = Modifier.width(64.dp).height(30.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                shape = RoundedCornerShape(9.dp),
                colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
            ) {
                Text("+ COINS", color = Color.White, fontWeight = FontWeight.Black, fontSize = 8.sp, maxLines = 1)
            }
            Column(Modifier.weight(1f)) {
                Text("FEED THE FROG", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Black, maxLines = 1, softWrap = false)
                Text(nextUnlockText(totalCaught), color = Cream, fontSize = 7.sp, fontWeight = FontWeight.Bold, maxLines = 1, softWrap = false)
            }
            Button(
                onClick = onToggleSound,
                modifier = Modifier.size(30.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Wood)
            ) { Text(if (soundOn) "🔊" else "🔇", fontSize = 12.sp) }
            Button(
                onClick = onShop,
                modifier = Modifier.width(72.dp).height(36.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent)
            ) {
                Image(painter = painterResource(R.drawable.ftf_upgrades), contentDescription = "Upgrades", modifier = Modifier.width(70.dp).height(34.dp))
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 1.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            HudChip("🪙", coins.toString(), Modifier.weight(1f))
            HudChip("🎲", if (secondDie) "D$dieSides+D$secondDieSides" else "D$dieSides", Modifier.weight(1f))
            HudChip("👅", "${RANGE_REACH_DP[rangeLevel]}dp", Modifier.weight(1f))
            HudChip("🐞", totalCaught.toString(), Modifier.weight(1f))
        }
        val rollText = if (lastRoll > 0) {
            if (secondDie) "$lastDieOne+$lastDieTwo=$lastRoll" else "Roll $lastDieOne"
        } else "Ready to roll"
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(latestEvent, color = Gold, fontSize = 8.sp, fontWeight = FontWeight.Bold, maxLines = 1, softWrap = false, modifier = Modifier.weight(1f))
            Spacer(Modifier.width(5.dp))
            Text(rollText, color = Cream, fontSize = 8.sp, textAlign = TextAlign.End, maxLines = 1, softWrap = false)
        }
    }
}
'''

text = text[:start] + new_header + '\n' + text[end:]

old_chip = '''@Composable
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
'''
new_chip = '''@Composable
private fun HudChip(icon: String, value: String, modifier: Modifier = Modifier) {
    Surface(modifier = modifier, color = Wood, shape = RoundedCornerShape(10.dp)) {
        Row(
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 3.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(icon, fontSize = 10.sp)
            Spacer(Modifier.width(2.dp))
            Text(value, color = Color.White, fontWeight = FontWeight.Black, fontSize = 9.sp, maxLines = 1)
        }
    }
}
'''
if old_chip not in text:
    raise SystemExit('Expected v0.9.4 HudChip block not found')
text = text.replace(old_chip, new_chip, 1)
main.write_text(text)

b = build.read_text()
if 'versionCode = 23' not in b or 'versionName = "0.9.4-tv-menu-pages"' not in b:
    raise SystemExit('Expected v0.9.4 version markers not found')
b = b.replace('versionCode = 23', 'versionCode = 24', 1)
b = b.replace('versionName = "0.9.4-tv-menu-pages"', 'versionName = "0.9.5-compact-hud"', 1)
build.write_text(b)

checks = {
    'compact header height': 'Modifier.fillMaxWidth().height(44.dp)',
    'coin shop preserved': 'onClick = onCoinShop',
    'sound control preserved': 'onClick = onToggleSound',
    'upgrades preserved': 'onClick = onShop',
    'TV picker preserved': 'TvPickerArtOverlay(',
    'advertiser preserved': 'VISIT ADVERTISER',
    'subscription preserved': 'SUBSCRIPTION SERVICE',
    'ladybug preserved': 'BugType.LADYBUG',
    'June Bug preserved': 'BugType.JUNE_BUG',
    'Lightning Bug preserved': 'BugType.LIGHTNING_BUG',
    'Bee -20 preserved': 'BEE_PENALTY = -20',
    'Lightning -25 preserved': 'LIGHTNING_BUG_PENALTY = -25',
}
final = main.read_text()
for name, marker in checks.items():
    if marker not in final:
        raise SystemExit(f'Missing preservation marker: {name}: {marker}')
print('patched v0.9.5 compact HUD; gameplay/TV/shop systems preserved')
