"""Calc 1: the guide's own example class (Guide v2 section 6), included because the required sibling-course
test imports it. Owner: the Calc 1 teammate; page_range, page_offset and the index are theirs to set."""
from courses.base import CourseModule


class Calc1(CourseModule):
    course_id = "calc1"
    book_title = "Stewart Calculus"
    keywords = ["antiderivative", "integration by parts", "substitution rule",
                "chain rule", "product rule", "quotient rule",
                "definite integral", "derivative of", "limit of"]
    trusted_domains = ["tutorial.math.lamar.edu"]
    claim_types = ["prose", "equation"]
    page_range = None                # set in step 2
    page_offset = 0                  # set in step 2
