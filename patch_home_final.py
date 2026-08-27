#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_home_final.py <MainActivity.kt>')

main_file = Path(sys.argv[1])
text = main_file.read_text()

start = text.find('@Composable\nprivate fun StartScreen(')
end = text.find('@Composable\nprivate fun ProgressChip', start)
if start < 0 or end < 0:
    raise SystemExit('home final patch failed: StartScreen bounds')

replacement = r'''@Composable
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
    // Keep the very first frame resource-free so startup remains as conservative
    // as the recovery build. Immediately after composition, display the user's
    // final approved pond background with the smaller bugs and flight trails.
    var finalHomeReady by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        delay(120)
        finalHomeReady = true
    }

    Surface(Modifier.fillMaxSize(), color = PondSky) {
        Box(Modifier.fillMaxSize()) {
            if (finalHomeReady) {
                Image(
                    painter = painterResource(R.drawable.ftf_home_screen_v2),
                    contentDescription = "Final approved Feed the Frog home background",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            } else {
                // Startup-safe first frame: no bitmap decode here.
                Box(Modifier.fillMaxSize().background(PondSky))
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 20.dp, vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Surface(
                    color = ShopPaper.copy(alpha = 0.88f),
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
                    colors = CardDefaults.cardColors(containerColor = ShopPaper.copy(alpha = 0.90f)),
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

'''

text = text[:start] + replacement + text[end:]
main_file.write_text(text)
print('restored final approved home background with startup-safe delayed bitmap decode')
