from data.utils import *
from data.subdivisions.utils import *
import json
from data.subdivisions.scripts.merge import merge_matched_sub
import os
from localis.models import SubdivisionModel


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def resolve_unmatched_subs(
    unmatched_iso_subs: list[SubdivisionModel], submap: SubdivisionMap
) -> dict | None:
    with open(SUB_SRC_PATH / "resolution_map.json", "r+", encoding="utf-8") as f:
        # load existing mappings
        resolution_map: dict[str, dict[int, str | list[str]]] = json.load(f) or {}

        for num, iso_sub in enumerate(unmatched_iso_subs, start=1):
            # merge if the mapping has already be manually completed
            if iso_sub.iso_code in resolution_map:
                data: dict[int, str | list[str]] = resolution_map[iso_sub.iso_code]
                added: bool = data.get("added")
                if added:
                    iso_sub.aliases.extend(data.get("names", []))
                    submap.add(iso_sub)
                    continue

                mapped_sub = submap.get(data.get("hashid"))
                if mapped_sub:
                    mapped_names = data.get("names", [])
                    mapped_sub.aliases.extend(mapped_names)
                    merge_matched_sub(iso_sub, mapped_sub)
                    continue
                else:
                    print(f"Could not find subdivision with id: {data.get('id')}")

            admin_level = iso_sub.admin_level

            merge_data: dict[int | list[str] | bool | None] = {
                "id": None,
                "names": [],
                "added": False,
            }

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

                print(f"\nResolve subdivision ({num}/{len(unmatched_iso_subs)}):")
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

            # update mapping file
            resolution_map[iso_sub.iso_code] = merge_data
            f.seek(0)
            json.dump(resolution_map, f, indent=2)
            f.truncate()
            print()
