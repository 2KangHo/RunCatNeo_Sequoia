#!/usr/bin/env python3
"""Backport selected RunCat Neo macOS 26-only APIs to macOS 15.

Verified against upstream main tree SHA 592cd606e735ce20da98d9ae62ecf1a2608635d7.
Run from the repository root. No non-stdlib Python dependencies.
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
    for store in (
        "CustomMetricsSettings",
        "Dashboard",
        "DashboardMenu",
        "MetricsBar",
        "MetricsBarSettings",
        "MetricsSettings",
        "RunnerBar",
    ):
        replace_exact(
            f"LocalPackage/Sources/Model/Stores/{store}.swift",
            "Task.immediate {",
            "Task {",
        )
    for store, count in (("DashboardMenu", 2), ("MetricsBar", 3), ("RunnerBar", 3)):
        # Unlike addImmediateTask, addTask does not inherit the caller's actor.
        replace_exact(
            f"LocalPackage/Sources/Model/Stores/{store}.swift",
            "group.addImmediateTask {",
            "group.addTask { @MainActor in",
            expected=count,
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
