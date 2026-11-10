
from decimal import Decimal, ROUND_HALF_UP


def money(value):
    """Convert an amount into money with two decimal places."""
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def distribute_amount(total, flats, basis):
    """Divide an expense equally, by area, or by residents."""

    total = money(total)

    if not flats:
        raise ValueError("No eligible flats for allocation")

    if basis == "equal":
        weights = [Decimal("1") for flat in flats]

    elif basis == "area":
        weights = [
            Decimal(str(flat["super_builtup_sqft"]))
            for flat in flats
        ]

    elif basis == "residents":
        weights = [
            Decimal(str(flat["declared_residents"]))
            for flat in flats
        ]

    else:
        raise ValueError(f"Unknown allocation basis: {basis}")

    if any(weight < 0 for weight in weights):
        raise ValueError("Allocation weights cannot be negative")

    total_weight = sum(weights)

    if total_weight <= 0:
        raise ValueError("Total allocation weight must be positive")

    allocations = []
    allocated_so_far = Decimal("0.00")

    for index, flat in enumerate(flats):

        if index == len(flats) - 1:
            share = total - allocated_so_far
        else:
            share = money(
                total * weights[index] / total_weight
            )

        allocations.append({
            "flat_id": flat["flat_id"],
            "amount": share
        })

        allocated_so_far += share

    return allocations


def get_tower_flats(flats, tower_id):
    """Return flats belonging to one tower."""

    return [
        flat for flat in flats
        if flat["tower_id"] == tower_id
    ]


def get_lift_amc_flats(flats, tower_id):
    """Exclude ground-floor flats from lift AMC."""

    if not tower_id:
        raise ValueError("Lift AMC must have a tower_id")

    return [
        flat for flat in flats
        if flat["tower_id"] == tower_id
        and int(flat["floor"]) != 0
    ]


def allocate_expense(expense, flats, basis=None):
    """
    Expense allocation rules:

    SECURITY and HOUSEKEEPING:
        Funded from maintenance.

    LIFT_AMC:
        Equally divided among eligible flats in the tower.

    COMMON_ELECTRICITY and GENERATOR_DIESEL:
        Divided according to flat area.

    WATER_TANKER:
        Equally divided among eligible flats.
    """

    head = expense["head"].strip().upper()

    # Security and housekeeping are funded from maintenance.
    if head in ("SECURITY", "HOUSEKEEPING"):
        return []

    # Lift AMC: equal sharing, excluding ground floor.
    if head == "LIFT_AMC":

        tower_id = expense.get("tower_id", "").strip()

        eligible_flats = get_lift_amc_flats(
            flats,
            tower_id
        )

        return distribute_amount(
            expense["amount"],
            eligible_flats,
            "equal"
        )

    # Electricity and diesel: area-based sharing.
    if head in ("COMMON_ELECTRICITY", "GENERATOR_DIESEL"):

        tower_id = expense.get("tower_id", "").strip()

        if tower_id:
            eligible_flats = get_tower_flats(flats, tower_id)
        else:
            eligible_flats = flats

        return distribute_amount(
            expense["amount"],
            eligible_flats,
            "area"
        )

    # Water tanker: equal sharing.
    if head == "WATER_TANKER":

        return distribute_amount(
            expense["amount"],
            flats,
            "equal"
        )

    raise ValueError(f"Unknown expense head: {head}")
