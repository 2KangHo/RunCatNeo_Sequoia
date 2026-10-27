#!/usr/bin/env python3
"""Backport RunCat Neo macOS 26-only UI and concurrency APIs to macOS 15.

Verified against upstream main tree SHA 592cd606e735ce20da98d9ae62ecf1a2608635d7.
Run from the repository root. No non-stdlib Python dependencies.
v2: replaces Task.immediate and TaskGroup.addImmediateTask (15 errors).
v3: adds actor hops to 8 state updates inside task-group children.
This is a source-compatibility attempt, NOT a tested macOS executable.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def replace_exact(relative, old, new, expected=1):
    target = ROOT / relative
    if not target.is_file():
        raise SystemExit(f"Missing upstream source: {relative}")
    text = target.read_text(encoding="utf-8")
    n = text.count(old)
    if n == 0 and new in text:
        print(f"[skip] already modified: {relative}")
        return
    if n != expected:
        raise SystemExit(f"Unexpected upstream version in {relative}: expected {expected} occurrence(s), found {n}")
    target.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[patch] {relative}: {n} replacement(s)")


def patch_sortable():
    path = "LocalPackage/Sources/UserInterface/Views/Settings/SortableViewModifier.swift"
    target = ROOT / path
    if not target.is_file():
        raise SystemExit(f"Missing upstream source: {path}")
    original = target.read_text(encoding="utf-8")
    if "// Backport: macOS 15 drag/drop handling" in original:
        print(f"[skip] already modified: {path}")
        return
    marker = "private struct SortableViewModifier<Item: Hashable & Identifiable>"
    if original.count(marker) != 1 or ".dropConfiguration { session in" not in original:
        raise SystemExit(f"Unexpected upstream SortableViewModifier: {path}")
    # Preserve original license header and imports; replace the implementation only.
    header = original[:original.index(marker)]
    new = '''// Backport: macOS 15 drag/drop handling.
// The original macOS 26 implementation uses DropConfiguration/DropSession.
// Older SwiftUI supports draggable + dropDestination with Transferable values.
private struct SortableViewModifier<Item: Hashable & Identifiable>: ViewModifier
where Item.ID: Sendable & Codable {
    var index: Int
    var item: Item
    @Binding var items: [Item]
    @Binding var draggingItem: Item?

    func body(content: Content) -> some View {
        content
            .draggable(DraggableItem(id: item.id)) {
                Color.clear.frame(width: 40, height: 40)
            }
            .dropDestination(for: DraggableItem.self) { dropped, _ in
                guard let payload = dropped.first,
                      let fromIndex = items.firstIndex(where: { $0.id == payload.id }),
                      fromIndex != index else {
                    return false
                }
                // SwiftUI's move(toOffset:) takes an insertion index; dropping
                // onto an item after the source needs an extra index offset.
                withAnimation(.bouncy) {
                    items.move(
                        fromOffsets: IndexSet(integer: fromIndex),
                        toOffset: index > fromIndex ? index + 1 : index
                    )
                }
                draggingItem = nil
                return true
            }
    }

    private struct DraggableItem: Codable, Transferable {
        var id: Item.ID

        static var transferRepresentation: some TransferRepresentation {
            CodableRepresentation(for: DraggableItem.self, contentType: .data)
        }
    }
}

extension View {
    func sortable<Item: Hashable & Identifiable>(
        index: Int,
        item: Item,
        items: Binding<[Item]>,
        draggingItem: Binding<Item?>
    ) -> some View where Item.ID: Sendable & Codable {
        modifier(SortableViewModifier(
            index: index,
            item: item,
            items: items,
            draggingItem: draggingItem
        ))
    }
}
'''
    target.write_text(header + new, encoding="utf-8")
    print(f"[patch] {path}: replaced macOS 26 drag-and-drop API")



def patch_immediate_tasks():
    """Replace the macOS 26-only Swift 6.2 task creation APIs.

    These stream subscriptions run from viewAppeared handlers. The non-immediate
    variants exist on macOS 15. They have slightly different scheduling order,
    so the resulting app still needs runtime testing on Sequoia.
    """
    stores = "LocalPackage/Sources/Model/Stores/"
    # (file name, Task.immediate count, group.addImmediateTask count)
    targets = [
        ("CustomMetricsSettings.swift", 1, 0),
        ("Dashboard.swift", 1, 0),
        ("DashboardMenu.swift", 1, 2),
        ("MetricsBar.swift", 1, 3),
        ("MetricsBarSettings.swift", 1, 0),
        ("MetricsSettings.swift", 1, 0),
        ("RunnerBar.swift", 1, 3),
    ]
    old_task = "task = Task.immediate { [weak self, appStateClient] in"
    new_task = "task = Task { [weak self, appStateClient] in"
    old_child = "group.addImmediateTask {"
    new_child = "group.addTask {"
    total = 0
    for filename, expected_tasks, expected_children in targets:
        rel = stores + filename
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"Missing upstream source: {rel}")
        source = path.read_text(encoding="utf-8")
        task_count = source.count(old_task)
        patched_task_count = source.count(new_task)
        child_count = source.count(old_child)
        patched_child_count = source.count(new_child)
        if (task_count + patched_task_count != expected_tasks or
                child_count + patched_child_count != expected_children):
            raise SystemExit(
                f"Unexpected upstream concurrency code in {rel}: "
                f"Task.immediate={task_count}, Task={patched_task_count}, "
                f"addImmediateTask={child_count}, addTask={patched_child_count}"
            )
        # Do not leave unrecognized overloads in the target file.
        if "Task.immediate" in source and task_count != source.count("Task.immediate"):
            raise SystemExit(f"Unknown Task.immediate call in {rel}")
        if "addImmediateTask" in source and child_count != source.count("addImmediateTask"):
            raise SystemExit(f"Unknown addImmediateTask call in {rel}")
        if task_count or child_count:
            patched = source.replace(old_task, new_task).replace(old_child, new_child)
            path.write_text(patched, encoding="utf-8")
            print(f"[patch] {rel}: Task {task_count}, child tasks {child_count}")
            total += task_count + child_count
        else:
            print(f"[skip] concurrency already modified: {rel}")
    print(f"Concurrency backport: {total} newly replaced call(s)")



def patch_main_actor_updates():
    """Backport Swift 6 main-actor isolation after replacing addImmediateTask.

    With the v2 addTask replacements, child closures are not MainActor-isolated;
    calls to @MainActor-isolated view-model methods must be explicit.
    Adding `await` performs the actor hop. Exact-match guards protect against
    silently patching different upstream versions. (8 errors in second log.)
    """
    base = "LocalPackage/Sources/Model/Stores/"
    fixes = {
        "DashboardMenu.swift": (
            "self?.updateCurrentRunner(from: value)",
            "self?.update(runnerBundleList: value)",
        ),
        "MetricsBar.swift": (
            "self?.updateMetrics(from: value)",
            "self?.updateMetricsBarConfiguration()",
        ),
        "RunnerBar.swift": (
            "self?.update(appearance: value)",
            "self?.update(runnerBundle: value)",
            "self?.update(runnerSpeed: value)",
        ),
    }
    # The MetricsBar configuration updater appears in two different children.
    expected_counts = {("MetricsBar.swift", "self?.updateMetricsBarConfiguration()"): 2}
    total = 0
    for filename, methods in fixes.items():
        for call in methods:
            expected = expected_counts.get((filename, call), 1)
            replace_exact(
                base + filename,
                "                            " + call,
                "                            await " + call,
                expected=expected,
            )
            total += expected
    print(f"Actor-isolation backport: {total} expected `await` call site(s)")


def main():
    if not (ROOT / "RunCatNeo.xcodeproj" / "project.pbxproj").is_file():
        sys.exit("Copy this script into the root of a RunCatNeo Git checkout first.")
    replace_exact(
        "RunCatNeo.xcodeproj/project.pbxproj",
        "MACOSX_DEPLOYMENT_TARGET = 26.0;",
        "MACOSX_DEPLOYMENT_TARGET = 15.0;",
        expected=2,
    )
    replace_exact(
        "LocalPackage/Package.swift",
        ".macOS(.v26),",
        ".macOS(.v15),",
    )
    replace_exact(
        "LocalPackage/Sources/UserInterface/Scenes/SettingsWindowScene.swift",
        "                .windowResizeAnchor(.topLeading)\n",
        "",
    )
    replace_exact(
        "LocalPackage/Sources/UserInterface/Views/Settings/DonationSettingsView.swift",
        "                .labelReservedIconWidth(32)\n",
        "",
    )
    patch_sortable()
    patch_immediate_tasks()
    patch_main_actor_updates()
    # This App Store product's original bundle ID must not be reused for a personal build.
    replace_exact(
        "RunCatNeo.xcodeproj/project.pbxproj",
        "PRODUCT_BUNDLE_IDENTIFIER = com.kyome.Neo.RunCat;",
        "PRODUCT_BUNDLE_IDENTIFIER = dev.local.RunCatNeoSequoia;",
        expected=2,
    )
    print("Port edits applied. Not yet compiled or verified on macOS 15.")


if __name__ == "__main__":
    main()
