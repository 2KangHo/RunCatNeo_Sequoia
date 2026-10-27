# RunCat Neo → macOS 15 Sequoia backport starter kit

This kit is **not a compiled app**. It changes selected source code and supplies an Xcode/macOS GitHub Actions build job. The result has **not** been compiled or tested on macOS 15.6.1. It was prepared against the upstream **main tree SHA `592cd606e735ce20da98d9ae62ecf1a2608635d7`** (Oct 2026). Apache-2.0 upstream license applies to RunCat Neo.

## Changes

- App and package minimum deployment target: macOS 26 → 15.
- Replace macOS 26-only `Task.immediate` / `addImmediateTask` with `Task` / `addTask`, preserving main-actor isolation. Tasks are scheduled normally rather than starting synchronously.
- Omit SwiftUI `windowResizeAnchor` (introduced macOS 26).
- Omit SwiftUI `labelReservedIconWidth` (introduced macOS 26).
- Rewrite custom-runner drag/drop reorder from new `DropConfiguration` APIs to macOS 15-compatible `draggable` / `dropDestination`. Drag reordering now happens on *drop*, not while hovering.
- Change bundle ID to `dev.local.RunCatNeoSequoia` to avoid conflicting with the official product.
- Keep original `windowResizeBehavior` and `defaultLaunchBehavior`, which are supported on macOS 15.

## Source setup

Use an internet-connected environment where GitHub source and Swift Package dependencies can be accessed.

```sh
git clone https://github.com/runcat-dev/RunCatNeo.git
cd RunCatNeo
git checkout 592cd606e735ce20da98d9ae62ecf1a2608635d7
```

Copy `port_sequoia.py` and `build_sequoia.sh` into the repository root. Then:

```sh
python3 port_sequoia.py
```

### Build on macOS 26 with Xcode 26.5+

```sh
bash ./build_sequoia.sh
```

The script creates `RunCatNeo-Sequoia-macOS15-arm64.zip` if compilation/signing succeeds. An Xcode 26.5 toolchain is needed to handle the upstream Swift 6.2 package manifests; **Xcode 26.5 generally requires a newer macOS than 15.6.1**. Building on a newer Mac or macOS CI runner and transferring the app to the M1 Max macOS 15 machine is the recommended approach.

### Build in GitHub Actions (no App Store)

1. Create a GitHub repository you control (it can be empty; no fork required). Add the two root scripts and `.github/workflows/build-sequoia.yml` from this kit, commit and push.
2. In Actions, enable workflows for this repository if needed. Run **Build RunCat Neo for macOS 15 (arm64)** via **Run workflow**. The job checks out the exact upstream commit and applies the patch automatically.
3. If the job succeeds, download `RunCatNeo-Sequoia-macOS15-arm64` under the run's **Artifacts** section. Inside is `RunCatNeo-Sequoia-macOS15-arm64.zip`.
4. Verify the SHA-256 checksum, review the code and executable trust/security state, and transfer through your organization's approved process. The app is ad-hoc signed, not Developer-ID signed or notarized; macOS Gatekeeper or organization controls may block it.

**No Apple Developer membership or App Store is needed to try a personal build.** GitHub Actions usage may be metered, depending on repository visibility and account plan. GitHub and Swift dependencies must be reachable by the build runner; the target corporate Mac itself does not need App Store access.

## Limitations / validation

- **No macOS compiler was available in this preparation environment**, so build success is not guaranteed. The build job may report additional SDK availability or Swift 6 strict-concurrency errors. Address these errors in the fork and rerun; do not treat the patch kit as a verified binary.
- Verify the compiled macOS deployment version is `15.0` and binary architecture `arm64` (the script prints both). Test on macOS 15.6.1 for menu-bar animation, CPU speed changes, custom runners, settings, launch-at-login, CPU/memory monitoring and Custom Metrics.
- The donation/subscription UI relies on App Store products and may not work correctly in a separately signed personal build. Do not use it for purchases.
- If running at macOS 15.6.1 is impossible after compiling, the problem may be an OS-26 symbol used at runtime or a dependency's compatibility bug. The macOS build machine alone cannot prove runtime compatibility.
- Avoid manually removing Gatekeeper protection for unknown or unaudited binaries; follow organizational app security policies.
