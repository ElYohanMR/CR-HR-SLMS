"""Keep physical observations while an open cut holds a locker in maintenance."""


def physical_condition(locker):
    return locker.condition_after_cut if locker.condition_after_cut is not None else locker.condition


def set_physical_condition(locker, condition):
    if locker.condition_after_cut is not None:
        locker.condition_after_cut = condition
        locker.condition = "mantenimiento"
    else:
        locker.condition = condition
