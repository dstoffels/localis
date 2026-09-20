from data.utils import *
from data.subdivisions.subdivisions_utils import *
from data.logger import log
import json
from data.subdivisions.scripts.merge_subdivisions import merge_matched_sub
from localis.models import SubdivisionModel


def clear_terminal():
    print("\033c", end="")


def _apply_cached_resolution(
    iso_sub: SubdivisionModel,
    resolution_map: dict[str, dict[str, str | list[str] | bool | None]],
    submap: SubdivisionMap,
) -> bool:
    """Re-apply a previously recorded decision for iso_sub, if one exists. Returns True if applied."""
    data = resolution_map.get(iso_sub.iso_code)
    if not data:
        return False

    if data.get("added"):
        iso_sub.aliases.extend(data.get("names", []))
        submap.add(iso_sub)
        return True

    mapped_sub = submap.get(data.get("hashid"))
    if mapped_sub:
        mapped_sub.aliases.extend(data.get("names", []))
        merge_matched_sub(iso_sub, mapped_sub)
        return True

    log.writeline(
        f"stale hashid reference: {data.get('hashid')} (iso_code {iso_sub.iso_code}) not found in current subdivision map"
    )
    return False


def _resolve_interactively(
    iso_sub: SubdivisionModel,
    submap: SubdivisionMap,
    num: int,
    total: int,
) -> dict[str, str | list[str] | bool | None]:
    """Prompt a human to resolve one unmatched subdivision. Returns the decision to persist."""
    admin_level = iso_sub.admin_level
    merge_data: dict[str, list[str] | bool | None] = {"names": [], "added": False}

    # Main Menu Loop
    while True:
        clear_terminal()
        candidate_geo_subs = sorted(
            submap.filter(iso_sub.country.alpha2, admin_level),
            key=lambda x: x.name,
        )

        for i, geo_sub in enumerate(candidate_geo_subs):
            print(
                f"{i + 1}. {[geo_sub.name, *geo_sub.aliases]} ({geo_sub.geonames_code}) (Admin{geo_sub.admin_level})"
            )

        print(f"\nResolve subdivision ({num}/{total}):")
        print(
            [iso_sub.name, *iso_sub.aliases],
            f"({iso_sub.iso_code}) (Admin{iso_sub.admin_level})",
        )

        # A helper link to quickly google search the subdivision
        link = f"https://google.com/search?q={iso_sub.name} {iso_sub.country.name}".replace(
            " ", "+"
        )

        print(f"Select a candidate by number to merge with {iso_sub.name}.")
        print(f"Enter 'a' to add {iso_sub.name} as-is.")
        print(f"Enter 'e' to add names to {iso_sub.name}.")
        print(f"Enter 's' to swap to other admin level candidates")
        print(f"\033]8;;{link}\033\\SEARCH\033]8;;\033\\")
        choice = input()

        choice = choice.lower()
        if choice == "a":
            submap.add(iso_sub)
            merge_data["added"] = True
            break

        elif choice == "e":
            # Add Names Loop
            while True:
                new_name = input(f'Enter a new name or type "EXIT" to return: ')
                if new_name == "EXIT":
                    break
                iso_sub.aliases.append(new_name)
                merge_data["names"].append(new_name)
        elif choice == "s":
            if admin_level == 1:
                admin_level = 2
            else:
                admin_level = 1
        elif choice.isdigit() and 1 <= int(choice) <= len(candidate_geo_subs):
            selected_geo_sub = candidate_geo_subs[int(choice) - 1]
            merge_matched_sub(iso_sub, selected_geo_sub)
            merge_data["hashid"] = selected_geo_sub.hashid

            if admin_level != iso_sub.admin_level:
                submap.refresh()

            break
        else:
            print("Invalid input.\n")

    return merge_data


def resolve_unmatched_subs(
    unmatched_iso_subs: list[SubdivisionModel],
    submap: SubdivisionMap,
    interactive_mode: bool = False,
) -> list[SubdivisionModel]:
    orphaned: list[SubdivisionModel] = []

    with open(
        SUBDIVISIONS_RAW_PATH / "resolution_map.json", "r+", encoding="utf-8"
    ) as f:
        # load existing mappings
        resolution_map: dict[int, dict[str, str | list[str] | bool | None]] = (
            json.load(f) or {}
        )

        for num, iso_sub in enumerate(unmatched_iso_subs, start=1):
            if _apply_cached_resolution(iso_sub, resolution_map, submap):
                continue

            if not interactive_mode:
                orphaned.append(iso_sub)
                continue

            merge_data = _resolve_interactively(
                iso_sub, submap, num, len(unmatched_iso_subs)
            )

            # update mapping file
            resolution_map[iso_sub.iso_code] = merge_data
            f.seek(0)
            json.dump(resolution_map, f, indent=2)
            f.truncate()
            print()

    return orphaned
