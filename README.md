# RunCat Neo -> macOS 15 Sequoia backport kit v4

**Target**: Apple M1 Max (`arm64`) on macOS 15.6.1 (Sequoia).  
**Status**: source patch prepared; **not** Xcode compiled or macOS 15 runtime-tested here.  
**Upstream source**: [runcat-dev/RunCatNeo](https://github.com/runcat-dev/RunCatNeo), pinned at commit `592cd606e735ce20da98d9ae62ecf1a2608635d7`. Upstream code is under Apache-2.0.

## v4: what the latest log showed

The GitHub Actions archive `logs_109648678794.zip`, dated 2026-10-27, shows `DataSource` and `Model` progressing beyond the earlier v3 actor-isolation errors. The build failed with exit code 65 during `UserInterface` compilation, emitting **35 compiler diagnostics across three source files**:

| Source file | Diagnostics | Underlying fix |
|---|---:|---|
| `CustomMetricsCardView.swift` | 10 | Materialize `snapshot.metrics.enumerated()` as an `Array` for `ForEach` on macOS 15 |
| `FrameImagesCollectionView.swift` | 23 | Materialize `store.frameImages.enumerated()` as an `Array` for `ForEach` on macOS 15 |
| `CustomRunnerEditorView.swift` | 2 | Add an explicit localized label to the cancellation button, replace macOS 26 `.confirm` button role with an ordinary button in `.confirmationAction` toolbar placement |

The `EnumeratedSequence` `RandomAccessCollection` conformance used by the original `ForEach` was introduced in macOS 26; wrapping the enumerated values in `Array(...)` avoids that dependency.

The log also contains `LLVM Profile Error: Failed to write file "default.profraw": Operation not permitted`. It appeared before the Swift compiler errors and **is not the direct cause of this build failure**.

## Changes retained from v1-v3

- Deployment target `macOS 26.0` -> `macOS 15.0` in Xcode project and Swift package.
- Remove unsupported `windowResizeAnchor` and `labelReservedIconWidth` SwiftUI modifiers.
- Replace macOS 26 drag/drop reorder APIs with macOS 15-compatible `draggable` and `dropDestination`.
- Replace 7 `Task.immediate` with `Task`, 8 `group.addImmediateTask` with `group.addTask`, and add 8 `await` actor crossings required by Swift 6.
- Change bundle identifier to `dev.local.RunCatNeoSequoia` for the personal build, avoiding conflicts with the official App Store app.

## How to rerun GitHub Actions

If you already installed **v3** in a GitHub repository, **only `port_sequoia.py` needs updating**. The build script and workflow YAML are unchanged from v3 and are included for convenience.

1. Download and unpack `RunCatNeo-macOS15-port-kit-v4.zip`.
2. In your existing GitHub Actions repository, replace the file `port_sequoia.py` at the repository root with the v4 copy; commit the change. Keep its original filename.
3. Navigate to **Actions -> Build RunCat Neo for macOS 15 (arm64) -> Run workflow**.
4. If successful, under **Artifacts**, download `RunCatNeo-Sequoia-macOS15-arm64` (which contains the app ZIP).
5. If unsuccessful, download `RunCatNeo-build-log`, or use the run's **Download log archive**. Upload the ZIP to the chat for the next diagnostic round.

You **do not** need to upload the full original RunCat Neo repository: the Actions workflow checks out the exact pinned upstream source at build time.

## Build directly on a macOS 26/Xcode 26.5+ machine (optional)

```bash
git clone https://github.com/runcat-dev/RunCatNeo.git
cd RunCatNeo
git checkout 592cd606e735ce20da98d9ae62ecf1a2608635d7
# Copy port_sequoia.py and build_sequoia.sh from the kit to this directory.
bash build_sequoia.sh
```

GitHub Actions uses a `macos-26` runner and Xcode 26.5 to build for the **older deployment target**. The destination M1 Max Mac itself does not need Xcode 26 or the App Store, but macOS 15 execution must be verified on that Mac.

## Included files

- `port_sequoia.py` — full v1-v4 compatibility edits; includes exact-match guards and supports re-running safely.
- `build_sequoia.sh` — build, ad-hoc sign, verify architecture and deployment target, then ZIP the app (requires macOS/Xcode).
- `.github/workflows/build-sequoia.yml` — GitHub Actions build and failure-log artifact upload.
- `test_patch.py` — optional local static fixture regression test (`python3 test_patch.py`, no Xcode needed).

## Verification and security

The patch passed Python syntax checking and a synthetic-source regression test covering all v1-v4 edits, safe reapplication, and unexpected-upstream-code rejection. **These checks do not prove that Swift compiles or that the app launches on macOS 15.6.1.** Additional errors might arise in the app target or at runtime.

Check the menu-bar animation, CPU load/speed updates, settings, memory monitoring, custom runners, launch-at-login, and sleep/wake on macOS 15.6.1. The finished `.app` will be **ad-hoc signed rather than Developer ID signed or notarized**. Corporate endpoint protection and Gatekeeper may block it; use your organization's approved verification and software-import procedures. App Store-linked donation/subscription features might not function in a self-built app.
