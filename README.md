# RunCat Neo -> macOS 15 Sequoia backport kit v3

**Status: source-level patch only; the finished macOS application has NOT been compiled or run-tested on macOS 15.6.1.** This kit provides a patch script and a GitHub Actions macOS build workflow. It targets M1 Max / Apple Silicon (`arm64`). The upstream RunCat Neo code is Apache-2.0 licensed.

Pinned upstream commit: `592cd606e735ce20da98d9ae62ecf1a2608635d7` in `runcat-dev/RunCatNeo`. Do not apply these exact-match patches to a newer upstream revision without reviewing differences.

## What v3 fixes from the second GitHub Actions log

On 2026-10-27, the second CI log failed in the `Model` target with eight Swift 6 actor-isolation diagnostics:

| Source | Number | Affected calls |
| --- | ---: | --- |
| `DashboardMenu.swift` | 2 | `updateCurrentRunner`, `update(runnerBundleList:)` |
| `MetricsBar.swift` | 3 | `updateMetrics`, `updateMetricsBarConfiguration` (twice) |
| `RunnerBar.swift` | 3 | `update(appearance:)`, `update(runnerBundle:)`, `update(runnerSpeed:)` |

The v2 patch replaced unavailable `group.addImmediateTask` with `group.addTask`. The resulting child tasks are not implicitly main-actor isolated; their calls to `@MainActor` view-model methods must cross actors. v3 adds the eight required `await` expressions. The Swift compiler explicitly suggested `await` in the uploaded log.

Example (within a group child closure):

```swift
// v2 - fails with: main actor-isolated instance method cannot be called from outside actor
self?.updateMetrics(from: value)
// v3 - crosses to MainActor explicitly
await self?.updateMetrics(from: value)
```

The log's `LLVM Profile Error: Failed to write file "default.profraw": Operation not permitted` appeared earlier, but the build terminated with exit code 65 for the eight Swift compiler errors. That profiling line is not addressed by this patch.

## Previous v1/v2 compatibility edits retained

- Set macOS deployment target to `15.0` in Xcode project and Swift package.
- Remove UI modifiers `windowResizeAnchor` and `labelReservedIconWidth` unavailable on macOS 15.
- Rewrite custom runner drag-and-drop ordering to use older SwiftUI `draggable` and `dropDestination` APIs. Reordering now completes on drop rather than while hovering.
- Replace 7 occurrences of `Task.immediate` with `Task`, and 8 of `group.addImmediateTask` with `group.addTask`.
- Use bundle identifier `dev.local.RunCatNeoSequoia` for the personal build so it does not conflict with the official App Store product.

## Re-run with your existing GitHub Actions repository

**You do not need to upload a full copy of the upstream project.** The workflow clones the pinned commit itself.

1. Extract this ZIP on your local computer.
2. Replace these files in your existing GitHub repository and commit the changes:
   - `port_sequoia.py`
   - `build_sequoia.sh`
   - `.github/workflows/build-sequoia.yml`
3. In GitHub: **Actions -> Build RunCat Neo for macOS 15 (arm64) -> Run workflow**.
4. On success, open the run and download the artifact `RunCatNeo-Sequoia-macOS15-arm64`. The artifact contains the app ZIP.
5. On failure, open the run, download `RunCatNeo-build-log`, or use **... -> Download log archive** if the artifact is absent, and attach the resulting ZIP in ChatGPT.

The build uses `macos-26` and Xcode 26.5 on GitHub-hosted runners to compile against an older macOS 15 deployment target, so the target M1 Max machine does not need Xcode 26 or the App Store. GitHub/Swift package dependencies need to be accessible by the runner, and GitHub Actions usage may be billed according to the repository and plan.

## Optional: build on an Xcode 26.5+ Mac

```bash
git clone https://github.com/runcat-dev/RunCatNeo.git
cd RunCatNeo
git checkout 592cd606e735ce20da98d9ae62ecf1a2608635d7
# Copy port_sequoia.py and build_sequoia.sh from this kit into the repository root.
bash build_sequoia.sh
```

The `build_sequoia.sh` script patches the checked-out source, invokes Xcode, signs the app ad hoc, verifies `arm64` and reports the minimum system version. It produces `RunCatNeo-Sequoia-macOS15-arm64.zip` only if successful.

## Limits and security notes

- The v3 patch script passed syntax checks and an isolated source-fixture test covering 15 concurrency API replacements, eight actor crossings, idempotence and unexpected-source rejection. **These tests do not constitute a successful Xcode build** or proof that the app runs on macOS 15.6.1. Further UI-stage diagnostics are possible.
- Test the generated app on macOS 15.6.1: menu bar rendering, runner speed, CPU/memory display, settings, custom runners, launch-at-login and wake-from-sleep.
- The personal build is **ad-hoc signed, not notarized or Developer-ID signed**. macOS Gatekeeper or company endpoint controls may prohibit execution. Follow company app-install/security policies; do not blindly bypass protective prompts.
- App Store purchase, donation and subscription flows may not function in a separately built app. Do not rely on them for financial transactions.
- The upstream project and all third-party Swift packages are downloaded during the GitHub Actions build. Use an appropriate approved external-network build environment for internal deployment.
