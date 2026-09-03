from __future__ import annotations

from typing import Any


def build_inventory_stock_metadata(item: Any) -> dict[str, str]:
    """Build stock metadata from an inventory item without legacy-module coupling."""
    return {
        "inventory_no": item.inventory_no or "",
        "computer_name": item.computer_name or "",
        "hostname": item.computer_name or "",
        "factory": item.factory.name if item.factory else "",
        "department": item.department or "",
        "hardware_type": item.hardware_type.name if item.hardware_type else "",
        "brand": item.brand.name if item.brand else "",
        "model": item.model.name if item.model else "",
        "serial_no": item.serial_no or "",
        "ifs_no": item.ifs_no or "",
        "ip_address": item.related_machine_no or "",
        "mac_address": item.machine_no or "",
        "responsible": (
            f"{item.responsible_user.first_name} {item.responsible_user.last_name}"
            if item.responsible_user
            else ""
        ),
    }
