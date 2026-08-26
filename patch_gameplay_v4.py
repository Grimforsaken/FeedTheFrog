#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_gameplay_v4.py <MainActivity.kt>')

path = Path(sys.argv[1])
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'v4 patch failed: {label}')
    text = text.replace(old, new, 1)

# Die #2 must be cheaper than the 1,000,000-coin Auto-Eat upgrade.
replace_once(
    'private const val SECOND_DIE_COST = 12_000_000',
    'private const val SECOND_DIE_COST = 500_000',
    'second die price',
)

# Put the tongue origin on the glossy frog's visible mouth instead of low/behind the sprite.
text = text.replace('boardSize.height * 0.665f', 'boardSize.height * 0.615f')
text = text.replace('size.height * 0.665f', 'size.height * 0.615f')

# Spawn each new swarm around the middle of the CRT screen.
old_spawn = '''                val mouth = mouthPosition()
                val reach = catchRadiusPx * 0.92f
                val x = mouth.x + (Random.nextFloat() - 0.5f) * reach * 1.45f
                val y = mouth.y - reach * (0.20f + Random.nextFloat() * 0.72f)
                onFlyMoved(
                    fly.id,
                    Offset(
                        x.coerceIn(28f, boardSize.width - 28f),
                        y.coerceIn(boardSize.height * 0.18f, boardSize.height * 0.64f)
                    )
                )'''
new_spawn = '''                val screenLeft = boardSize.width * 0.10f
                val screenRight = boardSize.width * 0.75f
                val screenTop = boardSize.height * 0.24f
                val screenBottom = boardSize.height * 0.54f
                val centerX = (screenLeft + screenRight) * 0.5f
                val centerY = (screenTop + screenBottom) * 0.5f
                val x = centerX + (Random.nextFloat() - 0.5f) * boardSize.width * 0.10f
                val y = centerY + (Random.nextFloat() - 0.5f) * boardSize.height * 0.06f
                onFlyMoved(
                    fly.id,
                    Offset(
                        x.coerceIn(screenLeft, screenRight),
                        y.coerceIn(screenTop, screenBottom)
                    )
                )'''
replace_once(old_spawn, new_spawn, 'center-screen swarm spawn')

# Make flies travel across the whole CRT picture instead of orbiting one tiny spot.
old_roam = '''                val mouth = mouthPosition()
                val currentDistance = distance(fly.position, mouth)
                if (currentDistance > catchRadiusPx * 0.94f) {
                    val pull = 0.012f
                    dx += (mouth.x - fly.position.x) * pull
                    dy += (mouth.y - fly.position.y) * pull
                }

                val margin = 26f
                val newX = (fly.position.x + dx).coerceIn(margin, boardSize.width - margin)
                val newY = (fly.position.y + dy).coerceIn(margin, boardSize.height * 0.64f)'''
new_roam = '''                val screenLeft = boardSize.width * 0.10f
                val screenRight = boardSize.width * 0.75f
                val screenTop = boardSize.height * 0.24f
                val screenBottom = boardSize.height * 0.56f

                // A slow moving target carries each bug across the entire TV picture,
                // while the type-specific dx/dy above keeps the small buzzing motion.
                val roamX = screenLeft +
                    ((sin(phase * 0.19f + fly.buzzSeed * 0.43f) + 1f) * 0.5f) *
                    (screenRight - screenLeft)
                val roamY = screenTop +
                    ((cos(phase * 0.15f + fly.buzzSeed * 0.71f) + 1f) * 0.5f) *
                    (screenBottom - screenTop)
                dx += (roamX - fly.position.x) * 0.055f
                dy += (roamY - fly.position.y) * 0.055f

                val newX = (fly.position.x + dx).coerceIn(screenLeft, screenRight)
                val newY = (fly.position.y + dy).coerceIn(screenTop, screenBottom)'''
replace_once(old_roam, new_roam, 'full-screen fly roaming')

# The Canvas contains the animated tongue. Put the frog image beneath that Canvas so
# the tongue visibly begins at the mouth instead of disappearing behind the frog art.
frog_layer = '''

        val frogWidth = maxWidth * 0.36f
        val frogBob = (kotlin.math.sin(buzzPhase * 0.55f) * 2.0f).dp
        Image(
            painter = painterResource(R.drawable.ftf_frog),
            contentDescription = "Feed the Frog",
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = maxHeight * 0.57f + frogBob)
                .width(frogWidth)
        )
'''
if frog_layer not in text:
    raise SystemExit('v4 patch failed: glossy frog layer')
text = text.replace(frog_layer, '', 1)

canvas_anchor = '''        TvScreenLayer(
            subscriptionPurchased = subscriptionPurchased,
            tvMode = tvMode,
            modifier = Modifier.fillMaxSize()
        )

        Canvas('''
canvas_with_frog = '''        TvScreenLayer(
            subscriptionPurchased = subscriptionPurchased,
            tvMode = tvMode,
            modifier = Modifier.fillMaxSize()
        )
''' + frog_layer + '''
        Canvas('''
replace_once(canvas_anchor, canvas_with_frog, 'frog below tongue canvas')

path.write_text(text)
print('patched full-screen fly roaming, center spawn, mouth-origin tongue, and cheaper second die')
