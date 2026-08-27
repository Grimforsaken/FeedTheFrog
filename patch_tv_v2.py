#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_tv_v2.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
root = Path(__file__).resolve().parent
text = main_file.read_text()


def once(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'tv v2 patch failed: {label}')
    text = text.replace(old, new, 1)


once(
    'private const val TV_MODE_POND_LIFE = 1',
    'private const val TV_MODE_POND_LIFE = 1\nprivate const val TV_MODE_MEADOW = 2\nprivate const val TV_MODE_SKUNK = 3',
    'TV mode constants',
)
once(
    'prefs.getInt("tvMode", TV_MODE_COMMERCIAL).coerceIn(TV_MODE_COMMERCIAL, TV_MODE_POND_LIFE)',
    'prefs.getInt("tvMode", TV_MODE_COMMERCIAL).coerceIn(TV_MODE_COMMERCIAL, TV_MODE_SKUNK)',
    'saved TV range',
)
once(
    'onSelectTvMode(if (tvMode == TV_MODE_COMMERCIAL) TV_MODE_POND_LIFE else TV_MODE_COMMERCIAL)',
    '''onSelectTvMode(
                            when (tvMode) {
                                TV_MODE_COMMERCIAL -> TV_MODE_POND_LIFE
                                TV_MODE_POND_LIFE -> TV_MODE_MEADOW
                                TV_MODE_MEADOW -> TV_MODE_SKUNK
                                else -> TV_MODE_COMMERCIAL
                            }
                        )''',
    'TV selector cycle',
)
once(
    '''if (!subscriptionPurchased) "SUBSCRIPTION SERVICE"
                    else if (tvMode == TV_MODE_POND_LIFE) "TV: POND LIFE • 1/3"
                    else "TV: COMMERCIAL BREAK"''',
    '''if (!subscriptionPurchased) "SUBSCRIPTION SERVICE"
                    else when (tvMode) {
                        TV_MODE_POND_LIFE -> "TV: POND LIFE • 1/3"
                        TV_MODE_MEADOW -> "TV: MEADOW • 2/3"
                        TV_MODE_SKUNK -> "TV: SKUNK WALK • 3/3"
                        else -> "TV: COMMERCIAL BREAK"
                    }''',
    'TV selector labels',
)

pat = re.compile(r'@Composable\nprivate fun TvScreenLayer\(.*?\n\}\n\nprivate fun DrawScope\.drawPondBackground\(\)', re.S)
replacement = r'''@Composable
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

        val videoRes = if (!subscriptionPurchased) null else when (tvMode) {
            TV_MODE_POND_LIFE -> R.raw.subscription_pond
            TV_MODE_MEADOW -> R.raw.subscription_meadow
            TV_MODE_SKUNK -> R.raw.subscription_skunk
            else -> null
        }

        if (videoRes != null) {
            AndroidView(
                factory = { context -> VideoView(context) },
                update = { view ->
                    if (view.tag != videoRes) {
                        view.tag = videoRes
                        view.setVideoURI(Uri.parse("android.resource://${view.context.packageName}/$videoRes"))
                        view.setOnPreparedListener { player ->
                            player.isLooping = true
                            player.setVolume(0f, 0f)
                            view.start()
                        }
                    } else if (!view.isPlaying) {
                        view.start()
                    }
                },
                modifier = screenModifier
            )
        } else {
            Surface(modifier = screenModifier, color = Color(0xFF101010)) {
                Box(contentAlignment = Alignment.Center) {
                    Text("COMMERCIAL BREAK", color = Gold, fontWeight = FontWeight.Black, fontSize = 14.sp, textAlign = TextAlign.Center)
                }
            }
        }
    }
}

private fun DrawScope.drawPondBackground()'''
text, n = pat.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('tv v2 patch failed: TvScreenLayer block')

raw_dir = project_dir / 'app' / 'src' / 'main' / 'res' / 'raw'
raw_dir.mkdir(parents=True, exist_ok=True)
for src_name, dst_name in [
    ('subscription_2.mp4', 'subscription_meadow.mp4'),
    ('subscription_3.mp4', 'subscription_skunk.mp4'),
]:
    src = root / 'tv_assets' / src_name
    if not src.exists():
        raise SystemExit(f'missing TV video asset: {src}')
    shutil.copy2(src, raw_dir / dst_name)

# Every MP4 used inside the TV must be physically video-only, not merely muted
# at playback. Stream-copying keeps the picture unchanged while -an removes any
# audio stream and therefore removes its bytes from the packaged APK.
ffmpeg = shutil.which('ffmpeg')
ffprobe = shutil.which('ffprobe')
if not ffmpeg or not ffprobe:
    print('ffmpeg is not preinstalled; installing it for TV video sanitation')
    subprocess.run(['sudo', 'apt-get', 'update', '-qq'], check=True)
    subprocess.run(['sudo', 'apt-get', 'install', '-y', '-qq', 'ffmpeg'], check=True)
    ffmpeg = shutil.which('ffmpeg')
    ffprobe = shutil.which('ffprobe')
if not ffmpeg or not ffprobe:
    raise SystemExit('tv v2 patch failed: ffmpeg/ffprobe could not be installed')

for video in sorted(raw_dir.glob('*.mp4')):
    temp = video.with_name(video.stem + '.video-only.mp4')
    before = video.stat().st_size
    subprocess.run(
        [
            ffmpeg,
            '-y',
            '-v', 'error',
            '-i', str(video),
            '-map', '0:v:0',
            '-c:v', 'copy',
            '-an',
            '-map_metadata', '-1',
            '-movflags', '+faststart',
            str(temp),
        ],
        check=True,
    )
    temp.replace(video)

    probe = subprocess.run(
        [
            ffprobe,
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index',
            '-of', 'csv=p=0',
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if probe.stdout.strip():
        raise SystemExit(f'tv v2 patch failed: audio stream remains in {video.name}')

    after = video.stat().st_size
    print(f'video-only TV asset {video.name}: {before} -> {after} bytes')

main_file.write_text(text)
print('added subscription videos 2/3, four-state TV selector, and enforced video-only MP4 assets')
