# Feed the Frog — Android Prototype v0.7

A self-contained Jetpack Compose Android game prototype.

## v0.7 UI polish + shop redesign
- Rebuilt the title screen with a cleaner game-logo panel, compact pond-progress card, and clearer Play/Sound controls.
- Reworked the in-game HUD into compact status chips for coins, dice, tongue reach, and total catches.
- Latest event and last-roll information are separated from the primary status bar.
- Rebuilt the bottom roll area around one large, obvious action button.
- Removed the old horizontally scrolling shop carousel.
- Shop now uses a vertical mobile layout that is easier to scan with one hand.
- Each upgrade card shows current value, next value, track progress, cost, and purchase state together.
- Die #1 and Die #2 remain fully independent upgrade tracks.
- Locked second die clearly explains that it starts at D3 and follows the full D3 → D20 progression.
- Bug Guide is now a dedicated shop section below upgrades instead of another card in the upgrade carousel.
- Locked bugs are visually distinct from unlocked bugs.
- Maxed upgrades receive a clear MAX state.
- Insufficient funds buttons show the required cost.

## Core loop
1. Start with a D3.
2. Roll to spawn bugs.
3. Bugs actively fly around the pond.
4. Drag each bug toward the frog.
5. The frog automatically snaps its tongue when the dragged bug enters the current catch radius.
6. Most bugs award coins; bees cost coins if eaten.
7. Feed every bug before rolling again.

## Upgrades
### Tongue Distance
48 → 66 → 84 → 102 → 120 → 138 → 156 dp.

Costs: 150, 350, 750, 1,500, 3,000, 6,000 coins.

### Die #1
D3 → D4 → D6 → D8 → D12 → D20.

Costs: 200, 500, 1,200, 3,000, 7,500 coins.

### Die #2
Unlock cost: 10,000 coins. The second die always begins at D3 and upgrades independently:
D3 → D4 → D6 → D8 → D12 → D20.

## Bugs
- Fly: +25 coins
- Mosquito: +15 coins
- Fast Fly: +35 coins
- Moth: +45 coins
- Bee: -40 coins
- Golden Fly: +100 coins

Unlocks: 0 / 8 / 18 / 35 / 55 / 80 successful catches.

## Audio
Includes 48 kHz mono OGG audio for looping swarm buzz, dice, grab, tongue snap, catches, golden catches, bee penalty, upgrades, and unlocks. Sound can be muted and the setting is saved.

## Open in Android Studio
Open the `FeedTheFrog` folder as a Gradle project and run the `app` configuration on an Android emulator or device.

## Build-ready update
- Gradle wrapper updated from 9.5.0 to 9.7.1.
- Gradle 9.7.1 checksum pinned in the wrapper configuration.
- Added `local.properties.example` for Android SDK configuration.
- Added `build-apk.sh` and `build-apk.bat` helpers.
- Added `BUILDING.md` with Android Studio and command-line build steps.

## v0.7.2 build pipeline
- App version bumped to 0.7.2 (versionCode 8).
- Added a GitHub Actions workflow that builds the debug APK on an internet-connected Android build runner.
- The workflow installs Android API 37 and the newest available Build-Tools 37.x.x, uses Java 21 and Gradle 9.7.1, then uploads `app-debug.apk` as an artifact.
- See `BUILD_ON_GITHUB.md` for the build steps.
