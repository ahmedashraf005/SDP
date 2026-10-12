"""Registers every course module (Guide v2 section 3). Owner: Wahib."""
from .cmp305 import CMP305
from .calc1 import Calc1

COURSES = [CMP305(), Calc1()]


def by_id(course_id: str):
    return next((c for c in COURSES if c.course_id == course_id), None)
