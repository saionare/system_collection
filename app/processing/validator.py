import math
from typing import Any
class Validator:
    @staticmethod
    def validate(value: Any, obj: dict) -> tuple[bool, str | None]:
        typ=obj.get("type"); req=obj.get("requirements", {})
        if typ == "boolean":
            if type(value) is not bool: return False, "expected boolean"
            return True, None
        if typ == "integer":
            if type(value) is not int: return False, "expected integer"
            number=value
        elif typ == "float":
            if type(value) not in (int,float) or type(value) is bool: return False, "expected numeric value"
            number=float(value)
            if not math.isfinite(number): return False, "value must be finite"
        else: return False, "unsupported configured type"
        if "min" in req and number < req["min"]: return False, f"value {number} is below minimum {req['min']}"
        if "max" in req and number > req["max"]: return False, f"value {number} is above maximum {req['max']}"
        return True, None
